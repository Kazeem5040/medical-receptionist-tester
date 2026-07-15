from __future__ import annotations

import pytest
from pydantic import ValidationError

from test_call_workflow import (
    ProviderCapabilityState,
)
from test_call_workflow import (
    TestCallWorkflowStatus as WorkflowStatus,
)
from test_call_workflow import (
    TestCallWorkflowWarning as WorkflowWarning,
)


def test_models_are_frozen() -> None:
    warning = WorkflowWarning(
        code="capability_notice",
        message="Assistant created, outbound call not yet started.",
    )

    with pytest.raises(ValidationError):
        warning.code = "changed"  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkflowWarning(
            code="capability_notice",
            message="Assistant created.",
            unexpected="nope",
        )


def test_enums_use_honest_capability_language() -> None:
    assert ProviderCapabilityState.ASSISTANT_CREATED.value == "assistant_created"
    assert WorkflowStatus.SUBMITTED.value == "submitted"
