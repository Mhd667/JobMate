"""Registry helpers: serialization and versioned identities."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

_META = {"id", "created_at", "updated_at", "version"}


def to_dict(obj, exclude: set[str] | None = None) -> dict:
    if obj is None:
        return {}
    out = {}
    for col in obj.__table__.columns:
        if exclude and col.name in exclude:
            continue
        v = getattr(obj, col.name)
        if isinstance(v, uuid.UUID):
            v = str(v)
        elif isinstance(v, Enum):
            v = v.value
        elif isinstance(v, (datetime, date)):
            v = v.isoformat()
        out[col.name] = v
    return out


# Which table / FK each versioned identity uses.
VERSIONED = {
    m.CompanyIdentity: "company_id",
    m.RoleIdentity: "role_id",
    m.SuccessModel: "role_id",
    m.ProfessionalIdentity: "candidate_id",
}


def current(db: Session, model, owner_id) -> object | None:
    fk = VERSIONED[model]
    return db.scalars(select(model).where(getattr(model, fk) == owner_id)
                      .order_by(model.version.desc()).limit(1)).first()


def history(db: Session, model, owner_id) -> list:
    fk = VERSIONED[model]
    return list(db.scalars(select(model).where(getattr(model, fk) == owner_id).order_by(model.version)))


def new_version(db: Session, model, owner_id, patch: dict, produced_by: str,
                merge_lists: bool = False) -> object:
    """Insert version N+1 = current + patch. With merge_lists, list fields are extended
    (deduplicated) instead of replaced, which suits incremental conversational updates."""
    fk = VERSIONED[model]
    cur = current(db, model, owner_id)
    data = to_dict(cur, exclude=_META | {fk, "produced_by"}) if cur else {}
    for k, v in patch.items():
        if v is None or not hasattr(model, k) or k in _META or k == fk:
            continue
        if merge_lists and isinstance(v, list) and isinstance(data.get(k), list):
            data[k] = list(dict.fromkeys([*data[k], *v]))
        else:
            data[k] = v
    obj = model(**{fk: owner_id}, version=(cur.version + 1) if cur else 1, produced_by=produced_by, **data)
    db.add(obj)
    db.flush()
    return obj
