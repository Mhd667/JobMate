# JobMate

Intelligence de recrutement conversationnelle (MVP). La conversation d'abord : l'employeur décrit son besoin
avec ses mots, le candidat parle de lui et de ce qu'il cherche. Les cartes interactives (synthèse du poste,
candidats, offre, évaluation) n'apparaissent dans le chat que lorsqu'elles sont utiles.

- `backend/` : API FastAPI (registres entreprise / talents, preuves, évaluation adaptative, matching, Top 3,
  confrontation, recommandation). LLM via Groq. Voir `backend/README.md`.
- `web/` : site Next.js relié au backend (connexion Supabase Auth, chat employeur et candidat).

## Lancer JobMate sur Windows

1. Une fois (et après une mise à jour qui ajoute des dépendances) : double-clic sur **setup.bat**.
2. `backend\.env` doit exister (copie de `backend\.env.example`, avec `DATABASE_URL` et `GROQ_API_KEY`).
3. Pour lancer : double-clic sur **start.bat**. Deux fenêtres s'ouvrent (backend sur le port 8000, site sur le
   port 3000), puis le navigateur sur http://localhost:3000. Pour arrêter : fermez ces deux fenêtres.

Le site tourne en mode production (moins gourmand en mémoire) et se recompile tout seul après un `git pull`.

## Parcours

- **Employeur** : décrit le poste en langage naturel → JobMate pose une question à la fois → synthèse du poste
  (corrigeable en répondant) → « lance la recherche » → Top 3 dans le chat (Passer / Entretien / Hire) →
  confrontation et recommandation à la demande. La décision reste humaine.
- **Candidat** : s'inscrit et discute (qui il est, ce qu'il cherche, quelles offres l'intéressent ; LinkedIn,
  portfolio ou CV s'il le souhaite) → attend → JobMate le prévient dans son chat quand une offre lui
  correspond → « Ça m'intéresse » → quelques questions ou une mise en situation → JobMate revient vers lui
  avec la suite (entretien, retenu, ou non retenu).

## Données de démonstration

`seed.bat` crée les 15 comptes de `backend\seed\demo-users.csv` (fichier gardé hors de Git) et leurs profils
synthétiques (`backend/seed/demo_profiles.py`) : 4 entreprises avec 5 offres, Baobab Conseil sans offre,
9 candidats complets et candidate10 vierge. L'IA lit ensuite chaque CV (capacités et preuves) et construit le
Success Model de chaque offre ; le matching n'est pas lancé, c'est à vous de le tester. Relançable sans risque.

Infra : Supabase (Postgres + Auth), Vercel plus tard (deux projets : `backend` et `web`).
