"""LLM path: prompt policy -> provider -> validation -> fallback, without network."""
import json

from app.intelligence import contracts as c
from app.intelligence.heuristic import HeuristicIntelligence
from app.intelligence.interface import set_intelligence
from app.intelligence.llm.scripted import ScriptedProvider
from app.intelligence.llm_policy import LLMIntelligence


def _ctx_json(user: str) -> dict:
    return json.loads(user.split("\n", 1)[1].split("\n\nTa réponse précédente")[0])


def test_llm_success_and_epistemic_guard(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    prov = ScriptedProvider()
    # the LLM claims a fact from a self-declaration -> must be downgraded
    prov.on("interpret_response", {
        "summary": "ok", "observed_behaviors": ["écoute"], "confidence": 0.8,
        "evidence": [{"subject_key": "conflict_management", "claim": "gère les conflits", "evidence": "dit-il",
                      "source": "self_declared", "epistemic_status": "fact", "confidence": 0.95}]})
    prov.on("next_assessment", lambda s, u: {
        "target_capability": "conflict_management", "objective": "tester", "question_type": "simulation",
        "question": "Un commerçant furieux vous appelle : que dites-vous ?", "expected_evidence": ["désescalade"],
        "rationale": "aucune preuve", "expected_value": 0.42})
    set_intelligence(LLMIntelligence(prov, fallback=HeuristicIntelligence(), max_retries=1))
    cid = ids["candidates"]["Aminata Diallo"]
    req = client.post(f"/roles/{ids['role_id']}/candidates/{cid}/assessments/next", headers=emp).json()
    assert req["expected_value"] == 0.42 and req["produced_by"].startswith("llm:scripted")
    # the context sent to the LLM is the controlled decision context, with coverage
    ctx = _ctx_json(prov.calls[-1]["user"])
    assert {"role", "candidate"} <= set(ctx) and ctx["candidate"]["coverage"]
    assert "password_hash" not in prov.calls[-1]["user"]
    resp = client.post(f"/assessments/{req['id']}/responses", headers=emp, json={"response": "Je reste calme."}).json()
    assert resp["evidence"][0]["status"] == "inference"  # downgraded, never a fact
    assert resp["evidence"][0]["confidence"] <= 0.7


def test_llm_invalid_output_retries_then_falls_back(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    prov = ScriptedProvider()

    def bad_confront(system, user):
        ctx = _ctx_json(user)
        cands = [x["id"] for x in ctx["candidates"]]
        return {"comparison_dimensions": ["x"], "profiles": [{"candidate_id": i, "headline": "h"} for i in cands],
                "items": [], "tradeoffs": [], "winner_candidate_id": "not-a-finalist", "reasoning": "r",
                "uncertainties": []}

    prov.on("confront", bad_confront)
    set_intelligence(LLMIntelligence(prov, fallback=HeuristicIntelligence(), max_retries=1))
    r = client.post(f"/roles/{ids['role_id']}/confrontations", headers=emp, json={})
    assert r.status_code == 201, r.text
    conf = r.json()
    assert prov.counts["confront"] == 2                      # first try + one corrective retry
    assert "invalide" in prov.calls[-1]["user"]              # the error was fed back
    assert conf["produced_by"] == "heuristic:fallback"
    assert conf["winner_candidate_id"] == ids["candidates"]["Aminata Diallo"]


def test_contract_schemas_are_tool_compatible():
    for model in (c.SuccessModelDraft, c.AssessmentPlan, c.MatchAnalysis, c.ConfrontationOutput,
                  c.RecommendationOutput, c.EmployerTurnOutput):
        schema = model.model_json_schema()
        assert schema["type"] == "object" and schema["properties"]
