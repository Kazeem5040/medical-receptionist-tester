"""Immutable models for submitting prepared calls."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .enums import (
    ExecutionSeverity,
    ExecutionStatus,
    ProviderName,
    ProviderResponseState,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CallExecutionModel(BaseModel):
    """Base class for immutable call execution models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ProviderResponseMetadata(CallExecutionModel):
    """Provider response details preserved for traceability."""

    provider_resource_id: NonEmptyString
    provider_call_id: NonEmptyString | None = None
    provider_status: NonEmptyString
    provider_state: ProviderResponseState
    http_status_code: int = Field(ge=100, le=599)
    http_reason_phrase: str | None = None
    values: dict[str, str] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class ExecutionWarning(CallExecutionModel):
    """Non-blocking warning produced during call execution."""

    code: NonEmptyString
    message: NonEmptyString
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: ExecutionSeverity = ExecutionSeverity.WARNING


class ExecutionTraceability(CallExecutionModel):
    """Trace IDs and fingerprints linking execution to prior components."""

    preparation_id: NonEmptyString
    idempotency_key: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_template_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString
    vapi_configuration_fingerprint: NonEmptyString
    request_fingerprint: NonEmptyString
    scenario_seed: NonEmptyString


class ExecutionStatistics(CallExecutionModel):
    """Small execution measurements recorded at submission time."""

    provider_attempt_count: int = Field(default=1, ge=1)
    elapsed_milliseconds: int = Field(default=0, ge=0)
    retries_enabled: bool
    maximum_retries: int = Field(ge=0)


class CallSubmissionResult(CallExecutionModel):
    """Final result after Vapi accepts or rejects a prepared call submission."""

    submission_id: NonEmptyString
    execution_status: ExecutionStatus
    provider_name: ProviderName
    provider_response: ProviderResponseMetadata
    submission_timestamp: datetime
    traceability: ExecutionTraceability
    statistics: ExecutionStatistics
    execution_version: NonEmptyString
    execution_policy_version: NonEmptyString
    result_fingerprint: NonEmptyString
    warnings: tuple[ExecutionWarning, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)
