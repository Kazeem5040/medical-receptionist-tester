"""Top-level coordinator for starting one AI receptionist test."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol

from call_execution import CallExecutionError, CallSubmissionResult, ExecutionStatus
from call_orchestrator import (
    CallOrchestrationError,
    CallOrchestrator,
    CallPreparationRequest,
    PreparedCall,
)

from .canonicalization import stable_fingerprint
from .enums import ProviderCapabilityState, TestCallWorkflowStatus
from .errors import (
    TestCallWorkflowError,
    TestCallWorkflowIssue,
    TestCallWorkflowValidationResult,
)
from .models import (
    TestCallStartResult,
    TestCallWorkflowStatistics,
    TestCallWorkflowTraceability,
    TestCallWorkflowWarning,
)
from .policies import (
    DEFAULT_TEST_CALL_WORKFLOW_POLICY,
    TestCallWorkflowPolicy,
)
from .validation import (
    validate_prepared_call_transition,
    validate_submission_transition,
    validate_test_call_request,
    validate_test_call_start_result,
)


class CallExecutionServiceLike(Protocol):
    """Minimal execution behavior required by the workflow coordinator."""

    async def execute(self, prepared_call: PreparedCall) -> CallSubmissionResult:
        """Submit a prepared call and return the immediate submission result."""


class TestCallCoordinator:
    """Coordinate the immediate command side of starting one test call."""

    def __init__(
        self,
        *,
        call_orchestrator: CallOrchestrator,
        call_execution_service: CallExecutionServiceLike,
        policy: TestCallWorkflowPolicy = DEFAULT_TEST_CALL_WORKFLOW_POLICY,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._call_orchestrator = call_orchestrator
        self._call_execution_service = call_execution_service
        self._policy = policy
        self._clock = clock or _utc_now
        self._monotonic_clock = monotonic_clock or perf_counter

    @property
    def policy(self) -> TestCallWorkflowPolicy:
        """Workflow policy used by this coordinator."""

        return self._policy

    async def start_test(
        self,
        request: CallPreparationRequest,
    ) -> TestCallStartResult:
        """Prepare and submit one test-call workflow without waiting for completion."""

        validate_test_call_request(request, self._policy).raise_if_invalid()

        started_at = self._clock()
        monotonic_started_at = self._monotonic_clock()
        request_fingerprint = self._call_orchestrator.create_fingerprint(request)

        try:
            prepared_call = self._call_orchestrator.prepare_call(request)
        except CallOrchestrationError as error:
            raise _workflow_error(
                code="call_preparation_failed",
                message=str(error),
                path=("prepared_call",),
            ) from error

        validate_prepared_call_transition(
            prepared_call,
            self._policy,
        ).raise_if_invalid()

        try:
            submission_result = await self._execute_prepared_call(prepared_call)
        except CallExecutionError as error:
            raise _workflow_error(
                code="call_submission_failed",
                message=str(error),
                path=("submission_result",),
            ) from error

        validate_submission_transition(
            prepared_call,
            submission_result,
            self._policy,
        ).raise_if_invalid()

        completed_at = self._clock()
        elapsed_ms = max(
            0,
            int((self._monotonic_clock() - monotonic_started_at) * 1000),
        )

        result = self._build_result(
            request_fingerprint=request_fingerprint,
            prepared_call=prepared_call,
            submission_result=submission_result,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_milliseconds=elapsed_ms,
        )
        validate_test_call_start_result(result, self._policy).raise_if_invalid()
        return result

    async def _execute_prepared_call(
        self,
        prepared_call: PreparedCall,
    ) -> CallSubmissionResult:
        result = await self._call_execution_service.execute(prepared_call)
        if not isinstance(result, CallSubmissionResult):
            raise _workflow_error(
                code="call_submission_failed",
                message="CallExecutionService returned an invalid result type.",
                path=("submission_result",),
            )
        return result

    def _build_result(
        self,
        *,
        request_fingerprint: str,
        prepared_call: PreparedCall,
        submission_result: CallSubmissionResult,
        started_at: datetime,
        completed_at: datetime,
        elapsed_milliseconds: int,
    ) -> TestCallStartResult:
        workflow_id = _derive_workflow_id(
            request_fingerprint=request_fingerprint,
            preparation_id=prepared_call.preparation_id,
            submission_id=submission_result.submission_id,
        )
        capability_state = _provider_capability_state(submission_result)
        status = _workflow_status(submission_result)
        traceability = TestCallWorkflowTraceability(
            workflow_id=workflow_id,
            request_fingerprint=request_fingerprint,
            preparation_id=prepared_call.preparation_id,
            submission_id=submission_result.submission_id,
            idempotency_key=prepared_call.idempotency_key,
            source_scenario_id=prepared_call.source_scenario_id,
            source_scenario_version=prepared_call.source_scenario_version,
            scenario_template_fingerprint=(
                prepared_call.scenario_template_fingerprint
            ),
            scenario_instance_fingerprint=(
                prepared_call.scenario_instance_fingerprint or ""
            ),
            conversation_contract_fingerprint=(
                prepared_call.conversation_contract_fingerprint or ""
            ),
            vapi_configuration_fingerprint=(
                prepared_call.vapi_configuration_fingerprint or ""
            ),
            submission_result_fingerprint=submission_result.result_fingerprint,
            scenario_seed=prepared_call.scenario_seed,
        )
        statistics = TestCallWorkflowStatistics(
            workflow_started_at=started_at,
            workflow_completed_at=completed_at,
            elapsed_milliseconds=elapsed_milliseconds,
            preparation_completed=True,
            provider_submission_completed=True,
        )
        warnings = _workflow_warnings(capability_state, submission_result)
        metadata = dict(prepared_call.metadata)
        fingerprint_source = {
            "workflow_id": workflow_id,
            "request_fingerprint": request_fingerprint,
            "preparation_id": prepared_call.preparation_id,
            "submission_id": submission_result.submission_id,
            "submission_result_fingerprint": submission_result.result_fingerprint,
            "status": status,
            "provider_capability_state": capability_state,
            "workflow_version": self._policy.workflow_version,
            "workflow_policy_version": self._policy.policy_version,
            "statistics": statistics,
            "warnings": warnings,
            "metadata": metadata,
        }
        result_fingerprint = stable_fingerprint(
            fingerprint_source,
            prefix="test_call_workflow",
        )

        return TestCallStartResult(
            workflow_id=workflow_id,
            status=status,
            provider_capability_state=capability_state,
            prepared_call=prepared_call,
            submission_result=submission_result,
            traceability=traceability,
            statistics=statistics,
            workflow_version=self._policy.workflow_version,
            workflow_policy_version=self._policy.policy_version,
            result_fingerprint=result_fingerprint,
            warnings=warnings,
            metadata=metadata,
        )


def _provider_capability_state(
    submission_result: CallSubmissionResult,
) -> ProviderCapabilityState:
    provider_response = submission_result.provider_response
    if provider_response.provider_call_id is not None:
        return ProviderCapabilityState.OUTBOUND_CALL_ID_AVAILABLE

    if provider_response.provider_resource_id.strip():
        return ProviderCapabilityState.ASSISTANT_CREATED

    return ProviderCapabilityState.UNKNOWN


def _workflow_status(
    submission_result: CallSubmissionResult,
) -> TestCallWorkflowStatus:
    if submission_result.execution_status == ExecutionStatus.ACCEPTED:
        return TestCallWorkflowStatus.SUBMITTED
    if submission_result.execution_status == ExecutionStatus.REJECTED:
        return TestCallWorkflowStatus.REJECTED
    return TestCallWorkflowStatus.FAILED


def _workflow_warnings(
    capability_state: ProviderCapabilityState,
    submission_result: CallSubmissionResult,
) -> tuple[TestCallWorkflowWarning, ...]:
    warnings: list[TestCallWorkflowWarning] = [
        TestCallWorkflowWarning(
            code=warning.code,
            message=warning.message,
            path=warning.path,
        )
        for warning in submission_result.warnings
    ]

    if capability_state == ProviderCapabilityState.ASSISTANT_CREATED:
        warnings.append(
            TestCallWorkflowWarning(
                code="outbound_call_not_yet_started",
                message=(
                    "Current execution created or submitted a provider assistant "
                    "resource, but did not return a provider outbound call ID."
                ),
                path=("provider_capability_state",),
            ),
        )

    return tuple(warnings)


def _derive_workflow_id(
    *,
    request_fingerprint: str,
    preparation_id: str,
    submission_id: str,
) -> str:
    digest = stable_fingerprint(
        {
            "request_fingerprint": request_fingerprint,
            "preparation_id": preparation_id,
            "submission_id": submission_id,
        },
    ).split(":", maxsplit=1)[1]
    return f"test-call-workflow-{digest[:16]}"


def _workflow_error(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
) -> TestCallWorkflowError:
    return TestCallWorkflowError(
        TestCallWorkflowValidationResult.from_issues(
            (
                TestCallWorkflowIssue(
                    code=code,
                    message=message,
                    path=path,
                ),
            ),
        ),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
