from __future__ import annotations

from copy import deepcopy

import pytest

from call_execution import CallExecutionError, ExecutionStatus
from call_execution.errors import (
    CallExecutionIssue,
    CallExecutionValidationResult,
)
from call_orchestrator import CallOrchestrationError
from call_orchestrator.errors import (
    CallOrchestrationIssue,
    CallOrchestrationValidationResult,
)
from test_call_workflow import (
    ProviderCapabilityState,
)
from test_call_workflow import (
    TestCallCoordinator as WorkflowCoordinator,
)
from test_call_workflow import (
    TestCallWorkflowError as WorkflowError,
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


@pytest.mark.asyncio
async def test_valid_request_prepares_and_submits_successfully() -> None:
    prepared = valid_prepared_call()
    orchestrator = RecordingOrchestrator(prepared)
    execution = RecordingExecutionService(submission_result_for(prepared))

    result = await _coordinator(orchestrator, execution).start_test(valid_request())

    assert result.status == WorkflowStatus.SUBMITTED
    assert result.provider_capability_state == ProviderCapabilityState.ASSISTANT_CREATED
    assert result.prepared_call is prepared
    assert result.submission_result is execution.submission
    assert result.traceability.preparation_id == prepared.preparation_id
    assert result.traceability.submission_id == "submission_123"
    assert result.result_fingerprint.startswith("test_call_workflow:")


@pytest.mark.asyncio
async def test_orchestrator_and_execution_receive_same_prepared_call() -> None:
    prepared = valid_prepared_call()
    orchestrator = RecordingOrchestrator(prepared)
    execution = RecordingExecutionService(submission_result_for(prepared))
    request = valid_request()

    await _coordinator(orchestrator, execution).start_test(request)

    assert orchestrator.prepare_calls == [request]
    assert execution.execute_calls == [prepared]


@pytest.mark.asyncio
async def test_traceability_preserves_fingerprints_across_stages() -> None:
    prepared = valid_prepared_call()

    result = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(submission_result_for(prepared)),
    ).start_test(valid_request())

    assert result.traceability.scenario_template_fingerprint == (
        prepared.scenario_template_fingerprint
    )
    assert result.traceability.scenario_instance_fingerprint == (
        prepared.scenario_instance_fingerprint
    )
    assert result.traceability.conversation_contract_fingerprint == (
        prepared.conversation_contract_fingerprint
    )
    assert result.traceability.vapi_configuration_fingerprint == (
        prepared.vapi_configuration_fingerprint
    )


@pytest.mark.asyncio
async def test_orchestrator_failure_is_translated() -> None:
    orchestrator_error = CallOrchestrationError(
        CallOrchestrationValidationResult.from_issues(
            (
                CallOrchestrationIssue(
                    code="bad_request",
                    message="bad request",
                    path=("request",),
                ),
            ),
        ),
    )

    with pytest.raises(WorkflowError) as error:
        await _coordinator(
            RecordingOrchestrator(error=orchestrator_error),
            RecordingExecutionService(),
        ).start_test(valid_request())

    assert "call_preparation_failed" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_execution_failure_is_translated() -> None:
    execution_error = CallExecutionError(
        CallExecutionValidationResult.from_issues(
            (
                CallExecutionIssue(
                    code="provider_timeout",
                    message="provider timed out",
                    path=("provider",),
                ),
            ),
        ),
    )

    with pytest.raises(WorkflowError) as error:
        await _coordinator(
            RecordingOrchestrator(),
            RecordingExecutionService(error=execution_error),
        ).start_test(valid_request())

    assert "call_submission_failed" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_provider_rejected_submission_returns_rejected_status() -> None:
    prepared = valid_prepared_call()
    submission = submission_result_for(
        prepared,
        execution_status=ExecutionStatus.REJECTED,
    )

    result = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(submission),
    ).start_test(valid_request())

    assert result.status == WorkflowStatus.REJECTED


@pytest.mark.asyncio
async def test_assistant_only_creation_does_not_claim_outbound_call() -> None:
    prepared = valid_prepared_call()

    result = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(submission_result_for(prepared)),
    ).start_test(valid_request())

    assert result.provider_capability_state == ProviderCapabilityState.ASSISTANT_CREATED
    assert result.submission_result.provider_response.provider_call_id is None
    assert "outbound_call_not_yet_started" in {
        warning.code for warning in result.warnings
    }


@pytest.mark.asyncio
async def test_provider_call_id_changes_capability_state() -> None:
    prepared = valid_prepared_call()

    result = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(
            submission_result_for(prepared, provider_call_id="call_123"),
        ),
    ).start_test(valid_request())

    assert result.provider_capability_state == (
        ProviderCapabilityState.OUTBOUND_CALL_ID_AVAILABLE
    )


@pytest.mark.asyncio
async def test_result_contains_no_obvious_secret_or_transcript_metadata() -> None:
    prepared = valid_prepared_call()

    result = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(submission_result_for(prepared)),
    ).start_test(valid_request())
    metadata_dump = str(result.metadata).lower()
    warning_dump = str([warning.model_dump() for warning in result.warnings]).lower()

    assert "api_key" not in metadata_dump
    assert "authorization" not in metadata_dump
    assert "secret" not in metadata_dump
    assert "transcript" not in metadata_dump
    assert "recording" not in metadata_dump
    assert "api_key" not in warning_dump
    assert "authorization" not in warning_dump
    assert "secret" not in warning_dump


@pytest.mark.asyncio
async def test_source_request_prepared_call_and_submission_are_not_mutated() -> None:
    request = valid_request()
    prepared = valid_prepared_call()
    submission = submission_result_for(prepared)
    before_request = deepcopy(request)
    before_prepared = prepared.model_dump(mode="json")
    before_submission = submission.model_dump(mode="json")

    await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(submission),
    ).start_test(request)

    assert request == before_request
    assert prepared.model_dump(mode="json") == before_prepared
    assert submission.model_dump(mode="json") == before_submission


@pytest.mark.asyncio
async def test_changed_submission_data_changes_workflow_fingerprint() -> None:
    prepared = valid_prepared_call()
    first = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(
            submission_result_for(prepared, result_fingerprint="call_submission:one"),
        ),
    ).start_test(valid_request())
    second = await _coordinator(
        RecordingOrchestrator(prepared),
        RecordingExecutionService(
            submission_result_for(prepared, result_fingerprint="call_submission:two"),
        ),
    ).start_test(valid_request())

    assert first.result_fingerprint != second.result_fingerprint


def _coordinator(
    orchestrator: RecordingOrchestrator,
    execution: RecordingExecutionService,
) -> WorkflowCoordinator:
    clock_values = fixed_clock()
    monotonic_values = fixed_monotonic()
    return WorkflowCoordinator(
        call_orchestrator=orchestrator,  # type: ignore[arg-type]
        call_execution_service=execution,
        clock=lambda: next(clock_values),
        monotonic_clock=lambda: next(monotonic_values),
    )
