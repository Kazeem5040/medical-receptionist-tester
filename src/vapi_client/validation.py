"""Validation helpers for Vapi client requests and responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import VapiClientValidationSeverity
from .errors import (
    VapiAuthenticationError,
    VapiResponseValidationError,
    VapiSerializationError,
)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "apiKey",
        "api_key",
        "authorization",
        "secret",
        "token",
        "credentials",
        "credentialIds",
    },
)


class VapiClientValidationIssue(BaseModel):
    """Structured validation issue for client input/output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    path: tuple[str | int, ...] = Field(default_factory=tuple)
    severity: VapiClientValidationSeverity = VapiClientValidationSeverity.ERROR


def validate_api_key(api_key: str) -> None:
    """Validate injected API key exists without inspecting secret contents."""

    if not api_key.strip():
        raise VapiAuthenticationError("Vapi API key must be provided.")


def validate_assistant_payload(payload: Mapping[str, Any]) -> None:
    """Validate minimum CreateAssistantDTO payload requirements."""

    required_keys = ("name", "model", "voice", "metadata")
    missing = [key for key in required_keys if key not in payload]
    if missing:
        raise VapiSerializationError(
            f"Vapi assistant payload is missing required keys: {missing}."
        )

    model = payload.get("model")
    if not isinstance(model, dict) or "provider" not in model or "model" not in model:
        raise VapiSerializationError("Vapi assistant payload has invalid model.")

    voice = payload.get("voice")
    if not isinstance(voice, dict) or "provider" not in voice:
        raise VapiSerializationError("Vapi assistant payload has invalid voice.")

    forbidden = _find_forbidden_keys(payload)
    if forbidden:
        raise VapiSerializationError(
            f"Vapi assistant payload contains forbidden keys: {sorted(forbidden)}."
        )


def validate_assistant_response_body(body: Mapping[str, Any]) -> str:
    """Validate Vapi assistant creation response and return assistant ID."""

    assistant_id = body.get("id")
    if not isinstance(assistant_id, str) or not assistant_id.strip():
        raise VapiResponseValidationError(
            "Vapi assistant response is missing a valid 'id' field.",
            response_body=dict(body),
        )
    return assistant_id


def _find_forbidden_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        matching_keys = {
            str(key) for key in value if str(key) in FORBIDDEN_PAYLOAD_KEYS
        }
        for item in value.values():
            matching_keys.update(_find_forbidden_keys(item))
        return matching_keys

    if isinstance(value, list | tuple):
        matching_keys = set()
        for item in value:
            matching_keys.update(_find_forbidden_keys(item))
        return matching_keys

    return set()
