from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from call_sessions import (
    CallLifecycleEventType,
    validate_call_lifecycle_event,
    validate_call_session,
    validate_outbound_call_start_for_session,
)
from tests.call_session_factories import (
    call_session,
    fixed_timestamp,
    lifecycle_event,
    outbound_call_start_result,
)


@pytest.mark.asyncio
async def test_outbound_start_missing_provider_call_id_is_rejected() -> None:
    result = await outbound_call_start_result()
    provider_response = result.provider_response.model_construct(
        **{
            **result.provider_response.model_dump(),
            "provider_call_id": "",
        },
    )
    invalid = result.model_copy(update={"provider_response": provider_response})

    validation = validate_outbound_call_start_for_session(invalid)

    assert "missing_provider_call_id" in {issue.code for issue in validation.errors}


def test_failure_event_needs_failure_information() -> None:
    event = lifecycle_event(
        event_type=CallLifecycleEventType.CALL_FAILED,
        provider_event_id="evt-failed",
    )

    validation = validate_call_lifecycle_event(event)

    assert "missing_failure_information" in {
        issue.code for issue in validation.errors
    }


def test_artifact_event_requires_matching_artifact_uri() -> None:
    event = lifecycle_event(
        event_type=CallLifecycleEventType.RECORDING_AVAILABLE,
        provider_event_id="evt-recording",
    )

    validation = validate_call_lifecycle_event(event)

    assert "missing_recording_artifact" in {issue.code for issue in validation.errors}


def test_naive_timestamp_is_rejected() -> None:
    event = lifecycle_event(
        occurred_at=datetime(2026, 1, 1, 1, 1, 1),
        provider_event_id="evt-naive",
    )

    validation = validate_call_lifecycle_event(event)

    assert "timestamp_not_timezone_aware" in {
        issue.code for issue in validation.errors
    }


@pytest.mark.asyncio
async def test_impossible_timestamp_ordering_is_rejected() -> None:
    session = await call_session()
    invalid = session.model_copy(
        update={
            "started_at": fixed_timestamp() + timedelta(minutes=5),
            "ended_at": fixed_timestamp() + timedelta(minutes=1),
        },
    )

    validation = validate_call_session(invalid)

    assert "ended_before_started" in {issue.code for issue in validation.errors}
