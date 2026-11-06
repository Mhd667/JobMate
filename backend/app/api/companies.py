"""Company registry: companies, company identity, roles, role identity, success model, role card."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.api import schemas as s
from app.api.access import own_company, own_role
from app.auth.deps import employer
from app.db import get_db
from app.engine import pipeline
from app.engine.context_builder import ContextBuilder
from app.engine.registry import current, history, new_version

router = APIRouter(tags=["company"])


@router.post("/companies", response_model=s.CompanyOut, status_code=201)
def create_company(body: s.CompanyIn, user=Depends(employer), db: Session = Depends(get_db)):
    co = m.Company(owner_user_id=user.id, **body.model_dump())
    db.add(co)
    db.flush()
    new_version(db, m.CompanyIdentity, co.id, {"unknowns": ["mission", "culture", "business_model"]}, "system")
    db.refresh(co)
    return co


@router.get("/companies", response_model=list[s.CompanyOut])
def my_companies(user=Depends(employer), db: Session = Depends(get_db)):
    return list(db.scalars(select(m.Company).where(m.Company.owner_user_id == user.id)))


@router.get("/companies/{company_id}", response_model=s.CompanyOut)
def get_company(company_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    return own_company(db, user, company_id)


@router.get("/companies/{company_id}/identity", response_model=s.CompanyIdentityOut | None)
def get_company_identity(company_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_company(db, user, company_id)
    return current(db, m.CompanyIdentity, company_id)


@router.get("/companies/{company_id}/identity/history", response_model=list[s.CompanyIdentityOut])
def company_identity_history(company_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_company(db, user, company_id)
    return history(db, m.CompanyIdentity, company_id)


@router.patch("/companies/{company_id}/identity", response_model=s.CompanyIdentityOut)
def patch_company_identity(company_id: uuid.UUID, body: s.CompanyIdentityPatch, user=Depends(employer),
                           db: Session = Depends(get_db)):
    own_company(db, user, company_id)
    return new_version(db, m.CompanyIdentity, company_id, body.model_dump(exclude_none=True), "manual")


# ------------------------------------------------------------------ roles
@router.post("/companies/{company_id}/roles", response_model=s.RoleOut, status_code=201, tags=["roles"])
def create_role(company_id: uuid.UUID, body: s.RoleIn, user=Depends(employer), db: Session = Depends(get_db)):
    own_company(db, user, company_id)
    role = m.Role(company_id=company_id, **body.model_dump())
    db.add(role)
    db.flush()
    new_version(db, m.RoleIdentity, role.id, {"unknowns": ["mission", "objectives", "success_factors"]}, "system")
    db.refresh(role)
    return role


@router.get("/companies/{company_id}/roles", response_model=list[s.RoleOut], tags=["roles"])
def list_roles(company_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_company(db, user, company_id)
    return list(db.scalars(select(m.Role).where(m.Role.company_id == company_id)))


@router.get("/roles/{role_id}", response_model=s.RoleOut, tags=["roles"])
def get_role(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    return own_role(db, user, role_id)


@router.get("/roles/{role_id}/card", response_model=s.RoleCardOut, tags=["roles"])
def role_card(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    role = own_role(db, user, role_id)
    cb = ContextBuilder(db)
    return s.RoleCardOut(
        role=role, company=role.company,
        company_identity=current(db, m.CompanyIdentity, role.company_id),
        role_identity=current(db, m.RoleIdentity, role_id),
        success_model=current(db, m.SuccessModel, role_id),
        missing_fields=cb.missing_company_role_fields(cb.company(role.company_id), cb.role(role_id)))


@router.get("/roles/{role_id}/identity", response_model=s.RoleIdentityOut | None, tags=["roles"])
def get_role_identity(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return current(db, m.RoleIdentity, role_id)


@router.patch("/roles/{role_id}/identity", response_model=s.RoleIdentityOut, tags=["roles"])
def patch_role_identity(role_id: uuid.UUID, body: s.RoleIdentityPatch, user=Depends(employer),
                        db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return new_version(db, m.RoleIdentity, role_id, body.model_dump(exclude_none=True), "manual")


# ------------------------------------------------------------------ success model
@router.get("/roles/{role_id}/success-model", response_model=s.SuccessModelOut | None, tags=["success model"])
def get_success_model(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return current(db, m.SuccessModel, role_id)


@router.post("/roles/{role_id}/success-model/generate", response_model=s.SuccessModelOut, tags=["success model"])
def generate_success_model(role_id: uuid.UUID, user=Depends(employer), db: Session = Depends(get_db)):
    own_role(db, user, role_id)
    return pipeline.generate_success_model(db, role_id)


@router.patch("/roles/{role_id}/success-model", response_model=s.SuccessModelOut, tags=["success model"])
def patch_success_model(role_id: uuid.UUID, body: s.SuccessModelIn, user=Depends(employer),
                        db: Session = Depends(get_db)):
    """Employer corrections to the model (e.g. changing the decision priority)."""
    own_role(db, user, role_id)
    return new_version(db, m.SuccessModel, role_id, body.model_dump(mode="json", exclude_none=True), "manual")
