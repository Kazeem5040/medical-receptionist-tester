from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from call_execution import (
    CallSubmissionResult,
    ExecutionStatistics,
    ExecutionStatus,
    ExecutionTraceability,
    ProviderName,
    ProviderResponseMetadata,
    ProviderResponseState,
)
from call_orchestrator import CallOrchestrator, PreparedCall
from tests.call_execution_factories import vapi_success_response
from tests.call_orchestrator_factories import call_policy, call_preparation_request
from tests.vapi_client_factories import prepared_call


def fixed_timestamp(offset_seconds: int = 0) -> datetime:
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC) + timedelta(
        seconds=offset_seconds,
    )


def fixed_clock() -> Iterator[datetime]:
    yield fixed_timestamp(0)
    yield fixed_timestamp(1)


def fixed_monotonic() -> Iterator[float]:
    yield 10.0
    yield 10.250


def valid_request():
    return call_preparation_request()


def valid_prepared_call() -> PreparedCall:
    return prepared_call()


class FakeVapiClient:
    def __init__(self) -> None:
        self.calls: list[PreparedCall] = []

    async def create_assistant_from_prepared_call(
        self,
        prepared: PreparedCall,
    ):
        self.calls.append(prepared)
        return vapi_success_response()


class RecordingOrchestrator:
    def __init__(
        self,
        prepared: PreparedCall | None = None,
        error: Exception | None = None,
    ) -> None:
        self.prepared = prepared or valid_prepared_call()
        self.error = error
        self.prepare_calls: list[object] = []
        self._fingerprinter = CallOrchestrator(policy=call_policy())

    def create_fingerprint(self, value: object) -> str:
        return self._fingerprinter.create_fingerprint(value)

    def prepare_call(self, request: object) -> PreparedCall:
        self.prepare_calls.append(request)
        if self.error is not None:
            raise self.error
        return self.prepared


class RecordingExecutionService:
    def __init__(
        self,
        submission: CallSubmissionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.submission = submission
        self.error = error
        self.execute_calls: list[PreparedCall] = []

    async def execute(self, prepared: PreparedCall) -> CallSubmissionResult:
        self.execute_calls.append(prepared)
        if self.error is not None:
            raise self.error
        return self.submission or submission_result_for(prepared)


def submission_result_for(
    prepared: PreparedCall,
    *,
    execution_status: ExecutionStatus = ExecutionStatus.ACCEPTED,
    provider_call_id: str | None = None,
    provider_resource_id: str = "asst_123",
    result_fingerprint: str = "call_submission:abc",
) -> CallSubmissionResult:
    provider_state = (
        ProviderResponseState.ACCEPTED
        if execution_status == ExecutionStatus.ACCEPTED
        else ProviderResponseState.REJECTED
    )
    return CallSubmissionResult(
        submission_id="submission_123",
        execution_status=execution_status,
        provider_name=ProviderName.VAPI,
        provider_response=ProviderResponseMetadata(
            provider_resource_id=provider_resource_id,
            provider_call_id=provider_call_id,
            provider_status=provider_state.value,
            provider_state=provider_state,
            http_status_code=201,
            values={"source": "unit-test"},
            raw_response={"id": provider_resource_id},
        ),
        submission_timestamp=fixed_timestamp(),
        traceability=ExecutionTraceability(
            preparation_id=prepared.preparation_id,
            idempotency_key=prepared.idempotency_key,
            source_scenario_id=prepared.source_scenario_id,
            source_scenario_version=prepared.source_scenario_version,
            scenario_template_fingerprint=prepared.scenario_template_fingerprint,
            scenario_instance_fingerprint=prepared.scenario_instance_fingerprint or "",
            conversation_contract_fingerprint=(
                prepared.conversation_contract_fingerprint or ""
            ),
            vapi_configuration_fingerprint=(
                prepared.vapi_configuration_fingerprint or ""
            ),
            request_fingerprint=prepared.request_fingerprint,
            scenario_seed=prepared.scenario_seed,
        ),
        statistics=ExecutionStatistics(
            provider_attempt_count=1,
            elapsed_milliseconds=123,
            retries_enabled=True,
            maximum_retries=2,
        ),
        execution_version="1.0",
        execution_policy_version="1.0",
        result_fingerprint=result_fingerprint,
        metadata={"suite": "unit-test"},
    )
