"""Runtime configuration, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv() -> None:
    """Load backend/.env into the environment (real env vars win). No extra dependency."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), value)


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Any Postgres works: local, Docker, or Supabase (use the Supabase "connection string").
    database_url: str = field(default_factory=lambda: _env(
        "DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/jobmate"))

    # Create tables at startup (local dev). In production the schema is applied as a migration.
    auto_create_tables: bool = field(default_factory=lambda: _env("AUTO_CREATE_TABLES", "false") == "true")

    # Auth: "supabase" = trust JWTs issued by Supabase Auth (JWKS, or legacy SUPABASE_JWT_SECRET).
    #       "local"    = own users table + bcrypt + JWT (tests / offline dev only).
    auth_provider: str = field(default_factory=lambda: _env("AUTH_PROVIDER", "supabase"))
    supabase_url: str = field(default_factory=lambda: _env("SUPABASE_URL").rstrip("/"))
    cors_origins: str = field(default_factory=lambda: _env("CORS_ORIGINS", "*"))
    jwt_secret: str = field(default_factory=lambda: _env("JWT_SECRET", "dev-secret-change-me-please-32bytes!"))
    jwt_ttl_minutes: int = field(default_factory=lambda: int(_env("JWT_TTL_MINUTES", "720")))
    supabase_jwt_secret: str = field(default_factory=lambda: _env("SUPABASE_JWT_SECRET"))

    # Intelligence: "llm" (Claude via the Anthropic API) is the product. "heuristic" (deterministic,
    # no LLM) exists for tests and offline development only and must be chosen explicitly.
    intelligence_mode: str = field(default_factory=lambda: _env("INTELLIGENCE_MODE", "llm"))
    # On invalid / failed LLM output: "error" (default, the API says so) or "heuristic".
    llm_fallback: str = field(default_factory=lambda: _env("LLM_FALLBACK", "error"))
    # LLM provider: "groq" (OpenAI-compatible API) or "anthropic". LLM_MODEL overrides the default model.
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "groq"))
    llm_model_override: str = field(default_factory=lambda: _env("LLM_MODEL"))
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    groq_api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY"))
    llm_max_retries: int = field(default_factory=lambda: int(_env("LLM_MAX_RETRIES", "1")))

    language: str = field(default_factory=lambda: _env("JOBMATE_LANGUAGE", "fr"))


DEFAULT_MODELS = {"groq": "openai/gpt-oss-120b", "anthropic": "claude-sonnet-5-5"}


def _llm_api_key(self: Settings) -> str:
    return {"groq": self.groq_api_key, "anthropic": self.anthropic_api_key}.get(self.llm_provider, "")


def _llm_model(self: Settings) -> str:
    return self.llm_model_override or DEFAULT_MODELS.get(self.llm_provider, "")


Settings.llm_api_key = property(_llm_api_key)  # type: ignore[attr-defined]
Settings.llm_model = property(_llm_model)  # type: ignore[attr-defined]

settings = Settings()
