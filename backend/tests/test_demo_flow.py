"""The full V0 story on the seeded data, with the heuristic intelligence."""


def test_end_to_end_story(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    rid, c = ids["role_id"], ids["candidates"]

    card = client.get(f"/roles/{rid}/card", headers=emp).json()
    assert card["success_model"]["priorities"]["primary"] == "immediate_performance"

    # adaptive assessment: different targets for different evidence profiles
    targets = {}
    for name in ["Aminata Diallo", "Ousmane Ndiaye", "Fatou Sow"]:
        r = client.post(f"/roles/{rid}/candidates/{c[name]}/assessments/next", headers=emp)
        assert r.status_code == 201, r.text
        targets[name] = r.json()
    assert targets["Aminata Diallo"]["target_capability"] == "conflict_management"
    assert targets["Ousmane Ndiaye"]["target_capability"] == "persuasion"
    assert targets["Ousmane Ndiaye"]["question_type"] in ("simulation", "situational")
    assert targets["Aminata Diallo"]["question"] != targets["Ousmane Ndiaye"]["question"]

    # candidate answers -> new evidence, not a fact
    cand = login("aminata@jobmate.demo")
    pending = client.get("/candidates/me/assessments", headers=cand).json()
    assert len(pending) == 1
    resp = client.post(f"/assessments/{pending[0]['id']}/responses", headers=cand, json={
        "response": "J'ai laissé le client parler, puis j'ai reconnu le problème et j'ai obtenu un remplacement "
                    "sous 48h. Il est resté client et a doublé ses commandes en 3 mois, malgré sa colère au départ."})
    assert resp.status_code == 201, resp.text
    ev = resp.json()["evidence"][0]
    assert ev["status"] in ("inference", "hypothesis")
    # second answer to the same request is refused
    assert client.post(f"/assessments/{pending[0]['id']}/responses", headers=cand,
                       json={"response": "encore"}).status_code == 409

    # matching is structured, not just a score
    matches = client.post(f"/roles/{rid}/matches/run", headers=emp, json={}).json()
    assert len(matches) == 5
    m0 = matches[0]
    for key in ("fit_summary", "fit_dimensions", "strengths", "gaps", "risks", "uncertainties", "evidence",
                "confidence"):
        assert key in m0
    fatou = next(x for x in matches if x["candidate_name"] == "Fatou Sow")
    assert any("Disponible" in r for r in fatou["risks"])

    # top 3
    sl = client.post(f"/roles/{rid}/shortlist", headers=emp, json={"k": 3}).json()
    names = [e["full_name"] for e in sl["shortlist"]]
    assert set(names) == {"Aminata Diallo", "Ousmane Ndiaye", "Fatou Sow"}
    assert names[0] == "Aminata Diallo"
    assert all(e["reason"] for e in sl["shortlist"]) and len(sl["excluded"]) == 2

    # confrontation from the conversation
    conv = client.post("/conversations", headers=emp, json={"kind": "employer", "company_id": ids["company_id"],
                                                            "role_id": rid}).json()
    turn = client.post(f"/conversations/{conv['id']}/messages", headers=emp,
                       json={"content": "Compare-moi les trois derniers candidats."}).json()
    assert turn["intent"] == "request_confrontation"
    conf = client.get(f"/confrontations/{turn['artifacts'][0]['id']}", headers=emp).json()
    assert conf["winner_candidate_id"] == c["Aminata Diallo"]
    prefer = {t["if_priority"]: t["prefer_candidate_id"] for t in conf["tradeoffs"]}
    assert prefer["learning_potential"] == c["Ousmane Ndiaye"]
    assert prefer["domain_expertise"] == c["Fatou Sow"]
    assert len(conf["items"]) >= 3 * 5
    headlines = " ".join(p["headline"] for p in conf["profiles"])
    assert "potentiel" in headlines and "expertise sectorielle" in headlines

    # recommendation, separate from comparison
    rec = client.post(f"/roles/{rid}/recommendations", headers=emp,
                      json={"confrontation_id": conf["id"]}).json()
    assert rec["recommended_candidate_id"] == c["Aminata Diallo"]
    assert rec["reasoning_summary"].startswith("Je recommande Aminata Diallo")
    assert {a["candidate_id"] for a in rec["alternatives"]} == {c["Ousmane Ndiaye"], c["Fatou Sow"]}
    assert client.get(f"/roles/{rid}/recommendations/latest", headers=emp).json()["id"] == rec["id"]


def test_employer_conversation_builds_role_identity(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    role = client.post(f"/companies/{ids['company_id']}/roles", headers=emp, json={"title": "Support lead"}).json()
    conv = client.post("/conversations", headers=emp, json={"kind": "employer", "company_id": ids["company_id"],
                                                            "role_id": role["id"]}).json()
    msgs = ["Beaucoup de commerçants partent après un incident.", "Garder les commerçants actifs.",
            "Churn sous 10 % ; 30 % en premium.", "Appeler les commerçants à risque ; traiter les litiges.",
            "Démarrage en février.", "Le support et le produit.",
            "Les meilleurs restent calmes face à un commerçant en colère et savent le convaincre."]
    for msg in msgs:
        r = client.post(f"/conversations/{conv['id']}/messages", headers=emp, json={"content": msg})
        assert r.status_code == 200, r.text
    card = client.get(f"/roles/{role['id']}/card", headers=emp).json()
    assert card["role_identity"]["mission"] == "Garder les commerçants actifs."
    assert card["missing_fields"] == []
    turn = client.post(f"/conversations/{conv['id']}/messages", headers=emp,
                       json={"content": "Construis le modèle de réussite."}).json()
    assert turn["intent"] == "request_success_model"
    sm = client.get(f"/roles/{role['id']}/success-model", headers=emp).json()
    keys = {x["key"] for x in sm["critical_capabilities"]}
    assert {"persuasion", "conflict_management"} <= keys
    for cond in sm["success_conditions"]:
        assert set(cond["requires"]) <= keys


def test_candidate_conversation_keeps_self_claims_as_hypotheses(demo):
    client, _, _ = demo
    tok = client.post("/auth/signup", json={"email": "awa@t.io", "password": "password1",
                                            "role": "candidate"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/candidates", headers=h, json={"full_name": "Awa Mbaye"})
    conv = client.post("/conversations", headers=h, json={"kind": "candidate"}).json()
    client.post(f"/conversations/{conv['id']}/messages", headers=h, json={"content": "Commercial en fintech."})
    client.post(f"/conversations/{conv['id']}/messages", headers=h,
                json={"content": "J'ai convaincu 50 commerçants d'ouvrir un compte."})
    prof = client.get("/candidates/me", headers=h).json()
    assert prof["professional_identity"]["career_direction"] == "Commercial en fintech."
    assert prof["evidence"] and all(e["epistemic_status"] == "hypothesis" and e["source"] == "self_declared"
                                    for e in prof["evidence"])
