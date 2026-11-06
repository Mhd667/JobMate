"""IntelligenceLayer: the single seam the engine calls.

Implementations:
  * HeuristicIntelligence  (heuristic.py)  deterministic baseline, no LLM, always available
  * LLMIntelligence        (llm_policy.py) prompt policy + LLM + validation, falls back to heuristic
  * tomorrow: a Bayesian / VoI layer (belief over candidates x Success Model x sources)
    that implements the same methods; `next_assessment` is where decision-oriented
    value of information plugs in (AssessmentPlan.expected_value).
"""
from __future__ import annotations

from typing import Protocol

from app.intelligence import contracts as c


class IntelligenceLayer(Protocol):
    name: str

    def employer_turn(self, ctx: c.EmployerConversationContext) -> c.EmployerTurnOutput: ...
    def candidate_turn(self, ctx: c.CandidateConversationContext) -> c.CandidateTurnOutput: ...
    def build_success_model(self, ctx: c.SuccessModelContext) -> c.SuccessModelDraft: ...
    def understand_candidate(self, ctx: c.CandidateUnderstandingContext) -> c.CandidateUnderstandingOutput: ...
    def next_assessment(self, ctx: c.AssessmentContext) -> c.AssessmentPlan: ...
    def interpret_response(self, ctx: c.ResponseContext) -> c.ResponseInterpretation: ...
    def match(self, ctx: c.MatchContext) -> c.MatchAnalysis: ...
    def shortlist(self, ctx: c.ShortlistContext) -> c.ShortlistOutput: ...
    def confront(self, ctx: c.ConfrontationContext) -> c.ConfrontationOutput: ...
    def recommend(self, ctx: c.RecommendationContext) -> c.RecommendationOutput: ...


class IntelligenceUnavailable(RuntimeError):
    """No usable intelligence (e.g. no LLM key). The API answers 503 instead of inventing output."""


class IntelligenceError(RuntimeError):
    """The LLM answered but its output stayed invalid after retries, or the provider failed."""


class _Unavailable:
    name = "unavailable"

    def __init__(self, reason: str):
        self.reason = reason

    def __getattr__(self, item):
        if item.startswith("__"):
            raise AttributeError(item)

        def _fail(*_a, **_k):
            raise IntelligenceUnavailable(self.reason)
        return _fail


_instance: IntelligenceLayer | None = None


def get_intelligence() -> IntelligenceLayer:
    global _instance
    if _instance is None:
        from app.config import settings
        from app.intelligence.heuristic import HeuristicIntelligence

        mode = settings.intelligence_mode
        if mode == "heuristic":
            _instance = HeuristicIntelligence()
        elif not settings.llm_api_key:
            var = {"groq": "GROQ_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(settings.llm_provider, "LLM key")
            return _Unavailable(f"LLM non configuré : {var} manquante côté serveur.")
        else:
            from app.intelligence.llm.factory import build_provider
            from app.intelligence.llm_policy import LLMIntelligence

            fallback = HeuristicIntelligence() if settings.llm_fallback == "heuristic" else None
            _instance = LLMIntelligence(build_provider(), fallback=fallback)
    return _instance


def set_intelligence(layer: IntelligenceLayer | None) -> None:
    """Override (tests, or swapping in tomorrow's layer)."""
    global _instance
    _instance = layer
