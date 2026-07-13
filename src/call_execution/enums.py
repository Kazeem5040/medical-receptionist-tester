"""Controlled vocabulary for call execution."""

from __future__ import annotations

from enum import StrEnum


class ExecutionStatus(StrEnum):
    """High-level status for submitting a prepared call to a provider."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class ProviderName(StrEnum):
    """Supported call execution providers."""

    VAPI = "vapi"


class ExecutionSeverity(StrEnum):
    """Severity level for execution validation issues and warnings."""

    ERROR = "error"
    WARNING = "warning"


class RetryStrategy(StrEnum):
    """Retry strategy recorded by the execution policy."""

    PROVIDER_CLIENT_MANAGED = "provider_client_managed"
    DISABLED = "disabled"


class ProviderResponseState(StrEnum):
    """Normalized provider response state."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"
