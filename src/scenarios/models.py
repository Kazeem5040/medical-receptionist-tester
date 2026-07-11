"""Pydantic models for patient testing scenarios."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .enums import (
    DisclosureTiming,
    EvaluationCriterionType,
    FactSensitivity,
    ObjectivePriority,
    ReceptionistBehaviorImportance,
    SafetyClassification,
    ScenarioCategory,
    ScenarioLifecycle,
    TerminationReason,
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


class ScenarioModel(BaseModel):
    """Base class for immutable scenario domain models."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ScenarioIdentity(ScenarioModel):
    """Stable identity and version metadata for a scenario template."""

    scenario_id: NonEmptyString
    slug: SlugString
    display_name: NonEmptyString
    description: NonEmptyString
    version: int = Field(ge=1)
    schema_version: NonEmptyString = "1.0"
    lifecycle: ScenarioLifecycle = ScenarioLifecycle.DRAFT
    category: ScenarioCategory
    tags: tuple[NonEmptyString, ...] = Field(default_factory=tuple)


class SyntheticPatientProfile(ScenarioModel):
    """Synthetic patient identity used by the AI patient during a test."""

    is_synthetic: Literal[True] = True
    given_name: NonEmptyString
    family_name: NonEmptyString
    birth_date: date | None = None
    pronouns: NonEmptyString | None = None
    phone_number: NonEmptyString | None = None
    insurance_name: NonEmptyString | None = None
    member_id: NonEmptyString | None = None
    notes: NonEmptyString | None = None


class PatientFact(ScenarioModel):
    """A single fact the synthetic patient may know or disclose."""

    key: SlugString
    value: NonEmptyString
    sensitivity: FactSensitivity = FactSensitivity.LOW
    required_for_objective: bool = False
    description: NonEmptyString | None = None


class DisclosureRule(ScenarioModel):
    """Rule controlling when a patient fact may be revealed."""

    fact_key: SlugString
    timing: DisclosureTiming
    patient_phrase: NonEmptyString | None = None
    rationale: NonEmptyString | None = None


class ScenarioObjective(ScenarioModel):
    """A goal the synthetic patient is trying to accomplish."""

    objective_id: SlugString
    title: NonEmptyString
    description: NonEmptyString
    priority: ObjectivePriority = ObjectivePriority.PRIMARY
    success_condition: NonEmptyString


class ConversationBehavior(ScenarioModel):
    """How the synthetic patient should behave conversationally."""

    persona: NonEmptyString = "realistic patient"
    tone: NonEmptyString = "calm and cooperative"
    pacing: NonEmptyString = "natural"
    cooperation_level: NonEmptyString = "answers reasonable questions"
    should_interrupt: bool = False
    steering_notes: NonEmptyString | None = None


class ExpectedReceptionistBehavior(ScenarioModel):
    """Behavior the receptionist should demonstrate."""

    expectation_id: SlugString
    behavior: NonEmptyString
    importance: ReceptionistBehaviorImportance = (
        ReceptionistBehaviorImportance.IMPORTANT
    )
    reason: NonEmptyString
    evidence_hint: NonEmptyString | None = None


class ProhibitedReceptionistBehavior(ScenarioModel):
    """Behavior the receptionist should not demonstrate."""

    prohibited_id: SlugString
    behavior: NonEmptyString
    importance: ReceptionistBehaviorImportance = ReceptionistBehaviorImportance.CRITICAL
    reason: NonEmptyString
    evidence_hint: NonEmptyString | None = None
    automatic_failure: bool = True


class EvaluationCriterion(ScenarioModel):
    """A structured requirement for a later transcript evaluator."""

    criterion_id: SlugString
    criterion_type: EvaluationCriterionType
    question: NonEmptyString
    pass_condition: NonEmptyString
    evidence_required: bool = True
    weight: int = Field(default=1, ge=1, le=5)


class SafetyPolicy(ScenarioModel):
    """Safety classification and escalation instructions for the scenario."""

    classification: SafetyClassification = SafetyClassification.LOW
    escalation_instruction: NonEmptyString | None = None
    emergency_keywords: tuple[NonEmptyString, ...] = Field(default_factory=tuple)


class TerminationRule(ScenarioModel):
    """A deterministic rule for when the call should stop."""

    reason: TerminationReason
    condition: NonEmptyString
    max_call_seconds: int | None = Field(default=None, ge=1)


class VariationOption(ScenarioModel):
    """One deterministic option for a controlled scenario variation."""

    option_id: SlugString
    value: NonEmptyString
    description: NonEmptyString | None = None


class ControlledVariation(ScenarioModel):
    """A controlled source of deterministic variation between instances."""

    variation_id: SlugString
    name: NonEmptyString
    options: tuple[VariationOption, ...] = Field(min_length=2)


class ResolvedVariation(ScenarioModel):
    """The selected option for one controlled variation."""

    variation_id: SlugString
    option_id: SlugString
    value: NonEmptyString


class ScenarioTemplate(ScenarioModel):
    """Reusable, versioned scenario definition."""

    identity: ScenarioIdentity
    patient_profile: SyntheticPatientProfile
    objectives: tuple[ScenarioObjective, ...] = Field(min_length=1)
    facts: tuple[PatientFact, ...] = Field(default_factory=tuple)
    disclosure_rules: tuple[DisclosureRule, ...] = Field(default_factory=tuple)
    conversation_behavior: ConversationBehavior = Field(
        default_factory=ConversationBehavior,
    )
    expected_behaviors: tuple[ExpectedReceptionistBehavior, ...] = Field(
        default_factory=tuple,
    )
    prohibited_behaviors: tuple[ProhibitedReceptionistBehavior, ...] = Field(
        default_factory=tuple,
    )
    evaluation_criteria: tuple[EvaluationCriterion, ...] = Field(default_factory=tuple)
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    termination_rules: tuple[TerminationRule, ...] = Field(default_factory=tuple)
    variations: tuple[ControlledVariation, ...] = Field(default_factory=tuple)


class ScenarioInstance(ScenarioModel):
    """Resolved, immutable scenario snapshot for one planned test call."""

    instance_id: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    source_fingerprint: NonEmptyString
    instantiation_seed: NonEmptyString
    identity: ScenarioIdentity
    patient_profile: SyntheticPatientProfile
    objectives: tuple[ScenarioObjective, ...]
    facts: tuple[PatientFact, ...]
    disclosure_rules: tuple[DisclosureRule, ...]
    conversation_behavior: ConversationBehavior
    expected_behaviors: tuple[ExpectedReceptionistBehavior, ...]
    prohibited_behaviors: tuple[ProhibitedReceptionistBehavior, ...]
    evaluation_criteria: tuple[EvaluationCriterion, ...]
    safety: SafetyPolicy
    termination_rules: tuple[TerminationRule, ...]
    selected_variations: tuple[ResolvedVariation, ...] = Field(default_factory=tuple)
    fingerprint: NonEmptyString | None = None

    def evaluation_contract(self) -> dict[str, Any]:
        """Return only the fields a future evaluator will need."""

        return {
            "objectives": self.objectives,
            "expected_behaviors": self.expected_behaviors,
            "prohibited_behaviors": self.prohibited_behaviors,
            "evaluation_criteria": self.evaluation_criteria,
            "safety": self.safety,
        }
