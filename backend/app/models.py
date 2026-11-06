"""Database tables.

Three separated layers:
  * Access identity   : users (auth only)
  * Company registry  : companies -> company_identities, roles -> role_identities, success_models
  * Talent registry   : candidates -> professional_identities, experiences, capabilities, evidence
Then the decision pipeline:
  conversations/messages -> assessment_requests/responses -> matches (incl. shortlist)
  -> confrontations/confrontation_items -> recommendations

Identity-like objects (company/role/professional identity, success model) are versioned:
each update inserts a new row with version+1, so history is kept and the latest is "current".
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _fk(target: str, nullable: bool = False, ondelete: str = "CASCADE") -> Mapped:
    return mapped_column(UUID(as_uuid=True), ForeignKey(target, ondelete=ondelete),
                         nullable=nullable, index=True)


def _json(default=dict) -> Mapped:
    return mapped_column(JSONB, nullable=False, default=default)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


# --------------------------------------------------------------------------- enums
class UserRole(str, enum.Enum):
    employer = "employer"
    candidate = "candidate"


class EpistemicStatus(str, enum.Enum):
    """Never silently promote a hypothesis to a fact."""
    fact = "fact"              # directly observed / verified
    inference = "inference"    # reasonably derived from facts
    hypothesis = "hypothesis"  # plausible, to be tested
    unknown = "unknown"        # explicitly not known


class EvidenceSource(str, enum.Enum):
    cv = "cv"
    previous_experience = "previous_experience"
    conversation = "conversation"
    assessment = "assessment"
    reference = "reference"
    employer_note = "employer_note"
    self_declared = "self_declared"


class AssessmentStatus(str, enum.Enum):
    pending = "pending"
    answered = "answered"
    evaluated = "evaluated"
    cancelled = "cancelled"


class ConversationKind(str, enum.Enum):
    employer = "employer"
    candidate = "candidate"


# --------------------------------------------------------------------------- access identity
class User(Base, Timestamped):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null when Supabase Auth owns it
    # Null until the person picks a role on the role-choice page.
    role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"), nullable=True)


# --------------------------------------------------------------------------- company registry
class Company(Base, Timestamped):
    __tablename__ = "companies"
    id: Mapped[uuid.UUID] = _uuid()
    owner_user_id: Mapped[uuid.UUID] = _fk("users.id")
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(80))
    size: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)

    roles: Mapped[list["Role"]] = relationship(back_populates="company")


class CompanyIdentity(Base, Timestamped):
    __tablename__ = "company_identities"
    __table_args__ = (UniqueConstraint("company_id", "version"),)
    id: Mapped[uuid.UUID] = _uuid()
    company_id: Mapped[uuid.UUID] = _fk("companies.id")
    version: Mapped[int] = mapped_column(Integer, default=1)
    mission: Mapped[str | None] = mapped_column(Text)
    business_model: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(200))
    culture: Mapped[str | None] = mapped_column(Text)
    work_style: Mapped[str | None] = mapped_column(Text)
    management_style: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)
    values: Mapped[list] = _json(list)
    context: Mapped[str | None] = mapped_column(Text)
    unknowns: Mapped[list] = _json(list)
    assumptions: Mapped[list] = _json(list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


class Role(Base, Timestamped):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = _uuid()
    company_id: Mapped[uuid.UUID] = _fk("companies.id")
    title: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(120))
    contract_type: Mapped[str | None] = mapped_column(String(40))
    duration: Mapped[str | None] = mapped_column(String(80))  # e.g. "6 mois", null = permanent
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|open|closed
    # Hard constraints usable by the engine, e.g. {"start_before": "2027-01-15", "languages": ["fr","wo"]}
    constraints: Mapped[dict] = _json(dict)

    company: Mapped[Company] = relationship(back_populates="roles")


class RoleIdentity(Base, Timestamped):
    __tablename__ = "role_identities"
    __table_args__ = (UniqueConstraint("role_id", "version"),)
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    version: Mapped[int] = mapped_column(Integer, default=1)
    mission: Mapped[str | None] = mapped_column(Text)
    responsibilities: Mapped[list] = _json(list)
    objectives: Mapped[list] = _json(list)
    constraints: Mapped[list] = _json(list)
    context: Mapped[str | None] = mapped_column(Text)
    work_environment: Mapped[str | None] = mapped_column(Text)
    stakeholders: Mapped[list] = _json(list)
    success_factors: Mapped[list] = _json(list)
    languages: Mapped[list] = _json(list)
    availability: Mapped[str | None] = mapped_column(Text)  # when the person must start / for how long
    priority: Mapped[str | None] = mapped_column(String(40))  # urgency: elevee|normale|faible
    unknowns: Mapped[list] = _json(list)
    assumptions: Mapped[list] = _json(list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


class SuccessModel(Base, Timestamped):
    """What makes someone likely to succeed in THIS role, in THIS context.

    critical_capabilities: [{key, name, description, importance: critical|important|nice,
                             observable_evidence: [str]}]
    success_conditions:    [{name, requires: [capability_key], description}]
                           -> "OR of ANDs": any satisfied path is a credible way to succeed.
    priorities:            {"primary": "immediate_performance" | ..., "notes": str}
    """
    __tablename__ = "success_models"
    __table_args__ = (UniqueConstraint("role_id", "version"),)
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    version: Mapped[int] = mapped_column(Integer, default=1)
    critical_outcomes: Mapped[list] = _json(list)
    critical_capabilities: Mapped[list] = _json(list)
    required_behaviors: Mapped[list] = _json(list)
    success_conditions: Mapped[list] = _json(list)
    tradeoffs: Mapped[list] = _json(list)
    risks: Mapped[list] = _json(list)
    unknowns: Mapped[list] = _json(list)
    priorities: Mapped[dict] = _json(dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


# --------------------------------------------------------------------------- talent registry
class Candidate(Base, Timestamped):
    __tablename__ = "candidates"
    id: Mapped[uuid.UUID] = _uuid()
    user_id: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True, ondelete="SET NULL")
    full_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(120))
    # {"available_from": "2026-12-01", "notice_weeks": 4, "notes": "..."}
    availability: Mapped[dict] = _json(dict)
    cv_text: Mapped[str | None] = mapped_column(Text)
    cv_filename: Mapped[str | None] = mapped_column(String(255))
    # Professional sources shared by the candidate: [{kind: linkedin|portfolio|other, url, added_at}]
    sources: Mapped[list] = _json(list)
    status: Mapped[str] = mapped_column(String(20), default="active")


class ProfessionalIdentity(Base, Timestamped):
    __tablename__ = "professional_identities"
    __table_args__ = (UniqueConstraint("candidate_id", "version"),)
    id: Mapped[uuid.UUID] = _uuid()
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    version: Mapped[int] = mapped_column(Integer, default=1)
    career_direction: Mapped[str | None] = mapped_column(Text)
    professional_goals: Mapped[list] = _json(list)
    strengths: Mapped[list] = _json(list)
    preferences: Mapped[list] = _json(list)
    constraints: Mapped[list] = _json(list)
    aspirations: Mapped[list] = _json(list)
    summary: Mapped[str | None] = mapped_column(Text)
    unknowns: Mapped[list] = _json(list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


class Experience(Base, Timestamped):
    __tablename__ = "experiences"
    id: Mapped[uuid.UUID] = _uuid()
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    title: Mapped[str] = mapped_column(String(200))
    organization: Mapped[str | None] = mapped_column(String(200))
    sector: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[str | None] = mapped_column(String(10))  # YYYY-MM
    end_date: Mapped[str | None] = mapped_column(String(10))    # YYYY-MM or null = current
    description: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list] = _json(list)
    skills: Mapped[list] = _json(list)


class Capability(Base, Timestamped):
    """A capability the system believes the candidate has, with its epistemic status."""
    __tablename__ = "capabilities"
    __table_args__ = (UniqueConstraint("candidate_id", "key"),)
    id: Mapped[uuid.UUID] = _uuid()
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    key: Mapped[str] = mapped_column(String(80))       # normalized, e.g. "objection_handling"
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[str | None] = mapped_column(String(20))  # weak|moderate|strong
    status: Mapped[EpistemicStatus] = mapped_column(Enum(EpistemicStatus, name="epistemic_status"))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[EvidenceSource] = mapped_column(Enum(EvidenceSource, name="evidence_source"))


class Evidence(Base, Timestamped):
    """Links a claim about a candidate to what supports it."""
    __tablename__ = "evidence"
    id: Mapped[uuid.UUID] = _uuid()
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    role_id: Mapped[uuid.UUID | None] = _fk("roles.id", nullable=True)
    subject_type: Mapped[str] = mapped_column(String(40))  # capability|behavior|experience|constraint|motivation
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    subject_key: Mapped[str | None] = mapped_column(String(80), index=True)  # e.g. capability key
    claim: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    source: Mapped[EvidenceSource] = mapped_column(Enum(EvidenceSource, name="evidence_source"))
    epistemic_status: Mapped[EpistemicStatus] = mapped_column(Enum(EpistemicStatus, name="epistemic_status"))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    polarity: Mapped[str] = mapped_column(String(12), default="supports")  # supports|contradicts
    assessment_response_id: Mapped[uuid.UUID | None] = _fk(
        "assessment_responses.id", nullable=True, ondelete="SET NULL")


# --------------------------------------------------------------------------- conversations
class Conversation(Base, Timestamped):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = _uuid()
    user_id: Mapped[uuid.UUID] = _fk("users.id")
    kind: Mapped[ConversationKind] = mapped_column(Enum(ConversationKind, name="conversation_kind"))
    company_id: Mapped[uuid.UUID | None] = _fk("companies.id", nullable=True)
    role_id: Mapped[uuid.UUID | None] = _fk("roles.id", nullable=True)
    candidate_id: Mapped[uuid.UUID | None] = _fk("candidates.id", nullable=True)
    title: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[dict] = _json(dict)  # dialogue state (e.g. which field was last asked)


class Message(Base, Timestamped):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = _uuid()
    conversation_id: Mapped[uuid.UUID] = _fk("conversations.id")
    sender: Mapped[str] = mapped_column(String(20))  # user|assistant|system
    content: Mapped[str] = mapped_column(Text)
    # structured side-channel: intent, updates applied, artifacts produced (ids), etc.
    meta: Mapped[dict] = _json(dict)


# --------------------------------------------------------------------------- assessment
class AssessmentRequest(Base, Timestamped):
    __tablename__ = "assessment_requests"
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    target_capability: Mapped[str] = mapped_column(String(80))
    objective: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(40))  # behavioral|situational|simulation|verification
    question: Mapped[str] = mapped_column(Text)
    expected_evidence: Mapped[list] = _json(list)
    rationale: Mapped[str | None] = mapped_column(Text)     # why THIS question for THIS candidate
    expected_value: Mapped[float | None] = mapped_column(Float)  # hook for tomorrow's VoI
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(AssessmentStatus, name="assessment_status"), default=AssessmentStatus.pending)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


class AssessmentResponse(Base, Timestamped):
    __tablename__ = "assessment_responses"
    id: Mapped[uuid.UUID] = _uuid()
    assessment_request_id: Mapped[uuid.UUID] = _fk("assessment_requests.id")
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    response: Mapped[str] = mapped_column(Text)
    observed_behaviors: Mapped[list] = _json(list)
    evidence: Mapped[list] = _json(list)  # summary of evidence rows created
    confidence: Mapped[float | None] = mapped_column(Float)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


# --------------------------------------------------------------------------- matching / decision
class Match(Base, Timestamped):
    """Structured analysis of one candidate against one role's Success Model."""
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("role_id", "candidate_id"),)
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    success_model_version: Mapped[int | None] = mapped_column(Integer)
    fit_summary: Mapped[str] = mapped_column(Text)
    fit_dimensions: Mapped[list] = _json(list)
    strengths: Mapped[list] = _json(list)
    gaps: Mapped[list] = _json(list)
    tradeoffs: Mapped[list] = _json(list)
    risks: Mapped[list] = _json(list)
    uncertainties: Mapped[list] = _json(list)
    evidence: Mapped[list] = _json(list)  # [{evidence_id, claim, confidence}]
    satisfied_conditions: Mapped[list] = _json(list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    ui_score: Mapped[int | None] = mapped_column(Integer)  # display only, never the reasoning
    shortlist_rank: Mapped[int | None] = mapped_column(Integer)
    shortlist_reason: Mapped[str | None] = mapped_column(Text)
    # Explanation addressed to the candidate (offer card), distinct from the employer-facing summary.
    candidate_explanation: Mapped[str | None] = mapped_column(Text)
    # Human decisions, recorded from card actions. The engine never decides these.
    employer_status: Mapped[str | None] = mapped_column(String(20))   # passed|interview|hired
    candidate_status: Mapped[str | None] = mapped_column(String(20))  # offered|interested|declined
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")


class Confrontation(Base, Timestamped):
    __tablename__ = "confrontations"
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    decision_question: Mapped[str] = mapped_column(Text)
    candidate_ids: Mapped[list] = _json(list)
    comparison_dimensions: Mapped[list] = _json(list)
    profiles: Mapped[list] = _json(list)  # [{candidate_id, headline}] e.g. "highest learning potential"
    tradeoffs: Mapped[list] = _json(list)  # [{if_priority, prefer_candidate_id, explanation}]
    winner_candidate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reasoning: Mapped[str] = mapped_column(Text, default="")
    uncertainties: Mapped[list] = _json(list)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")

    items: Mapped[list["ConfrontationItem"]] = relationship(
        back_populates="confrontation", cascade="all, delete-orphan")


class ConfrontationItem(Base, Timestamped):
    __tablename__ = "confrontation_items"
    id: Mapped[uuid.UUID] = _uuid()
    confrontation_id: Mapped[uuid.UUID] = _fk("confrontations.id")
    candidate_id: Mapped[uuid.UUID] = _fk("candidates.id")
    dimension: Mapped[str] = mapped_column(String(120))
    assessment: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = _json(list)
    strength: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[str | None] = mapped_column(Text)
    uncertainty: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String(20))  # strong|moderate|weak|unknown

    confrontation: Mapped[Confrontation] = relationship(back_populates="items")


class Recommendation(Base, Timestamped):
    __tablename__ = "recommendations"
    id: Mapped[uuid.UUID] = _uuid()
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    confrontation_id: Mapped[uuid.UUID | None] = _fk("confrontations.id", nullable=True)
    recommended_candidate_id: Mapped[uuid.UUID | None] = _fk("candidates.id", nullable=True)
    reasoning_summary: Mapped[str] = mapped_column(Text)
    key_evidence: Mapped[list] = _json(list)
    tradeoffs: Mapped[list] = _json(list)
    uncertainties: Mapped[list] = _json(list)
    alternatives: Mapped[list] = _json(list)  # [{candidate_id, when}]
    next_steps: Mapped[list] = _json(list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    produced_by: Mapped[str] = mapped_column(String(40), default="manual")
