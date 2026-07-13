from __future__ import annotations

import pytest

from call_execution import ExecutionStatus
from call_monitoring import (
    CallCompletionReason,
    CallMonitoringError,
    CallSessionCollector,
    CallSessionStatus,
    MonitoringEventKind,
)
from tests.call_monitoring_factories import (
    call_submission_result,
    monitoring_events,
)


def test_collector_builds_complete_call_session() -> None:
    session = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=monitoring_events(),
    )

    assert session.status == CallSessionStatus.COMPLETED
    assert session.provider_name == "vapi"
    assert session.traceability.provider_call_id == "call_123"
    assert session.completion_reason == CallCompletionReason.NORMAL_COMPLETION
    assert session.artifacts.recording_url == "https://example.test/recording.wav"
    assert session.artifacts.transcript_url == "https://example.test/transcript.json"
    assert session.artifacts.provider_recording_id == "rec_123"
    assert session.artifacts.provider_transcript_id == "tr_123"


def test_collector_preserves_turn_order_after_sorting_events() -> None:
    session = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=monitoring_events(),
    )

    assert [turn.turn_index for turn in session.transcript] == [0, 1]
    assert [turn.text for turn in session.transcript] == [
        "Hi, I need to book an appointment.",
        "We have Tuesday morning available.",
    ]
    assert [event.provider_event_id for event in session.provider_events] == [
        "provider-evt-001",
        "provider-evt-002",
        "provider-evt-003",
        "provider-evt-004",
        "provider-evt-005",
        "provider-evt-006",
        "provider-evt-007",
    ]


def test_collector_records_counts_and_duration() -> None:
    session = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=monitoring_events(),
    )

    assert session.statistics.provider_event_count == 7
    assert session.statistics.lifecycle_event_count == 2
    assert session.statistics.transcript_turn_count == 2
    assert session.statistics.assistant_utterance_count == 1
    assert session.statistics.receptionist_utterance_count == 1
    assert session.statistics.interruption_count == 1
    assert session.statistics.silence_event_count == 1
    assert session.statistics.duration_ms == 19_000


def test_collector_preserves_traceability_to_previous_components() -> None:
    submission = call_submission_result()

    session = CallSessionCollector().collect(
        submission=submission,
        events=monitoring_events(),
    )

    assert session.traceability.submission_id == submission.submission_id
    assert session.traceability.preparation_id == (
        submission.traceability.preparation_id
    )
    assert session.traceability.scenario_instance_fingerprint == (
        submission.traceability.scenario_instance_fingerprint
    )
    assert session.traceability.conversation_contract_fingerprint == (
        submission.traceability.conversation_contract_fingerprint
    )
    assert session.traceability.vapi_configuration_fingerprint == (
        submission.traceability.vapi_configuration_fingerprint
    )
    assert session.traceability.call_submission_fingerprint == (
        submission.result_fingerprint
    )


def test_collection_is_deterministic_for_same_submission_and_events() -> None:
    first = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=monitoring_events(),
    )
    second = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=tuple(reversed(monitoring_events())),
    )

    assert first.session_id == second.session_id
    assert first.session_fingerprint == second.session_fingerprint


def test_rejected_submission_is_not_monitorable_by_default() -> None:
    submission = call_submission_result().model_copy(
        update={"execution_status": ExecutionStatus.FAILED},
    )

    with pytest.raises(CallMonitoringError) as error:
        CallSessionCollector().collect(
            submission=submission,
            events=monitoring_events(),
        )

    assert "submission_not_accepted" in {
        issue.code for issue in error.value.result.errors
    }


def test_collector_does_not_create_evaluation_report_or_storage_fields() -> None:
    session = CallSessionCollector().collect(
        submission=call_submission_result(),
        events=monitoring_events(),
    )
    keys = _all_keys(session.model_dump(mode="json"))

    assert "score" not in keys
    assert "bug_report" not in keys
    assert "database" not in keys
    assert "s3" not in keys
    assert "openai_response" not in keys
    assert any(
        event.kind == MonitoringEventKind.TRANSCRIPT
        for event in session.provider_events
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()
