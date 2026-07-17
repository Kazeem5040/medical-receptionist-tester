"""Service for initiating real outbound phone calls through Vapi."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Protocol

from call_execution import ProviderName
from vapi_client import (
    VapiClientError,
    VapiCreateCallResponse,
)

from .canonicalization import stable_fingerprint
from .enums import OutboundCallStatus
from .errors import (
    OutboundCallCreationError,
    OutboundCallCreationIssue,
    OutboundCallCreationValidationResult,
)
from .models import (
    OutboundCallCreationRequest,
    OutboundCallProviderMetadata,
    OutboundCallStartResult,
    OutboundCallStatistics,
    OutboundCallTraceability,
)
from .policies import (
    DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
    OutboundCallCreationPolicy,
)
from .validation import (
    normalize_provider_call_state,
    validate_outbound_call_creation_request,
    validate_outbound_call_start_result,
    validate_provider_call_response,
)


class VapiOutboundCallClient(Protocol):
    """Minimal Vapi behavior required by outbound call creation."""

    async def create_outbound_call(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> VapiCreateCallResponse:
        """Create a real outbound call with Vapi."""


class OutboundCallCreator:
    """Create real outbound calls from accepted prepared-call submissions."""

    def __init__(
        self,
        *,
        vapi_client: VapiOutboundCallClient,
        policy: OutboundCallCreationPolicy = DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._vapi_client = vapi_client
        self._policy = policy
        self._clock = clock or _utc_now
        self._monotonic_clock = monotonic_clock or perf_counter

    @property
    def policy(self) -> OutboundCallCreationPolicy:
        """Outbound call creation policy used by this creator."""

        return self._policy

    async def create_call(
        self,
        request: OutboundCallCreationRequest,
    ) -> OutboundCallStartResult:
        """Initiate one real outbound provider call and return a typed receipt."""

        validate_outbound_call_creation_request(
            request,
            self._policy,
        ).raise_if_invalid()

        requested_at = self._clock()
        started_at = self._monotonic_clock()
        payload = self.build_vapi_call_payload(request)

        try:
            provider_response = await self._vapi_client.create_outbound_call(
                payload,
                idempotency_key=request.prepared_call.idempotency_key,
            )
        except VapiClientError as error:
            raise _provider_error(error) from error

        elapsed_ms = max(
            0,
            int((self._monotonic_clock() - started_at) * 1000),
        )

        validate_provider_call_response(
            provider_response,
            self._policy,
        ).raise_if_invalid()

        result = self._build_result(
            request=request,
            provider_response=provider_response,
            requested_at=requested_at,
            elapsed_milliseconds=elapsed_ms,
        )
        validate_outbound_call_start_result(result, self._policy).raise_if_invalid()
        return result

    def build_vapi_call_payload(
        self,
        request: OutboundCallCreationRequest,
    ) -> dict[str, Any]:
        """Build the Vapi /call payload without sending it."""

        assistant_id = (
            request.call_submission_result.provider_response.provider_resource_id
        )
        payload: dict[str, Any] = {
            "assistantId": assistant_id,
            "phoneNumberId": request.phone_number_id,
            "customer": {
                "number": request.prepared_call.destination.value,
            },
            "metadata": _metadata_for_provider(request),
        }
        if request.server_url is not None:
            payload["serverUrl"] = request.server_url
        return payload

    def _build_result(
        self,
        *,
        request: OutboundCallCreationRequest,
        provider_response: VapiCreateCallResponse,
        requested_at: datetime,
        elapsed_milliseconds: int,
    ) -> OutboundCallStartResult:
        prepared_call = request.prepared_call
        submission = request.call_submission_result
        provider_state = normalize_provider_call_state(provider_response)
        provider_assistant_id = submission.provider_response.provider_resource_id
        traceability = OutboundCallTraceability(
            preparation_id=prepared_call.preparation_id,
            submission_id=submission.submission_id,
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
            prepared_call_request_fingerprint=prepared_call.request_fingerprint,
            call_submission_fingerprint=submission.result_fingerprint,
            provider_assistant_id=provider_assistant_id,
            scenario_seed=prepared_call.scenario_seed,
        )
        provider_metadata = OutboundCallProviderMetadata(
            provider_call_id=provider_response.call_id.value,
            provider_assistant_id=provider_assistant_id,
            phone_number_id=request.phone_number_id,
            provider_status=provider_response.provider_status.value,
            provider_state=provider_state,
            http_status_code=provider_response.http_status.status_code,
            http_reason_phrase=provider_response.http_status.reason_phrase,
            monitor_listen_url=_monitor_url(
                provider_response.raw_response,
                "listenUrl",
            ),
            monitor_control_url=_monitor_url(
                provider_response.raw_response,
                "controlUrl",
            ),
            values=provider_response.provider_metadata.values,
            raw_response=provider_response.raw_response,
        )
        statistics = OutboundCallStatistics(
            provider_attempt_count=1,
            elapsed_milliseconds=elapsed_milliseconds,
        )
        metadata = {
            **prepared_call.metadata,
            **submission.metadata,
            **request.metadata,
        }
        status = OutboundCallStatus.ACCEPTED
        fingerprint_source = {
            "provider_name": ProviderName.VAPI.value,
            "provider_response": provider_metadata,
            "requested_at": requested_at,
            "traceability": traceability,
            "statistics": statistics,
            "creation_version": self._policy.creation_version,
            "creation_policy_version": self._policy.policy_version,
            "metadata": metadata,
        }
        result_fingerprint = stable_fingerprint(
            fingerprint_source,
            prefix="outbound_call",
        )
        outbound_call_id = stable_fingerprint(
            {
                "preparation_id": prepared_call.preparation_id,
                "submission_id": submission.submission_id,
                "provider_call_id": provider_response.call_id.value,
                "result_fingerprint": result_fingerprint,
            },
            prefix="outbound-call",
        )

        return OutboundCallStartResult(
            outbound_call_id=outbound_call_id,
            status=status,
            provider_name=ProviderName.VAPI,
            provider_response=provider_metadata,
            requested_at=requested_at,
            traceability=traceability,
            statistics=statistics,
            creation_version=self._policy.creation_version,
            creation_policy_version=self._policy.policy_version,
            result_fingerprint=result_fingerprint,
            metadata=metadata,
        )


def _metadata_for_provider(
    request: OutboundCallCreationRequest,
) -> dict[str, str]:
    prepared_call = request.prepared_call
    submission = request.call_submission_result
    metadata = {
        "preparation_id": prepared_call.preparation_id,
        "submission_id": submission.submission_id,
        "source_scenario_id": prepared_call.source_scenario_id,
        "source_scenario_version": str(prepared_call.source_scenario_version),
        "scenario_template_fingerprint": (
            prepared_call.scenario_template_fingerprint
        ),
        "scenario_instance_fingerprint": (
            prepared_call.scenario_instance_fingerprint or ""
        ),
        "conversation_contract_fingerprint": (
            prepared_call.conversation_contract_fingerprint or ""
        ),
        "vapi_configuration_fingerprint": (
            prepared_call.vapi_configuration_fingerprint or ""
        ),
        "call_submission_fingerprint": submission.result_fingerprint,
        "scenario_seed": prepared_call.scenario_seed,
    }
    metadata.update(request.metadata)
    return metadata


def _monitor_url(raw_response: dict[str, Any], key: str) -> str | None:
    monitor = raw_response.get("monitor")
    if not isinstance(monitor, dict):
        return None
    value = monitor.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _provider_error(error: VapiClientError) -> OutboundCallCreationError:
    code = "provider_call_request_failed"
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

    return OutboundCallCreationError(
        OutboundCallCreationValidationResult.from_issues(
            (
                OutboundCallCreationIssue(
                    code=code,
                    message=str(error),
                    path=("provider",),
                ),
            ),
        ),
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
