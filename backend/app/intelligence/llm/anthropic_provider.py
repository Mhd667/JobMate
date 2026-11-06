"""Claude via the Anthropic API. Structured output is obtained by forcing a single tool
whose input_schema is the pydantic JSON schema of the expected output."""
from __future__ import annotations

from pydantic import BaseModel

from app.intelligence.llm.base import LLMError


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096, timeout: float = 90.0):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens

    def generate_json(self, *, system: str, user: str, schema: type[BaseModel], task: str) -> dict:
        tool = {
            "name": "submit_" + task,
            "description": f"Submit the structured result for task '{task}'.",
            "input_schema": schema.model_json_schema(),
        }
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )
        except Exception as exc:  # network, auth, rate limit...
            raise LLMError(f"anthropic call failed: {exc}") from exc
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input)
        raise LLMError("no tool_use block in response")
