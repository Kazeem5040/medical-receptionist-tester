"""Controlled vocabulary for real outbound call creation."""

from __future__ import annotations

from enum import StrEnum


class OutboundCallStatus(StrEnum):
    """High-level result for requesting a real outbound call."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"


class ProviderCallState(StrEnum):
    """Normalized provider state after Vapi accepts a call request."""

    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    ENDED = "ended"
    ACCEPTED = "accepted"
    UNKNOWN = "unknown"


class OutboundCallCreationSeverity(StrEnum):
    """Severity level for outbound call creation issues and warnings."""

    ERROR = "error"
    WARNING = "warning"
