"""Call lifecycle session tracking package.

This bounded component maintains the provider-neutral lifecycle record for one
outbound call. It does not parse raw Vapi webhooks, perform HTTP requests,
store database rows, evaluate transcripts, or generate bug reports.
"""

from .canonicalization import canonical_json, canonical_snapshot, stable_fingerprint
from .enums import CallLifecycleEventType, CallSessionSeverity, CallSessionState
from .errors import (
    CallSessionConflictError,
    CallSessionError,
    CallSessionIssue,
    CallSessionNotFoundError,
    CallSessionValidationResult,
    InvalidCallTransitionError,
)
from .models import (
    CallLifecycleEvent,
    CallSession,
    CallSessionArtifacts,
    CallSessionTraceability,
    CallSessionUpdateResult,
)
from .policies import DEFAULT_CALL_SESSION_POLICY, CallSessionPolicy
from .repository import CallSessionRepository
from .service import CallSessionService, event_processing_identity
from .transitions import (
    is_artifact_event,
    is_terminal_state,
    is_transition_allowed,
    target_state_for_event,
)
from .validation import (
    validate_call_lifecycle_event,
    validate_call_session,
    validate_event_belongs_to_session,
    validate_outbound_call_start_for_session,
)

__all__ = [
    "DEFAULT_CALL_SESSION_POLICY",
    "CallLifecycleEvent",
    "CallLifecycleEventType",
    "CallSession",
    "CallSessionArtifacts",
    "CallSessionConflictError",
    "CallSessionError",
    "CallSessionIssue",
    "CallSessionNotFoundError",
    "CallSessionPolicy",
    "CallSessionRepository",
    "CallSessionService",
    "CallSessionSeverity",
    "CallSessionState",
    "CallSessionTraceability",
    "CallSessionUpdateResult",
    "CallSessionValidationResult",
    "InvalidCallTransitionError",
    "canonical_json",
    "canonical_snapshot",
    "event_processing_identity",
    "is_artifact_event",
    "is_terminal_state",
    "is_transition_allowed",
    "stable_fingerprint",
    "target_state_for_event",
    "validate_call_lifecycle_event",
    "validate_call_session",
    "validate_event_belongs_to_session",
    "validate_outbound_call_start_for_session",
]
