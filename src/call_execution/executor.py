"""Primary service for submitting prepared calls through Vapi."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol

from call_orchestrator import PreparedCall
from vapi_client import (
    VapiClientError,
    VapiCreateAssistantResponse,
)

from .canonicalization import stable_fingerprint
from .enums import ExecutionStatus, ProviderName
from .errors import (
    CallExecutionError,
    CallExecutionIssue,
    CallExecutionValidationResult,
)
from .models import (
    CallSubmissionResult,
    ExecutionStatistics,
    ExecutionTraceability,
    ExecutionWarning,
    ProviderResponseMetadata,
)
from .policies import DEFAULT_CALL_EXECUTION_POLICY, CallExecutionPolicy
from .validation import (
    normalize_provider_state,
    validate_call_submission_result,
    validate_prepared_call_for_execution,
    validate_provider_response,
)


class VapiPreparedCallClient(Protocol):
    """Minimal Vapi client behavior required by call execution."""

    async def create_assistant_from_prepared_call(
        self,
        prepared_call: PreparedCall,
    ) -> VapiCreateAssistantResponse:
        """Submit the prepared call's Vapi configuration to Vapi."""


class CallExecutionService:
    """Submit prepared calls using the existing Vapi API client."""

    def __init__(
        self,
        *,
        vapi_client: VapiPreparedCallClient,
        policy: CallExecutionPolicy = DEFAULT_CALL_EXECUTION_POLICY,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._vapi_client = vapi_client
        self._policy = policy
        self._clock = clock or _utc_now
        self._monotonic_clock = monotonic_clock or perf_counter

    @property
    def policy(self) -> CallExecutionPolicy:
        """Execution policy used by this service."""

        return self._policy

    async def execute(self, prepared_call: PreparedCall) -> CallSubmissionResult:
        """Submit a prepared call to Vapi and return a typed submission result."""

        validate_prepared_call_for_execution(
            prepared_call,
            self._policy,
        ).raise_if_invalid()

        # Extracting the payload here keeps this component honest about the
        # boundary it owns, while HTTP serialization stays inside VapiApiClient.
        prepared_call.provider_payload()

        started_at = self._monotonic_clock()
        submitted_at = self._clock()
        try:
            provider_response = (
                await self._vapi_client.create_assistant_from_prepared_call(
                    prepared_call,
                )
            )
        except VapiClientError as error:
            raise _provider_error(error) from error

        elapsed_ms = max(
            0,
            int((self._monotonic_clock() - started_at) * 1000),
        )

        validate_provider_response(provider_response).raise_if_invalid()
        result = self._build_result(
            prepared_call=prepared_call,
            provider_response=provider_response,
            submitted_at=submitted_at,
            elapsed_milliseconds=elapsed_ms,
        )
        validate_call_submission_result(result, self._policy).raise_if_invalid()
        return result

    def _build_result(
        self,
        *,
        prepared_call: PreparedCall,
        provider_response: VapiCreateAssistantResponse,
        submitted_at: datetime,
        elapsed_milliseconds: int,
    ) -> CallSubmissionResult:
        provider_state = normalize_provider_state(provider_response)
        traceability = ExecutionTraceability(
            preparation_id=prepared_call.preparation_id,
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
            request_fingerprint=prepared_call.request_fingerprint,
            scenario_seed=prepared_call.scenario_seed,
        )
        provider_metadata = ProviderResponseMetadata(
            provider_resource_id=provider_response.assistant_id.value,
            provider_call_id=None,
            provider_status=provider_response.provider_status.value,
            provider_state=provider_state,
            http_status_code=provider_response.http_status.status_code,
            http_reason_phrase=provider_response.http_status.reason_phrase,
            values=provider_response.provider_metadata.values,
            raw_response=provider_response.raw_response,
        )
        statistics = ExecutionStatistics(
            provider_attempt_count=1,
            elapsed_milliseconds=elapsed_milliseconds,
            retries_enabled=self._policy.retries_enabled,
            maximum_retries=self._policy.maximum_retries,
        )
        warnings = (
            ExecutionWarning(
                code="provider_call_id_unavailable",
                message=(
                    "Current Vapi client response exposes a provider resource ID, "
                    "not a final outbound call ID."
                ),
                path=("provider_response", "provider_call_id"),
            ),
        )

        fingerprint_source = {
            "provider_name": ProviderName.VAPI.value,
            "provider_response": provider_metadata,
            "submission_timestamp": submitted_at,
            "traceability": traceability,
            "statistics": statistics,
            "execution_version": self._policy.execution_version,
            "execution_policy_version": self._policy.policy_version,
            "warnings": warnings,
            "metadata": prepared_call.metadata,
        }
        result_fingerprint = stable_fingerprint(
            fingerprint_source,
            prefix="call_submission",
        )
        submission_id = stable_fingerprint(
            {
                "preparation_id": prepared_call.preparation_id,
                "provider_resource_id": provider_response.assistant_id.value,
                "result_fingerprint": result_fingerprint,
            },
            prefix="submission",
        )

        execution_status = (
            ExecutionStatus.ACCEPTED
            if provider_state in self._policy.acceptable_provider_states
            else ExecutionStatus.REJECTED
        )

        return CallSubmissionResult(
            submission_id=submission_id,
            execution_status=execution_status,
            provider_name=ProviderName.VAPI,
            provider_response=provider_metadata,
            submission_timestamp=submitted_at,
            traceability=traceability,
            statistics=statistics,
            execution_version=self._policy.execution_version,
            execution_policy_version=self._policy.policy_version,
            result_fingerprint=result_fingerprint,
            warnings=warnings,
            metadata=dict(prepared_call.metadata),
        )


def _provider_error(error: VapiClientError) -> CallExecutionError:
    code = "provider_request_failed"
    if type(error).__name__ == "VapiTimeoutError":
        code = "provider_timeout"
    elif type(error).__name__ == "VapiRateLimitError":
        code = "provider_rate_limited"
    elif type(error).__name__ == "VapiAuthenticationError":
        code = "provider_authentication_failed"
    elif type(error).__name__ == "VapiServerError":
        code = "provider_server_error"
    elif type(error).__name__ == "VapiNetworkError":
        code = "provider_network_error"

    return CallExecutionError(
        CallExecutionValidationResult.from_issues(
            (
                CallExecutionIssue(
                    code=code,
                    message=str(error),
                    path=("provider",),
                ),
            ),
        ),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
