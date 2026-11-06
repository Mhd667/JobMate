-- JobMate MVP schema (PostgreSQL / Supabase). Generated from app/models.py.

CREATE TYPE public.assessment_status AS ENUM (
    'pending',
    'answered',
    'evaluated',
    'cancelled'
);

CREATE TYPE public.conversation_kind AS ENUM (
    'employer',
    'candidate'
);

CREATE TYPE public.epistemic_status AS ENUM (
    'fact',
    'inference',
    'hypothesis',
    'unknown'
);

CREATE TYPE public.evidence_source AS ENUM (
    'cv',
    'previous_experience',
    'conversation',
    'assessment',
    'reference',
    'employer_note',
    'self_declared'
);

CREATE TYPE public.user_role AS ENUM (
    'employer',
    'candidate'
);

CREATE TABLE public.assessment_requests (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    target_capability character varying(80) NOT NULL,
    objective text NOT NULL,
    question_type character varying(40) NOT NULL,
    question text NOT NULL,
    expected_evidence jsonb NOT NULL,
    rationale text,
    expected_value double precision,
    status public.assessment_status NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.assessment_responses (
    id uuid NOT NULL,
    assessment_request_id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    response text NOT NULL,
    observed_behaviors jsonb NOT NULL,
    evidence jsonb NOT NULL,
    confidence double precision,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.candidates (
    id uuid NOT NULL,
    user_id uuid,
    full_name character varying(200) NOT NULL,
    headline character varying(300),
    location character varying(120),
    availability jsonb NOT NULL,
    cv_text text,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.capabilities (
    id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    key character varying(80) NOT NULL,
    name character varying(200) NOT NULL,
    level character varying(20),
    status public.epistemic_status NOT NULL,
    confidence double precision NOT NULL,
    source public.evidence_source NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.companies (
    id uuid NOT NULL,
    owner_user_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    website character varying(300),
    country character varying(80),
    city character varying(80),
    size character varying(40),
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.company_identities (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    version integer NOT NULL,
    mission text,
    business_model text,
    industry character varying(200),
    culture text,
    work_style text,
    management_style text,
    environment text,
    "values" jsonb NOT NULL,
    context text,
    unknowns jsonb NOT NULL,
    assumptions jsonb NOT NULL,
    confidence double precision NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.confrontation_items (
    id uuid NOT NULL,
    confrontation_id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    dimension character varying(120) NOT NULL,
    assessment text NOT NULL,
    evidence jsonb NOT NULL,
    strength text,
    risk text,
    uncertainty text,
    level character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.confrontations (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    decision_question text NOT NULL,
    candidate_ids jsonb NOT NULL,
    comparison_dimensions jsonb NOT NULL,
    profiles jsonb NOT NULL,
    tradeoffs jsonb NOT NULL,
    winner_candidate_id uuid,
    reasoning text NOT NULL,
    uncertainties jsonb NOT NULL,
    status character varying(20) NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.conversations (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    kind public.conversation_kind NOT NULL,
    company_id uuid,
    role_id uuid,
    candidate_id uuid,
    title character varying(200),
    state jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.evidence (
    id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    role_id uuid,
    subject_type character varying(40) NOT NULL,
    subject_id uuid,
    subject_key character varying(80),
    claim text NOT NULL,
    evidence text NOT NULL,
    source public.evidence_source NOT NULL,
    epistemic_status public.epistemic_status NOT NULL,
    confidence double precision NOT NULL,
    polarity character varying(10) NOT NULL,
    assessment_response_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.experiences (
    id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    organization character varying(200),
    sector character varying(120),
    start_date character varying(10),
    end_date character varying(10),
    description text,
    achievements jsonb NOT NULL,
    skills jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.matches (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    success_model_version integer,
    fit_summary text NOT NULL,
    fit_dimensions jsonb NOT NULL,
    strengths jsonb NOT NULL,
    gaps jsonb NOT NULL,
    tradeoffs jsonb NOT NULL,
    risks jsonb NOT NULL,
    uncertainties jsonb NOT NULL,
    evidence jsonb NOT NULL,
    satisfied_conditions jsonb NOT NULL,
    confidence double precision NOT NULL,
    ui_score integer,
    shortlist_rank integer,
    shortlist_reason text,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.messages (
    id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    sender character varying(20) NOT NULL,
    content text NOT NULL,
    meta jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.professional_identities (
    id uuid NOT NULL,
    candidate_id uuid NOT NULL,
    version integer NOT NULL,
    career_direction text,
    professional_goals jsonb NOT NULL,
    strengths jsonb NOT NULL,
    preferences jsonb NOT NULL,
    constraints jsonb NOT NULL,
    aspirations jsonb NOT NULL,
    summary text,
    unknowns jsonb NOT NULL,
    confidence double precision NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.recommendations (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    confrontation_id uuid,
    recommended_candidate_id uuid,
    reasoning_summary text NOT NULL,
    key_evidence jsonb NOT NULL,
    tradeoffs jsonb NOT NULL,
    uncertainties jsonb NOT NULL,
    alternatives jsonb NOT NULL,
    next_steps jsonb NOT NULL,
    confidence double precision NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.role_identities (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    version integer NOT NULL,
    mission text,
    responsibilities jsonb NOT NULL,
    objectives jsonb NOT NULL,
    constraints jsonb NOT NULL,
    context text,
    work_environment text,
    stakeholders jsonb NOT NULL,
    success_factors jsonb NOT NULL,
    unknowns jsonb NOT NULL,
    assumptions jsonb NOT NULL,
    confidence double precision NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.roles (
    id uuid NOT NULL,
    company_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    location character varying(120),
    contract_type character varying(40),
    status character varying(20) NOT NULL,
    constraints jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.success_models (
    id uuid NOT NULL,
    role_id uuid NOT NULL,
    version integer NOT NULL,
    critical_outcomes jsonb NOT NULL,
    critical_capabilities jsonb NOT NULL,
    required_behaviors jsonb NOT NULL,
    success_conditions jsonb NOT NULL,
    tradeoffs jsonb NOT NULL,
    risks jsonb NOT NULL,
    unknowns jsonb NOT NULL,
    priorities jsonb NOT NULL,
    confidence double precision NOT NULL,
    produced_by character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.users (
    id uuid NOT NULL,
    email character varying(320) NOT NULL,
    phone_number character varying(32),
    password_hash character varying(255),
    role public.user_role,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE ONLY public.assessment_requests
    ADD CONSTRAINT assessment_requests_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.assessment_responses
    ADD CONSTRAINT assessment_responses_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.candidates
    ADD CONSTRAINT candidates_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_candidate_id_key_key UNIQUE (candidate_id, key);

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.company_identities
    ADD CONSTRAINT company_identities_company_id_version_key UNIQUE (company_id, version);

ALTER TABLE ONLY public.company_identities
    ADD CONSTRAINT company_identities_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.confrontation_items
    ADD CONSTRAINT confrontation_items_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.confrontations
    ADD CONSTRAINT confrontations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.experiences
    ADD CONSTRAINT experiences_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_role_id_candidate_id_key UNIQUE (role_id, candidate_id);

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.professional_identities
    ADD CONSTRAINT professional_identities_candidate_id_version_key UNIQUE (candidate_id, version);

ALTER TABLE ONLY public.professional_identities
    ADD CONSTRAINT professional_identities_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.role_identities
    ADD CONSTRAINT role_identities_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.role_identities
    ADD CONSTRAINT role_identities_role_id_version_key UNIQUE (role_id, version);

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.success_models
    ADD CONSTRAINT success_models_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.success_models
    ADD CONSTRAINT success_models_role_id_version_key UNIQUE (role_id, version);

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE INDEX ix_assessment_requests_candidate_id ON public.assessment_requests USING btree (candidate_id);

CREATE INDEX ix_assessment_requests_role_id ON public.assessment_requests USING btree (role_id);

CREATE INDEX ix_assessment_responses_assessment_request_id ON public.assessment_responses USING btree (assessment_request_id);

CREATE INDEX ix_assessment_responses_candidate_id ON public.assessment_responses USING btree (candidate_id);

CREATE INDEX ix_candidates_user_id ON public.candidates USING btree (user_id);

CREATE INDEX ix_capabilities_candidate_id ON public.capabilities USING btree (candidate_id);

CREATE INDEX ix_companies_owner_user_id ON public.companies USING btree (owner_user_id);

CREATE INDEX ix_company_identities_company_id ON public.company_identities USING btree (company_id);

CREATE INDEX ix_confrontation_items_candidate_id ON public.confrontation_items USING btree (candidate_id);

CREATE INDEX ix_confrontation_items_confrontation_id ON public.confrontation_items USING btree (confrontation_id);

CREATE INDEX ix_confrontations_role_id ON public.confrontations USING btree (role_id);

CREATE INDEX ix_conversations_candidate_id ON public.conversations USING btree (candidate_id);

CREATE INDEX ix_conversations_company_id ON public.conversations USING btree (company_id);

CREATE INDEX ix_conversations_role_id ON public.conversations USING btree (role_id);

CREATE INDEX ix_conversations_user_id ON public.conversations USING btree (user_id);

CREATE INDEX ix_evidence_assessment_response_id ON public.evidence USING btree (assessment_response_id);

CREATE INDEX ix_evidence_candidate_id ON public.evidence USING btree (candidate_id);

CREATE INDEX ix_evidence_role_id ON public.evidence USING btree (role_id);

CREATE INDEX ix_evidence_subject_key ON public.evidence USING btree (subject_key);

CREATE INDEX ix_experiences_candidate_id ON public.experiences USING btree (candidate_id);

CREATE INDEX ix_matches_candidate_id ON public.matches USING btree (candidate_id);

CREATE INDEX ix_matches_role_id ON public.matches USING btree (role_id);

CREATE INDEX ix_messages_conversation_id ON public.messages USING btree (conversation_id);

CREATE INDEX ix_professional_identities_candidate_id ON public.professional_identities USING btree (candidate_id);

CREATE INDEX ix_recommendations_confrontation_id ON public.recommendations USING btree (confrontation_id);

CREATE INDEX ix_recommendations_recommended_candidate_id ON public.recommendations USING btree (recommended_candidate_id);

CREATE INDEX ix_recommendations_role_id ON public.recommendations USING btree (role_id);

CREATE INDEX ix_role_identities_role_id ON public.role_identities USING btree (role_id);

CREATE INDEX ix_roles_company_id ON public.roles USING btree (company_id);

CREATE INDEX ix_success_models_role_id ON public.success_models USING btree (role_id);

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);

ALTER TABLE ONLY public.assessment_requests
    ADD CONSTRAINT assessment_requests_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.assessment_requests
    ADD CONSTRAINT assessment_requests_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.assessment_responses
    ADD CONSTRAINT assessment_responses_assessment_request_id_fkey FOREIGN KEY (assessment_request_id) REFERENCES public.assessment_requests(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.assessment_responses
    ADD CONSTRAINT assessment_responses_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.candidates
    ADD CONSTRAINT candidates_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.capabilities
    ADD CONSTRAINT capabilities_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.company_identities
    ADD CONSTRAINT company_identities_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.confrontation_items
    ADD CONSTRAINT confrontation_items_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.confrontation_items
    ADD CONSTRAINT confrontation_items_confrontation_id_fkey FOREIGN KEY (confrontation_id) REFERENCES public.confrontations(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.confrontations
    ADD CONSTRAINT confrontations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_assessment_response_id_fkey FOREIGN KEY (assessment_response_id) REFERENCES public.assessment_responses(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidence_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.experiences
    ADD CONSTRAINT experiences_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.professional_identities
    ADD CONSTRAINT professional_identities_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_confrontation_id_fkey FOREIGN KEY (confrontation_id) REFERENCES public.confrontations(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_recommended_candidate_id_fkey FOREIGN KEY (recommended_candidate_id) REFERENCES public.candidates(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.recommendations
    ADD CONSTRAINT recommendations_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.role_identities
    ADD CONSTRAINT role_identities_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.success_models
    ADD CONSTRAINT success_models_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


-- Supabase: the tables are only read by the backend (postgres role, bypasses RLS).
-- RLS with no policy blocks direct access through the public anon/authenticated keys.
ALTER TABLE public.assessment_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessment_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.company_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.confrontation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.confrontations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.professional_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.success_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
