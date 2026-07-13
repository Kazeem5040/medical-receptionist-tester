"""Controlled vocabulary for the Vapi HTTP API client."""

from __future__ import annotations

from enum import StrEnum


class HttpMethod(StrEnum):
    """HTTP methods used by this client."""

    POST = "POST"


class RetryReason(StrEnum):
    """Reasons a request may be retried."""

    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"


class ProviderResourceStatus(StrEnum):
    """Provider resource status understood by this client."""

    CREATED = "created"
    UNKNOWN = "unknown"


class VapiResponseStatus(StrEnum):
    """High-level response status returned by the client."""

    SUCCESS = "success"
    FAILED = "failed"


class VapiClientValidationSeverity(StrEnum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
