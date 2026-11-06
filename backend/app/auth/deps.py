from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models as m
from app.auth.security import decode_token
from app.db import get_db

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> m.User:
    """Any authenticated account, with or without a chosen role."""
    if creds is None:
        raise HTTPException(401, "missing bearer token")
    try:
        claims = decode_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"invalid token: {exc}") from exc
    uid = uuid.UUID(claims["sub"])
    user = db.get(m.User, uid)
    if user is None:
        if not claims.get("email") and not claims.get("phone"):
            raise HTTPException(401, "unknown user")
        # First call after Supabase sign-up: create the access-identity row (no role yet).
        user = m.User(id=uid, email=(claims.get("email") or f"{uid}@phone.local").lower(),
                      phone_number=claims.get("phone") or None, role=None)
        db.add(user)
        db.flush()
        db.refresh(user)
    return user


def with_role(user: m.User = Depends(current_user)) -> m.User:
    if user.role is None:
        raise HTTPException(409, "role not chosen yet: POST /auth/role")
    return user


def employer(user: m.User = Depends(with_role)) -> m.User:
    if user.role != m.UserRole.employer:
        raise HTTPException(403, "employer account required")
    return user


def candidate_user(user: m.User = Depends(with_role)) -> m.User:
    if user.role != m.UserRole.candidate:
        raise HTTPException(403, "candidate account required")
    return user
