"""Typed request and response models for the Vapi API client."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .enums import (
    HttpMethod,
    ProviderResourceStatus,
    VapiResponseStatus,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class VapiClientModel(BaseModel):
    """Base class for immutable Vapi client models."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class VapiAssistantId(VapiClientModel):
    """Strongly typed Vapi assistant identifier."""

    value: NonEmptyString


class VapiCallId(VapiClientModel):
    """Strongly typed Vapi call identifier for future client methods."""

    value: NonEmptyString


class VapiHttpStatus(VapiClientModel):
    """HTTP status details returned by Vapi."""

    status_code: int = Field(ge=100, le=599)
    reason_phrase: str | None = None


class VapiProviderMetadata(VapiClientModel):
    """Safe provider metadata returned or associated with a response."""

    values: dict[str, str] = Field(default_factory=dict)


class VapiCreateAssistantRequest(VapiClientModel):
    """Prepared Vapi assistant creation HTTP request."""

    method: HttpMethod = HttpMethod.POST
    url: NonEmptyString
    headers: dict[str, str]
    json_payload: dict[str, Any]
    configuration_fingerprint: NonEmptyString | None = None


class VapiCreateCallRequest(VapiClientModel):
    """Prepared Vapi outbound call creation HTTP request."""

    method: HttpMethod = HttpMethod.POST
    url: NonEmptyString
    headers: dict[str, str]
    json_payload: dict[str, Any]
    idempotency_key: NonEmptyString | None = None


class VapiCreateAssistantResponse(VapiClientModel):
    """Typed response for successful Vapi assistant creation."""

    assistant_id: VapiAssistantId
    response_status: VapiResponseStatus = VapiResponseStatus.SUCCESS
    provider_status: ProviderResourceStatus = ProviderResourceStatus.CREATED
    http_status: VapiHttpStatus
    provider_metadata: VapiProviderMetadata = Field(
        default_factory=VapiProviderMetadata,
    )
    raw_response: dict[str, Any]


class VapiCreateCallResponse(VapiClientModel):
    """Typed response for successful Vapi outbound call creation."""

    call_id: VapiCallId
    response_status: VapiResponseStatus = VapiResponseStatus.SUCCESS
    provider_status: ProviderResourceStatus = ProviderResourceStatus.CREATED
    http_status: VapiHttpStatus
    provider_metadata: VapiProviderMetadata = Field(
        default_factory=VapiProviderMetadata,
    )
    raw_response: dict[str, Any]
