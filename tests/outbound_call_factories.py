from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from call_execution import CallSubmissionResult
from call_orchestrator import CallOrchestrator, PreparedCall
from outbound_calls import (
    OutboundCallCreationPolicy,
    OutboundCallCreationRequest,
    OutboundCallCreator,
)
from tests.call_execution_factories import FakeVapiClient, execution_service
from tests.call_orchestrator_factories import (
    call_policy,
    call_preparation_request,
    phone_destination,
)
from vapi_client import (
    VapiCallId,
    VapiCreateCallResponse,
    VapiHttpStatus,
    VapiProviderMetadata,
)


def fixed_timestamp() -> datetime:
    return datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)


def fixed_monotonic_pair() -> Iterator[float]:
    yield 20.0
    yield 20.045


def outbound_policy() -> OutboundCallCreationPolicy:
    return OutboundCallCreationPolicy(
        real_calls_enabled=True,
        allowed_destination_phone_numbers=("+18054398008",),
    )


def valid_prepared_call() -> PreparedCall:
    request = call_preparation_request().model_copy(
        update={"destination": phone_destination()},
    )
    return CallOrchestrator(policy=call_policy()).prepare_call(request)


async def valid_submission_result(
    prepared_call: PreparedCall | None = None,
) -> CallSubmissionResult:
    prepared = prepared_call or valid_prepared_call()
    return await execution_service(FakeVapiClient()).execute(prepared)


async def valid_creation_request(
    *,
    metadata: dict[str, str] | None = None,
) -> OutboundCallCreationRequest:
    prepared = valid_prepared_call()
    submission = await valid_submission_result(prepared)
    return OutboundCallCreationRequest(
        prepared_call=prepared,
        call_submission_result=submission,
        phone_number_id="vapi-phone-number-123",
        server_url="https://example.test/vapi/webhook",
        metadata=metadata or {"workflow": "unit-test"},
    )


class FakeVapiOutboundCallClient:
    def __init__(
        self,
        response: VapiCreateCallResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or vapi_call_success_response()
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.idempotency_keys: list[str | None] = []

    async def create_outbound_call(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> VapiCreateCallResponse:
        self.calls.append(payload)
        self.idempotency_keys.append(idempotency_key)
        if self.error is not None:
            raise self.error
        return self.response


def creator(client: FakeVapiOutboundCallClient) -> OutboundCallCreator:
    monotonic_values = fixed_monotonic_pair()
    return OutboundCallCreator(
        vapi_client=client,
        policy=outbound_policy(),
        clock=fixed_timestamp,
        monotonic_clock=lambda: next(monotonic_values),
    )


def vapi_call_success_response(
    *,
    call_id: str = "call_123",
    status: str = "queued",
) -> VapiCreateCallResponse:
    return VapiCreateCallResponse(
        call_id=VapiCallId(value=call_id),
        http_status=VapiHttpStatus(status_code=201, reason_phrase="Created"),
        provider_metadata=VapiProviderMetadata(values={"source": "unit-test"}),
        raw_response={
            "id": call_id,
            "status": status,
            "metadata": {"source": "unit-test"},
            "monitor": {
                "listenUrl": "wss://example.test/listen",
                "controlUrl": "https://example.test/control",
            },
        },
    )
