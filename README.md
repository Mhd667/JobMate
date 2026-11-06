# JobMate

Intelligence de recrutement conversationnelle (MVP).

- `backend/` — API FastAPI : registries entreprise / talents, preuves, assessment adaptatif, matching,
  Top 3, confrontation, recommandation. LLM via Groq (ou Claude). Voir `backend/README.md`.
- `web/` — frontend Next.js : connexion / inscription (Supabase Auth), choix du rôle, création de
  l'entreprise ou du profil.

Infra : Supabase (Postgres + Auth), Vercel (deux projets : `backend` et `web`).
