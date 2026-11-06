"""Conversation flows: the chat is the product.

Each turn returns {user_message, assistant_message, intent, updates, artifacts, cards, flow_state}.
Cards are attached to the assistant message (meta["cards"]) and answered through handle_action.

Employer flow:  discovery -> missions card -> role summary card -> search (success model, matching, top 3)
                -> candidate cards + "Que souhaitez-vous faire maintenant ?" -> confrontation -> recommendation.
Candidate flow: profile -> sources card (CV / LinkedIn / portfolio, optional) -> offer cards pushed by
                employer searches -> "Ça m'intéresse" -> adaptive assessment, one question at a time.
Humans decide: Passer / Entretien / Hire only record the employer's decision.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app import models as m
from app.engine import cards as k
from app.engine import pipeline as p
from app.engine.context_builder import ContextBuilder
from app.engine.registry import current, new_version
from app.intelligence import contracts as c
from app.intelligence.interface import get_intelligence

ASSESSMENT_QUESTIONS = 2

OPENERS = {
    "employer": "Bonjour, je suis JobMate. Décrivez-moi votre besoin avec vos mots : le poste, le contexte, "
                "l'urgence. Je m'occupe du reste.",
    "candidate": "Bonjour, je suis JobMate. Dites-moi ce que vous recherchez : le type de poste, le secteur, "
                 "la ville. Je construirai votre profil au fil de la conversation.",
}


def _post(db: Session, conv: m.Conversation, sender: str, content: str, meta: dict | None = None) -> m.Message:
    return p._post(db, conv, sender, content, meta)


def _set_state(conv: m.Conversation, **kw) -> None:
    conv.state = {**(conv.state or {}), **kw}
    flag_modified(conv, "state")


def _turn(user_msg, assistant, intent, updates=None, artifacts=None, conv=None) -> dict:
    return {"user_message": user_msg, "assistant_message": assistant, "intent": intent,
            "updates": updates or [], "artifacts": artifacts or [],
            "cards": (assistant.meta or {}).get("cards", []),
            "flow_state": (conv.state or {}).get("flow") if conv else None}


def _assistant(db, conv, text, cards=None, **meta) -> m.Message:
    return _post(db, conv, "assistant", text, {**meta, "cards": cards or []})


def find_card(db: Session, conv: m.Conversation, card_id: str) -> tuple[m.Message, dict]:
    for msg in db.scalars(select(m.Message).where(m.Message.conversation_id == conv.id,
                                                  m.Message.sender == "assistant")):
        for cd in (msg.meta or {}).get("cards", []):
            if cd["id"] == card_id:
                return msg, cd
    raise HTTPException(404, "card not found")


def close_card(msg: m.Message, card_id: str, result: dict | None = None) -> None:
    meta = dict(msg.meta)
    meta["cards"] = [cd | {"status": "done", "result": result or {}} if cd["id"] == card_id else cd
                     for cd in meta.get("cards", [])]
    msg.meta = meta
    flag_modified(msg, "meta")


# =========================================================================== conversation start
def start_conversation(db: Session, user: m.User, kind: str, company_id=None, role_id=None,
                       title: str | None = None) -> m.Conversation:
    conv = m.Conversation(user_id=user.id, kind=m.ConversationKind(kind), title=title)
    if kind == "employer":
        conv.company_id = company_id
        if role_id is None:
            # "Nouveau recrutement": every employer conversation works on its own (draft) role.
            role = m.Role(company_id=company_id, title="Nouveau recrutement", status="draft")
            db.add(role)
            db.flush()
            role_id = role.id
        conv.role_id = role_id
        conv.state = {"flow": "discovery"}
    else:
        conv.candidate_id = db.scalars(select(m.Candidate.id).where(m.Candidate.user_id == user.id)).first()
        conv.state = {"flow": "profile", "asked_field": "candidate.career_direction"}
    db.add(conv)
    db.flush()
    _assistant(db, conv, OPENERS[kind], intent="opening", asked_field=conv.state.get("asked_field"))
    return conv


# =========================================================================== employer
def _apply_role_basics(db: Session, conv: m.Conversation, turn: c.EmployerTurnOutput) -> list[str]:
    changed = []
    role = db.get(m.Role, conv.role_id)
    for f, v in turn.role_basics.model_dump(exclude_none=True).items():
        if v and getattr(role, f) != v:
            setattr(role, f, v)
            changed.append(f)
    if "title" in changed and not conv.title:
        conv.title = role.title
    company = db.get(m.Company, conv.company_id)
    for f, v in turn.company_basics.model_dump(exclude_none=True).items():
        if v and (f != "name" or company.name == DEFAULT_COMPANY_NAME):
            setattr(company, f, v)
    return changed


DEFAULT_COMPANY_NAME = "Mon entreprise"


def employer_message(db: Session, conv: m.Conversation, content: str) -> dict:
    cb, intel = ContextBuilder(db), get_intelligence()
    user_msg = _post(db, conv, "user", content)
    company, role = cb.company(conv.company_id), cb.role(conv.role_id)
    turn = intel.employer_turn(c.EmployerConversationContext(
        company=company, role=role, history=cb.history(conv.id), user_message=content,
        last_asked_field=conv.state.get("asked_field"), missing_fields=cb.missing_company_role_fields(company, role)))
    producer = p._producer(intel)
    updates = []
    basics = _apply_role_basics(db, conv, turn)
    if basics:
        updates.append({"entity": "role", "fields": basics})
    cpatch = turn.company_identity_patch.model_dump(exclude_none=True)
    if cpatch:
        new_version(db, m.CompanyIdentity, conv.company_id, cpatch, producer, merge_lists=True)
        updates.append({"entity": "company_identity", "fields": sorted(cpatch)})
    rpatch = turn.role_identity_patch.model_dump(exclude_none=True)
    if rpatch:
        new_version(db, m.RoleIdentity, conv.role_id, rpatch, producer, merge_lists=True)
        updates.append({"entity": "role_identity", "fields": sorted(rpatch)})
    _set_state(conv, asked_field=turn.asked_field)

    if turn.intent not in ("inform", "smalltalk"):
        return _employer_intent(db, conv, user_msg, turn.intent, content, updates)

    cards, flow = [], conv.state.get("flow", "discovery")
    role_row = db.get(m.Role, conv.role_id)
    ident = current(db, m.RoleIdentity, conv.role_id)
    has_missions = bool(ident and ident.responsibilities)
    searched = flow in ("results", "confrontation", "recommendation")
    if turn.mission_question and turn.mission_options and not has_missions:
        cards.append(k.missions_card(turn.mission_question, turn.mission_options))
        flow = "missions"
    elif has_missions and (turn.ready_for_search or cb.role_ready(cb.role(conv.role_id))) and \
            (not searched or updates):
        cards.append(k.role_summary_card(db, role_row))
        flow = "role_summary"
    _set_state(conv, flow=flow)
    assistant = _assistant(db, conv, turn.reply, cards, intent=turn.intent, updates=updates,
                           produced_by=producer, asked_field=turn.asked_field)
    return _turn(user_msg, assistant, turn.intent, updates, conv=conv)


def _employer_intent(db, conv, user_msg, intent, content, updates) -> dict:
    rid = conv.role_id
    cb = ContextBuilder(db)
    if cb.role(rid).success_model is None and intent != "request_success_model":
        assistant = _assistant(db, conv, "Je dois d'abord lancer la recherche sur ce poste. Validez le récapitulatif "
                                         "du poste et je vous présenterai les meilleurs profils.", intent=intent)
        return _turn(user_msg, assistant, intent, updates, conv=conv)
    artifacts, cards = [], []
    if intent == "request_success_model":
        sm = p.generate_success_model(db, rid)
        artifacts.append({"type": "success_model", "id": str(sm.id), "version": sm.version})
        cards.append(k.success_model_card(sm))
        text = "Voici ce qui fera réussir la personne dans ce poste."
    elif intent in ("request_matching", "request_shortlist"):
        return _search(db, conv, user_msg, intent)
    elif intent == "request_confrontation":
        cf = p.confront(db, rid, content)
        artifacts.append({"type": "confrontation", "id": str(cf.id)})
        cards.append(k.confrontation_card(db, cf))
        text = "Voici la confrontation des finalistes."
        _set_state(conv, flow="confrontation")
    else:  # request_recommendation
        rec = p.recommend(db, rid)
        artifacts.append({"type": "recommendation", "id": str(rec.id)})
        cards.append(k.recommendation_card(db, rec))
        text = "Voici ma recommandation argumentée. La décision vous revient."
        _set_state(conv, flow="recommendation")
    assistant = _assistant(db, conv, text, cards, intent=intent, artifacts=artifacts)
    return _turn(user_msg, assistant, intent, updates, artifacts, conv)


def _search(db: Session, conv: m.Conversation, user_msg, intent: str = "search") -> dict:
    """Role confirmed: Success Model -> matching -> Top 3 -> candidate cards; offers to the finalists."""
    rid = conv.role_id
    role = db.get(m.Role, rid)
    role.status = "open"
    sm = p.generate_success_model(db, rid)
    cards = [k.success_model_card(sm)]
    artifacts = [{"type": "success_model", "id": str(sm.id), "version": sm.version}]
    matches = p.run_matching(db, rid) if p._active_candidate_ids(db) else []
    if not matches:
        text = ("Le poste est prêt et son modèle de réussite est construit. Aucun profil n'est encore disponible "
                "dans JobMate : je vous préviendrai dès que des candidats correspondront.")
        _set_state(conv, flow="results")
        assistant = _assistant(db, conv, text, cards, intent=intent, artifacts=artifacts)
        return _turn(user_msg, assistant, intent, [], artifacts, conv)
    sl = p.build_shortlist(db, rid, k=min(3, len(matches)))
    top = list(db.scalars(select(m.Match).where(m.Match.role_id == rid, m.Match.shortlist_rank.is_not(None))
                          .order_by(m.Match.shortlist_rank)))
    cards += [k.candidates_card(db, top), k.next_steps_card()]
    artifacts.append({"type": "shortlist", "role_id": str(rid)})
    push_offers(db, top)
    _set_state(conv, flow="results")
    n = len(top)
    text = (f"Voici les {n} profils les plus pertinents pour ce poste." if n > 1 else
            "Voici le profil le plus pertinent pour ce poste.") + (" " + sl["summary"] if sl.get("summary") else "")
    assistant = _assistant(db, conv, text, cards, intent=intent, artifacts=artifacts)
    return _turn(user_msg, assistant, intent, [], artifacts, conv)


# =========================================================================== offers (employer -> candidate)
def _candidate_conversation(db: Session, cand: m.Candidate) -> m.Conversation | None:
    if cand.user_id is None:
        return None
    conv = db.scalars(select(m.Conversation).where(m.Conversation.user_id == cand.user_id,
                                                   m.Conversation.kind == m.ConversationKind.candidate)
                      .order_by(m.Conversation.created_at.desc())).first()
    if conv is None:
        conv = start_conversation(db, db.get(m.User, cand.user_id), "candidate")
    return conv


def push_offers(db: Session, matches: list[m.Match]) -> None:
    for x in matches:
        if x.offered_at is not None:
            continue
        conv = _candidate_conversation(db, db.get(m.Candidate, x.candidate_id))
        if conv is None:
            continue
        x.offered_at, x.candidate_status = datetime.now(timezone.utc), "offered"
        _assistant(db, conv, "Une nouvelle opportunité correspond à votre profil.", [k.offer_card(db, x)],
                   intent="offer")
    db.flush()


def _notify_candidate(db: Session, match: m.Match, text: str) -> None:
    conv = _candidate_conversation(db, db.get(m.Candidate, match.candidate_id))
    if conv is not None:
        _assistant(db, conv, text, intent="employer_update")


# =========================================================================== candidate
def candidate_message(db: Session, conv: m.Conversation, content: str) -> dict:
    pending = conv.state.get("assessment")
    if pending:
        return _answer_assessment(db, conv, content, pending)
    cb, intel = ContextBuilder(db), get_intelligence()
    user_msg = _post(db, conv, "user", content)
    cand = cb.candidate(conv.candidate_id)
    turn = intel.candidate_turn(c.CandidateConversationContext(
        candidate=cand, history=cb.history(conv.id), user_message=content,
        last_asked_field=conv.state.get("asked_field"), missing_fields=cb.missing_candidate_fields(cand)))
    producer = p._producer(intel)
    updates = []
    patch = turn.professional_identity_patch.model_dump(exclude_none=True)
    if patch:
        new_version(db, m.ProfessionalIdentity, conv.candidate_id, patch, producer, merge_lists=True)
        updates.append({"entity": "professional_identity", "fields": sorted(patch)})
        # What the candidate says about themself is kept as self-declared, never as fact.
        if patch.get("strengths"):
            from app.intelligence.heuristic import detect_capabilities
            p._save_evidence(db, conv.candidate_id, [c.EvidenceDraft(
                subject_type="capability", subject_key=(detect_capabilities(s) or [None])[0], claim=s,
                evidence=f"Déclaré en conversation : « {s} »", source="self_declared",
                epistemic_status="hypothesis", confidence=0.3) for s in patch["strengths"]])
    _set_state(conv, asked_field=turn.asked_field)
    cards = []
    ident = current(db, m.ProfessionalIdentity, conv.candidate_id)
    if not conv.state.get("sources_offered") and ident and ident.career_direction and ident.strengths:
        cards.append(k.sources_card())
        _set_state(conv, sources_offered=True, flow="sources")
    artifacts = []
    if turn.intent == "request_opportunities":
        artifacts.append({"type": "opportunities", "candidate_id": str(conv.candidate_id)})
    assistant = _assistant(db, conv, turn.reply, cards, intent=turn.intent, updates=updates, produced_by=producer)
    return _turn(user_msg, assistant, turn.intent, updates, artifacts, conv)


def _theme(db: Session, req: m.AssessmentRequest) -> str:
    sm = current(db, m.SuccessModel, req.role_id)
    names = {x["key"]: x["name"] for x in (sm.critical_capabilities if sm else [])}
    return names.get(req.target_capability, req.target_capability)


def _ask(db: Session, conv: m.Conversation, role_id, index: int, intro: str) -> m.Message:
    req = p.next_assessment(db, role_id, conv.candidate_id)
    _set_state(conv, flow="assessment", assessment={"request_id": str(req.id), "role_id": str(role_id),
                                                    "index": index, "total": ASSESSMENT_QUESTIONS})
    return _assistant(db, conv, intro, [k.assessment_card(req, _theme(db, req), index, ASSESSMENT_QUESTIONS)],
                      intent="assessment")


def _answer_assessment(db: Session, conv: m.Conversation, content: str, pending: dict) -> dict:
    user_msg = _post(db, conv, "user", content)
    resp = p.submit_response(db, uuid.UUID(pending["request_id"]), content)
    role_id = uuid.UUID(pending["role_id"])
    updates = [{"entity": "evidence", "ids": [e["evidence_id"] for e in resp.evidence]}]
    if pending["index"] < pending["total"]:
        assistant = _ask(db, conv, role_id, pending["index"] + 1, "Merci. Une dernière question :")
    else:
        _set_state(conv, assessment=None, flow="waiting")
        p.run_matching(db, role_id, [conv.candidate_id])
        assistant = _assistant(db, conv, "Merci, c'est terminé. Vos réponses ont été ajoutées à votre profil et "
                                         "transmises avec votre candidature. Je vous tiens informé de la suite.",
                               intent="assessment_done")
    return _turn(user_msg, assistant, "assessment_answer", updates, conv=conv)


# =========================================================================== card actions
EMPLOYER_LABELS = {"candidate.pass": "Passer", "candidate.interview": "Entretien", "candidate.hire": "Hire",
                   "next.hire": "Hirer un candidat", "next.interviews": "Planifier des entretiens",
                   "next.refine": "Affiner la recherche", "role_summary.confirm": "Lancer la recherche",
                   "role_summary.edit": "Modifier le poste", "recommend": "Obtenir une recommandation"}
CANDIDATE_LABELS = {"offer.interested": "Ça m'intéresse", "offer.decline": "Pas disponible",
                    "sources.skip": "Plus tard", "sources.submit": "J'ai ajouté mes informations"}


def _role_match(db: Session, conv: m.Conversation, payload: dict) -> m.Match:
    cid = payload.get("candidate_id")
    x = db.scalars(select(m.Match).where(m.Match.role_id == conv.role_id,
                                         m.Match.candidate_id == uuid.UUID(str(cid)))).first() if cid else None
    if x is None:
        raise HTTPException(400, "candidate_id inconnu pour ce poste")
    return x


def handle_action(db: Session, conv: m.Conversation, card_id: str, action: str, payload: dict) -> dict:
    msg, cd = find_card(db, conv, card_id)
    allowed = {a["id"] for a in cd.get("actions", [])}
    if action not in allowed:
        raise HTTPException(400, f"action {action!r} not available on this card")
    if conv.kind == m.ConversationKind.employer:
        return _employer_action(db, conv, msg, cd, action, payload)
    return _candidate_action(db, conv, msg, cd, action, payload)


def _employer_action(db, conv, msg, cd, action, payload) -> dict:
    if action == "missions.submit":
        selected = [s for s in payload.get("selected", []) if isinstance(s, str) and s.strip()]
        if payload.get("other"):
            selected.append(str(payload["other"]).strip())
        if not selected:
            raise HTTPException(400, "Sélectionnez au moins une mission.")
        close_card(msg, cd["id"], {"selected": selected})
        new_version(db, m.RoleIdentity, conv.role_id, {"responsibilities": selected}, "manual", merge_lists=True)
        return employer_message(db, conv, "Missions principales : " + ", ".join(selected) + ".")

    if action == "role_summary.edit":
        close_card(msg, cd["id"], {"action": action})
        user_msg = _post(db, conv, "user", EMPLOYER_LABELS[action])
        _set_state(conv, flow="discovery")
        assistant = _assistant(db, conv, "Bien sûr. Que souhaitez-vous modifier ?", intent="edit_role")
        return _turn(user_msg, assistant, "edit_role", conv=conv)

    if action == "role_summary.confirm":
        close_card(msg, cd["id"], {"action": action})
        return _search(db, conv, _post(db, conv, "user", EMPLOYER_LABELS[action]))

    if action == "recommend":
        return _employer_intent(db, conv, _post(db, conv, "user", EMPLOYER_LABELS[action]),
                                "request_recommendation", "", [])

    if action.startswith("candidate."):
        x = _role_match(db, conv, payload)
        name = db.get(m.Candidate, x.candidate_id).full_name
        decision = action.split(".", 1)[1]
        x.employer_status = {"pass": "passed", "interview": "interview", "hire": "hired"}[decision]
        user_msg = _post(db, conv, "user", f"{EMPLOYER_LABELS[action]} : {name}")
        text = {"pass": f"C'est noté, {name} est écarté(e) pour ce poste.",
                "interview": f"C'est noté. J'informe {name} que vous souhaitez un entretien.",
                "hire": f"C'est noté : vous avez choisi {name}. Je l'informe de votre décision."}[decision]
        if decision == "interview":
            _notify_candidate(db, x, f"Bonne nouvelle : l'employeur du poste « {db.get(m.Role, x.role_id).title} » "
                                     "souhaite vous rencontrer en entretien.")
        elif decision == "hire":
            _notify_candidate(db, x, f"Félicitations : l'employeur vous a choisi(e) pour le poste "
                                     f"« {db.get(m.Role, x.role_id).title} ».")
        db.flush()
        assistant = _assistant(db, conv, text, intent="employer_decision",
                               decision={"candidate_id": str(x.candidate_id), "status": x.employer_status})
        return _turn(user_msg, assistant, "employer_decision", [{"entity": "match", "id": str(x.id)}], conv=conv)

    # next_steps panel
    user_msg = _post(db, conv, "user", EMPLOYER_LABELS[action])
    if action == "next.refine":
        _set_state(conv, flow="discovery")
        assistant = _assistant(db, conv, "Dites-moi ce que vous voulez ajuster : un critère, une langue, la "
                                         "disponibilité… Je relancerai la recherche ensuite.", intent="refine")
        return _turn(user_msg, assistant, "refine", conv=conv)
    top = list(db.scalars(select(m.Match).where(m.Match.role_id == conv.role_id,
                                               m.Match.shortlist_rank.is_not(None)).order_by(m.Match.shortlist_rank)))
    text = ("Quel candidat souhaitez-vous recruter ? Ouvrez sa carte et cliquez sur « Hire »."
            if action == "next.hire" else
            "Avec qui souhaitez-vous un entretien ? Ouvrez chaque carte et cliquez sur « Entretien ».")
    assistant = _assistant(db, conv, text, [k.candidates_card(db, top)] if top else [], intent=action)
    return _turn(user_msg, assistant, action, conv=conv)


def _candidate_action(db, conv, msg, cd, action, payload) -> dict:
    close_card(msg, cd["id"], {"action": action})
    user_msg = _post(db, conv, "user", CANDIDATE_LABELS[action])
    if action == "sources.skip":
        _set_state(conv, flow="profile")
        assistant = _assistant(db, conv, "Pas de souci, vous pourrez les ajouter plus tard. Je vous préviens dès "
                                         "qu'une opportunité vous correspond.", intent="sources_skip")
        return _turn(user_msg, assistant, action, conv=conv)
    if action == "sources.submit":
        cand = db.get(m.Candidate, conv.candidate_id)
        if not (cand.cv_text or cand.sources):
            raise HTTPException(400, "Ajoutez un CV ou un lien avant de valider.")
        p.understand_candidate(db, conv.candidate_id)
        _set_state(conv, flow="profile")
        assistant = _assistant(db, conv, "Merci, j'ai enrichi votre profil avec ces informations. Ce que vous "
                                         "déclarez reste marqué comme déclaratif tant qu'il n'est pas vérifié.",
                               intent="sources_added")
        return _turn(user_msg, assistant, action, [{"entity": "candidate", "id": str(cand.id)}], conv=conv)

    x = db.get(m.Match, uuid.UUID(cd["data"]["match_id"]))
    if x is None or x.candidate_id != conv.candidate_id:
        raise HTTPException(404, "offer not found")
    if action == "offer.decline":
        x.candidate_status = "declined"
        _set_state(conv, flow="profile")
        assistant = _assistant(db, conv, "C'est noté, je ne vous proposerai plus ce poste. Je continue à chercher "
                                         "ce qui vous correspond.", intent="offer_declined")
        return _turn(user_msg, assistant, action, [{"entity": "match", "id": str(x.id)}], conv=conv)
    x.candidate_status = "interested"
    assistant = _ask(db, conv, x.role_id, 1, "Super ! Pour compléter votre candidature, j'ai deux questions "
                                             "courtes, une à la fois. Répondez simplement dans le chat.")
    return _turn(user_msg, assistant, action, [{"entity": "match", "id": str(x.id)}], conv=conv)
