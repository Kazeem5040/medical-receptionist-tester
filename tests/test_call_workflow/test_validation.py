from __future__ import annotations

from test_call_workflow import (
    ProviderCapabilityState,
    validate_prepared_call_transition,
    validate_submission_transition,
    validate_test_call_request,
    validate_test_call_start_result,
)
from test_call_workflow import (
    TestCallWorkflowPolicy as WorkflowPolicy,
)
from test_call_workflow import (
    TestCallWorkflowStatus as WorkflowStatus,
)
from tests.test_call_workflow_factories import (
    RecordingExecutionService,
    RecordingOrchestrator,
    fixed_clock,
    fixed_monotonic,
    submission_result_for,
    valid_prepared_call,
    valid_request,
)


def test_validate_test_call_request_rejects_disabled_feature() -> None:
    result = validate_test_call_request(
        valid_request(),
        WorkflowPolicy(
            require_real_calls_feature_flag=True,
            real_calls_enabled=False,
        ),
    )

    assert not result.is_valid
    assert "feature_disabled" in {issue.code for issue in result.errors}


def test_validate_test_call_request_rejects_forbidden_metadata() -> None:
    request = valid_request().model_copy(
        update={"metadata": {"api_key": "nope"}},
    )

    result = validate_test_call_request(request)

    assert not result.is_valid
    assert "forbidden_metadata" in {issue.code for issue in result.errors}


def test_validate_prepared_call_transition_rejects_missing_prepared_call() -> None:
    result = validate_prepared_call_transition(None)

    assert not result.is_valid
    assert "prepared_call_missing" in {issue.code for issue in result.errors}


def test_validate_submission_transition_detects_traceability_mismatch() -> None:
    prepared = valid_prepared_call()
    submission = submission_result_for(prepared).model_copy(
        update={
            "traceability": submission_result_for(prepared).traceability.model_copy(
                update={"preparation_id": "different-prep"},
            ),
        },
    )

    result = validate_submission_transition(prepared, submission)

    assert not result.is_valid
    assert "preparation_submission_traceability_mismatch" in {
        issue.code for issue in result.errors
    }


def test_validate_result_rejects_false_outbound_call_claim_without_call_id() -> None:
    import asyncio

    prepared = valid_prepared_call()
    result = asyncio.run(_start_result(prepared)).model_copy(
        update={
            "provider_capability_state": (
                ProviderCapabilityState.OUTBOUND_CALL_SUBMITTED
            ),
        },
    )

    validation = validate_test_call_start_result(result)

    assert not validation.is_valid
    assert "provider_capability_misrepresented" in {
        issue.code for issue in validation.errors
    }


def test_validate_result_rejects_status_mismatch() -> None:
    import asyncio

    prepared = valid_prepared_call()
    result = asyncio.run(_start_result(prepared)).model_copy(
        update={"status": WorkflowStatus.REJECTED},
    )

    validation = validate_test_call_start_result(result)

    assert not validation.is_valid
    assert "workflow_result_invalid" in {
        issue.code for issue in validation.errors
    }


async def _start_result(prepared):
    clock_values = fixed_clock()
    monotonic_values = fixed_monotonic()
    from test_call_workflow import TestCallCoordinator as WorkflowCoordinator

    return await WorkflowCoordinator(
        call_orchestrator=RecordingOrchestrator(prepared),  # type: ignore[arg-type]
        call_execution_service=RecordingExecutionService(
            submission_result_for(prepared),
        ),
        clock=lambda: next(clock_values),
        monotonic_clock=lambda: next(monotonic_values),
    ).start_test(valid_request())
