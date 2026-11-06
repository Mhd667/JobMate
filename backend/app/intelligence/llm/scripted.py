"""Deterministic provider for tests: returns pre-registered payloads per task."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from pydantic import BaseModel


class ScriptedProvider:
    name = "scripted"

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[str, str], dict]] = {}
        self.calls: list[dict] = []
        self.counts: dict[str, int] = defaultdict(int)

    def on(self, task: str, handler: Callable[[str, str], dict] | dict) -> "ScriptedProvider":
        self.handlers[task] = handler if callable(handler) else (lambda s, u, h=handler: h)
        return self

    def generate_json(self, *, system: str, user: str, schema: type[BaseModel], task: str) -> dict:
        self.calls.append({"task": task, "system": system, "user": user})
        self.counts[task] += 1
        if task not in self.handlers:
            from app.intelligence.llm.base import LLMError
            raise LLMError(f"no scripted answer for {task}")
        return self.handlers[task](system, user)
