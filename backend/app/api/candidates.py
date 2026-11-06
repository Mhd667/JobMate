"""Talent registry: candidates, professional identity, experiences, capabilities, evidence."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api import schemas as s
from app.api.access import my_candidate, own_role, readable_candidate, writable_candidate
from app.auth.deps import with_role as current_user, employer
from app.db import get_db
from app.engine import pipeline
from app.engine.context_builder import ContextBuilder
from app.engine.registry import current, new_version

router = APIRouter(tags=["candidates"])


@router.post("/candidates", response_model=s.CandidateOut, status_code=201)
def create_candidate(body: s.CandidateIn, user=Depends(current_user), db: Session = Depends(get_db)):
    """A candidate creates their own profile; an employer may add a candidate they sourced."""
    if user.role == m.UserRole.candidate and db.scalars(
            select(m.Candidate).where(m.Candidate.user_id == user.id)).first():
        raise HTTPException(409, "profile already exists")
    cand = m.Candidate(user_id=user.id if user.role == m.UserRole.candidate else None, **body.model_dump())
    db.add(cand)
    db.flush()
    new_version(db, m.ProfessionalIdentity, cand.id, {"unknowns": ["career_direction", "strengths"]}, "system")
    db.refresh(cand)
    return cand


@router.get("/candidates", response_model=list[s.CandidateOut])
def list_candidates(user=Depends(employer), db: Session = Depends(get_db)):
    return list(db.scalars(select(m.Candidate).where(m.Candidate.status == "active").order_by(m.Candidate.full_name)))


@router.get("/candidates/me", response_model=s.CandidateProfileOut)
def my_profile(user=Depends(current_user), db: Session = Depends(get_db)):
    return _profile(db, my_candidate(db, user))


def _profile(db: Session, cand: m.Candidate) -> s.CandidateProfileOut:
    q = lambda model: list(db.scalars(select(model).where(model.candidate_id == cand.id)))  # noqa: E731
    return s.CandidateProfileOut(candidate=cand, professional_identity=current(db, m.ProfessionalIdentity, cand.id),
                                 experiences=q(m.Experience), capabilities=q(m.Capability), evidence=q(m.Evidence))


@router.get("/candidates/{candidate_id}", response_model=s.CandidateProfileOut)
def get_candidate(candidate_id: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    return _profile(db, readable_candidate(db, user, candidate_id))


@router.get("/candidates/{candidate_id}/professional-identity", response_model=s.ProfessionalIdentityOut | None)
def get_identity(candidate_id: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    readable_candidate(db, user, candidate_id)
    return current(db, m.ProfessionalIdentity, candidate_id)


@router.patch("/candidates/{candidate_id}/professional-identity", response_model=s.ProfessionalIdentityOut)
def patch_identity(candidate_id: uuid.UUID, body: s.ProfessionalIdentityPatch, user=Depends(current_user),
                   db: Session = Depends(get_db)):
    writable_candidate(db, user, candidate_id)
    return new_version(db, m.ProfessionalIdentity, candidate_id, body.model_dump(exclude_none=True), "manual")


@router.post("/candidates/{candidate_id}/experiences", response_model=s.ExperienceOut, status_code=201)
def add_experience(candidate_id: uuid.UUID, body: s.ExperienceIn, user=Depends(current_user),
                   db: Session = Depends(get_db)):
    writable_candidate(db, user, candidate_id)
    exp = m.Experience(candidate_id=candidate_id, **body.model_dump())
    db.add(exp)
    db.flush()
    return exp


@router.post("/candidates/{candidate_id}/analyze", tags=["evidence"])
def analyze_candidate(candidate_id: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Candidate understanding: derive capabilities + evidence from experiences / CV."""
    writable_candidate(db, user, candidate_id)
    return pipeline.understand_candidate(db, candidate_id)


@router.get("/candidates/{candidate_id}/evidence", response_model=list[s.EvidenceOut], tags=["evidence"])
def list_evidence(candidate_id: uuid.UUID, role_id: uuid.UUID | None = None, user=Depends(current_user),
                  db: Session = Depends(get_db)):
    readable_candidate(db, user, candidate_id)
    q = select(m.Evidence).where(m.Evidence.candidate_id == candidate_id)
    if role_id:
        q = q.where((m.Evidence.role_id.is_(None)) | (m.Evidence.role_id == role_id))
    return list(db.scalars(q.order_by(m.Evidence.created_at)))


@router.post("/candidates/{candidate_id}/evidence", response_model=s.EvidenceOut, status_code=201, tags=["evidence"])
def add_evidence(candidate_id: uuid.UUID, body: s.EvidenceIn, user=Depends(employer), db: Session = Depends(get_db)):
    """Employer-side evidence (reference check, interview note...)."""
    readable_candidate(db, user, candidate_id)
    if body.role_id:
        own_role(db, user, body.role_id)
    data = body.model_dump()
    ev = m.Evidence(candidate_id=candidate_id, **{**data, "source": m.EvidenceSource(data["source"]),
                                                  "epistemic_status": m.EpistemicStatus(data["epistemic_status"])})
    db.add(ev)
    db.flush()
    return ev


@router.get("/roles/{role_id}/candidates/{candidate_id}/analysis", response_model=s.CandidateAnalysisOut,
            tags=["evidence"])
def candidate_analysis(role_id: uuid.UUID, candidate_id: uuid.UUID, user=Depends(employer),
                       db: Session = Depends(get_db)):
    """What is known / what remains uncertain about this candidate for this role."""
    own_role(db, user, role_id)
    cb = ContextBuilder(db)
    role = cb.role(role_id)
    if role.success_model is None:
        raise HTTPException(409, "generate the success model first")
    cv = cb.candidate(candidate_id, role)
    return s.CandidateAnalysisOut(
        candidate_id=candidate_id, role_id=role_id, coverage=[x.model_dump() for x in cv.coverage],
        known=[f"{x.capability_name} ({x.level})" for x in cv.coverage if x.level in ("strong", "moderate")],
        uncertain=[f"{x.capability_name} ({x.level}, certitude {x.certainty:.0%})" for x in cv.coverage
                   if x.level in ("weak", "unknown")],
        constraint_flags=cv.constraint_flags)


@router.get("/candidates/me/opportunities", response_model=list[s.OpportunityOut], tags=["candidates"])
def my_opportunities(user=Depends(current_user), db: Session = Depends(get_db)):
    cand = my_candidate(db, user)
    out = []
    for role in db.scalars(select(m.Role).where(m.Role.status == "open")):
        match = db.scalars(select(m.Match).where(m.Match.role_id == role.id, m.Match.candidate_id == cand.id)).first()
        out.append(s.OpportunityOut(role=role, company_name=role.company.name,
                                    match=s.MatchOut.model_validate(match) if match else None))
    return out
