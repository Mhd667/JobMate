"""Semantic validation of intelligence outputs, beyond pydantic typing.

A failing check raises ValidationFailure; the LLM policy retries once with the error, then
falls back to the heuristic layer. Some issues are repaired instead of rejected (e.g. an
unsupported 'fact' is downgraded to 'inference').
"""
from __future__ import annotations

from app.intelligence import contracts as c

_NON_FACT_SOURCES = {"conversation", "self_declared", "cv"}


class ValidationFailure(ValueError):
    pass


def _ensure(cond: bool, msg: str) -> None:
    if not cond:
        raise ValidationFailure(msg)


def guard_epistemics(drafts: list[c.EvidenceDraft]) -> list[c.EvidenceDraft]:
    """Self-declared / conversational / CV claims can never be facts."""
    for d in drafts:
        if d.epistemic_status == "fact" and d.source in _NON_FACT_SOURCES:
            d.epistemic_status = "inference"
            d.confidence = min(d.confidence, 0.7)
    return drafts


def _sm_keys(role: c.RoleView) -> set[str]:
    return {cap.key for cap in (role.success_model.critical_capabilities if role.success_model else [])}


def validate(task: str, out, ctx) -> object:
    if task == "build_success_model":
        keys = [cap.key for cap in out.critical_capabilities]
        _ensure(len(keys) >= 2, "need at least 2 critical capabilities")
        _ensure(len(set(keys)) == len(keys), "duplicate capability keys")
        for cond in out.success_conditions:
            unknown = set(cond.requires) - set(keys)
            _ensure(not unknown, f"success condition {cond.name} references unknown keys {unknown}")
    elif task == "understand_candidate":
        guard_epistemics(out.evidence)
    elif task == "next_assessment":
        keys = _sm_keys(ctx.role)
        _ensure(not keys or out.target_capability in keys,
                f"target_capability must be one of {sorted(keys)}")
        _ensure(len(out.question) > 15, "question too short")
    elif task == "interpret_response":
        # A written answer is the candidate's own account: observed behaviour in the answer can
        # support an inference, but nothing in it is verified -> never a fact in V0.
        for d in out.evidence:
            d.source = "assessment"
            if d.epistemic_status == "fact":
                d.epistemic_status = "inference"
                d.confidence = min(d.confidence, 0.7)
    elif task == "match":
        ev_ids = {e.id for e in ctx.candidate.evidence}
        out.evidence_ids = [i for i in out.evidence_ids if i in ev_ids]
        for dim in out.fit_dimensions:
            dim.evidence_ids = [i for i in dim.evidence_ids if i in ev_ids]
        _ensure(len(out.fit_dimensions) > 0, "fit_dimensions empty")
    elif task == "shortlist":
        ids = {m["candidate_id"] for m in ctx.matches}
        for e in out.shortlist:
            _ensure(e.candidate_id in ids, f"unknown candidate_id {e.candidate_id}")
        _ensure(len(out.shortlist) == min(ctx.k, len(ids)), f"shortlist must have {min(ctx.k, len(ids))} entries")
    elif task == "confront":
        ids = {cv.id for cv in ctx.candidates}
        _ensure(out.winner_candidate_id is None or out.winner_candidate_id in ids, "winner not a finalist")
        for it in out.items:
            _ensure(it.candidate_id in ids, f"item for unknown candidate {it.candidate_id}")
        for t in out.tradeoffs:
            _ensure(t.prefer_candidate_id in ids, "tradeoff prefers unknown candidate")
        _ensure(len(out.profiles) == len(ids), "one profile per finalist")
    elif task == "recommend":
        ids = {cv.id for cv in ctx.candidates}
        _ensure(out.recommended_candidate_id is None or out.recommended_candidate_id in ids,
                "recommended candidate not among candidates")
        out.alternatives = [a for a in out.alternatives if a.candidate_id in ids]
    return out
