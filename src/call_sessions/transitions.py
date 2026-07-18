"""Centralized lifecycle transition rules for call sessions."""

from __future__ import annotations

from .enums import CallLifecycleEventType, CallSessionState

STATE_CHANGING_EVENTS: dict[CallLifecycleEventType, CallSessionState] = {
    CallLifecycleEventType.CALL_QUEUED: CallSessionState.QUEUED,
    CallLifecycleEventType.CALL_RINGING: CallSessionState.RINGING,
    CallLifecycleEventType.CALL_STARTED: CallSessionState.IN_PROGRESS,
    CallLifecycleEventType.CALL_ANSWERED: CallSessionState.IN_PROGRESS,
    CallLifecycleEventType.CALL_ENDED: CallSessionState.COMPLETED,
    CallLifecycleEventType.CALL_FAILED: CallSessionState.FAILED,
    CallLifecycleEventType.CALL_CANCELLED: CallSessionState.CANCELLED,
}

ARTIFACT_EVENTS = frozenset(
    {
        CallLifecycleEventType.TRANSCRIPT_AVAILABLE,
        CallLifecycleEventType.RECORDING_AVAILABLE,
        CallLifecycleEventType.SUMMARY_AVAILABLE,
    },
)

TERMINAL_STATES = frozenset(
    {
        CallSessionState.COMPLETED,
        CallSessionState.FAILED,
        CallSessionState.CANCELLED,
    },
)

ALLOWED_TRANSITIONS: dict[CallSessionState, frozenset[CallSessionState]] = {
    CallSessionState.REQUESTED: frozenset(
        {
            CallSessionState.QUEUED,
            CallSessionState.RINGING,
            CallSessionState.IN_PROGRESS,
            CallSessionState.FAILED,
            CallSessionState.CANCELLED,
        },
    ),
    CallSessionState.QUEUED: frozenset(
        {
            CallSessionState.RINGING,
            CallSessionState.IN_PROGRESS,
            CallSessionState.FAILED,
            CallSessionState.CANCELLED,
        },
    ),
    CallSessionState.RINGING: frozenset(
        {
            CallSessionState.IN_PROGRESS,
            CallSessionState.FAILED,
            CallSessionState.CANCELLED,
        },
    ),
    CallSessionState.IN_PROGRESS: frozenset(
        {
            CallSessionState.COMPLETED,
            CallSessionState.FAILED,
            CallSessionState.CANCELLED,
        },
    ),
    CallSessionState.COMPLETED: frozenset(),
    CallSessionState.FAILED: frozenset(),
    CallSessionState.CANCELLED: frozenset(),
}


def is_artifact_event(event_type: CallLifecycleEventType) -> bool:
    """Return whether an event updates artifact references without changing state."""

    return event_type in ARTIFACT_EVENTS


def target_state_for_event(
    event_type: CallLifecycleEventType,
) -> CallSessionState | None:
    """Return the state requested by a lifecycle event, if any."""

    return STATE_CHANGING_EVENTS.get(event_type)


def is_terminal_state(state: CallSessionState) -> bool:
    """Return whether a state is terminal and should not be reopened."""

    return state in TERMINAL_STATES


def is_transition_allowed(
    current_state: CallSessionState,
    target_state: CallSessionState,
) -> bool:
    """Return whether a nonduplicate lifecycle transition is allowed."""

    if current_state == target_state:
        return True
    return target_state in ALLOWED_TRANSITIONS[current_state]
