"""Immutable models for collected call sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .enums import (
    CallCompletionReason,
    CallLifecycleState,
    CallParticipant,
    CallSessionStatus,
    MonitoringEventKind,
    MonitoringSeverity,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CallMonitoringModel(BaseModel):
    """Base class for immutable call monitoring models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class MonitoringInputEvent(CallMonitoringModel):
    """Provider-independent event input collected from future webhook/poller layers."""

    event_id: NonEmptyString
    kind: MonitoringEventKind
    occurred_at: datetime
    sequence_index: int = Field(ge=0)
    provider_event_id: NonEmptyString | None = None
    provider_event_type: NonEmptyString | None = None
    lifecycle_state: CallLifecycleState | None = None
    speaker: CallParticipant | None = None
    text: NonEmptyString | None = None
    interrupted_speaker: CallParticipant | None = None
    interrupting_speaker: CallParticipant | None = None
    silence_duration_ms: int | None = Field(default=None, ge=0)
    ended_at: datetime | None = None
    completion_reason: CallCompletionReason | None = None
    recording_url: NonEmptyString | None = None
    transcript_url: NonEmptyString | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ProviderEventMetadata(CallMonitoringModel):
    """Provider event identity and metadata preserved without interpretation."""

    event_id: NonEmptyString
    provider_event_id: NonEmptyString | None = None
    provider_event_type: NonEmptyString | None = None
    kind: MonitoringEventKind
    occurred_at: datetime
    sequence_index: int = Field(ge=0)
    values: dict[str, str] = Field(default_factory=dict)


class CallLifecycleEvent(CallMonitoringModel):
    """Lifecycle state transition observed during a call."""

    event_id: NonEmptyString
    state: CallLifecycleState
    occurred_at: datetime
    provider_event_id: NonEmptyString | None = None
    completion_reason: CallCompletionReason | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class TranscriptUtterance(CallMonitoringModel):
    """One ordered utterance from the AI patient or receptionist."""

    turn_index: int = Field(ge=0)
    event_id: NonEmptyString
    speaker: CallParticipant
    text: NonEmptyString
    started_at: datetime
    ended_at: datetime | None = None
    provider_event_id: NonEmptyString | None = None
    interrupted: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class InterruptionEvent(CallMonitoringModel):
    """Observed interruption between call participants."""

    event_id: NonEmptyString
    occurred_at: datetime
    interrupted_speaker: CallParticipant
    interrupting_speaker: CallParticipant
    provider_event_id: NonEmptyString | None = None
    reason: NonEmptyString | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class SilenceEvent(CallMonitoringModel):
    """Observed silence period during the call."""

    event_id: NonEmptyString
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    speaker: CallParticipant | None = None
    provider_event_id: NonEmptyString | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class CallSessionArtifacts(CallMonitoringModel):
    """Artifact locations reported by the provider."""

    recording_url: NonEmptyString | None = None
    transcript_url: NonEmptyString | None = None
    provider_recording_id: NonEmptyString | None = None
    provider_transcript_id: NonEmptyString | None = None


class CallSessionTraceability(CallMonitoringModel):
    """Trace IDs and fingerprints linking session events to prior components."""

    submission_id: NonEmptyString
    preparation_id: NonEmptyString
    idempotency_key: NonEmptyString
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    scenario_instance_fingerprint: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString
    vapi_configuration_fingerprint: NonEmptyString
    prepared_call_request_fingerprint: NonEmptyString
    call_submission_fingerprint: NonEmptyString
    provider_resource_id: NonEmptyString
    provider_call_id: NonEmptyString | None = None


class CallSessionStatistics(CallMonitoringModel):
    """Counts and timing details for the collected call session."""

    provider_event_count: int = Field(ge=0)
    lifecycle_event_count: int = Field(ge=0)
    transcript_turn_count: int = Field(ge=0)
    assistant_utterance_count: int = Field(ge=0)
    receptionist_utterance_count: int = Field(ge=0)
    interruption_count: int = Field(ge=0)
    silence_event_count: int = Field(ge=0)
    duration_ms: int | None = Field(default=None, ge=0)


class CallMonitoringWarning(CallMonitoringModel):
    """Non-blocking warning produced during call monitoring."""

    code: NonEmptyString
    message: NonEmptyString
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: MonitoringSeverity = MonitoringSeverity.WARNING


class CallSession(CallMonitoringModel):
    """Immutable representation of everything observed during one call."""

    session_id: NonEmptyString
    status: CallSessionStatus
    provider_name: NonEmptyString
    provider_events: tuple[ProviderEventMetadata, ...]
    lifecycle_events: tuple[CallLifecycleEvent, ...]
    transcript: tuple[TranscriptUtterance, ...]
    interruptions: tuple[InterruptionEvent, ...]
    silence_events: tuple[SilenceEvent, ...]
    artifacts: CallSessionArtifacts
    started_at: datetime | None = None
    ended_at: datetime | None = None
    completion_reason: CallCompletionReason | None = None
    traceability: CallSessionTraceability
    statistics: CallSessionStatistics
    monitoring_version: NonEmptyString
    monitoring_policy_version: NonEmptyString
    session_fingerprint: NonEmptyString
    warnings: tuple[CallMonitoringWarning, ...] = Field(default_factory=tuple)
    metadata: dict[str, str] = Field(default_factory=dict)
