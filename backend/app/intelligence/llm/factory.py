from __future__ import annotations

from app.config import settings


def build_provider():
    if settings.llm_provider == "groq":
        from app.intelligence.llm.groq_provider import GroqProvider
        return GroqProvider(settings.groq_api_key, settings.llm_model)
    if settings.llm_provider == "anthropic":
        from app.intelligence.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(settings.anthropic_api_key, settings.llm_model)
    raise RuntimeError(f"unknown LLM_PROVIDER={settings.llm_provider}")
