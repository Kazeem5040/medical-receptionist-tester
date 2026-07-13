from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from call_execution import CallExecutionService
from call_orchestrator import PreparedCall
from tests.vapi_client_factories import prepared_call
from vapi_client import (
    VapiAssistantId,
    VapiCreateAssistantResponse,
    VapiHttpStatus,
    VapiProviderMetadata,
)


def fixed_timestamp() -> datetime:
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def fixed_monotonic_pair() -> Iterator[float]:
    yield 10.0
    yield 10.123


def valid_prepared_call() -> PreparedCall:
    return prepared_call()


class FakeVapiClient:
    def __init__(
        self,
        response: VapiCreateAssistantResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or vapi_success_response()
        self.error = error
        self.calls: list[PreparedCall] = []

    async def create_assistant_from_prepared_call(
        self,
        prepared_call: PreparedCall,
    ) -> VapiCreateAssistantResponse:
        self.calls.append(prepared_call)
        if self.error is not None:
            raise self.error
        return self.response


def execution_service(client: FakeVapiClient) -> CallExecutionService:
    monotonic_values = fixed_monotonic_pair()
    return CallExecutionService(
        vapi_client=client,
        clock=fixed_timestamp,
        monotonic_clock=lambda: next(monotonic_values),
    )


def vapi_success_response(
    *,
    assistant_id: str = "asst_123",
) -> VapiCreateAssistantResponse:
    return VapiCreateAssistantResponse(
        assistant_id=VapiAssistantId(value=assistant_id),
        http_status=VapiHttpStatus(status_code=201, reason_phrase="Created"),
        provider_metadata=VapiProviderMetadata(values={"source": "unit-test"}),
        raw_response={"id": assistant_id, "metadata": {"source": "unit-test"}},
    )
