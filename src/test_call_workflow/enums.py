"""Controlled vocabulary for the test-call workflow use case."""

from __future__ import annotations

from enum import StrEnum


class TestCallWorkflowStatus(StrEnum):
    """High-level immediate workflow status."""

    SUBMITTED = "submitted"
    REJECTED = "rejected"
    FAILED = "failed"


class ProviderCapabilityState(StrEnum):
    """What the current provider path actually accomplished."""

    ASSISTANT_CREATED = "assistant_created"
    OUTBOUND_CALL_SUBMITTED = "outbound_call_submitted"
    OUTBOUND_CALL_ID_AVAILABLE = "outbound_call_id_available"
    OUTBOUND_CALL_NOT_YET_STARTED = "outbound_call_not_yet_started"
    UNKNOWN = "unknown"


class TestCallWorkflowSeverity(StrEnum):
    """Severity for workflow warnings and validation issues."""

    ERROR = "error"
    WARNING = "warning"
