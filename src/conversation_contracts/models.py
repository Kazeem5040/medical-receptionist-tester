"""Provider-independent conversation contract models."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from scenarios.enums import (
    DisclosureTiming,
    FactSensitivity,
    ObjectivePriority,
    SafetyClassification,
    TerminationReason,
)

from .enums import (
    ContractRuleSeverity,
    KnowledgeBoundaryType,
    MilestoneType,
    RecoveryStrategyType,
    SteeringStrategyType,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SlugString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]


class ContractModel(BaseModel):
    """Base class for immutable contract domain models."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ContractSource(ContractModel):
    """Traceability metadata back to the scenario instance."""

    scenario_instance_id: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    source_scenario_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString | None = None
    instantiation_seed: NonEmptyString


class ContractPatientIdentity(ContractModel):
    """Synthetic patient identity available to the conversation agent."""

    given_name: NonEmptyString
    family_name: NonEmptyString
    birth_date: date | None = None
    pronouns: NonEmptyString | None = None
    phone_number: NonEmptyString | None = None
    insurance_name: NonEmptyString | None = None
    member_id: NonEmptyString | None = None
    notes: NonEmptyString | None = None


class ContractObjective(ContractModel):
    """A patient objective expressed as behavior, not scripted dialogue."""

    objective_id: SlugString
    title: NonEmptyString
    description: NonEmptyString
    priority: ObjectivePriority
    success_condition: NonEmptyString


class ContractFact(ContractModel):
    """A fact the patient knows within the conversation."""

    key: SlugString
    value: NonEmptyString
    sensitivity: FactSensitivity
    required_for_objective: bool = False
    description: NonEmptyString | None = None


class KnownInformation(ContractModel):
    """Information the patient is allowed to know and use."""

    facts: tuple[ContractFact, ...] = Field(default_factory=tuple)


class UnknownInformation(ContractModel):
    """Information areas the patient must not invent."""

    unknown_id: SlugString
    topic: NonEmptyString
    behavior: NonEmptyString
    reason: NonEmptyString


class ContractDisclosureRule(ContractModel):
    """When and how a known fact may be disclosed."""

    fact_key: SlugString
    timing: DisclosureTiming
    behavior: NonEmptyString
    rationale: NonEmptyString | None = None


class ConversationStyle(ContractModel):
    """Patient conversation style and temperament."""

    persona: NonEmptyString
    personality: NonEmptyString
    tone: NonEmptyString
    pacing: NonEmptyString
    cooperation_level: NonEmptyString
    should_interrupt: bool = False
    steering_notes: NonEmptyString | None = None


class ConversationMilestone(ContractModel):
    """A behavioral checkpoint the patient should naturally work toward."""

    milestone_id: SlugString
    milestone_type: MilestoneType
    description: NonEmptyString
    related_objective_id: SlugString | None = None


class RecoveryRule(ContractModel):
    """How the patient should recover from conversational problems."""

    rule_id: SlugString
    strategy_type: RecoveryStrategyType
    trigger: NonEmptyString
    behavior: NonEmptyString


class ClarificationRule(ContractModel):
    """How the patient should ask for or provide clarification."""

    rule_id: SlugString
    trigger: NonEmptyString
    behavior: NonEmptyString


class SteeringRule(ContractModel):
    """How the patient should keep the call aligned with the objective."""

    rule_id: SlugString
    strategy_type: SteeringStrategyType
    trigger: NonEmptyString
    behavior: NonEmptyString


class ContractTerminationRule(ContractModel):
    """When the patient should allow or seek call termination."""

    reason: TerminationReason
    condition: NonEmptyString
    max_call_seconds: int | None = Field(default=None, ge=1)


class SafetyInstruction(ContractModel):
    """Safety behavior the patient should follow during the call."""

    classification: SafetyClassification
    instruction: NonEmptyString
    emergency_keywords: tuple[NonEmptyString, ...] = Field(default_factory=tuple)


class BehavioralConstraint(ContractModel):
    """A general patient behavior rule."""

    constraint_id: SlugString
    rule: NonEmptyString
    severity: ContractRuleSeverity = ContractRuleSeverity.IMPORTANT


class KnowledgeBoundary(ContractModel):
    """Allowed, unknown, or forbidden knowledge boundary."""

    boundary_id: SlugString
    boundary_type: KnowledgeBoundaryType
    rule: NonEmptyString
    reason: NonEmptyString


class ForbiddenBehavior(ContractModel):
    """A behavior the AI patient must not perform."""

    behavior_id: SlugString
    behavior: NonEmptyString
    reason: NonEmptyString
    severity: ContractRuleSeverity = ContractRuleSeverity.CRITICAL


class ConversationContract(ContractModel):
    """Provider-independent behavioral contract for the AI patient."""

    contract_id: NonEmptyString
    contract_version: NonEmptyString
    source: ContractSource
    patient_identity: ContractPatientIdentity
    objectives: tuple[ContractObjective, ...] = Field(min_length=1)
    known_information: KnownInformation
    unknown_information: tuple[UnknownInformation, ...] = Field(default_factory=tuple)
    disclosure_rules: tuple[ContractDisclosureRule, ...] = Field(default_factory=tuple)
    conversation_style: ConversationStyle
    milestones: tuple[ConversationMilestone, ...] = Field(default_factory=tuple)
    recovery_rules: tuple[RecoveryRule, ...] = Field(default_factory=tuple)
    clarification_rules: tuple[ClarificationRule, ...] = Field(default_factory=tuple)
    steering_rules: tuple[SteeringRule, ...] = Field(default_factory=tuple)
    termination_rules: tuple[ContractTerminationRule, ...] = Field(min_length=1)
    safety_instruction: SafetyInstruction
    behavioral_constraints: tuple[BehavioralConstraint, ...] = Field(
        default_factory=tuple,
    )
    knowledge_boundaries: tuple[KnowledgeBoundary, ...] = Field(default_factory=tuple)
    forbidden_behaviors: tuple[ForbiddenBehavior, ...] = Field(default_factory=tuple)
    fingerprint: NonEmptyString | None = None
