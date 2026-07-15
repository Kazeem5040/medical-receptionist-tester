from __future__ import annotations

import pytest

from test_call_workflow import (
    TestCallWorkflowError as WorkflowError,
)
from test_call_workflow import (
    TestCallWorkflowIssue as WorkflowIssue,
)
from test_call_workflow import (
    TestCallWorkflowValidationResult as WorkflowValidationResult,
)


def test_validation_result_separates_errors_and_warnings() -> None:
    result = WorkflowValidationResult.from_issues(
        (
            WorkflowIssue(
                code="call_preparation_failed",
                message="Preparation failed.",
            ),
        ),
    )

    assert not result.is_valid
    assert len(result.errors) == 1
    assert result.warnings == ()


def test_raise_if_invalid_raises_structured_error() -> None:
    result = WorkflowValidationResult.from_issues(
        (
            WorkflowIssue(
                code="call_submission_failed",
                message="Submission failed.",
            ),
        ),
    )

    with pytest.raises(WorkflowError) as error:
        result.raise_if_invalid()

    assert error.value.result is result
