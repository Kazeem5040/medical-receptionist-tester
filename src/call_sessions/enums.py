"""Controlled vocabulary for call lifecycle session tracking."""

from __future__ import annotations

from enum import StrEnum


class CallSessionState(StrEnum):
    """Current provider-neutral lifecycle state of one outbound call."""

    REQUESTED = "requested"
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallLifecycleEventType(StrEnum):
    """Provider-neutral event describing something that happened to a call."""

    CALL_QUEUED = "call_queued"
    CALL_RINGING = "call_ringing"
    CALL_STARTED = "call_started"
    CALL_ANSWERED = "call_answered"
    CALL_ENDED = "call_ended"
    CALL_FAILED = "call_failed"
    CALL_CANCELLED = "call_cancelled"
    TRANSCRIPT_AVAILABLE = "transcript_available"
    RECORDING_AVAILABLE = "recording_available"
    SUMMARY_AVAILABLE = "summary_available"


class CallSessionSeverity(StrEnum):
    """Severity level for call session validation issues."""

    ERROR = "error"
    WARNING = "warning"
