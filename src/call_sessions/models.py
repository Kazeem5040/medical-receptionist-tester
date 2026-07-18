"""Immutable domain models for provider-neutral call lifecycle sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from call_execution import ProviderName

from .enums import CallLifecycleEventType, CallSessionState

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CallSessionModel(BaseModel):
    """Base class for immutable call session domain models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class CallSessionArtifacts(CallSessionModel):
    """Safe artifact references known for a lifecycle session."""

    transcript_artifact_uri: NonEmptyString | None = None
    recording_artifact_uri: NonEmptyString | None = None
    summary_artifact_uri: NonEmptyString | None = None


class CallSessionTraceability(CallSessionModel):
    """Breadcrumbs linking a provider call back to earlier pipeline artifacts."""

    preparation_id: NonEmptyString
    submission_id: NonEmptyString
    outbound_call_id: NonEmptyString
    idempotency_key: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_template_fingerprint: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString
    vapi_configuration_fingerprint: NonEmptyString
    prepared_call_request_fingerprint: NonEmptyString
    call_submission_fingerprint: NonEmptyString
    outbound_call_fingerprint: NonEmptyString
    scenario_seed: NonEmptyString


class CallSession(CallSessionModel):
    """Current internal lifecycle record for one outbound provider call."""

    session_id: NonEmptyString
    provider: ProviderName
    provider_call_id: NonEmptyString
    provider_assistant_id: NonEmptyString
    destination_phone_number_redacted: NonEmptyString
    state: CallSessionState
    created_at: datetime
    updated_at: datetime
    requested_at: datetime
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    failure_code: NonEmptyString | None = None
    failure_message: NonEmptyString | None = None
    provider_ended_reason: NonEmptyString | None = None
    artifacts: CallSessionArtifacts = Field(default_factory=CallSessionArtifacts)
    processed_event_ids: tuple[NonEmptyString, ...] = Field(default_factory=tuple)
    latest_provider_event_at: datetime | None = None
    traceability: CallSessionTraceability
    metadata: dict[str, str] = Field(default_factory=dict)
    schema_version: NonEmptyString
    session_fingerprint: NonEmptyString


class CallLifecycleEvent(CallSessionModel):
    """Provider-neutral lifecycle event produced by a future webhook adapter."""

    provider: ProviderName
    provider_call_id: NonEmptyString
    event_type: CallLifecycleEventType
    occurred_at: datetime
    received_at: datetime
    provider_event_id: NonEmptyString | None = None
    sequence: int | None = Field(default=None, ge=0)
    ended_reason: NonEmptyString | None = None
    failure_code: NonEmptyString | None = None
    failure_message: NonEmptyString | None = None
    transcript_artifact_uri: NonEmptyString | None = None
    recording_artifact_uri: NonEmptyString | None = None
    summary_artifact_uri: NonEmptyString | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    event_fingerprint: NonEmptyString | None = None


class CallSessionUpdateResult(CallSessionModel):
    """Receipt for processing one lifecycle event against a session."""

    session: CallSession
    event_identity: NonEmptyString
    previous_state: CallSessionState
    current_state: CallSessionState
    applied: bool
    duplicate: bool
    terminal: bool
    became_terminal: bool
    processed_at: datetime
