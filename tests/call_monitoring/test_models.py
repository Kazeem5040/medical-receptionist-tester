from __future__ import annotations

import pytest
from pydantic import ValidationError

from call_monitoring import (
    CallParticipant,
    MonitoringEventKind,
    MonitoringInputEvent,
)
from tests.call_monitoring_factories import timestamp


def test_monitoring_models_are_immutable() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.METADATA,
        occurred_at=timestamp(),
        sequence_index=0,
    )

    with pytest.raises(ValidationError):
        event.event_id = "changed"  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        MonitoringInputEvent(
            event_id="evt-1",
            kind=MonitoringEventKind.METADATA,
            occurred_at=timestamp(),
            sequence_index=0,
            surprise="nope",
        )


def test_transcript_event_can_represent_ai_patient_or_receptionist() -> None:
    event = MonitoringInputEvent(
        event_id="evt-1",
        kind=MonitoringEventKind.TRANSCRIPT,
        occurred_at=timestamp(),
        sequence_index=0,
        speaker=CallParticipant.AI_PATIENT,
        text="Hello, I need an appointment.",
    )

    assert event.speaker == CallParticipant.AI_PATIENT
