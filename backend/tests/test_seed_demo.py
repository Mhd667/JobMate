"""The demo seed builds the expected registries (Supabase Auth replaced by fixed ids)."""
import uuid

from sqlalchemy import func, select

from app import models as m
from app.db import SessionLocal, init_db


def test_seed_demo_accounts(monkeypatch, tmp_path):
    from seed import seed_demo_accounts as sd
    init_db(drop=True)
    csv = tmp_path / "users.csv"
    lines = ["role,email,phone,password"]
    lines += [f"employer,employer0{i}@jobmate.test,+22100000010{i},x" for i in range(1, 6)]
    lines += [f"candidate,candidate{i:02d}@jobmate.test,+2210000002{i:02d},x" for i in range(1, 11)]
    csv.write_text("\n".join(lines), encoding="utf-8")

    class FakeAuth:
        service = "fake"
        def ensure(self, role, email, phone, password):
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, email))

    monkeypatch.setattr(sd, "Auth", FakeAuth)
    for _ in range(2):  # running twice changes nothing
        monkeypatch.setattr("sys.argv", ["seed", "--csv", str(csv)])
        sd.main()

    db = SessionLocal()
    count = lambda model: db.scalar(select(func.count()).select_from(model))  # noqa: E731
    assert count(m.User) == 15 and count(m.Company) == 5 and count(m.Role) == 5
    assert count(m.Candidate) == 9 and count(m.Match) == 0           # matching is left to the tester
    assert count(m.SuccessModel) == 5                                 # every offer can be matched against
    baobab = db.scalars(select(m.Company).where(m.Company.name == "Baobab Conseil")).one()
    assert not db.scalars(select(m.Role).where(m.Role.company_id == baobab.id)).all()
    blank = db.scalars(select(m.User).where(m.User.email == "candidate10@jobmate.test")).one()
    assert blank.role == m.UserRole.candidate
    assert db.scalars(select(m.Candidate).where(m.Candidate.user_id == blank.id)).first() is None
    assert count(m.Evidence) > 0 and count(m.Conversation) == 5 + 9
    db.close()
