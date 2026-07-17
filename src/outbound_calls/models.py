"""Immutable domain models for real outbound call creation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from call_execution import CallSubmissionResult, ProviderName
from call_orchestrator import PreparedCall

from .enums import (
    OutboundCallCreationSeverity,
    OutboundCallStatus,
    ProviderCallState,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class OutboundCallCreationModel(BaseModel):
    """Base class for immutable outbound call creation models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class OutboundCallCreationRequest(OutboundCallCreationModel):
    """Input required to initiate one real outbound provider call."""

    prepared_call: PreparedCall
    call_submission_result: CallSubmissionResult
    phone_number_id: NonEmptyString
    server_url: NonEmptyString | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class OutboundCallProviderMetadata(OutboundCallCreationModel):
    """Provider response details preserved after call creation."""

    provider_call_id: NonEmptyString
    provider_assistant_id: NonEmptyString
    phone_number_id: NonEmptyString
    provider_status: NonEmptyString
    provider_state: ProviderCallState
    http_status_code: int = Field(ge=100, le=599)
    http_reason_phrase: str | None = None
    monitor_listen_url: NonEmptyString | None = None
    monitor_control_url: NonEmptyString | None = None
    values: dict[str, str] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class OutboundCallWarning(OutboundCallCreationModel):
    """Non-blocking warning produced while creating an outbound call."""

    code: NonEmptyString
    message: NonEmptyString
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: OutboundCallCreationSeverity = OutboundCallCreationSeverity.WARNING


class OutboundCallTraceability(OutboundCallCreationModel):
    """Breadcrumbs linking the real call back to every earlier component."""

    preparation_id: NonEmptyString
    submission_id: NonEmptyString
    idempotency_key: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_template_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString
    vapi_configuration_fingerprint: NonEmptyString
    prepared_call_request_fingerprint: NonEmptyString
    call_submission_fingerprint: NonEmptyString
    provider_assistant_id: NonEmptyString
    scenario_seed: NonEmptyString


class OutboundCallStatistics(OutboundCallCreationModel):
    """Small measurements recorded during outbound call creation."""

    provider_attempt_count: int = Field(default=1, ge=1)
    elapsed_milliseconds: int = Field(default=0, ge=0)


class OutboundCallStartResult(OutboundCallCreationModel):
    """Final result after Vapi accepts or rejects the outbound call request."""

    outbound_call_id: NonEmptyString
    status: OutboundCallStatus
    provider_name: ProviderName
    provider_response: OutboundCallProviderMetadata
    requested_at: datetime
    traceability: OutboundCallTraceability
    statistics: OutboundCallStatistics
    creation_version: NonEmptyString
    creation_policy_version: NonEmptyString
    result_fingerprint: NonEmptyString
    warnings: tuple[OutboundCallWarning, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)
