"""Decision pipeline (the Engine).

Each operation: ContextBuilder -> IntelligenceLayer -> (validated output) -> persist.
Company/Role understanding -> Candidate understanding -> Evidence -> Assessment -> Matching
-> Top 3 -> Confrontation -> Recommendation.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.engine.context_builder import ContextBuilder
from app.engine.registry import current, new_version, to_dict
from app.intelligence import contracts as c
from app.intelligence.heuristic import IMPORTANCE_FR
from app.intelligence.interface import get_intelligence


def _producer(intel) -> str:
    return getattr(intel, "last_producer", None) or intel.name


def _require_sm(role: c.RoleView) -> None:
    if role.success_model is None:
        raise HTTPException(409, "Ce poste n'a pas encore de Success Model : générez-le d'abord.")


def _active_candidate_ids(db: Session) -> list[uuid.UUID]:
    return list(db.scalars(select(m.Candidate.id).where(m.Candidate.status == "active")))


def _save_evidence(db: Session, candidate_id, drafts: list[c.EvidenceDraft], role_id=None,
                   response_id=None) -> list[m.Evidence]:
    rows = []
    for d in drafts:
        row = m.Evidence(candidate_id=candidate_id, role_id=role_id, subject_type=d.subject_type,
                         subject_key=d.subject_key, claim=d.claim, evidence=d.evidence,
                         source=m.EvidenceSource(d.source), epistemic_status=m.EpistemicStatus(d.epistemic_status),
                         confidence=d.confidence, polarity=d.polarity, assessment_response_id=response_id)
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


# =========================================================================== role
def generate_success_model(db: Session, role_id) -> m.SuccessModel:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = db.get(m.Role, role_id)
    conv = db.scalars(select(m.Conversation).where(m.Conversation.role_id == role_id)
                      .order_by(m.Conversation.created_at.desc())).first()
    ctx = c.SuccessModelContext(company=cb.company(role.company_id), role=cb.role(role_id),
                                conversation_excerpt=cb.history(conv.id) if conv else [])
    draft = intel.build_success_model(ctx)
    return new_version(db, m.SuccessModel, role_id, draft.model_dump(mode="json"), _producer(intel))


# =========================================================================== candidate
def understand_candidate(db: Session, candidate_id) -> dict:
    cb, intel = ContextBuilder(db), get_intelligence()
    vocab = []
    for sm in db.scalars(select(m.SuccessModel)):
        vocab += [c.CapabilitySpec.model_validate(x) for x in sm.critical_capabilities]
    vocab = list({v.key: v for v in vocab}.values())
    out = intel.understand_candidate(c.CandidateUnderstandingContext(
        candidate=cb.candidate(candidate_id), capability_vocabulary=vocab))
    for cap in out.capabilities:
        row = db.scalars(select(m.Capability).where(m.Capability.candidate_id == candidate_id,
                                                    m.Capability.key == cap.key)).first()
        if row is None:
            db.add(m.Capability(candidate_id=candidate_id, key=cap.key, name=cap.name, level=cap.level,
                                status=m.EpistemicStatus(cap.status), confidence=cap.confidence,
                                source=m.EvidenceSource(cap.source)))
    rows = _save_evidence(db, candidate_id, out.evidence)
    patch = out.identity_patch.model_dump(exclude_none=True)
    if patch:
        new_version(db, m.ProfessionalIdentity, candidate_id, patch, _producer(intel), merge_lists=True)
    return {"capabilities_added": len(out.capabilities), "evidence_added": [str(r.id) for r in rows],
            "produced_by": _producer(intel)}


# =========================================================================== assessment
def next_assessment(db: Session, role_id, candidate_id) -> m.AssessmentRequest:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = cb.role(role_id)
    _require_sm(role)
    prev = [to_dict(x) for x in db.scalars(select(m.AssessmentRequest).where(
        m.AssessmentRequest.role_id == role_id, m.AssessmentRequest.candidate_id == candidate_id))]
    plan = intel.next_assessment(c.AssessmentContext(role=role, candidate=cb.candidate(candidate_id, role),
                                                     previous_questions=prev))
    req = m.AssessmentRequest(role_id=role_id, candidate_id=candidate_id, produced_by=_producer(intel),
                              **plan.model_dump())
    db.add(req)
    db.flush()
    return req


def submit_response(db: Session, request_id, response: str) -> m.AssessmentResponse:
    cb, intel = ContextBuilder(db), get_intelligence()
    req = db.get(m.AssessmentRequest, request_id)
    if req is None:
        raise HTTPException(404, "assessment request not found")
    if req.status != m.AssessmentStatus.pending:
        raise HTTPException(409, "assessment already answered")
    role = cb.role(req.role_id)
    interp = intel.interpret_response(c.ResponseContext(
        role=role, candidate=cb.candidate(req.candidate_id, role), request=to_dict(req), response=response))
    resp = m.AssessmentResponse(assessment_request_id=req.id, candidate_id=req.candidate_id, response=response,
                                observed_behaviors=interp.observed_behaviors, confidence=interp.confidence,
                                produced_by=_producer(intel))
    db.add(resp)
    db.flush()
    rows = _save_evidence(db, req.candidate_id, interp.evidence, role_id=req.role_id, response_id=resp.id)
    resp.evidence = [{"evidence_id": str(r.id), "claim": r.claim, "status": r.epistemic_status.value,
                      "confidence": r.confidence, "polarity": r.polarity} for r in rows]
    req.status = m.AssessmentStatus.evaluated
    db.flush()
    return resp


# =========================================================================== matching
def run_matching(db: Session, role_id, candidate_ids: list | None = None) -> list[m.Match]:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = cb.role(role_id)
    _require_sm(role)
    company = cb.company(db.get(m.Role, role_id).company_id)
    out = []
    for cid in candidate_ids or _active_candidate_ids(db):
        analysis = intel.match(c.MatchContext(company=company, role=role, candidate=cb.candidate(cid, role)))
        ev_by_id = {str(e.id): e for e in db.scalars(select(m.Evidence).where(m.Evidence.candidate_id == cid))}
        data = analysis.model_dump(mode="json")
        ev_ids = data.pop("evidence_ids")
        data["evidence"] = [{"evidence_id": i, "claim": ev_by_id[i].claim, "confidence": ev_by_id[i].confidence,
                             "status": ev_by_id[i].epistemic_status.value} for i in ev_ids if i in ev_by_id]
        row = db.scalars(select(m.Match).where(m.Match.role_id == role_id, m.Match.candidate_id == cid)).first()
        if row is None:
            row = m.Match(role_id=role_id, candidate_id=cid)
            db.add(row)
        for k, v in data.items():
            setattr(row, k, v)
        row.success_model_version = role.success_model.version
        row.produced_by = _producer(intel)
        out.append(row)
    db.flush()
    return out


def build_shortlist(db: Session, role_id, k: int = 3) -> dict:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = cb.role(role_id)
    _require_sm(role)
    if not db.scalars(select(m.Match.id).where(m.Match.role_id == role_id)).first():
        run_matching(db, role_id)
    matches = cb.match_dicts(role_id)
    out = intel.shortlist(c.ShortlistContext(role=role, matches=matches, k=k))
    by_cid = {str(x.candidate_id): x for x in db.scalars(select(m.Match).where(m.Match.role_id == role_id))}
    for x in by_cid.values():
        x.shortlist_rank, x.shortlist_reason = None, None
    for e in out.shortlist:
        by_cid[e.candidate_id].shortlist_rank = e.rank
        by_cid[e.candidate_id].shortlist_reason = e.reason
    db.flush()
    return {"role_id": str(role_id), "summary": out.summary,
            "shortlist": [e.model_dump() | {"full_name": next(mm["full_name"] for mm in matches
                                                             if mm["candidate_id"] == e.candidate_id)}
                          for e in out.shortlist],
            "excluded": out.excluded, "produced_by": _producer(intel)}


def current_shortlist_ids(db: Session, role_id) -> list[uuid.UUID]:
    return list(db.scalars(select(m.Match.candidate_id).where(
        m.Match.role_id == role_id, m.Match.shortlist_rank.is_not(None)).order_by(m.Match.shortlist_rank)))


# =========================================================================== confrontation
def confront(db: Session, role_id, decision_question: str, candidate_ids: list | None = None) -> m.Confrontation:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = cb.role(role_id)
    _require_sm(role)
    ids = candidate_ids or current_shortlist_ids(db, role_id)
    if not ids:
        build_shortlist(db, role_id)
        ids = current_shortlist_ids(db, role_id)
    if len(ids) < 2:
        raise HTTPException(409, "Il faut au moins deux candidats pour une confrontation.")
    out = intel.confront(c.ConfrontationContext(
        company=cb.company(db.get(m.Role, role_id).company_id), role=role, decision_question=decision_question,
        candidates=[cb.candidate(i, role) for i in ids], matches=cb.match_dicts(role_id, ids)))
    conf = m.Confrontation(
        role_id=role_id, decision_question=decision_question, candidate_ids=[str(i) for i in ids],
        comparison_dimensions=out.comparison_dimensions, profiles=[p.model_dump() for p in out.profiles],
        tradeoffs=[t.model_dump() for t in out.tradeoffs],
        winner_candidate_id=uuid.UUID(out.winner_candidate_id) if out.winner_candidate_id else None,
        reasoning=out.reasoning, uncertainties=out.uncertainties, produced_by=_producer(intel))
    conf.items = [m.ConfrontationItem(candidate_id=uuid.UUID(it.candidate_id), dimension=it.dimension,
                                      assessment=it.assessment, evidence=it.evidence, strength=it.strength,
                                      risk=it.risk, uncertainty=it.uncertainty, level=it.level)
                  for it in out.items]
    db.add(conf)
    db.flush()
    return conf


# =========================================================================== recommendation
def recommend(db: Session, role_id, confrontation_id=None) -> m.Recommendation:
    cb, intel = ContextBuilder(db), get_intelligence()
    role = cb.role(role_id)
    _require_sm(role)
    conf = db.get(m.Confrontation, confrontation_id) if confrontation_id else db.scalars(
        select(m.Confrontation).where(m.Confrontation.role_id == role_id)
        .order_by(m.Confrontation.created_at.desc())).first()
    if conf is None:
        conf = confront(db, role_id, "Qui devons-nous recruter pour ce poste ?")
    ids = [uuid.UUID(i) for i in conf.candidate_ids]
    out = intel.recommend(c.RecommendationContext(
        role=role, confrontation=to_dict(conf), matches=cb.match_dicts(role_id, ids),
        candidates=[cb.candidate(i, role) for i in ids]))
    rec = m.Recommendation(
        role_id=role_id, confrontation_id=conf.id,
        recommended_candidate_id=uuid.UUID(out.recommended_candidate_id) if out.recommended_candidate_id else None,
        reasoning_summary=out.reasoning_summary, key_evidence=out.key_evidence, tradeoffs=out.tradeoffs,
        uncertainties=out.uncertainties, alternatives=[a.model_dump() for a in out.alternatives],
        next_steps=out.next_steps, confidence=out.confidence, produced_by=_producer(intel))
    db.add(rec)
    db.flush()
    return rec


# =========================================================================== conversations
def _post(db: Session, conv: m.Conversation, sender: str, content: str, meta: dict | None = None) -> m.Message:
    msg = m.Message(conversation_id=conv.id, sender=sender, content=content, meta=meta or {})
    db.add(msg)
    db.flush()
    return msg


def employer_message(db: Session, conv: m.Conversation, content: str) -> dict:
    cb, intel = ContextBuilder(db), get_intelligence()
    user_msg = _post(db, conv, "user", content)
    company = cb.company(conv.company_id)
    role = cb.role(conv.role_id) if conv.role_id else None
    ctx = c.EmployerConversationContext(
        company=company, role=role, history=cb.history(conv.id), user_message=content,
        last_asked_field=conv.state.get("asked_field"),
        missing_fields=cb.missing_company_role_fields(company, role))
    turn = intel.employer_turn(ctx)
    producer = _producer(intel)
    updates, artifacts = [], []
    cpatch = turn.company_identity_patch.model_dump(exclude_none=True)
    if cpatch:
        new_version(db, m.CompanyIdentity, conv.company_id, cpatch, producer, merge_lists=True)
        updates.append({"entity": "company_identity", "fields": sorted(cpatch)})
    rpatch = turn.role_identity_patch.model_dump(exclude_none=True)
    if rpatch and conv.role_id:
        new_version(db, m.RoleIdentity, conv.role_id, rpatch, producer, merge_lists=True)
        updates.append({"entity": "role_identity", "fields": sorted(rpatch)})
    reply = turn.reply

    # Intent dispatch: the conversation is the primary interface to the whole pipeline.
    if turn.intent != "inform" and turn.intent != "smalltalk" and conv.role_id:
        rid = conv.role_id
        if turn.intent == "request_success_model":
            sm = generate_success_model(db, rid)
            artifacts.append({"type": "success_model", "id": str(sm.id), "version": sm.version})
            reply = ("Voici le modèle de réussite du poste : "
                     + ", ".join(f"{x['name']} ({IMPORTANCE_FR[x['importance']]})" for x in sm.critical_capabilities) + ".")
        elif turn.intent == "request_matching":
            ms = run_matching(db, rid)
            artifacts += [{"type": "match", "id": str(x.id)} for x in ms]
            reply = f"J'ai analysé {len(ms)} candidats au regard du modèle de réussite."
        elif turn.intent == "request_shortlist":
            sl = build_shortlist(db, rid)
            artifacts.append({"type": "shortlist", "role_id": str(rid)})
            reply = sl["summary"] + "\n" + "\n".join(f"{e['rank']}. {e['reason']}" for e in sl["shortlist"])
        elif turn.intent == "request_confrontation":
            cf = confront(db, rid, content)
            artifacts.append({"type": "confrontation", "id": str(cf.id)})
            reply = "\n".join(p["headline"] for p in cf.profiles) + "\n\n" + cf.reasoning
        elif turn.intent == "request_recommendation":
            rec = recommend(db, rid)
            artifacts.append({"type": "recommendation", "id": str(rec.id)})
            reply = rec.reasoning_summary
    conv.state = {**conv.state, "asked_field": turn.asked_field}
    assistant = _post(db, conv, "assistant", reply, {"intent": turn.intent, "updates": updates,
                                                     "artifacts": artifacts, "produced_by": producer,
                                                     "asked_field": turn.asked_field})
    return {"user_message": user_msg, "assistant_message": assistant, "intent": turn.intent,
            "updates": updates, "artifacts": artifacts}


def candidate_message(db: Session, conv: m.Conversation, content: str) -> dict:
    cb, intel = ContextBuilder(db), get_intelligence()
    user_msg = _post(db, conv, "user", content)
    cand = cb.candidate(conv.candidate_id)
    turn = intel.candidate_turn(c.CandidateConversationContext(
        candidate=cand, history=cb.history(conv.id), user_message=content,
        last_asked_field=conv.state.get("asked_field"), missing_fields=cb.missing_candidate_fields(cand)))
    producer = _producer(intel)
    updates, artifacts = [], []
    patch = turn.professional_identity_patch.model_dump(exclude_none=True)
    if patch:
        new_version(db, m.ProfessionalIdentity, conv.candidate_id, patch, producer, merge_lists=True)
        updates.append({"entity": "professional_identity", "fields": sorted(patch)})
        # What the candidate says about themself is kept as self-declared, never as fact.
        if patch.get("strengths"):
            from app.intelligence.heuristic import detect_capabilities
            _save_evidence(db, conv.candidate_id, [c.EvidenceDraft(
                subject_type="capability", subject_key=(detect_capabilities(s) or [None])[0], claim=s, evidence=f"Déclaré en conversation : « {s} »",
                source="self_declared", epistemic_status="hypothesis", confidence=0.3) for s in patch["strengths"]])
    if turn.intent == "request_opportunities":
        artifacts.append({"type": "opportunities", "candidate_id": str(conv.candidate_id)})
    conv.state = {**conv.state, "asked_field": turn.asked_field}
    assistant = _post(db, conv, "assistant", turn.reply, {"intent": turn.intent, "updates": updates,
                                                          "artifacts": artifacts, "produced_by": producer})
    return {"user_message": user_msg, "assistant_message": assistant, "intent": turn.intent,
            "updates": updates, "artifacts": artifacts}
