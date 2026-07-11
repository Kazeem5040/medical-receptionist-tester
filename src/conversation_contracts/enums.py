"""Controlled vocabulary for provider-independent conversation contracts."""

from __future__ import annotations

from enum import StrEnum


class ContractValidationSeverity(StrEnum):
    """Severity level for contract validation issues."""

    ERROR = "error"
    WARNING = "warning"


class KnowledgeBoundaryType(StrEnum):
    """Whether a knowledge boundary permits or forbids an information area."""

    ALLOWED = "allowed"
    UNKNOWN = "unknown"
    FORBIDDEN = "forbidden"


class ContractRuleSeverity(StrEnum):
    """How strongly a behavioral rule should be enforced."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    GUIDANCE = "guidance"


class MilestoneType(StrEnum):
    """Type of conversational checkpoint."""

    OPENING = "opening"
    OBJECTIVE_PROGRESS = "objective_progress"
    INFORMATION_EXCHANGE = "information_exchange"
    CONFIRMATION = "confirmation"
    CLOSING = "closing"


class RecoveryStrategyType(StrEnum):
    """Type of recovery behavior when a conversation gets messy."""

    MISUNDERSTANDING = "misunderstanding"
    INTERRUPTION = "interruption"
    OFF_TOPIC = "off_topic"
    UNKNOWN_INFORMATION = "unknown_information"
    SAFETY_BOUNDARY = "safety_boundary"


class SteeringStrategyType(StrEnum):
    """How the patient keeps the call aligned with the objective."""

    RETURN_TO_OBJECTIVE = "return_to_objective"
    ASK_NEXT_STEP = "ask_next_step"
    REQUEST_CLARIFICATION = "request_clarification"
