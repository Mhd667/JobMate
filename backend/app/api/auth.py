from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api.schemas import LoginIn, MeOut, RoleChoiceIn, SignupIn, TokenOut, UserOut
from app.auth.deps import current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _local_only():
    if settings.auth_provider != "local":
        raise HTTPException(400, "sign-up and login are handled by Supabase Auth")


@router.post("/signup", response_model=TokenOut, status_code=201, include_in_schema=False)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    """Local auth only (tests / offline dev). In production the frontend uses Supabase Auth."""
    _local_only()
    if db.scalars(select(m.User).where(m.User.email == body.email.lower())).first():
        raise HTTPException(409, "email already registered")
    user = m.User(email=body.email.lower(), phone_number=body.phone_number,
                  password_hash=hash_password(body.password), role=m.UserRole(body.role) if body.role else None)
    db.add(user)
    db.flush()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut, include_in_schema=False)
def login(body: LoginIn, db: Session = Depends(get_db)):
    _local_only()
    user = db.scalars(select(m.User).where(m.User.email == body.email.lower())).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


def _me(db: Session, user: m.User) -> MeOut:
    company = db.scalars(select(m.Company.id).where(m.Company.owner_user_id == user.id)).first()
    cand = db.scalars(select(m.Candidate.id).where(m.Candidate.user_id == user.id)).first()
    if user.role is None:
        nxt = "choose_role"
    elif user.role == m.UserRole.employer:
        nxt = "employer_home" if company else "create_company"
    else:
        nxt = "candidate_home" if cand else "create_profile"
    return MeOut(user=UserOut.model_validate(user), company_id=company, candidate_id=cand, next_step=nxt)


@router.get("/me", response_model=MeOut)
def me(user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Who am I, and where should the app send me next (role choice, onboarding, home)."""
    return _me(db, user)


@router.post("/role", response_model=MeOut)
def choose_role(body: RoleChoiceIn, user: m.User = Depends(current_user), db: Session = Depends(get_db)):
    """Role choice page. A role can be set once; changing it later is not allowed in the MVP."""
    if user.role is not None and user.role.value != body.role:
        raise HTTPException(409, "role already chosen")
    user.role = m.UserRole(body.role)
    if body.phone_number:
        user.phone_number = body.phone_number
    db.flush()
    db.refresh(user)
    return _me(db, user)
