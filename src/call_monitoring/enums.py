"""Controlled vocabulary for call monitoring."""

from __future__ import annotations

from enum import StrEnum


class MonitoringEventKind(StrEnum):
    """Kinds of events the monitoring component can organize."""

    LIFECYCLE = "lifecycle"
    TRANSCRIPT = "transcript"
    INTERRUPTION = "interruption"
    SILENCE = "silence"
    ARTIFACT = "artifact"
    METADATA = "metadata"


class CallLifecycleState(StrEnum):
    """Provider-independent lifecycle state for a submitted call."""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


class CallParticipant(StrEnum):
    """Participants that may appear in monitored call events."""

    AI_PATIENT = "ai_patient"
    RECEPTIONIST = "receptionist"
    PROVIDER = "provider"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class CallCompletionReason(StrEnum):
    """Normalized reason a monitored call ended."""

    NORMAL_COMPLETION = "normal_completion"
    PATIENT_ENDED = "patient_ended"
    RECEPTIONIST_ENDED = "receptionist_ended"
    PROVIDER_ENDED = "provider_ended"
    MAX_DURATION_REACHED = "max_duration_reached"
    SILENCE_TIMEOUT = "silence_timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


class CallSessionStatus(StrEnum):
    """Status of the collected call session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


class MonitoringSeverity(StrEnum):
    """Severity level for monitoring validation issues and warnings."""

    ERROR = "error"
    WARNING = "warning"
