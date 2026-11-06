-- JobMate: conversational cards (UX spec of 2026-11-06)
ALTER TABLE public.roles ADD COLUMN IF NOT EXISTS duration varchar(80);
ALTER TABLE public.roles ALTER COLUMN status SET DEFAULT 'draft';
ALTER TABLE public.role_identities ADD COLUMN IF NOT EXISTS languages jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.role_identities ADD COLUMN IF NOT EXISTS availability text;
ALTER TABLE public.role_identities ADD COLUMN IF NOT EXISTS priority varchar(40);
ALTER TABLE public.candidates ADD COLUMN IF NOT EXISTS cv_filename varchar(255);
ALTER TABLE public.candidates ADD COLUMN IF NOT EXISTS sources jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS candidate_explanation text;
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS employer_status varchar(20);
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS candidate_status varchar(20);
ALTER TABLE public.matches ADD COLUMN IF NOT EXISTS offered_at timestamptz;
ALTER TABLE public.evidence ALTER COLUMN polarity TYPE varchar(12);
