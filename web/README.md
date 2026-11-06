# JobMate — web

```bash
npm install
cp .env.example .env.local   # URL + clé publique Supabase, URL de l'API
npm run dev                  # http://localhost:3000
```

Parcours : `/login` (connexion ou inscription) → `/role` (recruteur ou candidat) → `/onboarding`
(entreprise ou profil) → `/home`. La page d'accueil suit `next_step` renvoyé par `GET /auth/me`.
