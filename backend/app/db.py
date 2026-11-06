from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

from sqlalchemy.pool import NullPool

# Serverless (Vercel) + Supabase pooler: no client-side pool, no prepared statements.
engine = create_engine(settings.database_url, poolclass=NullPool, future=True,
                       connect_args={"prepare_threshold": None, "connect_timeout": 10})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(drop: bool = False) -> None:
    from app import models  # noqa: F401  (register tables)

    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
