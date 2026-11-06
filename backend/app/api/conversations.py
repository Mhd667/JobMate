"""Conversations: the primary interface (the chat is the product).

Each turn returns the assistant's text plus structured cards (missions, role summary, candidates, offer,
assessment...) and the flow state. Cards are answered with POST /conversations/{id}/actions.
"""
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
from app.engine import flows

router = APIRouter(tags=["conversations"])


def _own_conv(db: Session, user: m.User, conv_id) -> m.Conversation:
    conv = db.get(m.Conversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "conversation not found")
    return conv


def _detail(db: Session, conv: m.Conversation) -> s.ConversationDetailOut:
    msgs = list(db.scalars(select(m.Message).where(m.Message.conversation_id == conv.id).order_by(m.Message.created_at)))
    base = s.ConversationOut.model_validate(conv).model_dump()
    return s.ConversationDetailOut(**base, messages=[s.MessageOut.model_validate(x) for x in msgs])


@router.post("/conversations", response_model=s.ConversationDetailOut, status_code=201)
def start(body: s.ConversationIn, user=Depends(current_user), db: Session = Depends(get_db)):
    """Employer: "Nouveau recrutement" (a draft role is created when role_id is omitted).
    Candidate: the candidate's chat. company_id defaults to the employer's own company."""
    if body.kind == "employer":
        if user.role != m.UserRole.employer:
            raise HTTPException(403, "employer conversation needs an employer account")
        company_id = body.company_id or db.scalars(
            select(m.Company.id).where(m.Company.owner_user_id == user.id)).first()
        if company_id is None:
            raise HTTPException(409, "no company for this account")
        own_company(db, user, company_id)
        if body.role_id:
            own_role(db, user, body.role_id)
        conv = flows.start_conversation(db, user, "employer", company_id, body.role_id, body.title)
    else:
        my_candidate(db, user)
        conv = flows.start_conversation(db, user, "candidate", title=body.title)
    return _detail(db, conv)


@router.get("/conversations", response_model=list[s.ConversationOut])
def mine(user=Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(m.Conversation).where(m.Conversation.user_id == user.id)
                           .order_by(m.Conversation.created_at.desc())))


@router.get("/conversations/{conversation_id}", response_model=s.ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    return _detail(db, _own_conv(db, user, conversation_id))


def _turn_out(db: Session, out: dict) -> s.TurnOut:
    db.flush()
    db.refresh(out["user_message"])
    db.refresh(out["assistant_message"])
    return s.TurnOut(user_message=s.MessageOut.model_validate(out["user_message"]),
                     assistant_message=s.MessageOut.model_validate(out["assistant_message"]),
                     intent=out["intent"], updates=out["updates"], artifacts=out["artifacts"],
                     cards=out["cards"], flow_state=out["flow_state"])


@router.post("/conversations/{conversation_id}/messages", response_model=s.TurnOut)
def send(conversation_id: uuid.UUID, body: s.MessageIn, user=Depends(current_user), db: Session = Depends(get_db)):
    conv = _own_conv(db, user, conversation_id)
    if conv.kind == m.ConversationKind.employer:
        out = flows.employer_message(db, conv, body.content)
    else:
        out = flows.candidate_message(db, conv, body.content)
    return _turn_out(db, out)


@router.post("/conversations/{conversation_id}/actions", response_model=s.TurnOut)
def act(conversation_id: uuid.UUID, body: s.ActionIn, user=Depends(current_user), db: Session = Depends(get_db)):
    """Answer a card: the click is recorded as a user message, followed by JobMate's reply (and new cards)."""
    conv = _own_conv(db, user, conversation_id)
    return _turn_out(db, flows.handle_action(db, conv, body.card_id, body.action, body.payload))
