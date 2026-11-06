"""Context Builder: Database -> Structured Decision Context.

The only place that decides WHAT the Intelligence Layer sees. It also computes the
deterministic evidence coverage (known / uncertain per Success Model capability), which is
the minimal "belief state" of V0. Tomorrow this is where the Bayesian belief is assembled.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.engine.registry import current, to_dict
from app.intelligence import contracts as c

STATUS_WEIGHT = {"fact": 1.0, "inference": 0.7, "hypothesis": 0.35, "unknown": 0.0}

COMPANY_FIELDS = ["mission", "business_model", "culture", "management_style"]
ROLE_FIELDS = ["mission", "objectives", "responsibilities", "constraints", "stakeholders", "success_factors"]
CANDIDATE_FIELDS = ["career_direction", "strengths", "professional_goals", "preferences", "constraints", "aspirations"]

_IDENT_EXCLUDE = {"id", "created_at", "updated_at", "company_id", "role_id", "candidate_id"}


def coverage_for(spec: c.CapabilitySpec, evidence: list[c.EvidenceView], open_count: int = 0) -> c.CoverageView:
    rel = [e for e in evidence if e.subject_key == spec.key]
    p_not_support, p_not_known, contra = 1.0, 1.0, 1.0
    for e in rel:
        w = STATUS_WEIGHT[e.epistemic_status] * e.confidence
        p_not_known *= 1 - 0.85 * w
        if e.polarity == "contradicts":
            contra *= 1 - 0.8 * w
        else:
            p_not_support *= 1 - w
    support = (1 - p_not_support) * contra
    certainty = 1 - p_not_known
    if certainty < 0.25:
        level = "unknown"
    elif support >= 0.72:
        level = "strong"
    elif support >= 0.45:
        level = "moderate"
    else:
        level = "weak"
    return c.CoverageView(capability_key=spec.key, capability_name=spec.name, importance=spec.importance,
                          support=round(support, 3), certainty=round(certainty, 3), level=level,
                          evidence_ids=[e.id for e in rel], open_assessments=open_count,
                          untested_claim=bool(rel) and all(e.epistemic_status == "hypothesis" for e in rel))


def _ident(obj) -> dict:
    d = to_dict(obj, exclude=_IDENT_EXCLUDE)
    return {k: v for k, v in d.items() if v not in (None, [], {}, "")}


class ContextBuilder:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ views
    def company(self, company_id) -> c.CompanyView:
        co = self.db.get(m.Company, company_id)
        return c.CompanyView(id=str(co.id), name=co.name, description=co.description,
                             identity=_ident(current(self.db, m.CompanyIdentity, co.id)))

    def success_model(self, role_id) -> c.SuccessModelView | None:
        sm = current(self.db, m.SuccessModel, role_id)
        if sm is None:
            return None
        return c.SuccessModelView.model_validate(to_dict(sm))

    def role(self, role_id) -> c.RoleView:
        r = self.db.get(m.Role, role_id)
        return c.RoleView(id=str(r.id), title=r.title, location=r.location, constraints=r.constraints or {},
                          identity=_ident(current(self.db, m.RoleIdentity, r.id)),
                          success_model=self.success_model(r.id))

    def candidate(self, candidate_id, role: c.RoleView | None = None) -> c.CandidateView:
        cand = self.db.get(m.Candidate, candidate_id)
        evid = [c.EvidenceView(id=str(e.id), subject_type=e.subject_type, subject_key=e.subject_key,
                               claim=e.claim, evidence=e.evidence, source=e.source.value,
                               epistemic_status=e.epistemic_status.value, confidence=e.confidence,
                               polarity=e.polarity)
                for e in self.db.scalars(select(m.Evidence).where(
                    m.Evidence.candidate_id == cand.id,
                    (m.Evidence.role_id.is_(None)) | (m.Evidence.role_id == (role.id if role else None))))]
        exps = [to_dict(x, exclude={"candidate_id", "created_at", "updated_at"}) for x in self.db.scalars(
            select(m.Experience).where(m.Experience.candidate_id == cand.id).order_by(m.Experience.start_date.desc()))]
        caps = [to_dict(x, exclude={"candidate_id", "created_at", "updated_at"}) for x in self.db.scalars(
            select(m.Capability).where(m.Capability.candidate_id == cand.id))]
        view = c.CandidateView(id=str(cand.id), full_name=cand.full_name, headline=cand.headline,
                               location=cand.location, availability=cand.availability or {},
                               identity=_ident(current(self.db, m.ProfessionalIdentity, cand.id)),
                               experiences=exps, capabilities=caps, evidence=evid)
        if role and role.success_model:
            open_counts = dict(self.db.execute(
                select(m.AssessmentRequest.target_capability, func.count()).where(
                    m.AssessmentRequest.role_id == role.id, m.AssessmentRequest.candidate_id == cand.id,
                    m.AssessmentRequest.status == m.AssessmentStatus.pending)
                .group_by(m.AssessmentRequest.target_capability)).all())
            view.coverage = [coverage_for(cp, evid, open_counts.get(cp.key, 0))
                             for cp in role.success_model.critical_capabilities]
            view.constraint_flags = self.constraint_flags(role, view)
        return view

    @staticmethod
    def constraint_flags(role: c.RoleView, cand: c.CandidateView) -> list[str]:
        flags = []
        start_before = role.constraints.get("start_before")
        avail = cand.availability.get("available_from")
        if start_before and avail:
            try:
                if date.fromisoformat(avail) > date.fromisoformat(start_before):
                    flags.append(f"Disponible le {avail}, après la date de démarrage souhaitée ({start_before})")
            except ValueError:
                pass
        loc = role.constraints.get("location")
        if loc and cand.location and loc.lower() not in cand.location.lower() and \
                not cand.availability.get("relocation_ok", True):
            flags.append(f"Basé(e) à {cand.location}, poste à {loc}, mobilité non confirmée")
        return flags

    # ------------------------------------------------------------------ dialogue
    def missing_company_role_fields(self, company: c.CompanyView, role: c.RoleView | None) -> list[str]:
        miss = [f"company.{f}" for f in COMPANY_FIELDS if not company.identity.get(f)]
        if role:
            miss += [f"role.{f}" for f in ROLE_FIELDS if not role.identity.get(f)]
        return miss

    def missing_candidate_fields(self, cand: c.CandidateView) -> list[str]:
        return [f"candidate.{f}" for f in CANDIDATE_FIELDS if not cand.identity.get(f)]

    def history(self, conversation_id, limit: int = 20) -> list[c.DialogueTurn]:
        msgs = list(self.db.scalars(select(m.Message).where(m.Message.conversation_id == conversation_id)
                                    .order_by(m.Message.created_at.desc()).limit(limit)))
        return [c.DialogueTurn(sender=x.sender, content=x.content) for x in reversed(msgs)]

    # ------------------------------------------------------------------ match context helpers
    def match_dicts(self, role_id, candidate_ids=None) -> list[dict]:
        q = select(m.Match, m.Candidate.full_name).join(m.Candidate, m.Candidate.id == m.Match.candidate_id) \
            .where(m.Match.role_id == role_id)
        if candidate_ids:
            q = q.where(m.Match.candidate_id.in_(candidate_ids))
        out = []
        for match, name in self.db.execute(q):
            d = to_dict(match)
            d["full_name"] = name
            out.append(d)
        return out
