from __future__ import annotations

import pytest
from pydantic import ValidationError

from call_orchestrator import ApprovedDestination, DestinationKind


def test_orchestrator_models_are_immutable() -> None:
    destination = ApprovedDestination(
        kind=DestinationKind.IDENTIFIER,
        value="clinic-main",
    )

    with pytest.raises(ValidationError):
        destination.value = "changed"


def test_orchestrator_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ApprovedDestination(
            kind=DestinationKind.IDENTIFIER,
            value="clinic-main",
            api_key="not-allowed",
        )
