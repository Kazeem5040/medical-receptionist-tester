from __future__ import annotations

from call_monitoring import (
    CallMonitoringPolicy,
    MonitoringEventKind,
    MonitoringInputEvent,
    validate_monitoring_events,
)
from tests.call_monitoring_factories import timestamp


def test_transcript_event_without_text_is_rejected() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.TRANSCRIPT,
        occurred_at=timestamp(),
        sequence_index=0,
    )

    result = validate_monitoring_events((event,))

    assert not result.is_valid
    assert "missing_transcript_text" in {issue.code for issue in result.errors}


def test_lifecycle_event_without_state_is_rejected() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.LIFECYCLE,
        occurred_at=timestamp(),
        sequence_index=0,
    )

    result = validate_monitoring_events((event,))

    assert not result.is_valid
    assert "missing_lifecycle_state" in {issue.code for issue in result.errors}


def test_artifact_event_without_urls_is_rejected() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.ARTIFACT,
        occurred_at=timestamp(),
        sequence_index=0,
    )

    result = validate_monitoring_events((event,))

    assert not result.is_valid
    assert "missing_artifact_reference" in {issue.code for issue in result.errors}


def test_duplicate_event_ids_are_rejected() -> None:
    first = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.METADATA,
        occurred_at=timestamp(),
        sequence_index=0,
    )
    second = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.METADATA,
        occurred_at=timestamp(1),
        sequence_index=1,
    )

    result = validate_monitoring_events((first, second))

    assert not result.is_valid
    assert "duplicate_event_id" in {issue.code for issue in result.errors}


def test_forbidden_metadata_is_rejected() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.METADATA,
        occurred_at=timestamp(),
        sequence_index=0,
        metadata={"bug_report": "not allowed here"},
    )

    result = validate_monitoring_events((event,))

    assert not result.is_valid
    assert "forbidden_metadata_key" in {issue.code for issue in result.errors}


def test_policy_limits_event_count() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.METADATA,
        occurred_at=timestamp(),
        sequence_index=0,
    )

    result = validate_monitoring_events(
        (event,),
        CallMonitoringPolicy(max_events_per_session=1),
    )

    assert result.is_valid
