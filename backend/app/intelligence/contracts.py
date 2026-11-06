"""The boundary between the Engine and the Intelligence Layer.

Engine (DB, services)  --builds-->  *Context (read-only, controlled view)
Intelligence Layer     --returns--> *Output  (structured, validated by pydantic)

The Intelligence Layer never touches the database. Anything that implements
`IntelligenceLayer` (see interface.py) can be swapped in: today a heuristic baseline and an
LLM-backed policy; tomorrow a Bayesian / VoI-driven layer with an explicit world model.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Epistemic = Literal["fact", "inference", "hypothesis", "unknown"]
Level = Literal["strong", "moderate", "weak", "unknown"]
Importance = Literal["critical", "important", "nice"]
Source = Literal["cv", "previous_experience", "conversation", "assessment", "reference",
                 "employer_note", "self_declared"]


class _M(BaseModel):
    model_config = {"extra": "ignore"}


# =========================================================================== shared views
class CompanyView(_M):
    id: str
    name: str
    description: str | None = None
    identity: dict = Field(default_factory=dict)


class CapabilitySpec(_M):
    key: str
    name: str
    description: str = ""
    importance: Importance = "important"
    observable_evidence: list[str] = Field(default_factory=list)


class SuccessCondition(_M):
    name: str
    requires: list[str] = Field(description="capability keys that must ALL hold for this path")
    description: str = ""
    weight: float = Field(1.0, ge=0, le=1, description="relative value of succeeding via this path "
                                                        "(e.g. <1 when it implies ramp-up)")


class SuccessModelView(_M):
    version: int = 0
    critical_outcomes: list[dict] = Field(default_factory=list)
    critical_capabilities: list[CapabilitySpec] = Field(default_factory=list)
    required_behaviors: list[str] = Field(default_factory=list)
    success_conditions: list[SuccessCondition] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    priorities: dict = Field(default_factory=dict)


class RoleView(_M):
    id: str
    title: str
    location: str | None = None
    constraints: dict = Field(default_factory=dict)
    identity: dict = Field(default_factory=dict)
    success_model: SuccessModelView | None = None


class EvidenceView(_M):
    id: str
    subject_type: str
    subject_key: str | None
    claim: str
    evidence: str
    source: str
    epistemic_status: Epistemic
    confidence: float
    polarity: str = "supports"


class CoverageView(_M):
    """What is already known about one capability of the Success Model, for one candidate.

    Computed deterministically by the Context Builder so every intelligence policy sees the
    same "known / uncertain" picture. `support` in [0,1] aggregates supporting evidence
    weighted by epistemic status; `certainty` says how much we actually know.
    """
    capability_key: str
    capability_name: str
    importance: Importance
    support: float
    certainty: float
    level: Level
    evidence_ids: list[str] = Field(default_factory=list)
    open_assessments: int = 0
    untested_claim: bool = Field(False, description="only hypotheses / self-declarations, nothing observed")


class CandidateView(_M):
    id: str
    full_name: str
    headline: str | None = None
    location: str | None = None
    availability: dict = Field(default_factory=dict)
    identity: dict = Field(default_factory=dict)
    experiences: list[dict] = Field(default_factory=list)
    capabilities: list[dict] = Field(default_factory=list)
    evidence: list[EvidenceView] = Field(default_factory=list)
    coverage: list[CoverageView] = Field(default_factory=list)
    constraint_flags: list[str] = Field(default_factory=list)  # e.g. availability vs role constraints


class DialogueTurn(_M):
    sender: str
    content: str


# =========================================================================== contexts
class EmployerConversationContext(_M):
    company: CompanyView
    role: RoleView | None = None
    history: list[DialogueTurn]
    user_message: str
    last_asked_field: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class CandidateConversationContext(_M):
    candidate: CandidateView
    history: list[DialogueTurn]
    user_message: str
    last_asked_field: str | None = None
    missing_fields: list[str] = Field(default_factory=list)


class SuccessModelContext(_M):
    company: CompanyView
    role: RoleView
    conversation_excerpt: list[DialogueTurn] = Field(default_factory=list)


class CandidateUnderstandingContext(_M):
    candidate: CandidateView
    capability_vocabulary: list[CapabilitySpec] = Field(default_factory=list)


class AssessmentContext(_M):
    role: RoleView
    candidate: CandidateView
    previous_questions: list[dict] = Field(default_factory=list)


class ResponseContext(_M):
    role: RoleView
    candidate: CandidateView
    request: dict
    response: str


class MatchContext(_M):
    company: CompanyView
    role: RoleView
    candidate: CandidateView


class ShortlistContext(_M):
    role: RoleView
    matches: list[dict]  # serialized match analyses + candidate name
    k: int = 3


class ConfrontationContext(_M):
    company: CompanyView
    role: RoleView
    decision_question: str
    candidates: list[CandidateView]
    matches: list[dict]


class RecommendationContext(_M):
    role: RoleView
    confrontation: dict | None
    matches: list[dict]
    candidates: list[CandidateView]


# =========================================================================== outputs
EmployerIntent = Literal["inform", "request_success_model", "request_matching", "request_shortlist",
                         "request_confrontation", "request_recommendation", "smalltalk"]
CandidateIntent = Literal["inform", "request_opportunities", "smalltalk"]


class CompanyIdentityPatch(_M):
    mission: str | None = None
    business_model: str | None = None
    industry: str | None = None
    culture: str | None = None
    work_style: str | None = None
    management_style: str | None = None
    environment: str | None = None
    values: list[str] | None = None
    context: str | None = None
    unknowns: list[str] | None = None
    assumptions: list[str] | None = None
    confidence: float | None = None


class RoleIdentityPatch(_M):
    mission: str | None = None
    responsibilities: list[str] | None = None
    objectives: list[str] | None = None
    constraints: list[str] | None = None
    context: str | None = None
    work_environment: str | None = None
    stakeholders: list[str] | None = None
    success_factors: list[str] | None = None
    unknowns: list[str] | None = None
    assumptions: list[str] | None = None
    confidence: float | None = None


class ProfessionalIdentityPatch(_M):
    career_direction: str | None = None
    professional_goals: list[str] | None = None
    strengths: list[str] | None = None
    preferences: list[str] | None = None
    constraints: list[str] | None = None
    aspirations: list[str] | None = None
    summary: str | None = None
    unknowns: list[str] | None = None
    confidence: float | None = None


class EmployerTurnOutput(_M):
    reply: str
    intent: EmployerIntent = "inform"
    company_identity_patch: CompanyIdentityPatch = Field(default_factory=CompanyIdentityPatch)
    role_identity_patch: RoleIdentityPatch = Field(default_factory=RoleIdentityPatch)
    asked_field: str | None = Field(None, description="the field the reply asks about, e.g. 'role.objectives'")


class CandidateTurnOutput(_M):
    reply: str
    intent: CandidateIntent = "inform"
    professional_identity_patch: ProfessionalIdentityPatch = Field(default_factory=ProfessionalIdentityPatch)
    asked_field: str | None = None


class SuccessModelDraft(_M):
    critical_outcomes: list[dict] = Field(description="[{outcome, horizon, measure}]")
    critical_capabilities: list[CapabilitySpec]
    required_behaviors: list[str]
    success_conditions: list[SuccessCondition]
    tradeoffs: list[str]
    risks: list[str]
    unknowns: list[str]
    priorities: dict = Field(default_factory=dict, description='{"primary": str, "notes": str}')
    confidence: float = 0.5


class EvidenceDraft(_M):
    subject_type: str = "capability"
    subject_key: str | None = None
    claim: str
    evidence: str
    source: Source
    epistemic_status: Epistemic
    confidence: float = Field(ge=0, le=1)
    polarity: Literal["supports", "contradicts"] = "supports"


class CapabilityDraft(_M):
    key: str
    name: str
    level: Level
    status: Epistemic
    confidence: float = Field(ge=0, le=1)
    source: Source


class CandidateUnderstandingOutput(_M):
    capabilities: list[CapabilityDraft]
    evidence: list[EvidenceDraft]
    identity_patch: ProfessionalIdentityPatch = Field(default_factory=ProfessionalIdentityPatch)


class AssessmentPlan(_M):
    target_capability: str
    objective: str
    question_type: Literal["behavioral", "situational", "simulation", "verification"]
    question: str
    expected_evidence: list[str]
    rationale: str
    expected_value: float | None = Field(None, description="decision value of the answer, if estimated")


class ResponseInterpretation(_M):
    summary: str
    observed_behaviors: list[str]
    evidence: list[EvidenceDraft]
    confidence: float = Field(ge=0, le=1)


class FitDimension(_M):
    dimension: str            # capability key or "availability", "motivation", ...
    label: str
    importance: Importance
    level: Level
    assessment: str
    evidence_ids: list[str] = Field(default_factory=list)
    certainty: float = 0.0


class MatchAnalysis(_M):
    fit_summary: str
    fit_dimensions: list[FitDimension]
    strengths: list[str]
    gaps: list[str]
    tradeoffs: list[str]
    risks: list[str]
    uncertainties: list[str]
    evidence_ids: list[str] = Field(default_factory=list)
    satisfied_conditions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    ui_score: int | None = Field(None, ge=0, le=100, description="display only")


class ShortlistEntry(_M):
    candidate_id: str
    rank: int
    reason: str


class ShortlistOutput(_M):
    shortlist: list[ShortlistEntry]
    excluded: list[dict] = Field(default_factory=list)  # [{candidate_id, reason}]
    summary: str


class ConfrontationItemOut(_M):
    candidate_id: str
    dimension: str
    level: Level
    assessment: str
    evidence: list[str] = Field(default_factory=list)
    strength: str | None = None
    risk: str | None = None
    uncertainty: str | None = None


class CandidateProfile(_M):
    candidate_id: str
    headline: str  # "strongest immediate performance evidence"


class ConditionalTradeoff(_M):
    if_priority: str
    prefer_candidate_id: str
    explanation: str


class ConfrontationOutput(_M):
    comparison_dimensions: list[str]
    profiles: list[CandidateProfile]
    items: list[ConfrontationItemOut]
    tradeoffs: list[ConditionalTradeoff]
    winner_candidate_id: str | None
    reasoning: str
    uncertainties: list[str]


class Alternative(_M):
    candidate_id: str
    when: str


class RecommendationOutput(_M):
    recommended_candidate_id: str | None
    reasoning_summary: str
    key_evidence: list[str]
    tradeoffs: list[str]
    uncertainties: list[str]
    alternatives: list[Alternative] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
