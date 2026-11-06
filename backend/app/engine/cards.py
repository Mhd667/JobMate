"""Chat cards: structured objects the frontend renders inside the conversation thread.

A card is {id, type, status, data, actions}. It is stored in the assistant message's meta["cards"],
so reloading a conversation re-renders it. The frontend answers a card with
POST /conversations/{id}/actions {card_id, action, payload}; the action ids are listed in `actions`.
Card data is built from the database only (never invented): when a field is unknown it is null.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.engine.registry import current
from app.intelligence.heuristic import IMPORTANCE_FR

PRIORITY_FR = {"elevee": "Élevée", "normale": "Normale", "faible": "Faible"}


def card(type_: str, data: dict, actions: list[dict] | None = None) -> dict:
    return {"id": str(uuid.uuid4()), "type": type_, "status": "open", "data": data, "actions": actions or []}


def action(id_: str, label: str, style: str = "secondary") -> dict:
    return {"id": id_, "label": label, "style": style}


# --------------------------------------------------------------------------- employer
def missions_card(question: str, options: list[str]) -> dict:
    return card("missions", {"question": question, "options": options, "multiple": True, "allow_other": True},
                [action("missions.submit", "Valider", "primary")])


def _contract_label(role: m.Role) -> str | None:
    if not role.contract_type:
        return None
    return f"{role.contract_type} ({role.duration})" if role.duration else role.contract_type


def role_summary_card(db: Session, role: m.Role) -> dict:
    ident = current(db, m.RoleIdentity, role.id)
    get = (lambda f, d=None: getattr(ident, f) if ident is not None else d)
    return card("role_summary", {
        "role_id": str(role.id),
        "title": role.title,
        "contract": _contract_label(role),
        "location": role.location,
        "mission": get("mission"),
        "missions": get("responsibilities", []) or [],
        "languages": get("languages", []) or [],
        "criteria": get("success_factors", []) or [],
        "availability": get("availability"),
        "priority": PRIORITY_FR.get(get("priority") or ""),
    }, [action("role_summary.confirm", "Lancer la recherche", "primary"),
        action("role_summary.edit", "Modifier")])


def success_model_card(sm: m.SuccessModel) -> dict:
    return card("success_model", {
        "version": sm.version,
        "capabilities": [{"key": x["key"], "name": x["name"], "importance": IMPORTANCE_FR[x["importance"]]}
                         for x in sm.critical_capabilities],
        "paths": [{"name": p.get("name"), "requires": p.get("requires", [])} for p in sm.success_conditions],
    })


def _years_of_experience(db: Session, candidate_id) -> int | None:
    months = 0
    today = date.today()
    for e in db.scalars(select(m.Experience).where(m.Experience.candidate_id == candidate_id)):
        try:
            y0, m0 = map(int, (e.start_date or "")[:7].split("-"))
        except ValueError:
            continue
        if e.end_date:
            try:
                y1, m1 = map(int, e.end_date[:7].split("-"))
            except ValueError:
                continue
        else:
            y1, m1 = today.year, today.month
        months += max(0, (y1 - y0) * 12 + (m1 - m0))
    return round(months / 12) if months else None


def _skills(db: Session, candidate_id, match: m.Match) -> list[str]:
    names = [c.name for c in db.scalars(select(m.Capability).where(m.Capability.candidate_id == candidate_id))]
    if not names:
        names = [(s if isinstance(s, str) else s.get("name") or s.get("claim", "")).split(" : ")[0]
                 for s in match.strengths]
    return [n for n in names if n][:6]


def candidate_card_data(db: Session, match: m.Match) -> dict:
    cand = db.get(m.Candidate, match.candidate_id)
    return {
        "candidate_id": str(cand.id),
        "match_id": str(match.id),
        "name": cand.full_name,
        "initials": "".join(p[0] for p in cand.full_name.split()[:2]).upper(),
        "headline": cand.headline,
        "city": cand.location,
        "years_experience": _years_of_experience(db, cand.id),
        "match_score": match.ui_score,
        "rank": match.shortlist_rank,
        "why": match.shortlist_reason or match.fit_summary,
        "skills": _skills(db, cand.id, match),
        "gaps": match.gaps[:3],
        "employer_status": match.employer_status,
    }


def candidates_card(db: Session, matches: list[m.Match]) -> dict:
    return card("candidates", {"candidates": [candidate_card_data(db, x) for x in matches]},
                [action("candidate.pass", "Passer"), action("candidate.interview", "Entretien"),
                 action("candidate.hire", "Hire", "primary")])


def next_steps_card() -> dict:
    return card("next_steps", {"question": "Que souhaitez-vous faire maintenant ?"},
                [action("next.hire", "Hirer un candidat"), action("next.interviews", "Planifier des entretiens"),
                 action("next.refine", "Affiner la recherche")])


def confrontation_card(db: Session, conf: m.Confrontation) -> dict:
    names = {str(i): db.get(m.Candidate, uuid.UUID(i)).full_name for i in conf.candidate_ids}
    return card("confrontation", {
        "confrontation_id": str(conf.id),
        "question": conf.decision_question,
        "profiles": [p | {"name": names.get(p.get("candidate_id"))} for p in conf.profiles],
        "tradeoffs": conf.tradeoffs,
        "reasoning": conf.reasoning,
        "uncertainties": conf.uncertainties,
        "leaning": names.get(str(conf.winner_candidate_id)) if conf.winner_candidate_id else None,
    }, [action("recommend", "Obtenir une recommandation", "primary")])


def recommendation_card(db: Session, rec: m.Recommendation) -> dict:
    cand = db.get(m.Candidate, rec.recommended_candidate_id) if rec.recommended_candidate_id else None
    return card("recommendation", {
        "recommendation_id": str(rec.id),
        "candidate_id": str(cand.id) if cand else None,
        "name": cand.full_name if cand else None,
        "summary": rec.reasoning_summary,
        "key_evidence": rec.key_evidence,
        "tradeoffs": rec.tradeoffs,
        "uncertainties": rec.uncertainties,
        "next_steps": rec.next_steps,
        "confidence": rec.confidence,
    }, [action("candidate.hire", "Hire", "primary"), action("candidate.interview", "Entretien")])


# --------------------------------------------------------------------------- candidate
def sources_card() -> dict:
    return card("sources", {"question": "Pour compléter votre profil, vous pouvez ajouter (facultatif) :",
                            "fields": ["cv", "linkedin", "portfolio"]},
                [action("sources.submit", "Ajouter", "primary"), action("sources.skip", "Plus tard")])


def offer_card(db: Session, match: m.Match) -> dict:
    role = db.get(m.Role, match.role_id)
    company = db.get(m.Company, role.company_id)
    ident = current(db, m.RoleIdentity, role.id)
    return card("offer", {
        "match_id": str(match.id),
        "role_id": str(role.id),
        "title": role.title,
        "company": company.name,
        "contract": role.contract_type,
        "duration": role.duration,
        "location": role.location or company.city,
        "missions": (ident.responsibilities if ident else []) or [],
        "match_score": match.ui_score,
        "explanation": match.candidate_explanation,
    }, [action("offer.interested", "Ça m'intéresse", "primary"), action("offer.decline", "Pas disponible")])


def assessment_card(req: m.AssessmentRequest, theme: str, index: int, total: int) -> dict:
    return card("assessment", {"request_id": str(req.id), "theme": theme,
                               "question": req.question, "index": index, "total": total})
