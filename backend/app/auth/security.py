"""Password hashing (bcrypt), local JWTs, and Supabase Auth JWT verification.

AUTH_PROVIDER=supabase (default) -> Supabase Auth issues the tokens (email/password, phone...).
    We verify them with the project's JWKS (asymmetric signing keys) or, for legacy projects,
    with SUPABASE_JWT_SECRET (HS256). `sub` = auth.users.id = users.id.
AUTH_PROVIDER=local -> our own bcrypt + HS256 JWTs (tests / offline dev).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode()[:72], password_hash.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
               "iss": "jobmate"}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@lru_cache(maxsize=1)
def _jwks() -> jwt.PyJWKClient:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    return jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json", cache_keys=True)


def decode_token(token: str) -> dict:
    if settings.auth_provider == "local":
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], issuer="jobmate")
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not configured")
        return jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
    key = _jwks().get_signing_key_from_jwt(token).key
    return jwt.decode(token, key, algorithms=["ES256", "RS256"], audience="authenticated")
