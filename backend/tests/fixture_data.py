"""Demo data: one fintech in Dakar, one B2B sales role, five candidates.

(test fixture only — not product data)
Accounts (password for all: jobmate-demo):
    employer@jobmate.demo  (employer)
    aminata@jobmate.demo / ousmane@jobmate.demo / fatou@jobmate.demo / moussa@jobmate.demo / khady@jobmate.demo
All companies and people are fictional.
"""
from __future__ import annotations

from app import models as m
from app.auth.security import hash_password
from app.db import SessionLocal, init_db
from app.engine.registry import new_version

PASSWORD = "jobmate-demo"
F, I, H = m.EpistemicStatus.fact, m.EpistemicStatus.inference, m.EpistemicStatus.hypothesis
S = m.EvidenceSource

SUCCESS_MODEL = {
    "critical_outcomes": [
        {"outcome": "80 nouveaux commerçants actifs sur la zone Dakar-Plateau / Médina", "horizon": "6 mois",
         "measure": "commerçants avec ≥ 20 transactions / mois"},
        {"outcome": "Taux de churn des commerçants signés < 15 %", "horizon": "6 mois", "measure": "churn à 90 jours"},
    ],
    "critical_capabilities": [
        {"key": "persuasion", "name": "Persuasion", "importance": "critical",
         "description": "Convaincre un commerçant habitué au cash d'adopter le paiement mobile",
         "observable_evidence": ["signatures obtenues auprès de prospects initialement réticents",
                                 "taux de conversion terrain"]},
        {"key": "objection_handling", "name": "Traitement des objections", "importance": "critical",
         "description": "Lever les objections frais / confiance / habitudes",
         "observable_evidence": ["réponse structurée à une objection prix ou confiance"]},
        {"key": "conflict_management", "name": "Gestion de clients difficiles / conflits", "importance": "critical",
         "description": "Garder le commerçant quand un incident de paiement le rend agressif",
         "observable_evidence": ["désescalade d'un client agressif", "rétention après incident"]},
        {"key": "b2b_prospecting", "name": "Prospection B2B terrain", "importance": "critical",
         "description": "Construire seul un pipeline de commerçants sur une zone",
         "observable_evidence": ["volume de prospection hebdomadaire", "portefeuille construit from scratch"]},
        {"key": "domain_knowledge", "name": "Connaissance mobile money / paiements", "importance": "important",
         "description": "Comprendre les usages et la concurrence du paiement marchand",
         "observable_evidence": ["expérience dans un opérateur ou un réseau d'agents"]},
        {"key": "learning_agility", "name": "Capacité d'apprentissage", "importance": "important",
         "description": "Monter en compétence vite sur un produit qui change chaque mois",
         "observable_evidence": ["montée en compétence rapide documentée", "promotion rapide"]},
    ],
    "required_behaviors": [
        "fait 25+ visites commerçants par semaine sans supervision",
        "revient vers un commerçant après un incident au lieu de l'éviter",
        "remonte les retours terrain à l'équipe produit",
    ],
    "success_conditions": [
        {"name": "performance_immediate", "requires": ["b2b_prospecting", "persuasion", "objection_handling"],
         "description": "Vendeur terrain déjà prouvé : productif dès le premier mois"},
        {"name": "potentiel_avec_ramp_up", "requires": ["learning_agility", "conflict_management"], "weight": 0.75,
         "description": "Excellent avec les clients et apprend vite : productif après 2-3 mois d'accompagnement"},
        {"name": "expertise_sectorielle", "requires": ["domain_knowledge", "b2b_prospecting"], "weight": 0.9,
         "description": "Connaît déjà le réseau marchand mobile money"},
    ],
    "tradeoffs": ["Performance immédiate vs potentiel de progression",
                  "Expertise sectorielle vs disponibilité rapide"],
    "risks": ["La concurrence recrute les mêmes profils terrain",
              "Les incidents de paiement génèrent des commerçants très mécontents"],
    "unknowns": ["Part réelle du temps passée sur le SAV vs la vente : à confirmer avec le manager"],
    "priorities": {"primary": "immediate_performance",
                   "notes": "Le lancement de la zone est prévu en janvier : la personne doit être productive vite."},
    "confidence": 0.7,
}

CANDIDATES = [
    {
        "email": "aminata@jobmate.demo", "full_name": "Aminata Diallo",
        "headline": "Commerciale terrain B2B — distribution télécom", "location": "Dakar",
        "availability": {"available_from": "2026-12-01", "notice_weeks": 4},
        "identity": {"career_direction": "Vente B2B dans la tech / fintech",
                     "strengths": ["closing", "prospection terrain"],
                     "professional_goals": ["prendre un portefeuille plus stratégique"],
                     "aspirations": ["devenir responsable d'équipe commerciale"],
                     "summary": "4 ans de vente terrain B2B auprès de revendeurs télécom, très orientée résultats."},
        "experiences": [
            {"title": "Commerciale terrain B2B", "organization": "Distributeur télécom (Dakar)", "sector": "télécom",
             "start_date": "2022-09", "end_date": None,
             "achievements": ["Signé 120 nouveaux points de vente en 2025, 140 % de l'objectif",
                              "Construit seule le portefeuille de la zone Pikine"],
             "skills": ["prospection", "négociation", "closing"]},
        ],
        "evidence": [
            ("persuasion", "Convainc des prospects réticents",
             "Signé 120 nouveaux points de vente en 2025 (140 % de l'objectif), confirmé par son ancien manager",
             S.reference, F, 0.85),
            ("b2b_prospecting", "Construit un pipeline seule",
             "A construit seule le portefeuille de la zone Pikine (0 → 90 revendeurs en 18 mois)",
             S.previous_experience, F, 0.85),
            ("objection_handling", "Lève les objections prix",
             "Décrit en détail sa méthode face à l'objection « marge trop faible » des revendeurs",
             S.conversation, I, 0.75),
            ("objection_handling", "Lève les objections de confiance",
             "Taux de conversion de 35 % sur des revendeurs initialement opposés au produit",
             S.previous_experience, I, 0.7),
            ("learning_agility", "Apprend un nouveau produit",
             "A lancé 3 nouvelles offres en 2024, formée en interne en 2 semaines", S.previous_experience, I, 0.5),
            ("domain_knowledge", "Connaît le commerce de détail",
             "Vend aux mêmes boutiques de quartier que la cible, mais pas de produit de paiement",
             S.previous_experience, I, 0.5),
        ],
    },
    {
        "email": "ousmane@jobmate.demo", "full_name": "Ousmane Ndiaye",
        "headline": "Ex-enseignant devenu team lead support client e-commerce", "location": "Dakar",
        "availability": {"available_from": "2026-11-15", "notice_weeks": 2},
        "identity": {"career_direction": "Passer du support à la vente",
                     "strengths": ["calme face aux clients difficiles", "apprend vite"],
                     "professional_goals": ["avoir un impact direct sur le chiffre d'affaires"],
                     "aspirations": ["devenir account manager"],
                     "summary": "Parcours atypique : 5 ans d'enseignement puis 2 ans dans le support client."},
        "experiences": [
            {"title": "Team lead support client", "organization": "Plateforme e-commerce (Dakar)",
             "sector": "e-commerce", "start_date": "2024-09", "end_date": None,
             "achievements": ["Promu team lead en 8 mois", "CSAT de l'équipe passée de 71 à 86"],
             "skills": ["gestion des escalades", "Zendesk", "formation"]},
            {"title": "Professeur de mathématiques", "organization": "Lycée (Thiès)", "sector": "éducation",
             "start_date": "2019-09", "end_date": "2024-07", "achievements": [], "skills": ["pédagogie"]},
        ],
        "evidence": [
            ("conflict_management", "Désamorce les clients agressifs",
             "Gère les escalades niveau 2 ; CSAT de l'équipe passée de 71 à 86 en un an (données internes)",
             S.reference, F, 0.85),
            ("conflict_management", "Retient des clients après incident",
             "A récupéré des clients ayant demandé la clôture de leur compte après des retards de livraison",
             S.previous_experience, I, 0.7),
            ("learning_agility", "Monte en compétence très vite",
             "Reconversion enseignant → support, promu team lead en 8 mois", S.previous_experience, F, 0.85),
            ("learning_agility", "Autodidacte",
             "A appris SQL seul pour analyser les tickets de son équipe", S.previous_experience, I, 0.6),
            ("objection_handling", "Répond aux réticences",
             "Gère des demandes de remboursement en proposant des alternatives", S.previous_experience, I, 0.45),
            ("persuasion", "Se dit convaincant",
             "Déclare « savoir convaincre », sans exemple de vente", S.self_declared, H, 0.4),
        ],
    },
    {
        "email": "fatou@jobmate.demo", "full_name": "Fatou Sow",
        "headline": "Responsable réseau marchands — opérateur mobile money", "location": "Dakar",
        "availability": {"available_from": "2027-03-01", "notice_weeks": 12,
                         "notes": "préavis de 3 mois non négociable"},
        "identity": {"career_direction": "Rejoindre une fintech plus agile",
                     "strengths": ["connaissance du réseau marchand", "prospection"],
                     "constraints": ["préavis de 3 mois"],
                     "summary": "6 ans dans le paiement mobile, du terrain à la gestion d'un réseau de 400 marchands."},
        "experiences": [
            {"title": "Responsable réseau marchands", "organization": "Opérateur mobile money", "sector": "fintech",
             "start_date": "2020-01", "end_date": None,
             "achievements": ["Réseau de 400 marchands actifs", "Lancement du paiement QR sur 3 villes"],
             "skills": ["mobile money", "prospection", "animation de réseau"]},
        ],
        "evidence": [
            ("domain_knowledge", "Experte paiement marchand",
             "6 ans chez un opérateur mobile money, a lancé le paiement QR sur 3 villes", S.reference, F, 0.9),
            ("b2b_prospecting", "Construit et anime un réseau",
             "A développé un réseau de 400 marchands actifs", S.previous_experience, F, 0.8),
            ("persuasion", "Convainc des commerçants",
             "Responsable de l'acquisition marchands, mais via une équipe d'agents", S.previous_experience, I, 0.65),
            ("objection_handling", "Connaît les objections du secteur",
             "Décrit les objections classiques (frais, liquidité) et les réponses de son équipe",
             S.conversation, I, 0.65),
            ("conflict_management", "Gère les litiges marchands",
             "Traitait les escalades de litiges marchands, sans détail sur sa méthode", S.previous_experience, I, 0.55),
            ("learning_agility", "S'adapte aux nouveaux produits",
             "A piloté le lancement du QR", S.previous_experience, I, 0.5),
        ],
    },
    {
        "email": "moussa@jobmate.demo", "full_name": "Moussa Fall",
        "headline": "Vendeur en boutique d'électroménager", "location": "Dakar",
        "availability": {"available_from": "2026-11-10", "notice_weeks": 0},
        "identity": {"career_direction": "Vente", "summary": "1 an de vente en magasin."},
        "experiences": [
            {"title": "Vendeur", "organization": "Magasin d'électroménager", "sector": "retail",
             "start_date": "2025-09", "end_date": None, "achievements": ["Meilleur vendeur du mois (2 fois)"],
             "skills": ["vente"]},
        ],
        "evidence": [
            ("persuasion", "Vend en magasin", "Meilleur vendeur du mois à 2 reprises (clients entrants)",
             S.previous_experience, I, 0.5),
        ],
    },
    {
        "email": "khady@jobmate.demo", "full_name": "Khady Ba",
        "headline": "Chargée de marketing digital", "location": "Saint-Louis",
        "availability": {"available_from": "2026-12-15", "notice_weeks": 4},
        "identity": {"career_direction": "Growth / acquisition", "summary": "3 ans de marketing digital B2C."},
        "experiences": [
            {"title": "Chargée de marketing digital", "organization": "Agence de communication", "sector": "marketing",
             "start_date": "2023-06", "end_date": None, "achievements": ["Campagnes d'acquisition pour 12 clients"],
             "skills": ["analyse de données", "réseaux sociaux"]},
        ],
        "evidence": [
            ("learning_agility", "Apprend de nouveaux outils", "A pris en main 4 outils d'analytics en un an",
             S.previous_experience, I, 0.6),
            ("persuasion", "Rédige des messages convaincants", "Campagnes d'acquisition B2C, pas de vente directe",
             S.previous_experience, H, 0.4),
        ],
    },
]

EMPLOYER_TRANSCRIPT = [
    ("assistant", "Bonjour ! Je suis JobMate. Parlez-moi de votre entreprise et du poste que vous voulez pourvoir."),
    ("user", "Kora Pay permet aux petits commerçants de Dakar d'accepter les paiements mobiles et de suivre leurs "
             "ventes. On se rémunère avec une commission sur chaque transaction."),
    ("assistant", "Merci. Pourquoi ouvrez-vous ce recrutement maintenant ?"),
    ("user", "On lance la zone Plateau / Médina en janvier. Il nous faut quelqu'un qui va chercher les commerçants "
             "sur le terrain, les convainc de passer au paiement mobile et les garde quand il y a des incidents."),
    ("assistant", "Qu'est-ce qui distingue les personnes qui réussissent vraiment à ce poste chez vous ?"),
    ("user", "Celles qui savent convaincre un commerçant qui dit « je préfère le cash », qui ne lâchent pas face "
             "aux objections, et qui restent calmes quand un commerçant crie parce que son paiement est bloqué."),
]


def seed(reset: bool = True) -> dict:
    init_db(drop=reset)
    db = SessionLocal()
    try:
        boss = m.User(email="employer@jobmate.demo", phone_number="+221770000000",
                      password_hash=hash_password(PASSWORD), role=m.UserRole.employer)
        db.add(boss)
        db.flush()
        co = m.Company(owner_user_id=boss.id, name="Kora Pay", country="Sénégal", city="Dakar", size="25-50",
                       website="https://kora-pay.example", description="Paiement mobile pour petits commerçants")
        db.add(co)
        db.flush()
        new_version(db, m.CompanyIdentity, co.id, {
            "mission": "Faire passer les petits commerçants du cash au paiement mobile, simplement",
            "business_model": "Commission sur chaque transaction marchande (B2B2C)",
            "industry": "Fintech — paiement marchand",
            "culture": "Startup terrain, orientée résultats, beaucoup d'autonomie",
            "work_style": "Équipes terrain autonomes, point quotidien à 8h30",
            "management_style": "Manager commercial proche du terrain, objectifs hebdomadaires",
            "environment": "Marché concurrentiel, opérateurs télécom très présents",
            "values": ["simplicité", "proximité", "fiabilité"],
            "context": "Série A récente, expansion sur 3 nouvelles zones de Dakar",
            "unknowns": ["politique de rémunération variable"],
            "assumptions": ["la croissance passe par l'acquisition terrain plutôt que le digital"],
            "confidence": 0.75}, "seed")
        role = m.Role(company_id=co.id, title="Account Executive B2B — Commerçants", location="Dakar",
                      contract_type="CDI", status="open",
                      constraints={"start_before": "2027-01-05", "location": "Dakar", "languages": ["fr", "wo"]})
        db.add(role)
        db.flush()
        new_version(db, m.RoleIdentity, role.id, {
            "mission": "Ouvrir et fidéliser le réseau de commerçants de la zone Plateau / Médina",
            "responsibilities": ["prospection terrain des commerçants", "démonstration et signature",
                                 "suivi et rétention après incidents", "remontée des retours terrain"],
            "objectives": ["80 commerçants actifs en 6 mois", "churn < 15 % à 90 jours"],
            "constraints": ["démarrage avant le 5 janvier 2027", "français et wolof"],
            "context": "Lancement d'une nouvelle zone en janvier",
            "work_environment": "80 % terrain, scooter fourni",
            "stakeholders": ["commerçants", "manager commercial", "support client", "équipe produit"],
            "success_factors": ["convaincre des commerçants attachés au cash", "ne pas lâcher face aux objections",
                                "rester calme face aux commerçants mécontents après un incident"],
            "unknowns": ["part du temps passée sur le SAV"],
            "assumptions": ["le poste est majoritairement de la vente, pas du support"],
            "confidence": 0.7}, "seed")
        new_version(db, m.SuccessModel, role.id, SUCCESS_MODEL, "seed")
        conv = m.Conversation(user_id=boss.id, kind=m.ConversationKind.employer, company_id=co.id,
                              role_id=role.id, title="Recrutement Account Executive", state={})
        db.add(conv)
        db.flush()
        for sender, content in EMPLOYER_TRANSCRIPT:
            db.add(m.Message(conversation_id=conv.id, sender=sender, content=content, meta={"seed": True}))
            db.flush()

        cand_ids = {}
        for spec in CANDIDATES:
            u = m.User(email=spec["email"], password_hash=hash_password(PASSWORD), role=m.UserRole.candidate)
            db.add(u)
            db.flush()
            cand = m.Candidate(user_id=u.id, full_name=spec["full_name"], headline=spec["headline"],
                               location=spec["location"], availability=spec["availability"])
            db.add(cand)
            db.flush()
            cand_ids[spec["full_name"]] = str(cand.id)
            new_version(db, m.ProfessionalIdentity, cand.id, {**spec["identity"], "confidence": 0.5}, "seed")
            for exp in spec["experiences"]:
                db.add(m.Experience(candidate_id=cand.id, **exp))
            for key, claim, ev, src, status, conf in spec["evidence"]:
                db.add(m.Evidence(candidate_id=cand.id, subject_type="capability", subject_key=key, claim=claim,
                                  evidence=ev, source=src, epistemic_status=status, confidence=conf))
            db.flush()
        db.commit()
        return {"company_id": str(co.id), "role_id": str(role.id), "conversation_id": str(conv.id),
                "candidates": cand_ids}
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(seed(), indent=2, ensure_ascii=False))
