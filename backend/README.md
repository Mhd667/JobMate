# JobMate — backend (MVP)

Intelligence de recrutement conversationnelle. Le pipeline complet tourne de bout en bout :

```
Company/Role understanding → Candidate understanding → Evidence → Assessment
→ Matching → Top 3 → Confrontation → Recommendation
```

Stack : Python 3.11+, FastAPI, SQLAlchemy 2, PostgreSQL (local ou Supabase), un LLM via Groq (par défaut `openai/gpt-oss-120b`) ou Claude via l'API Anthropic (`LLM_PROVIDER`).

## Lancer

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # Supabase + clé Groq
uvicorn index:app --port 8000   # contrat interactif sur http://localhost:8000/docs
python -m pytest tests          # 13 tests, sur un Postgres local (voir tests/conftest.py)
```

Le produit n'embarque aucune donnée : tout vient des comptes et des conversations réelles. Les données de
`tests/fixture_data.py` servent uniquement aux tests. Sans clé LLM (`GROQ_API_KEY`), les routes qui ont besoin de
l'intelligence répondent `503 intelligence_unavailable` au lieu d'inventer une réponse ; `/health` passe à
`degraded`.

Auth : Supabase Auth côté frontend (e-mail + mot de passe). Le backend vérifie le JWT (JWKS du projet),
crée la ligne `users` au premier appel (rôle vide), puis `POST /auth/role` fixe le rôle une fois.
`GET /auth/me` renvoie `next_step` (`choose_role`, `create_company`, `employer_home`, `create_profile`,
`candidate_home`) pour que le frontend sache où envoyer la personne.

## Architecture

```
app/
  models.py                 19 tables (users séparés des identités métier ; identités versionnées)
  api/                      routers FastAPI = contrat frontend (schemas.py = objets structurés)
  auth/                     bcrypt + JWT local, ou vérification des JWT Supabase Auth
  engine/
    context_builder.py      Database → Structured Decision Context (+ couverture des preuves)
    pipeline.py             orchestration : contexte → intelligence → validation → persistance
    registry.py             identités versionnées (chaque mise à jour = version N+1, historique conservé)
  intelligence/
    interface.py            IntelligenceLayer (la frontière Intelligence / Engine)
    contracts.py            contextes d'entrée et sorties structurées (pydantic)
    prompts.py              Prompt Policy (versionnée)
    validation.py           validation sémantique (ids existants, clés du Success Model, statut épistémique)
    llm_policy.py           LLM + retry correctif + fallback heuristique
    heuristic.py            baseline déterministe sans LLM
    llm/                    fournisseurs : groq, anthropic, scripted (tests)
index.py                    point d'entrée Vercel
sql/schema.sql              DDL Postgres (pour Supabase SQL editor)
openapi.json                contrat API exporté (38 routes)
```

Le LLM ne touche jamais la base. Chaque appel suit :
`DB → ContextBuilder → *Context → Prompt Policy → LLM (tool forcé = JSON schema) → pydantic + validation → DB`.
Si la sortie est invalide : un retry avec l'erreur, puis fallback heuristique. Le champ `produced_by` de
chaque objet indique qui l'a produit (`llm:anthropic:v0.1`, `heuristic`, `heuristic:fallback`, `manual`).

### Fait / inférence / hypothèse / inconnu

Chaque preuve porte un `epistemic_status`. Règles appliquées dans le code, pas seulement dans le prompt :
une déclaration du candidat (conversation, CV, auto-déclaration) ne peut jamais être un `fact`, et une
réponse d'assessment écrite non plus. Le LLM peut le proposer, la validation le rétrograde.

### Couverture des preuves (le « belief state » minimal de V0)

`ContextBuilder.coverage_for` calcule pour chaque capacité du Success Model : `support` (combinaison
noisy-OR des preuves pondérées par statut × confiance, les preuves contradictoires réduisent),
`certainty` (combien on sait vraiment), `level` (strong / moderate / weak / unknown), et
`untested_claim` (que des hypothèses). Toutes les politiques (heuristique, LLM, celle de demain) voient
la même image « connu / incertain ».

### Success Model = chemins de réussite

`success_conditions` est un « OU de ET » : chaque chemin liste des capacités toutes requises, avec un
`weight` (valeur relative du chemin, par ex. 0,75 si le chemin implique du ramp-up). C'est la forme
retenue dans le rapport de recherche, en version simplifiée.

## Contrat API (résumé, détail dans /docs et openapi.json)

| Domaine | Routes |
| --- | --- |
| auth | `GET /auth/me`, `POST /auth/role` (inscription / connexion : Supabase Auth) |
| company | `POST/GET /companies`, `GET /companies/{id}`, `GET/PATCH /companies/{id}/identity`, `GET …/identity/history` |
| roles | `POST/GET /companies/{id}/roles`, `GET /roles/{id}`, `GET /roles/{id}/card`, `GET/PATCH /roles/{id}/identity` |
| success model | `GET/PATCH /roles/{id}/success-model`, `POST /roles/{id}/success-model/generate` |
| candidates | `POST/GET /candidates`, `GET /candidates/me`, `GET /candidates/{id}`, `GET/PATCH …/professional-identity`, `POST …/experiences`, `GET /candidates/me/opportunities` |
| evidence | `POST /candidates/{id}/analyze`, `GET/POST /candidates/{id}/evidence`, `GET /roles/{rid}/candidates/{cid}/analysis` (connu / incertain) |
| assessment | `POST /roles/{rid}/candidates/{cid}/assessments/next`, `GET …/assessments`, `GET /candidates/me/assessments`, `POST /assessments/{id}/responses` |
| matching | `POST /roles/{id}/matches/run`, `GET /roles/{id}/matches`, `GET /roles/{id}/matches/{cid}` |
| shortlist | `POST/GET /roles/{id}/shortlist` |
| confrontation | `POST/GET /roles/{id}/confrontations`, `GET /confrontations/{id}` |
| recommendation | `POST /roles/{id}/recommendations`, `GET /roles/{id}/recommendations/latest` |
| conversations | `POST/GET /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages` |

`POST /conversations/{id}/messages` renvoie un `TurnOut` : la réponse, l'`intent` détecté, les objets
mis à jour (`updates`) et les objets produits (`artifacts`, par ex. une confrontation quand l'employeur
écrit « Compare-moi les trois derniers candidats »). Le frontend peut afficher la carte correspondante.

Parcours UX couverts — employeur : conversation → Role Card (`/roles/{id}/card`) → candidats → analyse
(`/analysis`, `/matches/{cid}`) → Top 3 → confrontation → recommandation. Candidat : conversation →
identité professionnelle (`/candidates/me`) → opportunités.

## Brancher l'Intelligence Layer de demain

Implémenter `IntelligenceLayer` (`app/intelligence/interface.py`, 10 méthodes) puis
`set_intelligence(MaLayer())`. Points d'ancrage prévus :

- `next_assessment` → VoI décisionnelle ; `AssessmentPlan.expected_value` est déjà stocké.
- `CoverageView` → remplacer par la croyance jointe (candidats × Success Model × sources).
- `SuccessCondition.weight` / `requires` → structure de conditions apprise.
- `Match.success_model_version` et les identités versionnées → base des labels d'issue pour l'apprentissage
  de niveau 2 (correction de sélection).

Aucune de ces évolutions ne demande de changer le schéma des routes.

## Supabase

1. Appliquer `sql/schema.sql` (migration). Il active RLS sans policy sur toutes les tables : la clé
   publique du frontend ne peut pas lire la base directement, seul le backend (rôle postgres) y accède.
2. `DATABASE_URL` = pooler en mode transaction (port 6543) ; le moteur SQLAlchemy est configuré pour
   (pas de pool côté client, pas de prepared statements).
3. `SUPABASE_URL` pour la vérification JWKS des tokens.

## Limites actuelles

- Le moteur heuristique remplit les champs dans l'ordre des questions qu'il pose ; la compréhension libre
  vient du LLM.
- Pas de migrations (Alembic) : `create_all` au démarrage. À ajouter avant la prod.
- Matching séquentiel par candidat (suffisant pour des dizaines de candidats).
- Inscription par e-mail uniquement ; le téléphone est demandé au choix du rôle (le SMS Supabase demande
  un fournisseur type Twilio).
