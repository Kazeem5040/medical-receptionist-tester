"""Controlled vocabulary for call preparation orchestration."""

from __future__ import annotations

from enum import StrEnum


class CallWorkflowStatus(StrEnum):
    """Preparation-stage workflow status for a test call."""

    REQUEST_RECEIVED = "request_received"
    VALIDATED = "validated"
    SCENARIO_INSTANTIATED = "scenario_instantiated"
    CONTRACT_BUILT = "contract_built"
    PROVIDER_CONFIG_BUILT = "provider_config_built"
    PREPARED = "prepared"
    FAILED = "failed"


class DestinationKind(StrEnum):
    """Supported destination reference types for this phase."""

    IDENTIFIER = "identifier"
    E164_PHONE_NUMBER = "e164_phone_number"


class CallOrchestrationValidationSeverity(StrEnum):
    """Severity level for orchestration validation issues."""

    ERROR = "error"
    WARNING = "warning"
