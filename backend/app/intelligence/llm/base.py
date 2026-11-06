"""LLM provider abstraction: one method, structured JSON in -> validated object out."""
from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str

    def generate_json(self, *, system: str, user: str, schema: type[BaseModel],
                      task: str) -> dict:
        """Return a dict that SHOULD match `schema` (validation is done by the caller)."""
        ...
