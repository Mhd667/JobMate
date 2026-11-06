"""Ownership checks (V0: an employer owns its companies; a candidate owns its profile)."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m


def own_company(db: Session, user: m.User, company_id) -> m.Company:
    co = db.get(m.Company, company_id)
    if co is None:
        raise HTTPException(404, "company not found")
    if co.owner_user_id != user.id:
        raise HTTPException(403, "not your company")
    return co


def own_role(db: Session, user: m.User, role_id) -> m.Role:
    role = db.get(m.Role, role_id)
    if role is None:
        raise HTTPException(404, "role not found")
    own_company(db, user, role.company_id)
    return role


def get_candidate(db: Session, candidate_id) -> m.Candidate:
    cand = db.get(m.Candidate, candidate_id)
    if cand is None:
        raise HTTPException(404, "candidate not found")
    return cand


def readable_candidate(db: Session, user: m.User, candidate_id) -> m.Candidate:
    """Employers can read the talent pool; candidates only themselves."""
    cand = get_candidate(db, candidate_id)
    if user.role == m.UserRole.candidate and cand.user_id != user.id:
        raise HTTPException(403, "not your profile")
    return cand


def writable_candidate(db: Session, user: m.User, candidate_id) -> m.Candidate:
    cand = get_candidate(db, candidate_id)
    if user.role == m.UserRole.candidate and cand.user_id != user.id:
        raise HTTPException(403, "not your profile")
    return cand


def my_candidate(db: Session, user: m.User) -> m.Candidate:
    cand = db.scalars(select(m.Candidate).where(m.Candidate.user_id == user.id)).first()
    if cand is None:
        raise HTTPException(404, "no candidate profile yet: POST /candidates first")
    return cand
