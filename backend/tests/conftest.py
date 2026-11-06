import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/jobmate_test")
os.environ["INTELLIGENCE_MODE"] = "heuristic"   # tests only: the product requires the LLM
os.environ["AUTH_PROVIDER"] = "local"
os.environ["AUTO_CREATE_TABLES"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.intelligence.interface import set_intelligence  # noqa: E402
from app.main import app  # noqa: E402
from tests.fixture_data import seed  # noqa: E402


@pytest.fixture()
def demo():
    set_intelligence(None)
    ids = seed(reset=True)
    client = TestClient(app)

    def login(email):
        r = client.post("/auth/login", json={"email": email, "password": "jobmate-demo"})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    yield client, ids, login
    set_intelligence(None)
