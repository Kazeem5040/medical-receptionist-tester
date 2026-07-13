from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.vapi_client_factories import prepared_call
from vapi_client import (
    VapiApiClient,
    VapiAuthenticationError,
    VapiClientPolicy,
    VapiNetworkError,
    VapiRateLimitError,
    VapiResponseValidationError,
    VapiSerializationError,
    VapiServerError,
    VapiTimeoutError,
)


@pytest.mark.asyncio
async def test_successful_assistant_creation_from_prepared_call() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(
            201,
            json={
                "id": "asst_123",
                "metadata": {"source": "unit-test"},
            },
        )

    async with _client(handler) as client:
        response = await client.create_assistant_from_prepared_call(prepared_call())

    assert response.assistant_id.value == "asst_123"
    assert response.http_status.status_code == 201
    assert response.provider_metadata.values == {"source": "unit-test"}
    assert len(seen_requests) == 1


@pytest.mark.asyncio
async def test_correct_headers_endpoint_and_serialization() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return httpx.Response(200, json={"id": "asst_123"})

    async with _client(handler, api_key="test-key") as client:
        await client.create_assistant_from_configuration(
            prepared_call().vapi_configuration,
        )

    request = seen_requests[0]
    payload = _json_body(request)

    assert request.method == "POST"
    assert str(request.url) == "https://api.vapi.ai/assistant"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["User-Agent"] == "ai-receptionist-tester/0.1"
    assert payload["model"]["provider"] == "openai"
    assert payload["voice"]["provider"] == "openai"


@pytest.mark.asyncio
async def test_authentication_failure_raises_authentication_error() -> None:
    async with _client(
        lambda _request: httpx.Response(401, json={"error": "bad"}),
    ) as client:
        with pytest.raises(VapiAuthenticationError):
            await client.create_assistant_from_prepared_call(prepared_call())


@pytest.mark.asyncio
async def test_timeout_raises_timeout_error_after_retries() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timeout")

    async with _client(handler, max_retries=1) as client:
        with pytest.raises(VapiTimeoutError):
            await client.create_assistant_from_prepared_call(prepared_call())

    assert attempts == 2


@pytest.mark.asyncio
async def test_network_error_raises_network_error_after_retries() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("network")

    async with _client(handler, max_retries=1) as client:
        with pytest.raises(VapiNetworkError):
            await client.create_assistant_from_prepared_call(prepared_call())

    assert attempts == 2


@pytest.mark.asyncio
async def test_rate_limit_retries_then_raises_rate_limit_error() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, json={"error": "rate limited"})

    async with _client(handler, max_retries=1) as client:
        with pytest.raises(VapiRateLimitError):
            await client.create_assistant_from_prepared_call(prepared_call())

    assert attempts == 2


@pytest.mark.asyncio
async def test_server_error_retries_then_succeeds() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(200, json={"id": "asst_123"})

    async with _client(handler, max_retries=1) as client:
        response = await client.create_assistant_from_prepared_call(prepared_call())

    assert response.assistant_id.value == "asst_123"
    assert attempts == 2


@pytest.mark.asyncio
async def test_server_error_after_retries_raises_server_error() -> None:
    async with _client(
        lambda _request: httpx.Response(503, json={"error": "down"}),
        max_retries=1,
    ) as client:
        with pytest.raises(VapiServerError):
            await client.create_assistant_from_prepared_call(prepared_call())


@pytest.mark.asyncio
async def test_no_retry_on_permanent_client_error() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"error": "bad request"})

    async with _client(handler, max_retries=3) as client:
        with pytest.raises(VapiResponseValidationError):
            await client.create_assistant_from_prepared_call(prepared_call())

    assert attempts == 1


def test_invalid_payload_is_rejected_before_request() -> None:
    with pytest.raises(VapiSerializationError):
        VapiApiClient(api_key="test-key").build_create_assistant_request(
            payload={"name": "missing-model-and-voice"},
        )


@pytest.mark.asyncio
async def test_invalid_response_missing_id_is_rejected() -> None:
    async with _client(
        lambda _request: httpx.Response(200, json={"name": "no-id"}),
    ) as client:
        with pytest.raises(VapiResponseValidationError):
            await client.create_assistant_from_prepared_call(prepared_call())


def test_missing_api_key_is_rejected() -> None:
    with pytest.raises(VapiAuthenticationError):
        VapiApiClient(api_key=" ")


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str = "test-key",
    max_retries: int = 0,
) -> VapiApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return VapiApiClient(
        api_key=api_key,
        policy=VapiClientPolicy(
            max_retries=max_retries,
            backoff_initial_seconds=0,
        ),
        http_client=http_client,
        sleep=_no_sleep,
    )


async def _no_sleep(_delay: float) -> None:
    return None


def _json_body(request: httpx.Request) -> dict[str, Any]:
    import json

    body = json.loads(request.content.decode("utf-8"))
    assert isinstance(body, dict)
    return body
