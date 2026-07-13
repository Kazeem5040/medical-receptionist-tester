from __future__ import annotations

from datetime import UTC, datetime, timedelta

from call_execution import (
    CallSubmissionResult,
    ExecutionStatistics,
    ExecutionStatus,
    ExecutionTraceability,
    ProviderName,
    ProviderResponseMetadata,
    ProviderResponseState,
)
from call_monitoring import (
    CallCompletionReason,
    CallLifecycleState,
    CallParticipant,
    MonitoringEventKind,
    MonitoringInputEvent,
)


def timestamp(offset_seconds: int = 0) -> datetime:
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC) + timedelta(
        seconds=offset_seconds,
    )


def call_submission_result() -> CallSubmissionResult:
    return CallSubmissionResult(
        submission_id="submission_123",
        execution_status=ExecutionStatus.ACCEPTED,
        provider_name=ProviderName.VAPI,
        provider_response=ProviderResponseMetadata(
            provider_resource_id="asst_123",
            provider_call_id="call_123",
            provider_status="queued",
            provider_state=ProviderResponseState.ACCEPTED,
            http_status_code=201,
            http_reason_phrase="Created",
            values={"source": "unit-test"},
            raw_response={"id": "call_123"},
        ),
        submission_timestamp=timestamp(),
        traceability=ExecutionTraceability(
            preparation_id="prep_123",
            idempotency_key="idem-key-0001",
            source_scenario_id="scenario-1",
            source_scenario_version=1,
            scenario_template_fingerprint="scenario_template:abc",
            scenario_instance_fingerprint="scenario_instance:abc",
            conversation_contract_fingerprint="conversation_contract:abc",
            vapi_configuration_fingerprint="vapi_configuration:abc",
            request_fingerprint="request:abc",
            scenario_seed="seed-1",
        ),
        statistics=ExecutionStatistics(
            provider_attempt_count=1,
            elapsed_milliseconds=123,
            retries_enabled=True,
            maximum_retries=2,
        ),
        execution_version="1.0",
        execution_policy_version="1.0",
        result_fingerprint="call_submission:abc",
        metadata={"suite": "unit-test"},
    )


def monitoring_events() -> tuple[MonitoringInputEvent, ...]:
    return (
        MonitoringInputEvent(
            event_id="evt-004",
            kind=MonitoringEventKind.TRANSCRIPT,
            occurred_at=timestamp(9),
            sequence_index=4,
            provider_event_id="provider-evt-004",
            provider_event_type="conversation.item",
            speaker=CallParticipant.RECEPTIONIST,
            text="We have Tuesday morning available.",
        ),
        MonitoringInputEvent(
            event_id="evt-001",
            kind=MonitoringEventKind.LIFECYCLE,
            occurred_at=timestamp(1),
            sequence_index=1,
            provider_event_id="provider-evt-001",
            provider_event_type="call.started",
            lifecycle_state=CallLifecycleState.IN_PROGRESS,
        ),
        MonitoringInputEvent(
            event_id="evt-002",
            kind=MonitoringEventKind.TRANSCRIPT,
            occurred_at=timestamp(4),
            sequence_index=2,
            provider_event_id="provider-evt-002",
            provider_event_type="conversation.item",
            speaker=CallParticipant.AI_PATIENT,
            text="Hi, I need to book an appointment.",
        ),
        MonitoringInputEvent(
            event_id="evt-003",
            kind=MonitoringEventKind.SILENCE,
            occurred_at=timestamp(6),
            sequence_index=3,
            provider_event_id="provider-evt-003",
            provider_event_type="silence.detected",
            silence_duration_ms=1200,
            speaker=CallParticipant.RECEPTIONIST,
        ),
        MonitoringInputEvent(
            event_id="evt-005",
            kind=MonitoringEventKind.INTERRUPTION,
            occurred_at=timestamp(10),
            sequence_index=5,
            provider_event_id="provider-evt-005",
            provider_event_type="speech.interrupted",
            interrupted_speaker=CallParticipant.AI_PATIENT,
            interrupting_speaker=CallParticipant.RECEPTIONIST,
            metadata={"reason": "barge_in"},
        ),
        MonitoringInputEvent(
            event_id="evt-006",
            kind=MonitoringEventKind.ARTIFACT,
            occurred_at=timestamp(12),
            sequence_index=6,
            provider_event_id="provider-evt-006",
            provider_event_type="artifact.ready",
            recording_url="https://example.test/recording.wav",
            transcript_url="https://example.test/transcript.json",
            metadata={
                "provider_recording_id": "rec_123",
                "provider_transcript_id": "tr_123",
            },
        ),
        MonitoringInputEvent(
            event_id="evt-007",
            kind=MonitoringEventKind.LIFECYCLE,
            occurred_at=timestamp(20),
            sequence_index=7,
            provider_event_id="provider-evt-007",
            provider_event_type="call.ended",
            lifecycle_state=CallLifecycleState.COMPLETED,
            completion_reason=CallCompletionReason.NORMAL_COMPLETION,
        ),
    )
