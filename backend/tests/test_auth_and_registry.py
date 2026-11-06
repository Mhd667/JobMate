from sqlalchemy import select

from app import models as m
from app.db import SessionLocal


def test_signup_login_and_password_is_hashed(demo):
    client, _, _ = demo
    r = client.post("/auth/signup", json={"email": "New@Test.io", "password": "s3cret-pass", "role": "employer",
                                          "phone_number": "+221700000001"})
    assert r.status_code == 201
    with SessionLocal() as db:
        u = db.scalars(select(m.User).where(m.User.email == "new@test.io")).one()
        assert u.password_hash.startswith("$2") and "s3cret-pass" not in u.password_hash
    assert client.post("/auth/login", json={"email": "new@test.io", "password": "wrong-pass"}).status_code == 401
    tok = client.post("/auth/login", json={"email": "new@test.io", "password": "s3cret-pass"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["user"]
    assert me["role"] == "employer" and me["phone_number"] == "+221700000001"
    assert client.get("/auth/me").status_code == 401


def test_role_separation_and_ownership(demo):
    client, ids, login = demo
    cand = login("aminata@jobmate.demo")
    assert client.get("/candidates", headers=cand).status_code == 403
    assert client.get(f"/roles/{ids['role_id']}/card", headers=cand).status_code == 403
    other = client.post("/auth/signup", json={"email": "x@y.io", "password": "password1", "role": "employer"}).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/roles/{ids['role_id']}/card", headers=h).status_code == 403
    # a candidate cannot read another candidate
    assert client.get(f"/candidates/{ids['candidates']['Fatou Sow']}", headers=cand).status_code == 403
    assert client.get(f"/candidates/{ids['candidates']['Aminata Diallo']}", headers=cand).status_code == 200


def test_identities_are_versioned(demo):
    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    rid = ids["role_id"]
    v1 = client.get(f"/roles/{rid}/identity", headers=emp).json()
    v2 = client.patch(f"/roles/{rid}/identity", headers=emp, json={"objectives": ["100 commerçants"]}).json()
    assert v2["version"] == v1["version"] + 1 and v2["objectives"] == ["100 commerçants"]
    assert v2["mission"] == v1["mission"]  # untouched fields carried over
    hist = client.get(f"/companies/{ids['company_id']}/identity/history", headers=emp).json()
    assert len(hist) >= 1


def test_role_choice_flow(demo):
    client, _, _ = demo
    tok = client.post("/auth/signup", json={"email": "fresh@t.io", "password": "password1"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    me = client.get("/auth/me", headers=h).json()
    assert me["user"]["role"] is None and me["next_step"] == "choose_role"
    assert client.get("/companies", headers=h).status_code == 409          # no role yet
    me = client.post("/auth/role", headers=h, json={"role": "employer", "phone_number": "+221701112233"}).json()
    # The company is created with the role choice: the employer lands directly in the chat.
    assert me["user"]["role"] == "employer" and me["next_step"] == "employer_home" and me["company_id"]
    assert client.post("/auth/role", headers=h, json={"role": "candidate"}).status_code == 409


def test_no_llm_means_explicit_503_not_invented_output(demo, monkeypatch):
    from app.config import settings
    from app.intelligence.interface import set_intelligence

    client, ids, login = demo
    emp = login("employer@jobmate.demo")
    object.__setattr__(settings, "intelligence_mode", "llm")
    object.__setattr__(settings, "anthropic_api_key", "")
    object.__setattr__(settings, "groq_api_key", "")
    set_intelligence(None)
    try:
        r = client.post(f"/roles/{ids['role_id']}/success-model/generate", headers=emp)
        assert r.status_code == 503 and r.json()["code"] == "intelligence_unavailable"
        assert client.get("/health").json()["status"] == "degraded"
    finally:
        object.__setattr__(settings, "intelligence_mode", "heuristic")
        set_intelligence(None)
