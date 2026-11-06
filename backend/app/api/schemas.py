"""Frontend contract: request bodies and structured response objects (OpenAPI at /docs)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.intelligence.contracts import (CapabilitySpec, CompanyIdentityPatch, ProfessionalIdentityPatch,
                                        RoleIdentityPatch, SuccessCondition)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ auth
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    phone_number: str | None = None
    role: Literal["employer", "candidate"] | None = None


class RoleChoiceIn(BaseModel):
    role: Literal["employer", "candidate"]
    phone_number: str | None = None
    full_name: str | None = Field(None, description="candidate: name shown to employers")
    company_name: str | None = Field(None, description="employer: company name (can be given later in the chat)")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(Out):
    id: uuid.UUID
    email: str
    phone_number: str | None
    role: str | None
    created_at: datetime


class MeOut(BaseModel):
    user: UserOut
    company_id: uuid.UUID | None
    candidate_id: uuid.UUID | None
    next_step: Literal["choose_role", "create_company", "employer_home", "create_profile", "candidate_home"]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ------------------------------------------------------------------ company
class CompanyIn(BaseModel):
    name: str
    website: str | None = None
    country: str | None = None
    city: str | None = None
    size: str | None = None
    description: str | None = None


class CompanyOut(Out):
    id: uuid.UUID
    name: str
    website: str | None
    country: str | None
    city: str | None
    size: str | None
    description: str | None
    created_at: datetime


class CompanyIdentityOut(Out):
    id: uuid.UUID
    company_id: uuid.UUID
    version: int
    mission: str | None
    business_model: str | None
    industry: str | None
    culture: str | None
    work_style: str | None
    management_style: str | None
    environment: str | None
    values: list
    context: str | None
    unknowns: list
    assumptions: list
    confidence: float
    produced_by: str
    created_at: datetime


# ------------------------------------------------------------------ role
class RoleIn(BaseModel):
    title: str
    location: str | None = None
    contract_type: str | None = None
    status: str = "open"
    constraints: dict = Field(default_factory=dict, examples=[{"start_before": "2027-01-15", "location": "Dakar"}])


class RoleOut(Out):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    location: str | None
    contract_type: str | None
    status: str
    constraints: dict
    created_at: datetime


class RoleIdentityOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    version: int
    mission: str | None
    responsibilities: list
    objectives: list
    constraints: list
    context: str | None
    work_environment: str | None
    stakeholders: list
    success_factors: list
    unknowns: list
    assumptions: list
    confidence: float
    produced_by: str
    created_at: datetime


class SuccessModelIn(BaseModel):
    critical_outcomes: list[dict] | None = None
    critical_capabilities: list[CapabilitySpec] | None = None
    required_behaviors: list[str] | None = None
    success_conditions: list[SuccessCondition] | None = None
    tradeoffs: list[str] | None = None
    risks: list[str] | None = None
    unknowns: list[str] | None = None
    priorities: dict | None = None
    confidence: float | None = None


class SuccessModelOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    version: int
    critical_outcomes: list[dict]
    critical_capabilities: list[CapabilitySpec]
    required_behaviors: list[str]
    success_conditions: list[SuccessCondition]
    tradeoffs: list[str]
    risks: list[str]
    unknowns: list[str]
    priorities: dict
    confidence: float
    produced_by: str
    created_at: datetime


class RoleCardOut(BaseModel):
    """Everything the employer UI needs to render the Role Card in one call."""
    role: RoleOut
    company: CompanyOut
    company_identity: CompanyIdentityOut | None
    role_identity: RoleIdentityOut | None
    success_model: SuccessModelOut | None
    missing_fields: list[str]


# ------------------------------------------------------------------ candidates
class CandidateIn(BaseModel):
    full_name: str
    headline: str | None = None
    location: str | None = None
    availability: dict = Field(default_factory=dict, examples=[{"available_from": "2026-12-01", "notice_weeks": 4}])
    cv_text: str | None = None


class CandidateOut(Out):
    id: uuid.UUID
    user_id: uuid.UUID | None
    full_name: str
    headline: str | None
    location: str | None
    availability: dict
    cv_filename: str | None = None
    sources: list[dict] = Field(default_factory=list)
    status: str
    created_at: datetime


class ProfessionalIdentityOut(Out):
    id: uuid.UUID
    candidate_id: uuid.UUID
    version: int
    career_direction: str | None
    professional_goals: list
    strengths: list
    preferences: list
    constraints: list
    aspirations: list
    summary: str | None
    unknowns: list
    confidence: float
    produced_by: str
    created_at: datetime


class ExperienceIn(BaseModel):
    title: str
    organization: str | None = None
    sector: str | None = None
    start_date: str | None = Field(None, examples=["2022-03"])
    end_date: str | None = None
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class ExperienceOut(Out, ExperienceIn):
    id: uuid.UUID
    candidate_id: uuid.UUID


class CapabilityOut(Out):
    id: uuid.UUID
    key: str
    name: str
    level: str | None
    status: str
    confidence: float
    source: str


Epistemic = Literal["fact", "inference", "hypothesis", "unknown"]
SourceT = Literal["cv", "previous_experience", "conversation", "assessment", "reference",
                  "employer_note", "self_declared"]


class EvidenceIn(BaseModel):
    role_id: uuid.UUID | None = None
    subject_type: str = "capability"
    subject_id: uuid.UUID | None = None
    subject_key: str | None = Field(None, examples=["objection_handling"])
    claim: str
    evidence: str
    source: SourceT
    epistemic_status: Epistemic
    confidence: float = Field(ge=0, le=1)
    polarity: Literal["supports", "contradicts"] = "supports"


class EvidenceOut(Out):
    id: uuid.UUID
    candidate_id: uuid.UUID
    role_id: uuid.UUID | None
    subject_type: str
    subject_id: uuid.UUID | None
    subject_key: str | None
    claim: str
    evidence: str
    source: str
    epistemic_status: str
    confidence: float
    polarity: str
    assessment_response_id: uuid.UUID | None
    created_at: datetime


class CoverageOut(BaseModel):
    capability_key: str
    capability_name: str
    importance: str
    support: float
    certainty: float
    level: str
    evidence_ids: list[str]
    open_assessments: int


class CandidateProfileOut(BaseModel):
    candidate: CandidateOut
    professional_identity: ProfessionalIdentityOut | None
    experiences: list[ExperienceOut]
    capabilities: list[CapabilityOut]
    evidence: list[EvidenceOut]


class CandidateAnalysisOut(BaseModel):
    """Known vs uncertain, for one candidate against one role's Success Model."""
    candidate_id: uuid.UUID
    role_id: uuid.UUID
    coverage: list[CoverageOut]
    known: list[str]
    uncertain: list[str]
    constraint_flags: list[str]


# ------------------------------------------------------------------ assessment
class AssessmentRequestOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    candidate_id: uuid.UUID
    target_capability: str
    objective: str
    question_type: str
    question: str
    expected_evidence: list[str]
    rationale: str | None
    expected_value: float | None
    status: str
    produced_by: str
    created_at: datetime


class AssessmentResponseIn(BaseModel):
    response: str = Field(min_length=1)


class AssessmentResponseOut(Out):
    id: uuid.UUID
    assessment_request_id: uuid.UUID
    candidate_id: uuid.UUID
    response: str
    observed_behaviors: list[str]
    evidence: list[dict]
    confidence: float | None
    produced_by: str
    created_at: datetime


# ------------------------------------------------------------------ matching / decision
class MatchRunIn(BaseModel):
    candidate_ids: list[uuid.UUID] | None = None


class MatchOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str | None = None
    success_model_version: int | None
    fit_summary: str
    fit_dimensions: list[dict]
    strengths: list[str]
    gaps: list[str]
    tradeoffs: list[str]
    risks: list[str]
    uncertainties: list[str]
    evidence: list[dict]
    satisfied_conditions: list[str]
    confidence: float
    ui_score: int | None = Field(description="display helper only; not the reasoning")
    shortlist_rank: int | None
    shortlist_reason: str | None
    produced_by: str
    updated_at: datetime


class ShortlistIn(BaseModel):
    k: int = Field(3, ge=1, le=10)


class ShortlistEntryOut(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    rank: int
    reason: str


class ShortlistOut(BaseModel):
    role_id: uuid.UUID
    summary: str
    shortlist: list[ShortlistEntryOut]
    excluded: list[dict]
    produced_by: str


class ConfrontationIn(BaseModel):
    decision_question: str = "Compare-moi les trois finalistes."
    candidate_ids: list[uuid.UUID] | None = Field(None, description="defaults to the current Top 3")


class ConfrontationItemOut(Out):
    id: uuid.UUID
    candidate_id: uuid.UUID
    dimension: str
    level: str | None
    assessment: str
    evidence: list
    strength: str | None
    risk: str | None
    uncertainty: str | None


class ConfrontationOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    decision_question: str
    candidate_ids: list[str]
    comparison_dimensions: list[str]
    profiles: list[dict]
    tradeoffs: list[dict]
    winner_candidate_id: uuid.UUID | None
    reasoning: str
    uncertainties: list[str]
    status: str
    items: list[ConfrontationItemOut]
    produced_by: str
    created_at: datetime


class RecommendationIn(BaseModel):
    confrontation_id: uuid.UUID | None = None


class RecommendationOut(Out):
    id: uuid.UUID
    role_id: uuid.UUID
    confrontation_id: uuid.UUID | None
    recommended_candidate_id: uuid.UUID | None
    reasoning_summary: str
    key_evidence: list[str]
    tradeoffs: list[str]
    uncertainties: list[str]
    alternatives: list[dict]
    next_steps: list[str]
    confidence: float
    produced_by: str
    created_at: datetime


# ------------------------------------------------------------------ conversations
class ConversationIn(BaseModel):
    kind: Literal["employer", "candidate"]
    company_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None
    title: str | None = None


class ConversationOut(Out):
    id: uuid.UUID
    kind: str
    company_id: uuid.UUID | None
    role_id: uuid.UUID | None
    candidate_id: uuid.UUID | None
    title: str | None
    created_at: datetime


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


class MessageOut(Out):
    id: uuid.UUID
    sender: str
    content: str
    meta: dict
    created_at: datetime


class CardActionOut(BaseModel):
    id: str
    label: str
    style: str = "secondary"


class CardOut(BaseModel):
    id: str
    type: Literal["missions", "role_summary", "success_model", "candidates", "next_steps", "confrontation",
                  "recommendation", "sources", "offer", "assessment"]
    status: Literal["open", "done"] = "open"
    data: dict
    actions: list[CardActionOut] = Field(default_factory=list)
    result: dict | None = None


class TurnOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    intent: str
    updates: list[dict] = Field(description="identity objects updated by this turn, e.g. role_identity")
    artifacts: list[dict] = Field(description="objects produced (success_model, shortlist, confrontation...)")
    cards: list[CardOut] = Field(default_factory=list, description="cards to render under the assistant message")
    flow_state: str | None = Field(None, description="employer: discovery|missions|role_summary|results|"
                                                    "confrontation|recommendation; candidate: profile|sources|"
                                                    "assessment|waiting")


class ActionIn(BaseModel):
    card_id: str
    action: str = Field(description="one of the card's actions[].id, e.g. missions.submit, candidate.hire")
    payload: dict = Field(default_factory=dict, description="missions.submit: {selected: [...], other?}; "
                                                            "candidate.*: {candidate_id}")


class SourceIn(BaseModel):
    kind: Literal["linkedin", "portfolio", "other"]
    url: str = Field(pattern=r"^https?://", max_length=500)


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class OpportunityOut(BaseModel):
    role: RoleOut
    company_name: str
    match: MatchOut | None


__all__ = [n for n in dir() if n.endswith(("In", "Out"))] + [
    "CompanyIdentityPatch", "RoleIdentityPatch", "ProfessionalIdentityPatch"]
