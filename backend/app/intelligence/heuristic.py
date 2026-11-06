"""Deterministic baseline Intelligence Layer (no LLM).

Purpose: (1) the demo always works, even without an API key; (2) the LLM layer falls back to
it; (3) it is the reference that tomorrow's Bayesian/VoI layer must beat.
It is intentionally simple and transparent: every number comes from the evidence coverage
computed by the Context Builder (support / certainty per Success Model capability).
"""
from __future__ import annotations

import re
import unicodedata

from app.intelligence import contracts as c

IMPORTANCE_W = {"critical": 1.0, "important": 0.6, "nice": 0.25}
IMPORTANCE_FR = {"critical": "critique", "important": "importante", "nice": "secondaire"}
LEVEL_FR = {"strong": "solide", "moderate": "partielle", "weak": "faible", "unknown": "inconnue"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower()


# Small canonical capability vocabulary (FR keywords -> key, label). Extensible.
VOCAB: dict[str, tuple[str, list[str]]] = {
    "b2b_prospecting": ("Prospection B2B", ["prospect", "chasse", "nouveaux clients", "pipeline", "acquisition"]),
    "persuasion": ("Persuasion", ["persuad", "convain", "pitch", "closing", "conclure", "signer"]),
    "objection_handling": ("Traitement des objections", ["objection", "reticen", "refus"]),
    "conflict_management": ("Gestion de clients difficiles / conflits", ["conflit", "agressi", "difficile", "mecontent", "litige", "plainte", "colere", "calme"]),
    "client_relationship": ("Relation client / fidélisation", ["fidelis", "relation client", "satisfaction", "compte client", "account"]),
    "domain_knowledge": ("Connaissance du secteur", ["mobile money", "fintech", "paiement", "banque", "secteur"]),
    "learning_agility": ("Capacité d'apprentissage", ["apprendre", "apprentissage", "monter en competence", "rapidement appris", "autodidacte", "ramp"]),
    "autonomy": ("Autonomie / organisation", ["autonom", "organis"]),
    "negotiation": ("Négociation", ["negoci", "tarif", "marge"]),
    "team_leadership": ("Leadership d'équipe", ["encadr", "leadership", "diriger une equipe", "management d'equipe"]),
    "data_analysis": ("Analyse de données", ["donnees", "excel", "analyse", "kpi", "reporting"]),
}


def detect_capabilities(text: str) -> list[str]:
    t = norm(text)
    return [k for k, (_, kws) in VOCAB.items() if any(kw in t for kw in kws)]


def split_items(text: str) -> list[str]:
    parts = re.split(r"[;\n•]|\s-\s|\.\s", text)
    return [p.strip(" .-") for p in parts if len(p.strip(" .-")) > 2]


# --------------------------------------------------------------------------- conversation
COMPANY_Q = {
    "company.mission": "Pour commencer, quelle est la mission de votre entreprise, en une ou deux phrases ?",
    "company.business_model": "Comment l'entreprise gagne-t-elle de l'argent ? Qui sont vos clients ?",
    "company.culture": "Comment décririez-vous la culture de l'équipe, au quotidien ?",
    "company.management_style": "Comment est managée l'équipe que cette personne va rejoindre ?",
}
ROLE_Q = {
    "role.mission": "Parlons du poste. Pourquoi ouvrez-vous ce recrutement maintenant, et quelle est sa mission ?",
    "role.objectives": "Dans 6 mois, qu'est-ce qui vous ferait dire que c'était le bon recrutement ?",
    "role.responsibilities": "Concrètement, à quoi ressemble une semaine type dans ce poste ?",
    "role.constraints": "Y a-t-il des contraintes fortes : date de démarrage, langues, déplacements, budget ?",
    "role.stakeholders": "Avec qui cette personne va-t-elle travailler au quotidien (clients, équipes, manager) ?",
    "role.languages": "Quelles langues la personne doit-elle parler avec vos clients et l'équipe ?",
    "role.availability": "Pour quand avez-vous besoin de cette personne, et pour combien de temps ?",
    "role.success_factors": "D'après votre expérience, qu'est-ce qui distingue les personnes qui réussissent "
                            "vraiment à ce type de poste chez vous ? Et celles qui échouent ?",
}
CANDIDATE_Q = {
    "candidate.career_direction": "Vers quel type de poste aimeriez-vous aller dans les prochaines années ?",
    "candidate.strengths": "Racontez-moi une réussite professionnelle dont vous êtes fier ou fière. Qu'avez-vous fait, concrètement ?",
    "candidate.professional_goals": "Qu'aimeriez-vous accomplir dans votre prochain poste ?",
    "candidate.preferences": "Dans quel type d'environnement travaillez-vous le mieux ?",
    "candidate.constraints": "Avez-vous des contraintes à connaître : disponibilité, lieu, préavis, salaire ?",
    "candidate.aspirations": "Si tout se passait bien, où vous voyez-vous dans 3 ans ?",
}
LIST_FIELDS = {"values", "responsibilities", "objectives", "constraints", "stakeholders", "success_factors",
               "professional_goals", "strengths", "preferences", "aspirations", "unknowns", "assumptions",
               "languages"}


def employer_intent(msg: str) -> c.EmployerIntent:
    t = norm(msg)
    if re.search(r"lance[rz]? la recherche|cherche[rz]? (des|les) profils|c.est bon,? vas", t):
        return "start_search"
    if re.search(r"compar|confront|departag", t):
        return "request_confrontation"
    if "recommand" in t or "qui recruter" in t or "qui choisir" in t:
        return "request_recommendation"
    if re.search(r"top ?3|shortlist|finaliste|preselection|selectionne", t):
        return "request_shortlist"
    if re.search(r"analys\w* (les )?candidat|matching|match", t):
        return "request_matching"
    if re.search(r"success model|modele de reussite", t):
        return "request_success_model"
    return "inform"


def _fill(field: str, msg: str) -> dict:
    name = field.split(".", 1)[1]
    return {name: split_items(msg) or [msg.strip()]} if name in LIST_FIELDS else {name: msg.strip()}


# --------------------------------------------------------------------------- question bank
QUESTION_BANK: dict[str, dict[str, str]] = {
    "conflict_management": {
        "behavioral": "Racontez-moi la dernière fois qu'un client s'est montré agressif ou très mécontent face à vous. "
                      "Qu'a-t-il dit, qu'avez-vous fait, et comment cela s'est-il terminé ?",
        "simulation": "Simulation : un commerçant vous appelle, furieux, parce que ses paiements sont bloqués depuis "
                      "deux jours et qu'il menace de partir chez un concurrent. Répondez-lui comme si vous étiez au téléphone.",
    },
    "persuasion": {
        "behavioral": "Décrivez une situation où vous avez convaincu quelqu'un qui n'était pas du tout intéressé au départ. "
                      "Quels arguments avez-vous utilisés et qu'est-ce qui l'a fait changer d'avis ?",
        "simulation": "Simulation : vous avez 2 minutes face au gérant d'une boutique qui utilise uniquement le cash "
                      "et dit « je n'en ai pas besoin ». Faites-lui votre pitch.",
    },
    "objection_handling": {
        "behavioral": "Quelle est l'objection client la plus difficile que vous ayez rencontrée, et comment l'avez-vous levée ?",
        "simulation": "Le prospect vous dit : « Vos frais sont trop élevés et je ne fais pas confiance aux paiements "
                      "mobiles. » Que répondez-vous ?",
    },
    "learning_agility": {
        "situational": "Imaginez que vous découvrez un produit et un secteur que vous ne connaissez pas, et que vous devez "
                       "être opérationnel sur le terrain dans 3 semaines. Comment organisez-vous ces 3 semaines ?",
        "behavioral": "Racontez une situation où vous avez dû apprendre très vite quelque chose de nouveau. Combien de "
                      "temps cela a pris et comment l'avez-vous su ?",
    },
    "b2b_prospecting": {
        "behavioral": "Comment avez-vous construit votre portefeuille de clients dans votre dernier poste ? "
                      "Combien de prospects contactiez-vous par semaine, et avec quel taux de conversion ?",
        "situational": "On vous confie un quartier de Dakar où personne ne connaît notre produit. Que faites-vous le premier mois ?",
    },
    "domain_knowledge": {
        "verification": "Expliquez-moi, comme à un commerçant, comment fonctionne un paiement marchand par mobile money "
                        "et ce qui le différencie d'un transfert entre particuliers.",
    },
}


def _question_for(spec: c.CapabilitySpec, qtype: str) -> tuple[str, str]:
    bank = QUESTION_BANK.get(spec.key, {})
    if qtype in bank:
        return qtype, bank[qtype]
    if bank:
        k = next(iter(bank))
        return k, bank[k]
    obs = spec.observable_evidence[0] if spec.observable_evidence else spec.name.lower()
    if qtype in ("situational", "simulation"):
        return "situational", (f"Mise en situation : dans ce poste, vous devez démontrer « {spec.name} ». "
                               f"Décrivez précisément comment vous vous y prendriez, étape par étape.")
    return "behavioral", (f"Racontez une situation réelle qui montre votre capacité à {obs}. "
                          f"Qu'avez-vous fait, et quel a été le résultat ?")


class HeuristicIntelligence:
    name = "heuristic"
    last_producer = "heuristic"

    # ------------------------------------------------------------------ conversations
    def employer_turn(self, ctx: c.EmployerConversationContext) -> c.EmployerTurnOutput:
        msg = ctx.user_message.strip()
        intent = employer_intent(msg)
        company_patch: dict = {}
        role_patch: dict = {}
        ack = ""
        if intent == "inform" and len(msg) > 3:
            target = ctx.last_asked_field
            if target is None:
                target = "company.context" if not ctx.company.identity.get("context") else "role.context"
            patch = _fill(target, msg)
            (company_patch if target.startswith("company.") else role_patch).update(patch)
            ack = "Merci, c'est noté. "
            caps = detect_capabilities(msg)
            if caps and target.startswith("role."):
                ack += ("Je retiens que le poste demande notamment : "
                        + ", ".join(VOCAB[k][0].lower() for k in caps[:3]) + ". ")
        missing = [f for f in ctx.missing_fields if f != ctx.last_asked_field or intent != "inform"]
        if intent != "inform":
            return c.EmployerTurnOutput(reply="Je m'en occupe.", intent=intent)
        role_missing = [f for f in missing if f.startswith("role.")]
        if role_missing:
            nxt = role_missing[0]
            if nxt == "role.responsibilities" and re.search(r"sugg|propos|je ne sais pas|aucune idee", norm(msg)):
                # Deterministic baseline: generic options; the LLM proposes options adapted to the role.
                return c.EmployerTurnOutput(
                    reply=ack + "Pour bien cibler la recherche, cochez les missions principales du poste.",
                    intent="inform", asked_field=nxt,
                    company_identity_patch=c.CompanyIdentityPatch(**company_patch),
                    role_identity_patch=c.RoleIdentityPatch(**role_patch),
                    mission_question="Quelles sont les principales missions du poste ?",
                    mission_options=["Prospection", "Vente / conversion", "Suivi client", "Gestion des réclamations",
                                     "Reporting"])
            q = ROLE_Q.get(nxt, "Pouvez-vous m'en dire plus ?")
            return c.EmployerTurnOutput(reply=ack + q, intent="inform",
                                        company_identity_patch=c.CompanyIdentityPatch(**company_patch),
                                        role_identity_patch=c.RoleIdentityPatch(**role_patch), asked_field=nxt)
        return c.EmployerTurnOutput(
            reply=ack + "J'ai une bonne image du poste. Voici le récapitulatif avant de lancer la recherche.",
            intent="inform", ready_for_search=True,
            company_identity_patch=c.CompanyIdentityPatch(**company_patch),
            role_identity_patch=c.RoleIdentityPatch(**role_patch))

    def candidate_turn(self, ctx: c.CandidateConversationContext) -> c.CandidateTurnOutput:
        msg = ctx.user_message.strip()
        if re.search(r"offre|opportunit|poste ouvert|annonce", norm(msg)):
            return c.CandidateTurnOutput(reply="Voici les opportunités qui correspondent à votre profil.",
                                         intent="request_opportunities")
        wants_sources = bool(re.search(r"(ajouter|envoyer|partager).{0,20}(cv|linkedin|portfolio)", norm(msg)))
        patch: dict = {}
        if wants_sources:
            pass
        elif ctx.last_asked_field and len(msg) > 3:
            patch = _fill(ctx.last_asked_field, msg)
        elif len(msg) > 3:
            patch = {"summary": msg}
        missing = [f for f in ctx.missing_fields if f != ctx.last_asked_field]
        if missing:
            return c.CandidateTurnOutput(reply=("Merci. " if patch else "") + CANDIDATE_Q.get(missing[0], "Dites-m'en plus ?"),
                                         professional_identity_patch=c.ProfessionalIdentityPatch(**patch),
                                         asked_field=missing[0], show_sources_card=wants_sources)
        return c.CandidateTurnOutput(reply="Merci, votre profil est prêt. Je vous préviens ici dès qu'une offre "
                                           "vous correspond.", show_sources_card=wants_sources,
                                     professional_identity_patch=c.ProfessionalIdentityPatch(**patch))

    # ------------------------------------------------------------------ success model
    def build_success_model(self, ctx: c.SuccessModelContext) -> c.SuccessModelDraft:
        ident = ctx.role.identity
        text = " ".join(str(ident.get(k, "")) for k in
                        ("mission", "objectives", "responsibilities", "success_factors", "context", "constraints"))
        keys = detect_capabilities(text) or ["communication"]
        if "learning_agility" not in keys:
            keys.append("learning_agility")
        sf_text = norm(" ".join(map(str, ident.get("success_factors", []))))
        caps = []
        for k in keys[:7]:
            label = VOCAB.get(k, (k.replace("_", " ").title(), []))[0]
            kws = VOCAB.get(k, ("", []))[1]
            imp = "critical" if any(kw in sf_text for kw in kws) else "important"
            if k == "learning_agility":
                imp = "important"
            caps.append(c.CapabilitySpec(key=k, name=label, importance=imp,
                                         observable_evidence=[f"exemple concret et vérifiable de {label.lower()}"]))
        if not any(cp.importance == "critical" for cp in caps):
            caps[0].importance = "critical"
        crit = [cp.key for cp in caps if cp.importance == "critical"]
        conditions = [c.SuccessCondition(name="performance_immediate", requires=crit,
                                         description="Maîtrise déjà démontrée des capacités critiques")]
        non_domain = [k for k in crit if k != "domain_knowledge"]
        if "learning_agility" in keys and non_domain:
            conditions.append(c.SuccessCondition(
                name="potentiel_et_accompagnement", requires=["learning_agility"] + non_domain[:1], weight=0.8,
                description="Forte capacité d'apprentissage + une capacité critique, avec ramp-up accepté"))
        prio = "immediate_performance" if re.search(r"immediat|rapidement|vite|des le", norm(text)) else "balanced"
        return c.SuccessModelDraft(
            critical_outcomes=[{"outcome": o, "horizon": "6 mois", "measure": "à préciser"}
                               for o in ident.get("objectives", [])[:3]],
            critical_capabilities=caps,
            required_behaviors=[f"démontre {cp.name.lower()} en situation réelle" for cp in caps if cp.importance == "critical"],
            success_conditions=conditions,
            tradeoffs=["Performance immédiate vs potentiel de progression"],
            risks=["Modèle construit sans données d'historique de recrutement : à valider avec l'employeur"],
            unknowns=["Poids relatif des capacités critiques non confirmé par l'employeur"],
            priorities={"primary": prio, "notes": "déduit du discours de l'employeur"},
            confidence=0.4)

    # ------------------------------------------------------------------ candidate understanding
    def understand_candidate(self, ctx: c.CandidateUnderstandingContext) -> c.CandidateUnderstandingOutput:
        caps: dict[str, c.CapabilityDraft] = {}
        evidence: list[c.EvidenceDraft] = []
        for exp in ctx.candidate.experiences:
            for skill in exp.get("skills", []):
                for k in detect_capabilities(skill):
                    caps.setdefault(k, c.CapabilityDraft(key=k, name=VOCAB[k][0], level="moderate",
                                                         status="inference", confidence=0.4, source="cv"))
            for ach in exp.get("achievements", []):
                for k in detect_capabilities(ach):
                    evidence.append(c.EvidenceDraft(
                        subject_key=k, claim=VOCAB[k][0], evidence=f"{ach} ({exp.get('title')}, {exp.get('organization')})",
                        source="previous_experience", epistemic_status="inference", confidence=0.55))
        return c.CandidateUnderstandingOutput(capabilities=list(caps.values()), evidence=evidence)

    # ------------------------------------------------------------------ adaptive assessment
    def next_assessment(self, ctx: c.AssessmentContext) -> c.AssessmentPlan:
        sm = ctx.role.success_model
        specs = {cp.key: cp for cp in sm.critical_capabilities}
        cov = ctx.candidate.coverage
        crit_cov = [cv for cv in cov if cv.importance == "critical"]
        unknown_share = sum(1 for cv in crit_cov if cv.level == "unknown") / max(1, len(crit_cov))
        atypical = unknown_share >= 0.5
        asked = {q.get("target_capability") for q in ctx.previous_questions}
        best, best_v = None, -1.0
        for cv in cov:
            if cv.open_assessments or cv.level == "strong":
                continue
            v = IMPORTANCE_W[cv.importance] * (1 - cv.certainty) * (0.5 if cv.capability_key in asked else 1.0)
            if cv.level == "weak":
                v += 0.1 * IMPORTANCE_W[cv.importance]  # evidence points the wrong way: worth checking
            if cv.untested_claim:
                v += 0.15 * IMPORTANCE_W[cv.importance]  # a claim nobody has observed: test the hypothesis
            if v > best_v:
                best, best_v = cv, v
        if best is None:  # everything strong or already being tested: verify the least certain
            best = min(cov, key=lambda x: x.certainty)
            best_v = 0.05
        spec = specs[best.capability_key]
        if atypical:
            qtype = "situational" if spec.key == "learning_agility" else "simulation"
            why = (f"Profil atypique avec peu de preuves directes ({int(unknown_share*100)} % des capacités critiques "
                   f"sont inconnues) : une mise en situation permet de vérifier l'hypothèse sur "
                   f"« {spec.name} » plutôt que de se fier au parcours.")
            if best.untested_claim:
                why += " Cette capacité est revendiquée, mais rien ne l'a encore montrée."
        elif best.level == "unknown":
            qtype = "simulation" if spec.key in QUESTION_BANK and "simulation" in QUESTION_BANK[spec.key] else "behavioral"
            strong = [cv.capability_name for cv in cov if cv.level == "strong"]
            why = (f"Les preuves sont déjà solides sur {', '.join(strong) or 'plusieurs dimensions'}, mais il n'y a "
                   f"presque rien sur « {spec.name} », capacité {IMPORTANCE_FR[spec.importance]} du modèle de réussite. "
                   f"C'est l'information qui peut le plus changer la décision.")
        else:
            qtype = "behavioral" if best.level == "weak" else "verification"
            why = (f"La couverture de « {spec.name} » est {LEVEL_FR[best.level]} (certitude {best.certainty:.0%}) : "
                   f"une question ciblée permet de confirmer ou d'infirmer ce point.")
        qtype, question = _question_for(spec, qtype)
        return c.AssessmentPlan(
            target_capability=spec.key,
            objective=f"Réduire l'incertitude sur « {spec.name} » pour {ctx.candidate.full_name}",
            question_type=qtype, question=question,
            expected_evidence=spec.observable_evidence or [f"exemple concret de {spec.name.lower()}"],
            rationale=why, expected_value=round(best_v, 3))

    def interpret_response(self, ctx: c.ResponseContext) -> c.ResponseInterpretation:
        r = ctx.response
        t = norm(r)
        key = ctx.request["target_capability"]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", r) if s.strip()]
        actions = [s for s in sentences if re.search(r"\b(j'ai|je |nous avons|j ai)", norm(s))]
        concrete = bool(re.search(r"\d", r))
        on_topic = key in detect_capabilities(r) or any(
            w in t for e in ctx.request.get("expected_evidence", []) for w in norm(e).split() if len(w) > 5)
        quality = min(1.0, 0.25 * (len(r) > 200) + 0.25 * bool(actions) + 0.2 * concrete + 0.3 * on_topic)
        status = "inference" if quality >= 0.5 else "hypothesis"
        conf = round(0.3 + 0.4 * quality, 2)
        label = VOCAB.get(key, (key, []))[0]
        ev = [c.EvidenceDraft(
            subject_key=key, claim=f"{label} {'démontrée' if quality >= 0.5 else 'peu démontrée'} en assessment",
            evidence=(actions[0] if actions else (sentences[0] if sentences else r))[:400],
            source="assessment", epistemic_status=status, confidence=conf,
            polarity="supports" if quality >= 0.35 else "contradicts")]
        return c.ResponseInterpretation(
            summary=f"Réponse {'concrète et ciblée' if quality >= 0.5 else 'peu concrète'} sur « {label} ».",
            observed_behaviors=actions[:3], evidence=ev, confidence=conf)

    # ------------------------------------------------------------------ matching
    def match(self, ctx: c.MatchContext) -> c.MatchAnalysis:
        cand, sm = ctx.candidate, ctx.role.success_model
        cov = {cv.capability_key: cv for cv in cand.coverage}
        ev_by_id = {e.id: e for e in cand.evidence}
        dims, strengths, gaps, uncertainties, ev_ids = [], [], [], [], []
        for cp in sm.critical_capabilities:
            cv = cov[cp.key]
            best_ev = sorted((ev_by_id[i] for i in cv.evidence_ids), key=lambda e: -e.confidence)
            note = best_ev[0].evidence if best_ev else "aucune preuve disponible"
            dims.append(c.FitDimension(dimension=cp.key, label=cp.name, importance=cp.importance, level=cv.level,
                                       assessment=f"Preuve {LEVEL_FR[cv.level]} : {note}",
                                       evidence_ids=cv.evidence_ids, certainty=cv.certainty))
            ev_ids += cv.evidence_ids
            if cv.level == "strong":
                strengths.append(f"{cp.name} : {note}")
            elif cv.level in ("weak", "unknown") and cp.importance != "nice":
                gaps.append(f"{cp.name} ({'peu de preuves' if cv.level == 'unknown' else 'preuves faibles'})")
            if cp.importance == "critical" and cv.certainty < 0.5:
                uncertainties.append(f"{cp.name} : certitude {cv.certainty:.0%}, à tester")
        risks = list(cand.constraint_flags)
        if cand.constraint_flags:
            dims.append(c.FitDimension(dimension="availability", label="Disponibilité / contraintes",
                                       importance="important", level="weak",
                                       assessment="; ".join(cand.constraint_flags), certainty=0.9))
        satisfied, path_scores = [], []
        for cond in sm.success_conditions:
            sup = [cov[k].support for k in cond.requires if k in cov]
            score = (min(sup) if sup else 0.0) * cond.weight
            path_scores.append((score, cond))
            if all(cov[k].level in ("strong", "moderate") for k in cond.requires if k in cov):
                satisfied.append(cond.name)
        best_score = max((s for s, _ in path_scores), default=0.0)
        crit = [cov[cp.key] for cp in sm.critical_capabilities if cp.importance == "critical"]
        confidence = round(sum(cv.certainty for cv in crit) / max(1, len(crit)), 2)
        tradeoffs = []
        if "learning_agility" in cov and cov["learning_agility"].level == "strong" and gaps:
            tradeoffs.append("Fort potentiel d'apprentissage qui peut compenser des manques actuels, au prix d'un ramp-up")
        if strengths and risks:
            tradeoffs.append("Bon niveau sur le fond mais contrainte pratique à arbitrer")
        n_strong = sum(1 for d in dims if d.level == "strong" and d.importance == "critical")
        n_crit = sum(1 for cp in sm.critical_capabilities if cp.importance == "critical")
        summary = (f"{cand.full_name} : {n_strong}/{n_crit} capacités critiques avec des preuves solides. "
                   + (f"Chemin(s) de réussite plausibles : {', '.join(satisfied)}. " if satisfied
                      else "Aucun chemin de réussite n'est encore établi par les preuves. ")
                   + (f"Points à vérifier : {', '.join(g.split(' (')[0] for g in gaps[:3])}." if gaps else ""))
        if risks:
            summary += f" Risque : {risks[0]}."
        ui = round(100 * best_score * (0.85 if risks else 1.0))
        return c.MatchAnalysis(fit_summary=summary, fit_dimensions=dims, strengths=strengths, gaps=gaps,
                               tradeoffs=tradeoffs, risks=risks, uncertainties=uncertainties,
                               evidence_ids=list(dict.fromkeys(ev_ids)), satisfied_conditions=satisfied,
                               confidence=confidence, ui_score=ui,
                               candidate_explanation=(
                                   "Ce poste s'appuie sur des points forts de votre profil : "
                                   + ", ".join(x.split(" :")[0].lower() for x in strengths[:3]) + "."
                                   if strengths else None))

    def shortlist(self, ctx: c.ShortlistContext) -> c.ShortlistOutput:
        ranked = sorted(ctx.matches, key=lambda m: (-(m.get("ui_score") or 0), -m["confidence"]))
        top, rest = ranked[:ctx.k], ranked[ctx.k:]
        entries = []
        for i, m in enumerate(top, 1):
            why = []
            if m["satisfied_conditions"]:
                why.append("satisfait le chemin de réussite " + ", ".join(m["satisfied_conditions"]))
            if m["strengths"]:
                why.append("forces prouvées : " + "; ".join(s.split(" : ")[0] for s in m["strengths"][:3]))
            if m["risks"]:
                why.append("à surveiller : " + m["risks"][0])
            elif m["gaps"]:
                why.append("à vérifier : " + m["gaps"][0])
            entries.append(c.ShortlistEntry(candidate_id=m["candidate_id"], rank=i,
                                            reason=f"{m['full_name']} — " + " ; ".join(why)))
        excluded = [{"candidate_id": m["candidate_id"],
                     "reason": f"{m['full_name']} : " + (", ".join(m["gaps"][:2]) or "moins de preuves que les finalistes")}
                    for m in rest]
        names = ", ".join(m["full_name"] for m in top)
        return c.ShortlistOutput(shortlist=entries, excluded=excluded,
                                 summary=f"Finalistes : {names}. Sélection fondée sur la couverture des capacités "
                                         f"critiques du modèle de réussite par des preuves, pas sur un score de CV.")

    # ------------------------------------------------------------------ confrontation
    @staticmethod
    def _lenses(role: c.RoleView, cands: list[c.CandidateView]) -> dict[str, dict[str, float]]:
        sm = role.success_model
        crit = [cp.key for cp in sm.critical_capabilities
                if cp.importance == "critical" and cp.key not in ("learning_agility", "domain_knowledge")]
        lenses: dict[str, dict[str, float]] = {}
        for cv in cands:
            cov = {x.capability_key: x for x in cv.coverage}
            lenses.setdefault("immediate_performance", {})[cv.id] = (
                sum(cov[k].support for k in crit) / max(1, len(crit)))
            if "learning_agility" in cov:
                lenses.setdefault("learning_potential", {})[cv.id] = cov["learning_agility"].support
            if "domain_knowledge" in cov:
                lenses.setdefault("domain_expertise", {})[cv.id] = cov["domain_knowledge"].support
            lenses.setdefault("availability", {})[cv.id] = 0.3 if cv.constraint_flags else 1.0
        return lenses

    LENS_FR = {
        "immediate_performance": ("la performance immédiate", "les preuves de performance immédiate les plus solides"),
        "learning_potential": ("le potentiel d'apprentissage", "le plus fort potentiel d'apprentissage"),
        "domain_expertise": ("l'expertise sectorielle", "la meilleure expertise sectorielle"),
        "availability": ("une disponibilité rapide", "la disponibilité la plus compatible"),
    }

    def confront(self, ctx: c.ConfrontationContext) -> c.ConfrontationOutput:
        sm = ctx.role.success_model
        names = {cv.id: cv.full_name for cv in ctx.candidates}
        lenses = self._lenses(ctx.role, ctx.candidates)
        # each finalist gets the lens where they are most clearly ahead (greedy, by margin)
        margins = []
        for lens, scores in lenses.items():
            for cid, s in scores.items():
                others = [v for k, v in scores.items() if k != cid]
                margins.append((s - max(others, default=0), lens, cid))
        headline: dict[str, str] = {}
        used: set[str] = set()
        for m, lens, cid in sorted(margins, reverse=True):
            if cid in headline or lens in used or m <= 0:
                continue
            headline[cid], _ = self.LENS_FR[lens][1], used.add(lens)
        profiles = []
        for cv in ctx.candidates:
            h = headline.get(cv.id, "un profil équilibré sans avantage distinctif net")
            if cv.constraint_flags:
                h += ", mais " + cv.constraint_flags[0].lower()
            profiles.append(c.CandidateProfile(candidate_id=cv.id, headline=f"{cv.full_name} : {h}"))
        dims = [cp.key for cp in sm.critical_capabilities if cp.importance != "nice"] + ["availability"]
        labels = {cp.key: cp.name for cp in sm.critical_capabilities} | {"availability": "Disponibilité"}
        items = []
        for cv in ctx.candidates:
            cov = {x.capability_key: x for x in cv.coverage}
            evs = {e.id: e for e in cv.evidence}
            for d in dims:
                if d == "availability":
                    items.append(c.ConfrontationItemOut(
                        candidate_id=cv.id, dimension=d, level="weak" if cv.constraint_flags else "strong",
                        assessment=cv.constraint_flags[0] if cv.constraint_flags else "Disponible dans les délais",
                        risk=cv.constraint_flags[0] if cv.constraint_flags else None))
                    continue
                x = cov[d]
                top = sorted((evs[i] for i in x.evidence_ids), key=lambda e: -e.confidence)[:2]
                items.append(c.ConfrontationItemOut(
                    candidate_id=cv.id, dimension=d, level=x.level,
                    assessment=f"{labels[d]} : preuve {LEVEL_FR[x.level]} (certitude {x.certainty:.0%})",
                    evidence=[e.evidence for e in top],
                    strength=top[0].claim if x.level == "strong" and top else None,
                    risk=f"{labels[d]} non démontrée" if x.level == "weak" else None,
                    uncertainty="peu ou pas de preuves" if x.level == "unknown" else None))
        tradeoffs = []
        for lens, scores in lenses.items():
            best = max(scores, key=scores.get)
            tradeoffs.append(c.ConditionalTradeoff(
                if_priority=lens, prefer_candidate_id=best,
                explanation=f"Si la priorité est {self.LENS_FR[lens][0]}, {names[best]} est préférable "
                            f"({self.LENS_FR[lens][1]})."))
        prio = (sm.priorities or {}).get("primary", "immediate_performance")
        prio = prio if prio in lenses else "immediate_performance"
        avail = lenses["availability"]
        weighted = {cid: s * (0.8 if avail[cid] < 1 else 1.0) for cid, s in lenses[prio].items()}
        winner = max(weighted, key=weighted.get)
        ordered = sorted(weighted, key=weighted.get, reverse=True)
        runner = ordered[1] if len(ordered) > 1 else None
        reasoning = (f"Au regard de la priorité déclarée ({self.LENS_FR[prio][0]}), {names[winner]} est le "
                     f"choix préférable. ")
        for cid in ordered[1:]:
            alt = next((t for t in tradeoffs if t.prefer_candidate_id == cid and t.if_priority not in (prio, "availability")),
                       None)
            if alt:
                reasoning += (f"Le choix de {names[cid]} devient plus pertinent si l'entreprise privilégie "
                              f"{self.LENS_FR[alt.if_priority][0]}"
                              + (" et accepte davantage de ramp-up. " if alt.if_priority == "learning_potential"
                                 else (", à condition d'accepter un démarrage plus tardif. " if cid in [
                                     c_.id for c_ in ctx.candidates if c_.constraint_flags] else ". ")))
        uncertainties = []
        for cv in ctx.candidates:
            for x in cv.coverage:
                if x.importance == "critical" and x.level == "unknown":
                    uncertainties.append(f"{cv.full_name} : {x.capability_name} non encore évaluée")
        return c.ConfrontationOutput(comparison_dimensions=dims, profiles=profiles, items=items,
                                     tradeoffs=tradeoffs, winner_candidate_id=winner, reasoning=reasoning,
                                     uncertainties=uncertainties)

    # ------------------------------------------------------------------ recommendation
    def recommend(self, ctx: c.RecommendationContext) -> c.RecommendationOutput:
        conf = ctx.confrontation
        names = {cv.id: cv.full_name for cv in ctx.candidates}
        if conf is None:
            conf = self.confront(c.ConfrontationContext(
                company=c.CompanyView(id="", name=""), role=ctx.role,
                decision_question="Qui recruter ?", candidates=ctx.candidates, matches=ctx.matches)).model_dump()
        win = conf["winner_candidate_id"]
        wcv = next(cv for cv in ctx.candidates if cv.id == win)
        strong = [x for x in wcv.coverage if x.level == "strong" and x.importance == "critical"]
        n_crit = sum(1 for x in wcv.coverage if x.importance == "critical")
        profile = {p["candidate_id"]: p["headline"].split(" : ", 1)[-1] for p in conf["profiles"]}
        parts = [f"Je recommande {names[win]} parce que c'est le profil qui couvre {len(strong)} des {n_crit} "
                 f"capacités critiques du modèle de réussite avec des preuves solides "
                 f"({', '.join(x.capability_name for x in strong)})."]
        alternatives = []
        for cid in names:
            if cid == win:
                continue
            other = next(cv for cv in ctx.candidates if cv.id == cid)
            gaps = [x.capability_name.lower() for x in other.coverage
                    if x.importance == "critical" and x.level in ("weak", "unknown")]
            txt = f"{names[cid]} présente {profile.get(cid, 'un profil intéressant')}"
            if gaps and not other.constraint_flags:
                txt += f", mais moins de preuves sur : {', '.join(gaps[:3])}"
            parts.append(txt + ".")
            when = [t["explanation"] for t in conf["tradeoffs"] if t["prefer_candidate_id"] == cid]
            if when:
                alternatives.append(c.Alternative(candidate_id=cid, when=when[0]))
        evs = sorted(wcv.evidence, key=lambda e: -e.confidence)
        key_ev = [f"{e.claim} — {e.evidence} ({e.source}, {e.epistemic_status}, {e.confidence:.2f})"
                  for e in evs if e.polarity == "supports"][:4]
        weak = [x for x in wcv.coverage if x.importance == "critical" and x.level in ("weak", "unknown")]
        unc = [f"{x.capability_name} encore peu prouvée chez {names[win]}" for x in weak] + conf.get("uncertainties", [])[:3]
        steps = [f"Faire passer à {names[win]} le test ciblé sur « {x.capability_name} »" for x in weak[:2]]
        steps += [f"Vérifier une référence professionnelle de {names[win]}", "Entretien final avec le manager"]
        certainty = sum(x.certainty for x in wcv.coverage if x.importance == "critical") / max(1, n_crit)
        return c.RecommendationOutput(
            recommended_candidate_id=win, reasoning_summary=" ".join(parts), key_evidence=key_ev,
            tradeoffs=[t["explanation"] for t in conf["tradeoffs"]], uncertainties=unc,
            alternatives=alternatives, next_steps=steps, confidence=round(0.85 * certainty, 2))
