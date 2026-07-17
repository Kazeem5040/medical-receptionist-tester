"""Async Vapi HTTP API client.

This component communicates with Vapi only. It does not build scenarios,
contracts, provider configuration, transcripts, recordings, or bug reports.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from call_orchestrator import PreparedCall
from vapi_adapter import VapiAssistantConfiguration

from .errors import (
    VapiAuthenticationError,
    VapiNetworkError,
    VapiRateLimitError,
    VapiResponseValidationError,
    VapiServerError,
    VapiTimeoutError,
)
from .models import (
    VapiAssistantId,
    VapiCreateAssistantRequest,
    VapiCreateAssistantResponse,
    VapiCreateCallRequest,
    VapiCreateCallResponse,
    VapiHttpStatus,
    VapiCallId,
    VapiProviderMetadata,
)
from .policies import DEFAULT_VAPI_CLIENT_POLICY, VapiClientPolicy
from .retry import should_retry_status
from .validation import (
    validate_api_key,
    validate_assistant_payload,
    validate_assistant_response_body,
    validate_call_response_body,
    validate_outbound_call_payload,
)


class VapiApiClient:
    """Async client for Vapi assistant and outbound call creation."""

    def __init__(
        self,
        *,
        api_key: str,
        policy: VapiClientPolicy = DEFAULT_VAPI_CLIENT_POLICY,
        http_client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        validate_api_key(api_key)
        self._api_key = api_key
        self._policy = policy
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=str(policy.base_url),
            timeout=policy.timeout_seconds,
        )
        self._sleep = sleep

    @property
    def policy(self) -> VapiClientPolicy:
        """HTTP policy used by this client."""

        return self._policy

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this instance created it."""

        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> VapiApiClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def create_assistant_from_prepared_call(
        self,
        prepared_call: PreparedCall,
    ) -> VapiCreateAssistantResponse:
        """Create a Vapi assistant from a prepared call artifact."""

        return await self.create_assistant_from_configuration(
            prepared_call.vapi_configuration,
        )

    async def create_assistant_from_configuration(
        self,
        configuration: VapiAssistantConfiguration,
    ) -> VapiCreateAssistantResponse:
        """Create a Vapi assistant from a completed Vapi configuration."""

        payload = configuration.to_vapi_payload()
        request = self.build_create_assistant_request(
            payload=payload,
            configuration_fingerprint=configuration.configuration_fingerprint,
        )
        return await self._send_create_assistant_request(request)

    async def create_outbound_call(
        self,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> VapiCreateCallResponse:
        """Create a Vapi outbound call from an already-built call payload."""

        request = self.build_create_call_request(
            payload=payload,
            idempotency_key=idempotency_key,
        )
        return await self._send_create_call_request(request)

    def build_create_assistant_request(
        self,
        *,
        payload: dict[str, Any],
        configuration_fingerprint: str | None = None,
    ) -> VapiCreateAssistantRequest:
        """Build and validate the HTTP request model without sending it."""

        validate_assistant_payload(payload)
        return VapiCreateAssistantRequest(
            url=self._create_assistant_url(),
            headers=self._headers(),
            json_payload=payload,
            configuration_fingerprint=configuration_fingerprint,
        )

    def build_create_call_request(
        self,
        *,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> VapiCreateCallRequest:
        """Build and validate the Vapi Create Call request without sending it."""

        validate_outbound_call_payload(payload)
        return VapiCreateCallRequest(
            url=self._create_call_url(),
            headers=self._headers(),
            json_payload=payload,
            idempotency_key=idempotency_key,
        )

    async def _send_create_assistant_request(
        self,
        request: VapiCreateAssistantRequest,
    ) -> VapiCreateAssistantResponse:
        response = await self._post_with_retries(request)
        self._raise_for_response_status(response)
        body = self._parse_json_response(response)
        assistant_id = validate_assistant_response_body(body)
        return VapiCreateAssistantResponse(
            assistant_id=VapiAssistantId(value=assistant_id),
            http_status=VapiHttpStatus(
                status_code=response.status_code,
                reason_phrase=response.reason_phrase,
            ),
            provider_metadata=VapiProviderMetadata(
                values=_safe_metadata(body.get("metadata")),
            ),
            raw_response=body,
        )

    async def _send_create_call_request(
        self,
        request: VapiCreateCallRequest,
    ) -> VapiCreateCallResponse:
        response = await self._post_with_retries(request)
        self._raise_for_response_status(response)
        body = self._parse_json_response(response)
        call_id = validate_call_response_body(body)
        return VapiCreateCallResponse(
            call_id=VapiCallId(value=call_id),
            http_status=VapiHttpStatus(
                status_code=response.status_code,
                reason_phrase=response.reason_phrase,
            ),
            provider_metadata=VapiProviderMetadata(
                values=_safe_metadata(body.get("metadata")),
            ),
            raw_response=body,
        )

    async def _post_with_retries(
        self,
        request: VapiCreateAssistantRequest | VapiCreateCallRequest,
    ) -> httpx.Response:
        attempt = 0
        delay = self._policy.backoff_initial_seconds
        while True:
            try:
                response = await self._http_client.post(
                    request.url,
                    headers=request.headers,
                    json=request.json_payload,
                )
            except httpx.TimeoutException as error:
                if attempt >= self._policy.max_retries:
                    raise VapiTimeoutError("Vapi request timed out.") from error
                await self._sleep_for_retry(delay)
            except httpx.TransportError as error:
                if attempt >= self._policy.max_retries:
                    raise VapiNetworkError("Vapi network request failed.") from error
                await self._sleep_for_retry(delay)
            else:
                if not should_retry_status(response.status_code):
                    return response
                if attempt >= self._policy.max_retries:
                    return response
                await self._sleep_for_retry(delay)

            attempt += 1
            delay *= self._policy.backoff_multiplier

    async def _sleep_for_retry(self, delay: float) -> None:
        if delay <= 0:
            return
        if self._sleep is not None:
            await self._sleep(delay)
            return
        await asyncio.sleep(delay)

    def _raise_for_response_status(self, response: httpx.Response) -> None:
        body = self._response_body_or_none(response)
        if response.status_code in {401, 403}:
            raise VapiAuthenticationError(
                "Vapi authentication failed.",
                status_code=response.status_code,
                response_body=body,
            )
        if response.status_code == 429:
            raise VapiRateLimitError(
                "Vapi rate limit exceeded.",
                status_code=response.status_code,
                response_body=body,
            )
        if 500 <= response.status_code <= 599:
            raise VapiServerError(
                "Vapi server error.",
                status_code=response.status_code,
                response_body=body,
            )
        if response.status_code >= 400:
            raise VapiResponseValidationError(
                "Vapi returned an unsuccessful response.",
                status_code=response.status_code,
                response_body=body,
            )

    def _parse_json_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as error:
            raise VapiResponseValidationError(
                "Vapi response was not valid JSON.",
                status_code=response.status_code,
            ) from error

        if not isinstance(body, dict):
            raise VapiResponseValidationError(
                "Vapi response JSON must be an object.",
                status_code=response.status_code,
                response_body=body,
            )
        return body

    def _response_body_or_none(self, response: httpx.Response) -> Any | None:
        try:
            return response.json()
        except ValueError:
            return None

    def _create_assistant_url(self) -> str:
        return self._url_for_path(self._policy.create_assistant_path)

    def _create_call_url(self) -> str:
        return self._url_for_path(self._policy.create_call_path)

    def _url_for_path(self, path: str) -> str:
        base = str(self._policy.base_url).rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": self._policy.user_agent,
        }


def _safe_metadata(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}
