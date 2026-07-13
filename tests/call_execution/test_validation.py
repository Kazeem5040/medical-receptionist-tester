from __future__ import annotations

import pytest

from call_execution import (
    CallExecutionPolicy,
    ProviderResponseState,
    validate_call_submission_result,
    validate_prepared_call_for_execution,
    validate_provider_response,
)
from call_orchestrator import CallWorkflowStatus
from tests.call_execution_factories import (
    FakeVapiClient,
    execution_service,
    valid_prepared_call,
    vapi_success_response,
)


def test_valid_prepared_call_passes_execution_validation() -> None:
    result = validate_prepared_call_for_execution(valid_prepared_call())

    assert result.is_valid


def test_prepared_call_with_wrong_status_is_rejected() -> None:
    prepared = valid_prepared_call().model_copy(
        update={"status": CallWorkflowStatus.FAILED},
    )

    result = validate_prepared_call_for_execution(prepared)

    assert not result.is_valid
    assert "prepared_call_not_ready" in {issue.code for issue in result.errors}


def test_prepared_call_forbidden_metadata_is_rejected() -> None:
    prepared = valid_prepared_call().model_copy(
        update={"metadata": {"transcript": "should-not-live-here"}},
    )

    result = validate_prepared_call_for_execution(prepared)

    assert not result.is_valid
    assert "forbidden_metadata_key" in {issue.code for issue in result.errors}


def test_provider_response_validation_accepts_complete_response() -> None:
    result = validate_provider_response(vapi_success_response())

    assert result.is_valid


@pytest.mark.asyncio
async def test_call_submission_result_validation_rejects_unacceptable_state() -> None:
    service = execution_service(FakeVapiClient(vapi_success_response()))
    prepared = valid_prepared_call()
    valid_result = await service.execute(prepared)

    result = valid_result.model_copy(
        update={
            "provider_response": valid_result.provider_response.model_copy(
                update={"provider_state": ProviderResponseState.REJECTED},
            ),
        },
    )

    validation = validate_call_submission_result(
        result,
        CallExecutionPolicy(),
    )

    assert not validation.is_valid
    assert "unacceptable_provider_state" in {
        issue.code for issue in validation.errors
    }
