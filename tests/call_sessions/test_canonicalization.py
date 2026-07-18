from __future__ import annotations

from datetime import timedelta

import pytest

from call_sessions import canonical_snapshot, event_processing_identity
from tests.call_session_factories import fixed_timestamp, lifecycle_event


def test_canonically_equivalent_events_create_same_fallback_fingerprint() -> None:
    first = lifecycle_event(provider_event_id=None)
    second = lifecycle_event(provider_event_id=None)

    assert event_processing_identity(first) == event_processing_identity(second)


def test_meaningfully_different_events_create_different_fingerprints() -> None:
    first = lifecycle_event(provider_event_id=None, ended_reason="completed")
    second = lifecycle_event(provider_event_id=None, ended_reason="busy")

    assert event_processing_identity(first) != event_processing_identity(second)


def test_event_fingerprint_does_not_depend_on_received_at() -> None:
    first = lifecycle_event(
        provider_event_id=None,
        received_at=fixed_timestamp() + timedelta(seconds=1),
    )
    second = lifecycle_event(
        provider_event_id=None,
        received_at=fixed_timestamp() + timedelta(days=1),
    )

    assert event_processing_identity(first) == event_processing_identity(second)


@pytest.mark.asyncio
async def test_canonical_snapshot_is_stable() -> None:
    event = lifecycle_event(provider_event_id=None)

    assert canonical_snapshot(event) == canonical_snapshot(event)
