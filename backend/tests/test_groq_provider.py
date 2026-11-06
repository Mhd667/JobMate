import json

import httpx

from app.intelligence import contracts as c
from app.intelligence.llm import groq_provider
from app.intelligence.llm.groq_provider import GroqProvider, inline_refs


def test_inline_refs_removes_all_refs():
    s = json.dumps(inline_refs(c.ConfrontationOutput.model_json_schema()))
    assert "$ref" not in s and "$defs" not in s


def test_groq_forced_tool_call(monkeypatch):
    seen = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        seen.update(url=url, body=json, headers=headers)
        args = {"target_capability": "persuasion", "objective": "o", "question_type": "simulation",
                "question": "Faites votre pitch au commerçant.", "expected_evidence": ["x"], "rationale": "r"}
        return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
            {"function": {"name": "submit_next_assessment", "arguments": __import__("json").dumps(args)}}]}}]})

    monkeypatch.setattr(groq_provider.httpx, "post", fake_post)
    out = GroqProvider("k", "openai/gpt-oss-120b").generate_json(
        system="s", user="u", schema=c.AssessmentPlan, task="next_assessment")
    assert out["target_capability"] == "persuasion"
    assert seen["body"]["tool_choice"]["function"]["name"] == "submit_next_assessment"
    assert seen["headers"]["Authorization"] == "Bearer k"
