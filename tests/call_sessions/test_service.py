from __future__ import annotations

from datetime import timedelta

import pytest

from call_execution import ProviderName
from call_sessions import (
    CallLifecycleEventType,
    CallSessionError,
    CallSessionNotFoundError,
    CallSessionState,
    InvalidCallTransitionError,
    event_processing_identity,
)
from tests.call_session_factories import (
    InMemoryCallSessionRepository,
    call_session_service,
    fixed_timestamp,
    lifecycle_event,
    outbound_call_start_result,
)


@pytest.mark.asyncio
async def test_session_is_created_from_valid_outbound_call_result() -> None:
    result = await outbound_call_start_result()

    session = call_session_service().create_session(result)

    assert session.state == CallSessionState.REQUESTED
    assert session.provider == ProviderName.VAPI
    assert session.provider_call_id == "call_123"
    assert session.provider_assistant_id == "asst_123"
    assert session.requested_at == result.requested_at
    assert session.session_fingerprint.startswith("call_session:")


@pytest.mark.asyncio
async def test_initial_state_does_not_claim_answered_or_completed() -> None:
    session = call_session_service().create_session(await outbound_call_start_result())

    assert session.state == CallSessionState.REQUESTED
    assert session.answered_at is None
    assert session.ended_at is None
    assert session.state != CallSessionState.COMPLETED


@pytest.mark.asyncio
async def test_traceability_ids_are_preserved() -> None:
    result = await outbound_call_start_result()
    session = call_session_service().create_session(result)

    assert session.traceability.preparation_id == result.traceability.preparation_id
    assert session.traceability.submission_id == result.traceability.submission_id
    assert session.traceability.outbound_call_id == result.outbound_call_id
    assert session.traceability.outbound_call_fingerprint == (
        result.result_fingerprint
    )


@pytest.mark.asyncio
async def test_valid_starting_event_advances_session() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())

    update = service.process_event(session, lifecycle_event())

    assert update.applied is True
    assert update.duplicate is False
    assert update.previous_state == CallSessionState.REQUESTED
    assert update.current_state == CallSessionState.QUEUED
    assert update.session.state == CallSessionState.QUEUED


@pytest.mark.asyncio
async def test_terminal_event_marks_session_terminal() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    started = service.process_event(
        session,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_ANSWERED,
            provider_event_id="evt-answer",
        ),
    ).session

    update = service.process_event(
        started,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_ENDED,
            provider_event_id="evt-ended",
            ended_reason="customer-ended-call",
        ),
    )

    assert update.current_state == CallSessionState.COMPLETED
    assert update.terminal is True
    assert update.became_terminal is True
    assert update.session.ended_at is not None
    assert update.session.provider_ended_reason == "customer-ended-call"


@pytest.mark.asyncio
async def test_failure_event_records_failure_without_marking_completed() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())

    update = service.process_event(
        session,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_FAILED,
            provider_event_id="evt-failed",
            failure_code="provider_error",
            failure_message="Provider could not connect the call.",
        ),
    )

    assert update.current_state == CallSessionState.FAILED
    assert update.session.state != CallSessionState.COMPLETED
    assert update.session.failure_code == "provider_error"
    assert update.session.failure_message == "Provider could not connect the call."


@pytest.mark.asyncio
async def test_duplicate_event_is_not_applied_twice() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    event = lifecycle_event(provider_event_id="evt-duplicate")

    first = service.process_event(session, event)
    second = service.process_event(first.session, event)

    assert first.applied is True
    assert second.applied is False
    assert second.duplicate is True
    assert second.session.processed_event_ids.count(
        event_processing_identity(event),
    ) == 1


@pytest.mark.asyncio
async def test_duplicate_artifact_event_is_not_duplicated() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    event = lifecycle_event(
        event_type=CallLifecycleEventType.RECORDING_AVAILABLE,
        provider_event_id="evt-recording",
        recording_artifact_uri="s3://bucket/recording.wav",
    )

    first = service.process_event(session, event)
    second = service.process_event(first.session, event)

    assert first.session.artifacts.recording_artifact_uri == (
        "s3://bucket/recording.wav"
    )
    assert second.duplicate is True
    assert second.session.artifacts.recording_artifact_uri == (
        "s3://bucket/recording.wav"
    )


@pytest.mark.asyncio
async def test_late_nonterminal_event_cannot_reopen_completed_session() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    active = service.process_event(
        session,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_ANSWERED,
            provider_event_id="evt-answer",
        ),
    ).session
    completed = service.process_event(
        active,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_ENDED,
            provider_event_id="evt-ended",
            ended_reason="completed",
        ),
    ).session

    update = service.process_event(
        completed,
        lifecycle_event(
            event_type=CallLifecycleEventType.CALL_RINGING,
            provider_event_id="evt-late-ringing",
            occurred_at=fixed_timestamp() + timedelta(seconds=1),
        ),
    )

    assert update.applied is False
    assert update.duplicate is False
    assert update.session.state == CallSessionState.COMPLETED


@pytest.mark.asyncio
async def test_invalid_transition_raises_domain_error() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())

    with pytest.raises(InvalidCallTransitionError):
        service.process_event(
            session,
            lifecycle_event(
                event_type=CallLifecycleEventType.CALL_ENDED,
                provider_event_id="evt-ended-too-soon",
            ),
        )


@pytest.mark.asyncio
async def test_event_for_different_provider_call_id_is_rejected() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())

    with pytest.raises(CallSessionError) as error:
        service.process_event(
            session,
            lifecycle_event(
                provider_call_id="call_other",
                provider_event_id="evt-other-call",
            ),
        )

    assert "event_provider_call_id_mismatch" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_event_from_different_provider_is_rejected() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    event = lifecycle_event(provider_event_id="evt-other-provider").model_construct(
        **{
            **lifecycle_event(provider_event_id="evt-other-provider").model_dump(),
            "provider": "other-provider",
        },
    )

    with pytest.raises(CallSessionError) as error:
        service.process_event(session, event)  # type: ignore[arg-type]

    assert "event_provider_mismatch" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_timestamps_remain_utc_aware() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    update = service.process_event(session, lifecycle_event())

    assert update.session.created_at.tzinfo is not None
    assert update.session.updated_at.utcoffset() == timedelta(0)
    assert update.processed_at.utcoffset() == timedelta(0)


@pytest.mark.asyncio
async def test_repository_can_process_event_by_provider_call_id() -> None:
    repository = InMemoryCallSessionRepository()
    service = call_session_service(repository=repository)
    session = service.create_session(await outbound_call_start_result())

    update = service.process_event_for_provider_call(lifecycle_event())

    assert update.session.session_id == session.session_id
    assert repository.get_by_provider_call_id(
        ProviderName.VAPI,
        "call_123",
    ).state == CallSessionState.QUEUED


@pytest.mark.asyncio
async def test_repository_missing_session_raises_not_found() -> None:
    service = call_session_service(repository=InMemoryCallSessionRepository())

    with pytest.raises(CallSessionNotFoundError):
        service.process_event_for_provider_call(lifecycle_event())


@pytest.mark.asyncio
async def test_repository_uniqueness_prevents_conflicting_sessions() -> None:
    repository = InMemoryCallSessionRepository()
    service = call_session_service(repository=repository)
    session = service.create_session(await outbound_call_start_result())
    conflicting = session.model_copy(update={"session_id": "session-other"})

    with pytest.raises(CallSessionError) as error:
        repository.save(conflicting)

    assert "provider_call_session_conflict" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_no_raw_provider_dicts_are_required_or_stored_as_payloads() -> None:
    service = call_session_service()
    session = service.create_session(await outbound_call_start_result())
    update = service.process_event(session, lifecycle_event(metadata={"safe": "yes"}))

    serialized = update.session.model_dump(mode="json")

    assert "raw_vapi_payload" not in _all_keys(serialized)
    assert "vapi_payload" not in _all_keys(serialized)
    assert serialized["metadata"]["suite"] == "unit-test"


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
