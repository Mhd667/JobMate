"""Assessment, matching, shortlist (Top 3), confrontation, recommendation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api import schemas as s
from app.api.access import get_candidate, my_candidate, own_role
from app.auth.deps import with_role as current_user, employer
from app.db import get_db
from app.engine import pipeline

router = APIRouter()


# ------------------------------------------------------------------ assessment
@router.post("/roles/{role_id}/candidates/{candidate_id}/assessments/next", response_model=s.AssessmentRequestOut,
             status_code=201, tags=["assessment"])
def next_assessment(role_id: uuid.UUID, candidate_id: uuid.UUID, user=Depends(employer),
                    db: Session = Depends(get_db)):
    """Adaptive: picks the question that most reduces the uncertainty that matters for the decision."""
    own_role(db, user, role_id)
    get_candidate(db, candidate_id)
    return pipeline.next_assessment(db, role_id, candidate_id)


@router.get("/roles/{role_id}/candidates/{candidate_id}/assessments", response_model=list[s.AssessmentRequestOut],
            tags=["assessment"])
def list_assessments(role_id: uuid.UUID, candidate_id: uuid.UUID, user=Depends(employer),
                     db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return list(db.scalars(select(m.AssessmentRequest).where(
        m.AssessmentRequest.role_id == role_id, m.AssessmentRequest.candidate_id == candidate_id)
        .order_by(m.AssessmentRequest.created_at)))


@router.get("/candidates/me/assessments", response_model=list[s.AssessmentRequestOut], tags=["assessment"])
def my_assessments(user=Depends(current_user), db: Session = Depends(get_db)):
    cand = my_candidate(db, user)
    return list(db.scalars(select(m.AssessmentRequest).where(
        m.AssessmentRequest.candidate_id == cand.id, m.AssessmentRequest.status == m.AssessmentStatus.pending)))


@router.post("/assessments/{request_id}/responses", response_model=s.AssessmentResponseOut, status_code=201,
             tags=["assessment"])
def answer(request_id: uuid.UUID, body: s.AssessmentResponseIn, user=Depends(current_user),
           db: Session = Depends(get_db)):
    """The candidate answers (or, for the demo, the employer records the answer)."""
    req = db.get(m.AssessmentRequest, request_id)
    if req is None:
        raise HTTPException(404, "assessment request not found")
    if user.role == m.UserRole.candidate:
        if my_candidate(db, user).id != req.candidate_id:
            raise HTTPException(403, "not your assessment")
    else:
        own_role(db, user, req.role_id)
    return pipeline.submit_response(db, request_id, body.response)


# ------------------------------------------------------------------ matching
def _match_out(db: Session, rows) -> list[s.MatchOut]:
    names = {c.id: c.full_name for c in db.scalars(select(m.Candidate))}
    return [s.MatchOut.model_validate(r).model_copy(update={"candidate_name": names.get(r.candidate_id)})
            for r in rows]


@router.post("/roles/{role_id}/matches/run", response_model=list[s.MatchOut], tags=["matching"])
def run_matching(role_id: uuid.UUID, body: s.MatchRunIn | None = None, user=Depends(employer),
                 db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    rows = pipeline.run_matching(db, role_id, body.candidate_ids if body else None)
    db.flush()
    for r in rows:
        db.refresh(r)
    return _match_out(db, rows)


@router.get("/roles/{role_id}/matches", response_model=list[s.MatchOut], tags=["matching"])
def list_matches(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    rows = db.scalars(select(m.Match).where(m.Match.role_id == role_id)
                      .order_by(m.Match.shortlist_rank.asc().nulls_last(), m.Match.ui_score.desc()))
    return _match_out(db, rows)


@router.get("/roles/{role_id}/matches/{candidate_id}", response_model=s.MatchOut, tags=["matching"])
def get_match(role_id: uuid.UUID, candidate_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    row = db.scalars(select(m.Match).where(m.Match.role_id == role_id, m.Match.candidate_id == candidate_id)).first()
    if row is None:
        raise HTTPException(404, "no match yet: run matching")
    return _match_out(db, [row])[0]


# ------------------------------------------------------------------ shortlist
@router.post("/roles/{role_id}/shortlist", response_model=s.ShortlistOut, tags=["shortlist"])
def make_shortlist(role_id: uuid.UUID, body: s.ShortlistIn | None = None, user=Depends(employer),
                   db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return pipeline.build_shortlist(db, role_id, (body or s.ShortlistIn()).k)


@router.get("/roles/{role_id}/shortlist", response_model=list[s.MatchOut], tags=["shortlist"])
def get_shortlist(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    rows = db.scalars(select(m.Match).where(m.Match.role_id == role_id, m.Match.shortlist_rank.is_not(None))
                      .order_by(m.Match.shortlist_rank))
    return _match_out(db, rows)


# ------------------------------------------------------------------ confrontation
@router.post("/roles/{role_id}/confrontations", response_model=s.ConfrontationOut, status_code=201,
             tags=["confrontation"])
def create_confrontation(role_id: uuid.UUID, body: s.ConfrontationIn, user=Depends(employer),
                         db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    conf = pipeline.confront(db, role_id, body.decision_question, body.candidate_ids)
    db.refresh(conf)
    return conf


@router.get("/roles/{role_id}/confrontations", response_model=list[s.ConfrontationOut], tags=["confrontation"])
def list_confrontations(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return list(db.scalars(select(m.Confrontation).where(m.Confrontation.role_id == role_id)
                           .order_by(m.Confrontation.created_at.desc())))


@router.get("/confrontations/{confrontation_id}", response_model=s.ConfrontationOut, tags=["confrontation"])
def get_confrontation(confrontation_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    conf = db.get(m.Confrontation, confrontation_id)
    if conf is None:
        raise HTTPException(404, "not found")
    own_role(db, user, conf.role_id)
    return conf


# ------------------------------------------------------------------ recommendation
@router.post("/roles/{role_id}/recommendations", response_model=s.RecommendationOut, status_code=201,
             tags=["recommendation"])
def create_recommendation(role_id: uuid.UUID, body: s.RecommendationIn | None = None, user=Depends(employer),
                          db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    rec = pipeline.recommend(db, role_id, body.confrontation_id if body else None)
    db.refresh(rec)
    return rec


@router.get("/roles/{role_id}/recommendations/latest", response_model=s.RecommendationOut, tags=["recommendation"])
def latest_recommendation(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    rec = db.scalars(select(m.Recommendation).where(m.Recommendation.role_id == role_id)
                     .order_by(m.Recommendation.created_at.desc())).first()
    if rec is None:
        raise HTTPException(404, "no recommendation yet")
    return rec
