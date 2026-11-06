"""Chat-card protocol: the employer and candidate journeys of the UX spec, end to end (heuristic layer)."""


def _send(client, h, conv_id, text):
    r = client.post(f"/conversations/{conv_id}/messages", headers=h, json={"content": text})
    assert r.status_code == 200, r.text
    return r.json()


def _act(client, h, conv_id, card, action, payload=None):
    r = client.post(f"/conversations/{conv_id}/actions", headers=h,
                    json={"card_id": card["id"], "action": action, "payload": payload or {}})
    assert r.status_code == 200, r.text
    return r.json()


def _card(turn, type_):
    found = [c for c in turn["cards"] if c["type"] == type_]
    assert found, f"no {type_} card in {[c['type'] for c in turn['cards']]}"
    return found[0]


def test_employer_and_candidate_journeys(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    conv = client.post("/conversations", headers=emp, json={"kind": "employer"}).json()
    assert conv["role_id"] and conv["messages"][0]["content"].startswith("Bonjour, je suis JobMate")
    cid = conv["id"]

    # Conversation first: missions are given in natural language, no checkbox card by default.
    _send(client, emp, cid, "Notre commerciale part en congé maternité, poste vacant 6 mois.")
    _send(client, emp, cid, "Garder nos commerçants actifs et en signer de nouveaux.")
    turn = _send(client, emp, cid, "Prospection, relances et gestion des réclamations.")
    assert not any(c["type"] == "missions" for c in turn["cards"])
    turn = _send(client, emp, cid, "Les meilleurs restent calmes face à un commerçant en colère et savent convaincre.")
    for _ in range(3):  # languages, availability... until the summary appears
        if turn["cards"]:
            break
        turn = _send(client, emp, cid, "Français et wolof, dès que possible.")
    summary = _card(turn, "role_summary")
    assert any("relances" in x for x in summary["data"]["missions"]) and summary["data"]["criteria"]

    # The search can be started in words as well as with the card's button.
    turn = _send(client, emp, cid, "C'est bon, lance la recherche.")
    assert turn["flow_state"] == "results"
    hist = client.get(f"/conversations/{cid}", headers=emp).json()["messages"]
    assert all(c["status"] == "done" for msg in hist for c in msg["meta"].get("cards", []) if c["type"] == "role_summary")
    cands = _card(turn, "candidates")["data"]["candidates"]
    _card(turn, "success_model")
    panel = _card(turn, "next_steps")
    assert 1 <= len(cands) <= 3 and all(c["match_score"] is not None and c["name"] for c in cands)

    top = cands[0]
    turn = _act(client, emp, cid, _card(turn, "candidates"), "candidate.interview", {"candidate_id": top["candidate_id"]})
    assert turn["intent"] == "employer_decision"
    turn = _act(client, emp, cid, panel, "next.refine")
    assert turn["flow_state"] == "discovery"

    # Confrontation and recommendation on request; the human still decides.
    turn = _send(client, emp, cid, "Compare-moi les trois finalistes")
    conf = _card(turn, "confrontation")
    turn = _act(client, emp, cid, conf, "recommend")
    rec = _card(turn, "recommendation")
    assert rec["data"]["summary"]

    # The shortlisted candidate got the offer in their own chat.
    email = {"Aminata Diallo": "aminata", "Ousmane Ndiaye": "ousmane", "Fatou Sow": "fatou",
             "Moussa Fall": "moussa", "Khady Ba": "khady"}[top["name"]] + "@jobmate.demo"
    ch = login(email)
    convs = client.get("/conversations", headers=ch).json()
    detail = client.get(f"/conversations/{convs[0]['id']}", headers=ch).json()
    offers = [c for msg in detail["messages"] for c in msg["meta"].get("cards", []) if c["type"] == "offer"]
    assert offers and offers[0]["data"]["explanation"] is not None
    assert any("entretien" in msg["content"] for msg in detail["messages"])

    apps = client.get("/candidates/me/applications", headers=ch).json()
    assert apps and apps[0]["status"] == "interview" and apps[0]["status_label"] == "Entretien"
    turn = _act(client, ch, detail["id"], offers[0], "offer.interested")
    q1 = _card(turn, "assessment")
    assert turn["flow_state"] == "assessment" and q1["data"]["index"] == 1 and q1["data"]["total"] == 2
    turn = _send(client, ch, detail["id"], "Je l'ai écouté, reformulé son problème, puis proposé une solution "
                                           "concrète et rappelé le lendemain : il est resté client.")
    assert _card(turn, "assessment")["data"]["index"] == 2
    turn = _send(client, ch, detail["id"], "Je commence par comprendre son activité, puis je montre ce qu'il gagne.")
    assert turn["flow_state"] == "waiting" and not turn["cards"]
    assert "en attente" in turn["assistant_message"]["content"]
    emp_hist = client.get(f"/conversations/{cid}", headers=emp).json()["messages"]
    assert any(msg["meta"].get("intent") == "candidate_update" for msg in emp_hist)
    prof = client.get("/candidates/me", headers=ch).json()
    assert all(e["epistemic_status"] != "fact" for e in prof["evidence"] if e["source"] == "assessment")


def test_candidate_sources_card_and_cv_upload(demo):
    client, _, _ = demo
    tok = client.post("/auth/signup", json={"email": "awa2@t.io", "password": "password1"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    me = client.post("/auth/role", headers=h, json={"role": "candidate", "full_name": "Awa Mbaye"}).json()
    assert me["next_step"] == "candidate_home"
    conv = client.post("/conversations", headers=h, json={"kind": "candidate"}).json()
    _send(client, h, conv["id"], "Je cherche un poste de commerciale en fintech à Dakar.")
    turn = _send(client, h, conv["id"], "Je sais convaincre et je reste calme avec les clients difficiles.")
    assert not turn["cards"]  # no card pushed: sources are optional and offered in words
    # Third answer: no more questions, the optional sources card is offered once.
    turn = _send(client, h, conv["id"], "Un CDI à Dakar. Mon profil : https://www.linkedin.com/in/awa-mbaye et x.com/awa")
    assert turn["updates"][-1]["entity"] == "candidate_sources"
    assert {x["kind"] for x in turn["updates"][-1]["added"]} == {"linkedin", "x"}
    src = _card(turn, "sources")
    turn = _send(client, h, conv["id"], "Merci !")
    assert not turn["cards"]
    # Profile ready -> matched against open offers that have a Success Model; the offer arrives in the chat.
    apps = client.get("/candidates/me/applications", headers=h).json()
    assert len(apps) == 1 and apps[0]["status"] == "new"
    hist = client.get(f"/conversations/{conv['id']}", headers=h).json()["messages"]
    assert any(c["type"] == "offer" for msg in hist for c in msg["meta"].get("cards", []))
    assert client.post("/candidates/me/sources", headers=h, json={"kind": "linkedin", "url": "javascript:x"}).status_code == 422
    r = client.post("/candidates/me/sources", headers=h, json={"kind": "linkedin", "url": "https://linkedin.com/in/awa"})
    assert r.status_code == 200 and all(x["verified"] is False for x in r.json()["sources"])
    assert any("awa-mbaye" in x["url"] for x in r.json()["sources"]) is False  # replaced by the new LinkedIn link
    cv = ("Awa Mbaye, commerciale terrain chez Wave (2022-2025). Ouverture de 120 comptes marchands, "
          "gestion des réclamations, formation des agents.").encode()
    r = client.post("/candidates/me/cv", headers=h, files={"file": ("cv.txt", cv, "text/plain")})
    assert r.status_code == 200 and r.json()["cv_filename"] == "cv.txt"
    assert client.post("/candidates/me/cv", headers=h, files={"file": ("cv.exe", b"x" * 40)}).status_code == 415
    turn = _act(client, h, conv["id"], src, "sources.submit")
    assert turn["intent"] == "sources.submit"
