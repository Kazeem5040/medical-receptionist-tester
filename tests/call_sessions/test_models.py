from __future__ import annotations

import pytest
from pydantic import ValidationError

from call_sessions import CallLifecycleEvent
from tests.call_session_factories import call_session, lifecycle_event


@pytest.mark.asyncio
async def test_call_session_is_immutable() -> None:
    session = await call_session()

    with pytest.raises(ValidationError):
        session.provider_call_id = "different"  # type: ignore[misc]


def test_lifecycle_event_rejects_unknown_fields() -> None:
    event = lifecycle_event()

    with pytest.raises(ValidationError):
        CallLifecycleEvent.model_validate(
            {
                **event.model_dump(),
                "raw_vapi_payload": {"message": "should not enter domain"},
            },
        )
