"""Groq (OpenAI-compatible chat completions). Structured output = one forced function call whose
parameters are the pydantic JSON schema of the expected output (refs inlined)."""
from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from app.intelligence.llm.base import LLMError

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def inline_refs(schema: dict) -> dict:
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {k: walk(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096, timeout: float = 90.0):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate_json(self, *, system: str, user: str, schema: type[BaseModel], task: str) -> dict:
        fn = "submit_" + task
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "tools": [{"type": "function", "function": {
                "name": fn, "description": f"Submit the structured result for task '{task}'.",
                "parameters": inline_refs(schema.model_json_schema())}}],
            "tool_choice": {"type": "function", "function": {"name": fn}},
        }
        try:
            r = httpx.post(GROQ_URL, json=payload, timeout=self.timeout,
                           headers={"Authorization": f"Bearer {self.api_key}"})
        except httpx.HTTPError as exc:
            raise LLMError(f"groq call failed: {exc}") from exc
        if r.status_code >= 400:
            raise LLMError(f"groq {r.status_code}: {r.text[:400]}")
        try:
            call = r.json()["choices"][0]["message"]["tool_calls"][0]["function"]
            return json.loads(call["arguments"])
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise LLMError(f"groq returned no usable tool call: {r.text[:300]}") from exc
