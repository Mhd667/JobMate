"""LLM-backed Intelligence Layer.

Context (pydantic) -> prompt policy -> LLM (structured output) -> pydantic + semantic validation.
On repeated failure, the heuristic layer answers so the product never breaks mid-demo; the
output's `produced_by` (set by the engine via `last_producer`) records who answered.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.intelligence import contracts as c
from app.intelligence.llm.base import LLMError
from app.intelligence.prompts import PROMPT_VERSION, system_prompt
from app.intelligence.validation import ValidationFailure, validate

log = logging.getLogger("jobmate.intelligence")

_OUTPUTS: dict[str, type[BaseModel]] = {
    "employer_turn": c.EmployerTurnOutput,
    "candidate_turn": c.CandidateTurnOutput,
    "build_success_model": c.SuccessModelDraft,
    "understand_candidate": c.CandidateUnderstandingOutput,
    "next_assessment": c.AssessmentPlan,
    "interpret_response": c.ResponseInterpretation,
    "match": c.MatchAnalysis,
    "shortlist": c.ShortlistOutput,
    "confront": c.ConfrontationOutput,
    "recommend": c.RecommendationOutput,
}


class LLMIntelligence:
    name = "llm"

    def __init__(self, provider, fallback=None, max_retries: int | None = None):
        self.provider = provider
        self.fallback = fallback
        self.max_retries = settings.llm_max_retries if max_retries is None else max_retries
        self.last_producer = self.name

    # ------------------------------------------------------------------ core loop
    def _run(self, task: str, ctx: BaseModel, fallback_method: str):
        schema = _OUTPUTS[task]
        user = ("Contexte de décision (JSON) :\n"
                + json.dumps(ctx.model_dump(mode="json"), ensure_ascii=False, indent=1))
        error: str | None = None
        for _attempt in range(self.max_retries + 1):
            prompt = user if error is None else (
                user + f"\n\nTa réponse précédente était invalide : {error}\nCorrige-la.")
            try:
                raw = self.provider.generate_json(system=system_prompt(task), user=prompt,
                                                  schema=schema, task=task)
                out = validate(task, schema.model_validate(raw), ctx)
                self.last_producer = f"llm:{getattr(self.provider, 'name', '?')}:{PROMPT_VERSION}"
                return out
            except (ValidationError, ValidationFailure) as exc:
                error = str(exc)[:800]
                log.warning("intelligence %s invalid output: %s", task, error)
            except LLMError as exc:  # e.g. provider rejected a malformed tool call: retry once
                log.warning("intelligence %s provider error: %s", task, exc)
                error = str(exc)[:300]
        if self.fallback is None:
            from app.intelligence.interface import IntelligenceError
            raise IntelligenceError(f"La tâche « {task} » a échoué : {error or 'fournisseur LLM injoignable'}")
        self.last_producer = "heuristic:fallback"
        return getattr(self.fallback, fallback_method)(ctx)

    # ------------------------------------------------------------------ interface
    def employer_turn(self, ctx):
        return self._run("employer_turn", ctx, "employer_turn")

    def candidate_turn(self, ctx):
        return self._run("candidate_turn", ctx, "candidate_turn")

    def build_success_model(self, ctx):
        return self._run("build_success_model", ctx, "build_success_model")

    def understand_candidate(self, ctx):
        return self._run("understand_candidate", ctx, "understand_candidate")

    def next_assessment(self, ctx):
        return self._run("next_assessment", ctx, "next_assessment")

    def interpret_response(self, ctx):
        return self._run("interpret_response", ctx, "interpret_response")

    def match(self, ctx):
        return self._run("match", ctx, "match")

    def shortlist(self, ctx):
        return self._run("shortlist", ctx, "shortlist")

    def confront(self, ctx):
        return self._run("confront", ctx, "confront")

    def recommend(self, ctx):
        return self._run("recommend", ctx, "recommend")
