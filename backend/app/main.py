from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, candidates, companies, conversations, decisions
from app.config import settings
from app.db import init_db
from app.intelligence.interface import IntelligenceError, IntelligenceUnavailable, get_intelligence

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app):
    if settings.auto_create_tables:
        init_db()  # local dev only; production schema = sql/schema.sql applied as a migration
    yield


app = FastAPI(
    title="JobMate API",
    version="0.2.0",
    description="Intelligence de recrutement conversationnelle — MVP. "
                "Company/Role understanding → Candidate understanding → Evidence → Assessment → "
                "Matching → Top 3 → Confrontation → Recommendation.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(IntelligenceUnavailable)
def _unavailable(_req: Request, exc: IntelligenceUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "intelligence_unavailable"})


@app.exception_handler(IntelligenceError)
def _intel_error(_req: Request, exc: IntelligenceError):
    return JSONResponse(status_code=502, content={"detail": str(exc), "code": "intelligence_error"})

for r in (auth.router, companies.router, candidates.router, decisions.router, conversations.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health() -> dict:
    intel = get_intelligence()
    db_ok = True
    try:
        from sqlalchemy import text

        from app.db import engine
        with engine.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        logging.getLogger("jobmate").error("database check failed: %s", type(exc).__name__ + ": " + str(exc)[:200])
    return {"status": "ok" if db_ok and intel.name != "unavailable" else "degraded", "database": db_ok,
            "intelligence": intel.name, "auth_provider": settings.auth_provider,
            "llm_model": settings.llm_model if intel.name == "llm" else None}
