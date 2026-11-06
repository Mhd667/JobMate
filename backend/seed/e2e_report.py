"""End-to-end test of the engine on the demo data, with a readable report.

Usage (backend folder, after seed.bat):
    py -m seed.e2e_report                 # runs everything, then UNDOES it (nothing stays in the database)
    py -m seed.e2e_report --commit        # keeps the results (matches, offers sent, messages)
    py -m seed.e2e_report --out rapport.md

It goes through the same functions as the chat (flows.py), with the configured intelligence (Groq on your PC):
1. each of the 5 offers: "lance la recherche" -> Success Model, matching, Top 3;
2. confrontation of the finalists, then recommendation;
3. the first finalist of each offer says "Ça m'intéresse" and answers the adaptive assessment;
   its score before / after is reported;
4. candidate10 joins (3 answers) -> matched against the open offers;
5. employer05 describes a new offer in the chat -> search.
"""
from __future__ import annotations

import argparse
import time
import traceback
import uuid

from sqlalchemy import select

from app import models as m
from app.config import settings
from app.db import SessionLocal
from app.engine import flows
from app.intelligence.interface import get_intelligence

ASSESSMENT_ANSWERS = [
    "Je commence par écouter la personne jusqu'au bout et je reformule son problème pour être sûr de l'avoir "
    "compris. Ensuite je propose une solution concrète, avec un délai, et je rappelle le lendemain pour vérifier.",
    "Dans mon dernier poste, j'ai eu un cas difficile : j'ai pris le temps d'analyser ce qui bloquait, j'ai "
    "demandé de l'aide à un collègue plus expérimenté, et on a trouvé une solution en deux jours.",
]
CANDIDATE10 = [
    "Je m'appelle Khady Sow, je cherche un poste de commerciale ou de conseillère clientèle à Dakar.",
    "J'ai 3 ans d'expérience en vente en boutique de téléphonie, puis 1 an au téléphone pour une assurance. "
    "J'étais souvent la meilleure vendeuse du mois.",
    "Je cherche un CDI ou un CDD long, je suis disponible tout de suite, je parle wolof, français et un peu anglais.",
]
EMPLOYER05 = [
    "Bonjour, nous cherchons un ou une assistant(e) commercial(e) pour notre cabinet à Dakar, en CDI.",
    "Il faut relancer nos prospects PME par téléphone, préparer les propositions commerciales et suivre les "
    "inscriptions à nos formations.",
    "Ceux qui réussissent chez nous sont organisés, à l'aise au téléphone et rigoureux sur le suivi.",
    "Français et wolof, démarrage dès que possible.",
    "C'est bon, lance la recherche.",
]


class Report:
    def __init__(self):
        self.lines: list[str] = []
        self.errors = 0

    def h(self, t):
        self.lines += ["", f"## {t}", ""]
        print(f"\n== {t}")

    def p(self, t=""):
        self.lines.append(t)
        print(t)

    def fail(self, step, e):
        self.errors += 1
        self.p(f"**ÉCHEC** ({step}) : {type(e).__name__}: {e}")
        traceback.print_exc()


def cards(turn, type_):
    return [c for c in turn["cards"] if c["type"] == type_]


def run(db, r: Report) -> None:
    intel = get_intelligence()
    r.p(f"Intelligence : **{intel.name}**"
        + (f" ({settings.llm_provider}, {settings.llm_model})" if intel.name == "llm" else "")
        + f" — base : {settings.database_url.split('@')[-1].split('/')[0] if '@' in settings.database_url else 'locale'}")
    roles = list(db.scalars(select(m.Role).join(m.Company).join(m.User, m.User.id == m.Company.owner_user_id)
                            .where(m.User.email.like("employer0%@jobmate.test")).order_by(m.User.email, m.Role.title)))
    n_cand = len(list(db.scalars(select(m.Candidate.id).where(m.Candidate.status == "active"))))
    r.p(f"{len(roles)} offres, {n_cand} candidats actifs.")
    finalists: dict = {}

    # 1-2. search, confrontation, recommendation for each offer
    for role in roles:
        r.h(f"Offre : {role.title} — {role.company.name}")
        conv = db.scalars(select(m.Conversation).where(m.Conversation.role_id == role.id)).first()
        if conv is None:
            r.p("Pas de conversation employeur pour cette offre (seed.bat pas lancé ?)")
            continue
        try:
            t0 = time.time()
            turn = flows.employer_message(db, conv, "C'est bon, lance la recherche.")
            sm = cards(turn, "success_model")
            if sm:
                r.p("Ce qui fera réussir : " + ", ".join(f"{c['name']} ({c['importance']})"
                                                         for c in sm[0]["data"]["capabilities"]))
            cl = cards(turn, "candidates")
            top = cl[0]["data"]["candidates"] if cl else []
            r.p(f"Recherche : {time.time() - t0:.1f} s. JobMate : « {turn['assistant_message'].content[:300]} »")
            r.p("")
            r.p("| Rang | Candidat | Profil | Match | Pourquoi |")
            r.p("|---|---|---|---|---|")
            for c in top:
                r.p(f"| {c['rank']} | {c['name']} | {c['headline'] or ''} | {c['match_score']} % | "
                    f"{(c['why'] or '').replace('|', '/')[:220]} |")
            others = list(db.scalars(select(m.Match).where(m.Match.role_id == role.id,
                                                          m.Match.shortlist_rank.is_(None))
                                     .order_by(m.Match.ui_score.desc())))
            if others:
                r.p("")
                r.p("Hors Top 3 : " + ", ".join(f"{db.get(m.Candidate, x.candidate_id).full_name} "
                                                f"({x.ui_score} %)" for x in others))
            finalists[role.id] = top
        except Exception as e:
            r.fail("recherche", e)
            continue
        if len(top) >= 2:
            try:
                turn = flows.employer_message(db, conv, "Compare-moi les finalistes.")
                cf = cards(turn, "confrontation")
                if cf:
                    d = cf[0]["data"]
                    r.p("")
                    r.p(f"**Confrontation** — penche pour : {d.get('leaning') or 'aucun'}")
                    r.p(f"> {(d.get('reasoning') or '')[:600]}")
                    for t in d.get("tradeoffs", [])[:3]:
                        r.p(f"- {t.get('explanation') or t.get('if_priority')}")
                    act = flows.handle_action(db, conv, cf[0]["id"], "recommend", {})
                    rec = cards(act, "recommendation")
                    if rec:
                        d = rec[0]["data"]
                        r.p("")
                        r.p(f"**Recommandation** : {d.get('name') or 'aucune'} "
                            f"(confiance {round((d.get('confidence') or 0) * 100)} %)")
                        r.p(f"> {(d.get('summary') or '')[:600]}")
                        for u in (d.get("uncertainties") or [])[:3]:
                            r.p(f"- Incertitude : {u}")
            except Exception as e:
                r.fail("confrontation / recommandation", e)

    # 3. the first finalist of each offer is interested and answers the assessment
    r.h("Côté candidat : offre, intérêt, évaluation adaptative")
    for role_id, top in finalists.items():
        if not top:
            continue
        cid = uuid.UUID(top[0]["candidate_id"])
        cand = db.get(m.Candidate, cid)
        role = db.get(m.Role, role_id)
        conv = db.scalars(select(m.Conversation).where(m.Conversation.candidate_id == cid,
                                                       m.Conversation.kind == m.ConversationKind.candidate)).first()
        try:
            offer_card = msg_card = None
            for msg in db.scalars(select(m.Message).where(m.Message.conversation_id == conv.id)):
                for c in (msg.meta or {}).get("cards", []):
                    if c["type"] == "offer" and c["data"]["role_id"] == str(role_id) and c["status"] == "open":
                        offer_card, msg_card = c, msg
            if offer_card is None:
                r.p(f"- {cand.full_name} / {role.title} : pas d'offre reçue dans son chat")
                continue
            before = top[0]["match_score"]
            turn = flows.handle_action(db, conv, offer_card["id"], "offer.interested", {})
            qs = []
            for i in range(2):
                a = cards(turn, "assessment")
                if not a:
                    break
                qs.append(f"{a[0]['data']['theme']} : {a[0]['data']['question']}")
                turn = flows.candidate_message(db, conv, ASSESSMENT_ANSWERS[i])
            x = db.scalars(select(m.Match).where(m.Match.role_id == role_id, m.Match.candidate_id == cid)).one()
            r.p(f"**{cand.full_name} → {role.title}** : explication de l'offre « {(offer_card['data'].get('explanation') or '')[:250]} »")
            for q in qs:
                r.p(f"- Question posée — {q[:300]}")
            r.p(f"- Match avant évaluation : {before} % → après : {x.ui_score} %")
            r.p("")
        except Exception as e:
            r.fail(f"évaluation de {cand.full_name}", e)

    # decision -> candidate informed
    first = next(((rid, top[0]) for rid, top in finalists.items() if top), None)
    if first:
        rid, c = first
        try:
            econv = db.scalars(select(m.Conversation).where(m.Conversation.role_id == rid)).first()
            cl = None
            for msg in db.scalars(select(m.Message).where(m.Message.conversation_id == econv.id)):
                for cd in (msg.meta or {}).get("cards", []):
                    if cd["type"] == "candidates":
                        cl = cd
            flows.handle_action(db, econv, cl["id"], "candidate.hire", {"candidate_id": c["candidate_id"]})
            cconv = db.scalars(select(m.Conversation).where(
                m.Conversation.candidate_id == uuid.UUID(c["candidate_id"]))).first()
            last = db.scalars(select(m.Message).where(m.Message.conversation_id == cconv.id)
                              .order_by(m.Message.created_at.desc())).first()
            r.p(f"Décision « Hire » sur {c['name']} → message reçu par le candidat : « {last.content} »")
        except Exception as e:
            r.fail("décision employeur", e)

    # 4. candidate10 joins
    r.h("Nouveau candidat (candidate10) : 3 réponses, puis matching sur les offres ouvertes")
    try:
        user = db.scalars(select(m.User).where(m.User.email == "candidate10@jobmate.test")).one()
        cand = db.scalars(select(m.Candidate).where(m.Candidate.user_id == user.id)).first()
        if cand is None:
            cand = m.Candidate(user_id=user.id, full_name="candidate10")
            db.add(cand)
            db.flush()
        conv = flows.start_conversation(db, user, "candidate")
        for t in CANDIDATE10:
            turn = flows.candidate_message(db, conv, t)
            r.p(f"- Candidat : « {t} »")
            r.p(f"  JobMate : « {turn['assistant_message'].content[:300]} »")
        db.refresh(cand)
        r.p(f"Profil retenu : {cand.full_name} — {cand.headline or '?'} — {cand.location or '?'}")
        offers = list(db.scalars(select(m.Match).where(m.Match.candidate_id == cand.id)))
        for x in sorted(offers, key=lambda x: -(x.ui_score or 0)):
            role = db.get(m.Role, x.role_id)
            r.p(f"- {role.title} ({role.company.name}) : match {x.ui_score} % — "
                + ("offre envoyée" if x.offered_at else "pas d'offre (hors Top 3)"))
    except Exception as e:
        r.fail("candidate10", e)

    # 5. employer05 creates an offer in the chat
    r.h("Nouvelle offre (employer05, Baobab Conseil) créée en conversation")
    try:
        user = db.scalars(select(m.User).where(m.User.email == "employer05@jobmate.test")).one()
        company = db.scalars(select(m.Company).where(m.Company.owner_user_id == user.id)).one()
        conv = flows.start_conversation(db, user, "employer", company.id)
        turn = None
        for t in EMPLOYER05:
            turn = flows.employer_message(db, conv, t)
            r.p(f"- Employeur : « {t} »")
            r.p(f"  JobMate : « {turn['assistant_message'].content[:300]} »"
                + (f" [cartes : {', '.join(c['type'] for c in turn['cards'])}]" if turn["cards"] else ""))
        role = db.get(m.Role, conv.role_id)
        r.p(f"Poste créé : {role.title} ({role.contract_type or '?'}, {role.location or '?'})")
        cl = cards(turn, "candidates")
        for c in (cl[0]["data"]["candidates"] if cl else []):
            r.p(f"- {c['rank']}. {c['name']} — {c['headline']} — {c['match_score']} %")
        if not cl:
            r.p("Pas de Top 3 affiché (la recherche n'a pas été lancée).")
    except Exception as e:
        r.fail("employer05", e)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--commit", action="store_true", help="garder les résultats dans la base")
    ap.add_argument("--out", default="seed/rapport-e2e.md")
    args = ap.parse_args()
    r = Report()
    r.p("# JobMate — test de bout en bout du moteur")
    t0 = time.time()
    db = SessionLocal()
    try:
        run(db, r)
        if args.commit:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    r.h("Bilan")
    r.p(f"Durée totale : {time.time() - t0:.0f} s. Étapes en échec : {r.errors}. "
        + ("Résultats conservés dans la base." if args.commit else "Rien n'a été gardé dans la base (test annulé à la fin)."))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(r.lines) + "\n")
    print(f"\nRapport écrit dans {args.out}")


if __name__ == "__main__":
    main()
