from __future__ import annotations

import pytest
from pydantic import ValidationError

from call_execution import (
    ExecutionStatus,
    ProviderName,
    ProviderResponseMetadata,
    ProviderResponseState,
)


def test_models_are_immutable() -> None:
    metadata = ProviderResponseMetadata(
        provider_resource_id="asst_123",
        provider_status="created",
        provider_state=ProviderResponseState.ACCEPTED,
        http_status_code=201,
    )

    with pytest.raises(ValidationError):
        metadata.provider_status = "changed"  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ProviderResponseMetadata(
            provider_resource_id="asst_123",
            provider_status="created",
            provider_state=ProviderResponseState.ACCEPTED,
            http_status_code=201,
            unexpected="nope",
        )


def test_enums_use_clear_provider_and_execution_values() -> None:
    assert ProviderName.VAPI.value == "vapi"
    assert ExecutionStatus.ACCEPTED.value == "accepted"
