"""Structured exceptions for Vapi API communication."""

from __future__ import annotations

from typing import Any


class VapiClientError(Exception):
    """Base class for Vapi client failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class VapiAuthenticationError(VapiClientError):
    """Raised for missing/invalid credentials or 401/403 responses."""


class VapiNetworkError(VapiClientError):
    """Raised for network transport failures."""


class VapiTimeoutError(VapiClientError):
    """Raised when the Vapi request times out."""


class VapiRateLimitError(VapiClientError):
    """Raised when Vapi returns HTTP 429."""


class VapiServerError(VapiClientError):
    """Raised when Vapi returns HTTP 5xx."""


class VapiSerializationError(VapiClientError):
    """Raised when payload serialization fails."""


class VapiResponseValidationError(VapiClientError):
    """Raised when a Vapi response body is missing required fields."""
