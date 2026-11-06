"""Conversations: the primary interface. Employer conversations build the Company/Role identities
and can trigger the pipeline ("compare-moi les trois finalistes"); candidate conversations build
the Professional Identity."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api import schemas as s
from app.api.access import my_candidate, own_company, own_role
from app.auth.deps import with_role as current_user
from app.db import get_db
from app.engine import pipeline

router = APIRouter(tags=["conversations"])

OPENERS = {
    "employer": "Bonjour ! Je suis JobMate. Parlez-moi de votre entreprise et du poste que vous voulez pourvoir, "
                "avec vos mots : je construirai la fiche du poste au fil de la conversation.",
    "candidate": "Bonjour ! Je suis JobMate. Je vais apprendre à vous connaître pour vous proposer des opportunités "
                 "qui vous correspondent vraiment. Vers quel type de poste aimeriez-vous aller ?",
}


def _own_conv(db: Session, user: m.User, conv_id) -> m.Conversation:
    conv = db.get(m.Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "conversation not found")
    return conv


@router.post("/conversations", response_model=s.ConversationDetailOut, status_code=201)
def start(body: s.ConversationIn, user=Depends(current_user), db: Session = Depends(get_db)):
    conv = m.Conversation(user_id=user.id, kind=m.ConversationKind(body.kind), title=body.title)
    state: dict = {}
    if body.kind == "employer":
        if user.role != m.UserRole.employer or not body.company_id:
            raise HTTPException(400, "employer conversation needs an employer account and company_id")
        own_company(db, user, body.company_id)
        conv.company_id = body.company_id
        if body.role_id:
            own_role(db, user, body.role_id)
            conv.role_id = body.role_id
    else:
        conv.candidate_id = my_candidate(db, user).id
        state["asked_field"] = "candidate.career_direction"
    conv.state = state
    db.add(conv)
    db.flush()
    db.add(m.Message(conversation_id=conv.id, sender="assistant", content=OPENERS[body.kind],
                     meta={"intent": "opening", "asked_field": state.get("asked_field")}))
    db.flush()
    return _detail(db, conv)


def _detail(db: Session, conv: m.Conversation) -> s.ConversationDetailOut:
    msgs = list(db.scalars(select(m.Message).where(m.Message.conversation_id == conv.id).order_by(m.Message.created_at)))
    base = s.ConversationOut.model_validate(conv).model_dump()
    return s.ConversationDetailOut(**base, messages=[s.MessageOut.model_validate(x) for x in msgs])


@router.get("/conversations", response_model=list[s.ConversationOut])
def mine(user=Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(m.Conversation).where(m.Conversation.user_id == user.id)
                           .order_by(m.Conversation.created_at.desc())))


@router.get("/conversations/{conversation_id}", response_model=s.ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    return _detail(db, _own_conv(db, user, conversation_id))


@router.post("/conversations/{conversation_id}/messages", response_model=s.TurnOut)
def send(conversation_id: uuid.UUID, body: s.MessageIn, user=Depends(current_user), db: Session = Depends(get_db)):
    conv = _own_conv(db, user, conversation_id)
    if conv.kind == m.ConversationKind.employer:
        out = pipeline.employer_message(db, conv, body.content)
    else:
        out = pipeline.candidate_message(db, conv, body.content)
    db.refresh(out["user_message"])
    db.refresh(out["assistant_message"])
    return s.TurnOut(user_message=s.MessageOut.model_validate(out["user_message"]),
                     assistant_message=s.MessageOut.model_validate(out["assistant_message"]),
                     intent=out["intent"], updates=out["updates"], artifacts=out["artifacts"])
