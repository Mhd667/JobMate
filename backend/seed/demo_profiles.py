"""Synthetic test profiles for the demo accounts (fictional companies and people, Senegal).

Keyed by the account e-mail of supabase-demo-users.csv. Requested by Mouhamed on 2026-11-06:
9 complete candidates + 1 blank candidate, 4 complete companies with offers + 1 company without offer.
Candidates are written with deliberate trade-offs so the matching engine has real decisions to make.
"""

# --------------------------------------------------------------------------- companies and offers
COMPANIES = {
    "employer01@jobmate.test": {
        "company": {"name": "Teranga Pay", "city": "Dakar", "country": "Sénégal", "size": "51-200",
                    "description": "Fintech de paiement marchand : encaissement mobile money et carte pour les "
                                   "commerçants de proximité."},
        "identity": {
            "industry": "Fintech / paiements",
            "mission": "Permettre à chaque commerçant sénégalais d'encaisser sans cash, simplement.",
            "business_model": "Commission sur chaque transaction encaissée et abonnement mensuel pour les "
                              "commerçants qui utilisent le terminal.",
            "culture": "Équipe jeune, orientée résultats, beaucoup d'entraide entre les équipes terrain et le "
                       "call center.",
            "work_style": "Objectifs hebdomadaires suivis chaque lundi ; travail sur site au call center.",
            "management_style": "Management de proximité : un superviseur pour 8 téléconseillers, coaching "
                                "sur écoute d'appels.",
            "environment": "Plateau de 25 personnes à Dakar (Mermoz), horaires 8h-17h du lundi au samedi.",
            "values": ["Simplicité", "Respect du commerçant", "Résultat"],
            "context": "Croissance rapide : 12 000 commerçants actifs, objectif 20 000 d'ici fin 2027.",
            "confidence": 0.8,
        },
        "roles": [{
            "title": "Commerciale – Call Center", "location": "Dakar", "contract_type": "Remplacement",
            "duration": "6 mois",
            "identity": {
                "mission": "Remplacer notre meilleure commerciale du call center pendant son congé maternité : "
                           "convertir les commerçants qui appellent et relancer ceux qui hésitent.",
                "responsibilities": ["Appels entrants", "Vente / conversion", "Relance des prospects",
                                     "Gestion des réclamations simples"],
                "objectives": ["Tenir un taux de conversion d'au moins 18 % sur les appels entrants",
                               "40 nouveaux commerçants activés par mois"],
                "constraints": ["Démarrage sous 2 semaines", "Présence sur site à Dakar"],
                "stakeholders": ["Superviseur du call center", "Équipe terrain", "Support technique"],
                "success_factors": ["Excellent accueil au téléphone", "Aisance orale en wolof et en français",
                                    "Sens commercial : savoir conclure", "Calme face aux commerçants mécontents"],
                "languages": ["Français", "Wolof"],
                "availability": "Dès que possible · 6 mois",
                "priority": "elevee",
                "confidence": 0.85,
            },
        }],
    },
    "employer02@jobmate.test": {
        "company": {"name": "Sahel Logistique", "city": "Thiès", "country": "Sénégal", "size": "201-500",
                    "description": "Entreposage et distribution de produits de grande consommation pour "
                                   "l'intérieur du pays."},
        "identity": {
            "industry": "Logistique / entreposage",
            "mission": "Livrer à temps les boutiques de l'intérieur du pays, même loin de Dakar.",
            "business_model": "Contrats annuels avec des distributeurs : stockage facturé au mètre carré, "
                              "livraison à la tournée.",
            "culture": "Rigueur, sécurité d'abord, équipes stables avec beaucoup d'ancienneté.",
            "work_style": "Travail posté en 2 équipes (6h-14h, 14h-22h), inventaires mensuels.",
            "management_style": "Hiérarchie claire ; le responsable d'entrepôt rend compte au directeur des "
                                "opérations chaque semaine.",
            "environment": "Entrepôt de 6 000 m² à Thiès, 45 manutentionnaires et caristes.",
            "values": ["Sécurité", "Fiabilité", "Respect des équipes"],
            "context": "Nouveau logiciel de gestion d'entrepôt (WMS) déployé en 2026 ; taux d'erreur de "
                       "préparation à réduire.",
            "confidence": 0.8,
        },
        "roles": [{
            "title": "Responsable d'entrepôt", "location": "Thiès", "contract_type": "CDI", "duration": None,
            "identity": {
                "mission": "Faire tourner l'entrepôt de Thiès : stocks justes, préparations sans erreur, équipes "
                           "en sécurité.",
                "responsibilities": ["Encadrement de 2 équipes (45 personnes)", "Gestion des stocks et inventaires",
                                     "Pilotage des indicateurs (erreurs, délais)", "Sécurité et prévention"],
                "objectives": ["Taux d'erreur de préparation sous 0,5 %", "Inventaire tournant mensuel juste à 99 %"],
                "constraints": ["Basé à Thiès", "Disponible pour les deux équipes en rotation"],
                "stakeholders": ["Directeur des opérations", "Chefs d'équipe", "Clients distributeurs"],
                "success_factors": ["Leadership d'équipe terrain", "Maîtrise de la gestion de stock",
                                    "Aisance avec un logiciel WMS", "Rigueur sur la sécurité"],
                "languages": ["Français", "Wolof"],
                "availability": "Sous 1 mois",
                "priority": "normale",
                "confidence": 0.8,
            },
        }],
    },
    "employer03@jobmate.test": {
        "company": {"name": "Résidence Océane", "city": "Saly", "country": "Sénégal", "size": "51-200",
                    "description": "Hôtel 4 étoiles de 120 chambres sur la Petite-Côte, clientèle touristique et "
                                   "séminaires."},
        "identity": {
            "industry": "Hôtellerie",
            "mission": "Offrir un séjour chaleureux et sans accroc à une clientèle internationale.",
            "business_model": "Nuitées (60 % tour-opérateurs, 40 % réservations directes) et séminaires d'entreprise.",
            "culture": "Hospitalité, sourire, grande exigence sur le détail.",
            "work_style": "Travail en rotation 3x8, week-ends selon planning.",
            "management_style": "Chef de réception présent, briefing à chaque relève.",
            "environment": "Réception ouverte 24h/24, logiciel de gestion hôtelière, clientèle française, "
                           "anglaise et espagnole.",
            "values": ["Accueil", "Discrétion", "Esprit d'équipe"],
            "context": "Haute saison de novembre à avril ; deux départs à la réception à remplacer.",
            "confidence": 0.75,
        },
        "roles": [{
            "title": "Réceptionniste bilingue", "location": "Saly", "contract_type": "CDD", "duration": "12 mois",
            "identity": {
                "mission": "Accueillir les clients, gérer arrivées et départs, et régler les demandes avec le "
                           "sourire, en français et en anglais.",
                "responsibilities": ["Check-in / check-out", "Gestion des réservations", "Réponse aux demandes clients",
                                     "Encaissements et clôture de caisse"],
                "objectives": ["Note d'accueil au-dessus de 4,5/5 sur les avis clients", "Zéro écart de caisse"],
                "constraints": ["Horaires en rotation, nuits et week-ends", "Logement possible à Saly"],
                "stakeholders": ["Chef de réception", "Housekeeping", "Clients et tour-opérateurs"],
                "success_factors": ["Anglais courant", "Sens de l'accueil", "Gestion calme des réclamations",
                                    "Rigueur en caisse"],
                "languages": ["Français", "Anglais"],
                "availability": "Avant le 1er décembre · 12 mois",
                "priority": "elevee",
                "confidence": 0.8,
            },
        }],
    },
    "employer04@jobmate.test": {
        "company": {"name": "Kodelab", "city": "Dakar", "country": "Sénégal", "size": "11-50",
                    "description": "Studio produit qui conçoit des applications web et mobiles pour des PME et des ONG."},
        "identity": {
            "industry": "Logiciel / services numériques",
            "mission": "Construire des produits numériques utiles et simples pour les organisations africaines.",
            "business_model": "Projets au forfait et maintenance mensuelle ; un produit SaaS de prise de rendez-vous.",
            "culture": "Autonomie, revue de code systématique, démos chaque vendredi.",
            "work_style": "Hybride : 3 jours au bureau (Sacré-Cœur), 2 jours en télétravail.",
            "management_style": "Lead technique qui accompagne ; objectifs par sprint de 2 semaines.",
            "environment": "Équipe de 18 personnes : développeurs, designers, chefs de projet.",
            "values": ["Qualité", "Transparence", "Apprendre ensemble"],
            "context": "Deux nouveaux clients signés ; besoin de renfort côté développement et design.",
            "confidence": 0.8,
        },
        "roles": [{
            "title": "Développeur·se full-stack JavaScript", "location": "Dakar (hybride)", "contract_type": "CDI",
            "duration": None,
            "identity": {
                "mission": "Développer et maintenir les applications clients, du front React à l'API Node.js.",
                "responsibilities": ["Développement front-end React", "API Node.js et base PostgreSQL",
                                     "Revue de code", "Échanges techniques avec les clients"],
                "objectives": ["Livrer des fonctionnalités chaque sprint sans régression",
                               "Être autonome sur un projet client en 3 mois"],
                "constraints": ["3 jours par semaine au bureau à Dakar"],
                "stakeholders": ["Lead technique", "Chefs de projet", "Designers"],
                "success_factors": ["Bonne maîtrise de React et Node.js", "Code propre et testé",
                                    "Capacité à apprendre vite", "Communication claire avec les non-techniciens"],
                "languages": ["Français", "Anglais technique"],
                "availability": "Dès que possible",
                "priority": "normale",
                "confidence": 0.8,
            },
        }, {
            "title": "Designer UX/UI", "location": "Dakar (hybride)", "contract_type": "Freelance",
            "duration": "4 mois",
            "identity": {
                "mission": "Concevoir les parcours et les écrans de deux nouvelles applications clients.",
                "responsibilities": ["Recherche utilisateur", "Maquettes et prototypes Figma",
                                     "Design system", "Tests utilisateurs"],
                "objectives": ["Prototypes validés par les clients en 6 semaines"],
                "constraints": ["Présence aux ateliers clients à Dakar"],
                "stakeholders": ["Chefs de projet", "Développeurs", "Clients"],
                "success_factors": ["Maîtrise de Figma", "Recherche et tests utilisateurs",
                                    "Portfolio d'applications mobiles", "Savoir présenter et défendre ses choix"],
                "languages": ["Français"],
                "availability": "Mi-novembre · 4 mois",
                "priority": "normale",
                "confidence": 0.75,
            },
        }],
    },
    # Complete company profile, no offer: to create one in the chat and test matching from scratch.
    "employer05@jobmate.test": {
        "company": {"name": "Baobab Conseil", "city": "Dakar", "country": "Sénégal", "size": "11-50",
                    "description": "Cabinet de conseil en organisation et en formation pour les PME."},
        "identity": {
            "industry": "Conseil / formation",
            "mission": "Aider les PME à mieux s'organiser et à faire grandir leurs équipes.",
            "business_model": "Missions de conseil au forfait et formations inter-entreprises.",
            "culture": "Bienveillance, exigence intellectuelle, beaucoup de terrain chez les clients.",
            "work_style": "Missions chez les clients, déplacements fréquents à Dakar et Thiès.",
            "management_style": "Associés très disponibles, points hebdomadaires.",
            "environment": "Petite équipe de 14 consultants et formateurs.",
            "values": ["Utilité", "Rigueur", "Bienveillance"],
            "context": "Le cabinet veut renforcer son équipe commerciale et administrative en 2027.",
            "confidence": 0.7,
        },
        "roles": [],
    },
}

# --------------------------------------------------------------------------- candidates
CANDIDATES = {
    "candidate01@jobmate.test": {
        "full_name": "Awa Ndiaye", "headline": "Téléconseillère vente – 4 ans de call center", "location": "Dakar",
        "availability": {"available_from": "2026-11-16", "notice_weeks": 1},
        "identity": {
            "career_direction": "Poste commercial en call center ou en relation client, à Dakar.",
            "professional_goals": ["Devenir superviseure d'équipe d'ici 2 ans"],
            "strengths": ["Conversion au téléphone", "Calme avec les clients mécontents", "Wolof et français"],
            "preferences": ["Objectifs clairs et primes sur résultats", "Travail en équipe"],
            "constraints": ["Pas de déplacements hors de Dakar"],
            "aspirations": ["Encadrer une petite équipe de vente"],
            "summary": "Quatre ans de vente par téléphone chez un opérateur télécom, régulièrement dans le top 3 "
                       "de son plateau.",
            "confidence": 0.6,
        },
        "experiences": [
            {"title": "Téléconseillère vente", "organization": "Opérateur télécom (centre d'appels)",
             "sector": "Télécoms", "start_date": "2022-09", "end_date": None,
             "description": "Vente d'offres internet et mobile sur appels entrants et sortants.",
             "achievements": ["Taux de conversion moyen de 21 % sur 2025", "Top 3 du plateau 7 mois sur 12"],
             "skills": ["Vente au téléphone", "Traitement des objections", "CRM"]},
            {"title": "Agente d'accueil", "organization": "Agence commerciale télécom", "sector": "Télécoms",
             "start_date": "2021-03", "end_date": "2022-08",
             "description": "Accueil et orientation des clients en agence.",
             "achievements": ["Formée comme référente réclamations"], "skills": ["Accueil", "Réclamations"]},
        ],
    },
    "candidate02@jobmate.test": {
        "full_name": "Ibrahima Sarr", "headline": "Commercial terrain mobile money – 3 ans", "location": "Dakar",
        "availability": {"available_from": "2026-12-01", "notice_weeks": 4},
        "identity": {
            "career_direction": "Vente B2B auprès des commerçants, idéalement dans la fintech.",
            "professional_goals": ["Passer responsable de zone"],
            "strengths": ["Convaincre des commerçants réticents", "Connaissance du terrain à Dakar et Pikine"],
            "preferences": ["Autonomie", "Rémunération variable importante"],
            "constraints": ["Préavis de 4 semaines"],
            "aspirations": ["Ouvrir de nouvelles zones commerciales"],
            "summary": "Commercial terrain qui a recruté plus de 300 marchands pour un service de mobile money ; "
                       "peu d'expérience du téléphone.",
            "confidence": 0.6,
        },
        "experiences": [
            {"title": "Commercial terrain", "organization": "Distributeur de services mobile money",
             "sector": "Fintech", "start_date": "2023-01", "end_date": None,
             "description": "Prospection et activation de marchands dans les marchés de Dakar.",
             "achievements": ["320 marchands activés en 2025", "Meilleur vendeur du trimestre 2 fois"],
             "skills": ["Prospection", "Négociation", "Formation des marchands"]},
        ],
    },
    "candidate03@jobmate.test": {
        "full_name": "Mariama Ba", "headline": "Chargée de service client e-commerce – anglais courant",
        "location": "Mbour",
        "availability": {"available_from": "2026-11-20", "notice_weeks": 2},
        "identity": {
            "career_direction": "Accueil et relation client, dans l'hôtellerie ou un call center.",
            "professional_goals": ["Travailler avec une clientèle internationale"],
            "strengths": ["Anglais courant", "Patience avec les clients", "Organisation"],
            "preferences": ["Contact humain", "Environnement international"],
            "constraints": ["Habite à Mbour, peut aller jusqu'à Saly ou Dakar"],
            "aspirations": ["Devenir chef de réception"],
            "summary": "Deux ans de service client pour un site de e-commerce, plus une saison comme hôtesse "
                       "d'accueil dans un hôtel.",
            "confidence": 0.6,
        },
        "experiences": [
            {"title": "Chargée de service client", "organization": "Site de e-commerce", "sector": "E-commerce",
             "start_date": "2024-06", "end_date": None,
             "description": "Réponse aux clients par téléphone, chat et e-mail, en français et en anglais.",
             "achievements": ["Satisfaction client de 4,7/5 sur ses tickets"],
             "skills": ["Service client", "Anglais", "Gestion des réclamations"]},
            {"title": "Hôtesse d'accueil (saisonnière)", "organization": "Hôtel club de la Petite-Côte",
             "sector": "Hôtellerie", "start_date": "2023-11", "end_date": "2024-04",
             "description": "Accueil des clients, informations et réservations d'excursions.",
             "achievements": [], "skills": ["Accueil", "Anglais"]},
        ],
    },
    "candidate04@jobmate.test": {
        "full_name": "Cheikh Diop", "headline": "Chef d'équipe logistique – 6 ans d'entrepôt", "location": "Thiès",
        "availability": {"available_from": "2026-12-15", "notice_weeks": 4},
        "identity": {
            "career_direction": "Responsable d'entrepôt ou de plateforme logistique.",
            "professional_goals": ["Prendre la responsabilité complète d'un site"],
            "strengths": ["Encadrement d'équipes de manutentionnaires", "Inventaires", "Sécurité"],
            "preferences": ["Rester dans la région de Thiès"],
            "constraints": ["Préavis d'un mois"],
            "aspirations": ["Diriger une plateforme régionale"],
            "summary": "Six ans en entrepôt, dont trois comme chef d'équipe de 20 personnes ; utilise un WMS "
                       "depuis un an.",
            "confidence": 0.65,
        },
        "experiences": [
            {"title": "Chef d'équipe entrepôt", "organization": "Distributeur de boissons", "sector": "Logistique",
             "start_date": "2023-02", "end_date": None,
             "description": "Encadrement de l'équipe de préparation (20 personnes), inventaires, sécurité.",
             "achievements": ["Erreurs de préparation divisées par deux en 2025", "Zéro accident en 18 mois"],
             "skills": ["Management d'équipe", "Inventaire", "WMS", "Sécurité"]},
            {"title": "Cariste puis préparateur", "organization": "Distributeur de boissons",
             "sector": "Logistique", "start_date": "2020-01", "end_date": "2023-01",
             "description": "Préparation de commandes et conduite de chariot élévateur.",
             "achievements": ["CACES chariot élévateur"], "skills": ["Préparation de commandes", "Cariste"]},
        ],
    },
    "candidate05@jobmate.test": {
        "full_name": "Fatoumata Kane", "headline": "Ingénieure supply chain junior", "location": "Dakar",
        "availability": {"available_from": "2026-11-10", "notice_weeks": 0},
        "identity": {
            "career_direction": "Supply chain ou gestion d'entrepôt, prête à bouger à Thiès.",
            "professional_goals": ["Prendre un premier poste de responsabilité"],
            "strengths": ["Analyse de données (Excel, SQL)", "Amélioration des processus"],
            "preferences": ["Projets d'amélioration continue"],
            "constraints": [],
            "aspirations": ["Devenir directrice des opérations"],
            "summary": "Master en supply chain, stage d'un an en entrepôt où elle a paramétré un WMS ; pas "
                       "encore d'encadrement d'équipe.",
            "confidence": 0.55,
        },
        "experiences": [
            {"title": "Stagiaire méthodes logistiques", "organization": "Plateforme logistique portuaire",
             "sector": "Logistique", "start_date": "2025-09", "end_date": "2026-08",
             "description": "Paramétrage du WMS, tableaux de bord et analyse des erreurs de préparation.",
             "achievements": ["Tableau de bord des erreurs adopté par le site"],
             "skills": ["WMS", "Excel", "SQL", "Lean"]},
        ],
    },
    "candidate06@jobmate.test": {
        "full_name": "Ousseynou Faye", "headline": "Réceptionniste d'hôtel – 5 ans, trilingue", "location": "Saly",
        "availability": {"available_from": "2026-11-25", "notice_weeks": 2},
        "identity": {
            "career_direction": "Réception en hôtel 4 ou 5 étoiles sur la Petite-Côte.",
            "professional_goals": ["Devenir chef de réception"],
            "strengths": ["Anglais et espagnol courants", "Logiciel de gestion hôtelière", "Gestion des réclamations"],
            "preferences": ["Clientèle internationale"],
            "constraints": ["Préfère éviter les nuits fixes"],
            "aspirations": ["Travailler un jour dans un hôtel de luxe à l'étranger"],
            "summary": "Cinq ans de réception dans deux hôtels de Saly, habitué aux arrivées de groupes.",
            "confidence": 0.65,
        },
        "experiences": [
            {"title": "Réceptionniste", "organization": "Hôtel 4 étoiles de Saly", "sector": "Hôtellerie",
             "start_date": "2021-10", "end_date": None,
             "description": "Arrivées et départs, réservations, caisse, gestion des groupes.",
             "achievements": ["Cité dans 40 avis clients positifs en 2025"],
             "skills": ["Réception", "Caisse", "Anglais", "Espagnol", "Logiciel hôtelier"]},
        ],
    },
    "candidate07@jobmate.test": {
        "full_name": "Aïssatou Mbaye", "headline": "Développeuse full-stack React / Node.js – 3 ans",
        "location": "Dakar",
        "availability": {"available_from": "2026-12-01", "notice_weeks": 4},
        "identity": {
            "career_direction": "Développement web full-stack dans une équipe produit.",
            "professional_goals": ["Devenir lead technique"],
            "strengths": ["React", "Node.js et PostgreSQL", "Tests automatisés"],
            "preferences": ["Revue de code", "Télétravail partiel"],
            "constraints": ["Préavis d'un mois"],
            "aspirations": ["Contribuer à des produits utilisés en Afrique"],
            "summary": "Trois ans dans une agence web : applications React et API Node.js pour des clients du "
                       "secteur bancaire.",
            "confidence": 0.65,
        },
        "experiences": [
            {"title": "Développeuse full-stack", "organization": "Agence web", "sector": "Logiciel",
             "start_date": "2023-09", "end_date": None,
             "description": "Applications React et API Node.js/PostgreSQL pour des clients bancaires.",
             "achievements": ["A mis en place les tests automatisés de l'agence"],
             "skills": ["React", "Node.js", "PostgreSQL", "Jest", "Git"]},
        ],
    },
    "candidate08@jobmate.test": {
        "full_name": "Moustapha Gueye", "headline": "Développeur web autodidacte – front-end et un peu de design",
        "location": "Dakar",
        "availability": {"available_from": "2026-11-10", "notice_weeks": 0},
        "identity": {
            "career_direction": "Premier CDI de développeur, front-end ou full-stack.",
            "professional_goals": ["Monter en compétence sur le back-end"],
            "strengths": ["Apprend très vite", "Interfaces soignées", "Projets personnels livrés"],
            "preferences": ["Mentorat", "Équipe bienveillante"],
            "constraints": [],
            "aspirations": ["Créer un jour son propre produit"],
            "summary": "Ancien vendeur en boutique, formé en bootcamp en 2025, un an de missions freelance en "
                       "React ; bases de Node.js.",
            "confidence": 0.5,
        },
        "experiences": [
            {"title": "Développeur front-end freelance", "organization": "Indépendant", "sector": "Logiciel",
             "start_date": "2025-10", "end_date": None,
             "description": "Sites et petites applications React pour des commerces locaux.",
             "achievements": ["6 projets livrés", "Une application de réservation utilisée par 3 salons"],
             "skills": ["React", "JavaScript", "Figma", "Node.js (bases)"]},
            {"title": "Vendeur", "organization": "Boutique d'électronique", "sector": "Commerce",
             "start_date": "2021-01", "end_date": "2025-03", "description": "Vente et conseil client.",
             "achievements": [], "skills": ["Vente", "Relation client"]},
        ],
    },
    "candidate09@jobmate.test": {
        "full_name": "Ndèye Fall", "headline": "Designer UX/UI – 4 ans, applications mobiles", "location": "Dakar",
        "availability": {"available_from": "2026-11-15", "notice_weeks": 1},
        "identity": {
            "career_direction": "Missions de design UX/UI, en freelance ou en CDI.",
            "professional_goals": ["Piloter le design de bout en bout d'un produit"],
            "strengths": ["Figma et design systems", "Tests utilisateurs", "Présentation aux clients"],
            "preferences": ["Missions variées", "Freelance accepté"],
            "constraints": [],
            "aspirations": ["Monter un studio de design"],
            "summary": "Quatre ans de design d'applications mobiles (santé, éducation), avec des tests "
                       "utilisateurs sur le terrain.",
            "confidence": 0.65,
        },
        "experiences": [
            {"title": "Designer UX/UI", "organization": "Startup e-santé", "sector": "Santé numérique",
             "start_date": "2022-10", "end_date": None,
             "description": "Conception de l'application patient et du design system.",
             "achievements": ["Taux de rendez-vous honorés +15 % après la refonte"],
             "skills": ["Figma", "Recherche utilisateur", "Design system", "Prototypage"]},
        ],
    },
    # candidate10@jobmate.test: left blank on purpose (to test the candidate conversation and matching).
}


def cv_text(p: dict) -> str:
    """A plain-text CV built from the profile, analysed by the engine like an uploaded CV."""
    lines = [p["full_name"], p["headline"], p["location"], "", "Profil", p["identity"]["summary"], "", "Expérience"]
    for e in p["experiences"]:
        end = e["end_date"] or "aujourd'hui"
        lines.append(f"- {e['title']}, {e['organization']} ({e['start_date']} – {end})")
        lines.append(f"  {e['description']}")
        lines += [f"  • {a}" for a in e["achievements"]]
        if e["skills"]:
            lines.append("  Compétences : " + ", ".join(e["skills"]))
    return "\n".join(lines)
