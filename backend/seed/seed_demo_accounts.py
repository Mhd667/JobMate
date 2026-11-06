"""Create the demo accounts and their synthetic profiles.

Usage (from the backend folder, on the machine that holds backend/.env):
    py -m seed.seed_demo_accounts --csv seed\\demo-users.csv

1. Accounts: each CSV line becomes a Supabase Auth account (already confirmed when
   SUPABASE_SERVICE_ROLE_KEY is set in backend/.env; otherwise a normal sign-up, which needs
   "Confirm email" turned off in Supabase), then a JobMate user with its role.
2. Profiles: companies + offers and candidates from seed/demo_profiles.py. employer05 gets a company
   without offer, candidate10 stays blank.
3. The engine then reads each profile like the real product does (LLM): the candidate CV becomes
   capabilities and evidence with their provenance, and each offer gets its Success Model so that
   new candidates can be matched to it. Matching itself is NOT run: that is what you test.

Safe to run again: existing accounts and profiles are kept as they are.
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid

import httpx
from sqlalchemy import select

from app import models as m
from app.config import settings
from app.db import SessionLocal, init_db
from app.engine import flows, pipeline
from app.engine.cards import role_summary_card
from app.engine.registry import new_version
from seed.demo_profiles import CANDIDATES, COMPANIES, cv_text

PUBLISHABLE_DEFAULT = "sb_publishable_mA0e5QwJUcdLmGqkgGrW3A_zlAgkynV"  # public key (same as the website)


# --------------------------------------------------------------------------- Supabase Auth
class Auth:
    def __init__(self):
        import os
        self.url = settings.supabase_url
        if not self.url:
            sys.exit("SUPABASE_URL manque dans backend/.env")
        self.service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.public = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "").strip() or PUBLISHABLE_DEFAULT
        self.http = httpx.Client(timeout=20)
        self._admin_users: dict[str, str] | None = None

    def _admin_headers(self):
        return {"apikey": self.service, "Authorization": f"Bearer {self.service}"}

    def _find_admin(self, email: str) -> str | None:
        if self._admin_users is None:
            self._admin_users = {}
            page = 1
            while True:
                r = self.http.get(f"{self.url}/auth/v1/admin/users", params={"page": page, "per_page": 200},
                                  headers=self._admin_headers())
                r.raise_for_status()
                users = r.json().get("users", [])
                self._admin_users.update({u["email"].lower(): u["id"] for u in users if u.get("email")})
                if len(users) < 200:
                    break
                page += 1
        return self._admin_users.get(email.lower())

    def ensure(self, role: str, email: str, phone: str, password: str) -> str:
        """Return the auth user id, creating the account if needed."""
        if self.service:
            uid = self._find_admin(email)
            if uid:
                return uid
            r = self.http.post(f"{self.url}/auth/v1/admin/users", headers=self._admin_headers(), json={
                "email": email, "password": password, "email_confirm": True,
                "user_metadata": {"jobmate_role": role, "phone": phone}})
            if r.status_code >= 400:
                sys.exit(f"Création du compte {email} refusée par Supabase ({r.status_code}) : {r.text[:300]}")
            return r.json()["id"]
        # No admin key: sign in, or sign up (needs "Confirm email" off for the .test addresses).
        h = {"apikey": self.public}
        r = self.http.post(f"{self.url}/auth/v1/token", params={"grant_type": "password"}, headers=h,
                           json={"email": email, "password": password})
        if r.status_code == 200:
            return r.json()["user"]["id"]
        r = self.http.post(f"{self.url}/auth/v1/signup", headers=h, json={
            "email": email, "password": password, "data": {"jobmate_role": role, "phone": phone}})
        if r.status_code >= 400:
            sys.exit(f"Inscription de {email} refusée ({r.status_code}) : {r.text[:300]}")
        body = r.json()
        if not body.get("access_token"):
            sys.exit("Supabase demande une confirmation par e-mail, impossible avec des adresses .test.\n"
                     "Soit vous ajoutez SUPABASE_SERVICE_ROLE_KEY dans backend/.env, soit vous désactivez\n"
                     "« Confirm email » (Authentication > Sign In / Providers > Email), puis relancez.")
        return (body.get("user") or body)["id"]


# --------------------------------------------------------------------------- JobMate data
def ensure_user(db, uid: str, email: str, phone: str, role: str) -> m.User:
    user = db.get(m.User, uuid.UUID(uid))
    if user is None:
        user = m.User(id=uuid.UUID(uid), email=email.lower(), phone_number=phone or None, role=m.UserRole(role))
        db.add(user)
        db.flush()
    elif user.role is None:
        user.role = m.UserRole(role)
    return user


def seed_company(db, user: m.User, spec: dict, analyze: bool, log) -> None:
    if db.scalars(select(m.Company.id).where(m.Company.owner_user_id == user.id)).first():
        log(f"  {user.email} : entreprise déjà présente, inchangée")
        return
    co = m.Company(owner_user_id=user.id, **spec["company"])
    db.add(co)
    db.flush()
    new_version(db, m.CompanyIdentity, co.id, spec["identity"], "seed:demo")
    for r in spec["roles"]:
        role = m.Role(company_id=co.id, title=r["title"], location=r["location"], contract_type=r["contract_type"],
                      duration=r["duration"], status="open")
        db.add(role)
        db.flush()
        new_version(db, m.RoleIdentity, role.id, r["identity"], "seed:demo")
        # The employer finds the offer summary in the chat and can launch the search from there.
        conv = m.Conversation(user_id=user.id, kind=m.ConversationKind.employer, company_id=co.id,
                              role_id=role.id, title=role.title, state={"flow": "role_summary"})
        db.add(conv)
        db.flush()
        flows._assistant(db, conv, f"Bonjour, je suis JobMate. Voici la synthèse de votre offre « {role.title} ». "
                                   "Corrigez-la en me répondant, ou dites-moi de lancer la recherche des profils.",
                         [role_summary_card(db, role)], intent="opening")
        if analyze:
            sm = pipeline.generate_success_model(db, role.id)
            log(f"    Success Model de « {role.title} » : {len(sm.critical_capabilities)} capacités")
    log(f"  {user.email} : {co.name}, {len(spec['roles'])} offre(s)")


def seed_candidate(db, user: m.User, spec: dict | None, analyze: bool, log) -> None:
    if db.scalars(select(m.Candidate.id).where(m.Candidate.user_id == user.id)).first():
        log(f"  {user.email} : profil candidat déjà présent, inchangé")
        return
    if spec is None:  # blank candidate: the profile will be created at first login, in the conversation
        log(f"  {user.email} : laissé vierge")
        return
    cand = m.Candidate(user_id=user.id, full_name=spec["full_name"], headline=spec["headline"],
                       location=spec["location"], availability=spec["availability"], cv_text=cv_text(spec),
                       cv_filename="cv-synthetique.txt")
    db.add(cand)
    db.flush()
    new_version(db, m.ProfessionalIdentity, cand.id, spec["identity"], "seed:demo")
    for e in spec["experiences"]:
        db.add(m.Experience(candidate_id=cand.id, **e))
    conv = m.Conversation(user_id=user.id, kind=m.ConversationKind.candidate, candidate_id=cand.id,
                          state={"flow": "waiting", "answers": 3, "sources_offered": True, "matched_on_join": True})
    db.add(conv)
    db.flush()
    first = spec["full_name"].split()[0]
    flows._assistant(db, conv, f"Bonjour {first}, je suis JobMate. Votre profil est prêt. Je vous préviens ici dès "
                               "qu'une offre vous correspond.", intent="opening")
    if analyze:
        out = pipeline.understand_candidate(db, cand.id)
        log(f"    {spec['full_name']} : {out['capabilities_added']} capacités, "
            f"{len(out['evidence_added'])} preuves (source : CV)")
    log(f"  {user.email} : {spec['full_name']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="seed/demo-users.csv", help="role,email,phone,password")
    ap.add_argument("--no-analyze", action="store_true",
                    help="ne pas appeler l'IA (pas de Success Model ni d'analyse des CV)")
    args = ap.parse_args()
    analyze = not args.no_analyze

    with open(args.csv, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("email")]
    print(f"{len(rows)} comptes dans {args.csv}")
    if settings.auto_create_tables:
        init_db()
    auth = Auth()
    print("Création des comptes :", "clé admin (comptes confirmés)" if auth.service else "inscription standard")

    db = SessionLocal()
    try:
        for r in rows:
            role, email = r["role"].strip(), r["email"].strip().lower()
            uid = auth.ensure(role, email, r.get("phone", "").strip(), r["password"])
            user = ensure_user(db, uid, email, r.get("phone", "").strip(), role)
            if role == "employer":
                spec = COMPANIES.get(email)
                if spec:
                    seed_company(db, user, spec, analyze, print)
                else:
                    print(f"  {email} : employeur sans profil prévu, laissé vierge")
            else:
                seed_candidate(db, user, CANDIDATES.get(email), analyze, print)
            db.commit()  # one account at a time: a failure later keeps what is done
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Terminé. Connectez-vous sur http://localhost:3000 avec ces comptes.")


if __name__ == "__main__":
    main()
