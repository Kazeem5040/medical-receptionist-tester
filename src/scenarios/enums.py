"""Controlled vocabulary for medical receptionist testing scenarios."""

from __future__ import annotations

from enum import StrEnum


class ScenarioLifecycle(StrEnum):
    """Lifecycle state for a scenario definition."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ScenarioCategory(StrEnum):
    """High-level type of receptionist workflow being tested."""

    SCHEDULING = "scheduling"
    RESCHEDULING = "rescheduling"
    CANCELLATION = "cancellation"
    PRESCRIPTION_REFILL = "prescription_refill"
    OFFICE_INFORMATION = "office_information"
    INSURANCE = "insurance"
    BILLING = "billing"
    PRIVACY = "privacy"
    EMERGENCY = "emergency"
    AMBIGUOUS_REQUEST = "ambiguous_request"
    OUT_OF_SCOPE = "out_of_scope"
    PROMPT_INJECTION = "prompt_injection"


class ObjectivePriority(StrEnum):
    """Importance of a patient objective inside the call."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class FactSensitivity(StrEnum):
    """Sensitivity level for synthetic patient facts."""

    LOW = "low"
    MEDICAL = "medical"
    INSURANCE = "insurance"
    FINANCIAL = "financial"
    IDENTIFIER = "identifier"


class DisclosureTiming(StrEnum):
    """When the synthetic patient is allowed to disclose a fact."""

    IMMEDIATE = "immediate"
    WHEN_ASKED = "when_asked"
    ONLY_IF_NEEDED = "only_if_needed"
    NEVER_VOLUNTEER = "never_volunteer"


class ReceptionistBehaviorImportance(StrEnum):
    """How important an expected or prohibited receptionist behavior is."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"


class EvaluationCriterionType(StrEnum):
    """The kind of judgment a future evaluator should make."""

    REQUIRED_BEHAVIOR = "required_behavior"
    PROHIBITED_BEHAVIOR = "prohibited_behavior"
    QUALITY = "quality"
    SAFETY = "safety"


class SafetyClassification(StrEnum):
    """Safety risk level of the scenario."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EMERGENCY = "emergency"


class TerminationReason(StrEnum):
    """Why a call should end."""

    OBJECTIVE_MET = "objective_met"
    MAX_DURATION_REACHED = "max_duration_reached"
    RECEPTIONIST_ENDED_CALL = "receptionist_ended_call"
    SAFETY_ESCALATION = "safety_escalation"
    POLICY_VIOLATION = "policy_violation"


class ValidationSeverity(StrEnum):
    """Severity level for structured validation issues."""

    ERROR = "error"
    WARNING = "warning"
