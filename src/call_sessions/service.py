"""Application service for call lifecycle session creation and updates.

The service owns lifecycle state processing only:

- ``OutboundCallStartResult`` means Vapi accepted a real outbound call request.
- ``CallSession`` is this application's internal lifecycle record for that call.
- ``CallSessionUpdateResult`` is the receipt for one normalized event update.
- completed conversation evidence belongs to monitoring/transcript packages.
- receptionist evaluation and bug reports belong to later components.

The provider call ID is the correlation key because it is the stable Vapi
identifier that all later webhook/status events should reference. Provider
events can be delivered more than once, so event processing is idempotent.
Lifecycle state and event type are separate: an event is something that
happened, while state is what the session currently is after valid events are
applied. Terminal sessions are never reopened by late nonterminal events.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from outbound_calls import OutboundCallStartResult

from .canonicalization import stable_fingerprint
from .enums import CallLifecycleEventType, CallSessionState
from .errors import (
    CallSessionIssue,
    CallSessionNotFoundError,
    CallSessionValidationResult,
    InvalidCallTransitionError,
)
from .models import (
    CallLifecycleEvent,
    CallSession,
    CallSessionTraceability,
    CallSessionUpdateResult,
)
from .policies import DEFAULT_CALL_SESSION_POLICY, CallSessionPolicy
from .repository import CallSessionRepository
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


class CallSessionService:
    """Create and update immutable lifecycle records for outbound provider calls."""

    def __init__(
        self,
        *,
        repository: CallSessionRepository | None = None,
        policy: CallSessionPolicy = DEFAULT_CALL_SESSION_POLICY,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy
        self._clock = clock or _utc_now

    @property
    def policy(self) -> CallSessionPolicy:
        """Lifecycle policy used by this service."""

        return self._policy

    def create_session(
        self,
        outbound_call_start_result: OutboundCallStartResult,
    ) -> CallSession:
        """Create the initial internal lifecycle session for an outbound call."""

        validate_outbound_call_start_for_session(
            outbound_call_start_result,
            self._policy,
        ).raise_if_invalid()

        now = self._clock()
        provider_response = outbound_call_start_result.provider_response
        traceability = outbound_call_start_result.traceability
        session_traceability = CallSessionTraceability(
            preparation_id=traceability.preparation_id,
            submission_id=traceability.submission_id,
            outbound_call_id=outbound_call_start_result.outbound_call_id,
            idempotency_key=traceability.idempotency_key,
            source_scenario_id=traceability.source_scenario_id,
            source_scenario_version=traceability.source_scenario_version,
            scenario_template_fingerprint=(
                traceability.scenario_template_fingerprint
            ),
            scenario_instance_fingerprint=(
                traceability.scenario_instance_fingerprint
            ),
            conversation_contract_fingerprint=(
                traceability.conversation_contract_fingerprint
            ),
            vapi_configuration_fingerprint=(
                traceability.vapi_configuration_fingerprint
            ),
            prepared_call_request_fingerprint=(
                traceability.prepared_call_request_fingerprint
            ),
            call_submission_fingerprint=traceability.call_submission_fingerprint,
            outbound_call_fingerprint=outbound_call_start_result.result_fingerprint,
            scenario_seed=traceability.scenario_seed,
        )
        metadata = dict(outbound_call_start_result.metadata)
        fingerprint_source = {
            "provider": outbound_call_start_result.provider_name.value,
            "provider_call_id": provider_response.provider_call_id,
            "provider_assistant_id": provider_response.provider_assistant_id,
            "state": self._policy.initial_state.value,
            "requested_at": outbound_call_start_result.requested_at,
            "traceability": session_traceability,
            "metadata": metadata,
            "schema_version": self._policy.schema_version,
        }
        session_fingerprint = stable_fingerprint(
            fingerprint_source,
            prefix="call_session",
        )
        session_id = stable_fingerprint(
            {
                "provider": outbound_call_start_result.provider_name.value,
                "provider_call_id": provider_response.provider_call_id,
                "outbound_call_id": outbound_call_start_result.outbound_call_id,
            },
            prefix="session",
        )
        session = CallSession(
            session_id=session_id,
            provider=outbound_call_start_result.provider_name,
            provider_call_id=provider_response.provider_call_id,
            provider_assistant_id=provider_response.provider_assistant_id,
            destination_phone_number_redacted=_redact_phone_number(
                outbound_call_start_result.metadata.get(
                    "destination_phone_number",
                    "",
                ),
            ),
            state=self._policy.initial_state,
            created_at=now,
            updated_at=now,
            requested_at=outbound_call_start_result.requested_at,
            traceability=session_traceability,
            metadata=metadata,
            schema_version=self._policy.schema_version,
            session_fingerprint=session_fingerprint,
        )
        validate_call_session(session, self._policy).raise_if_invalid()
        self._save_if_configured(session)
        return session

    def process_event(
        self,
        session: CallSession,
        event: CallLifecycleEvent,
    ) -> CallSessionUpdateResult:
        """Apply one normalized lifecycle event to a session immutably."""

        validate_call_lifecycle_event(event, self._policy).raise_if_invalid()
        validate_event_belongs_to_session(session, event).raise_if_invalid()

        event_identity = event_processing_identity(event)
        processed_at = self._clock()
        previous_state = session.state
        was_terminal = is_terminal_state(previous_state)

        if event_identity in session.processed_event_ids:
            return CallSessionUpdateResult(
                session=session,
                event_identity=event_identity,
                previous_state=previous_state,
                current_state=session.state,
                applied=False,
                duplicate=True,
                terminal=was_terminal,
                became_terminal=False,
                processed_at=processed_at,
            )

        if is_artifact_event(event.event_type):
            updated_session = self._apply_artifact_event(
                session,
                event,
                event_identity,
                processed_at,
            )
            self._save_if_configured(updated_session)
            return self._result(
                session=updated_session,
                event_identity=event_identity,
                previous_state=previous_state,
                applied=True,
                duplicate=False,
                processed_at=processed_at,
                was_terminal=was_terminal,
            )

        target_state = target_state_for_event(event.event_type)
        if target_state is None:
            raise _invalid_transition(
                current_state=previous_state,
                event_type=event.event_type,
                target_state=None,
            )

        if was_terminal:
            updated_session = self._mark_event_processed(
                session,
                event,
                event_identity,
                processed_at,
            )
            self._save_if_configured(updated_session)
            return self._result(
                session=updated_session,
                event_identity=event_identity,
                previous_state=previous_state,
                applied=False,
                duplicate=False,
                processed_at=processed_at,
                was_terminal=True,
            )

        if not is_transition_allowed(previous_state, target_state):
            raise _invalid_transition(
                current_state=previous_state,
                event_type=event.event_type,
                target_state=target_state,
            )

        updated_session = self._apply_state_event(
            session,
            event,
            event_identity,
            target_state,
            processed_at,
        )
        self._save_if_configured(updated_session)
        return self._result(
            session=updated_session,
            event_identity=event_identity,
            previous_state=previous_state,
            applied=True,
            duplicate=False,
            processed_at=processed_at,
            was_terminal=was_terminal,
        )

    def process_event_for_provider_call(
        self,
        event: CallLifecycleEvent,
    ) -> CallSessionUpdateResult:
        """Load the matching session from the repository and process an event."""

        if self._repository is None:
            raise CallSessionNotFoundError(
                CallSessionValidationResult.from_issues(
                    (
                        CallSessionIssue(
                            code="repository_not_configured",
                            message=(
                                "A repository is required to process events by "
                                "provider_call_id."
                            ),
                            path=("repository",),
                        ),
                    ),
                ),
            )

        session = self._repository.get_by_provider_call_id(
            event.provider,
            event.provider_call_id,
        )
        if session is None:
            raise CallSessionNotFoundError(
                CallSessionValidationResult.from_issues(
                    (
                        CallSessionIssue(
                            code="call_session_not_found",
                            message="No call session exists for provider_call_id.",
                            path=("provider_call_id",),
                        ),
                    ),
                ),
            )
        return self.process_event(session, event)

    def _apply_state_event(
        self,
        session: CallSession,
        event: CallLifecycleEvent,
        event_identity: str,
        target_state: CallSessionState,
        processed_at: datetime,
    ) -> CallSession:
        started_at = session.started_at
        answered_at = session.answered_at
        ended_at = session.ended_at
        failure_code = session.failure_code
        failure_message = session.failure_message
        provider_ended_reason = session.provider_ended_reason

        if target_state == CallSessionState.IN_PROGRESS:
            started_at = started_at or event.occurred_at
            if event.event_type == CallLifecycleEventType.CALL_ANSWERED:
                answered_at = answered_at or event.occurred_at

        if target_state in {
            CallSessionState.COMPLETED,
            CallSessionState.FAILED,
            CallSessionState.CANCELLED,
        }:
            ended_at = event.occurred_at
            provider_ended_reason = event.ended_reason or provider_ended_reason

        if target_state == CallSessionState.FAILED:
            failure_code = event.failure_code
            failure_message = event.failure_message

        if target_state == CallSessionState.COMPLETED:
            failure_code = None
            failure_message = None

        return self._replace_session(
            session,
            event,
            event_identity,
            processed_at,
            state=target_state,
            started_at=started_at,
            answered_at=answered_at,
            ended_at=ended_at,
            failure_code=failure_code,
            failure_message=failure_message,
            provider_ended_reason=provider_ended_reason,
        )

    def _apply_artifact_event(
        self,
        session: CallSession,
        event: CallLifecycleEvent,
        event_identity: str,
        processed_at: datetime,
    ) -> CallSession:
        artifacts = session.artifacts.model_copy(
            update={
                "transcript_artifact_uri": (
                    event.transcript_artifact_uri
                    or session.artifacts.transcript_artifact_uri
                ),
                "recording_artifact_uri": (
                    event.recording_artifact_uri
                    or session.artifacts.recording_artifact_uri
                ),
                "summary_artifact_uri": (
                    event.summary_artifact_uri
                    or session.artifacts.summary_artifact_uri
                ),
            },
        )
        return self._replace_session(
            session,
            event,
            event_identity,
            processed_at,
            artifacts=artifacts,
        )

    def _mark_event_processed(
        self,
        session: CallSession,
        event: CallLifecycleEvent,
        event_identity: str,
        processed_at: datetime,
    ) -> CallSession:
        return self._replace_session(session, event, event_identity, processed_at)

    def _replace_session(
        self,
        session: CallSession,
        event: CallLifecycleEvent,
        event_identity: str,
        processed_at: datetime,
        **updates: object,
    ) -> CallSession:
        processed_event_ids = session.processed_event_ids + (event_identity,)
        latest_provider_event_at = _latest_datetime(
            session.latest_provider_event_at,
            event.occurred_at,
        )
        updated_values = {
            "updated_at": processed_at,
            "processed_event_ids": processed_event_ids,
            "latest_provider_event_at": latest_provider_event_at,
            **updates,
        }
        updated_session = session.model_copy(update=updated_values)
        updated_session = updated_session.model_copy(
            update={
                "session_fingerprint": self._fingerprint_for_session(
                    updated_session,
                ),
            },
        )
        validate_call_session(updated_session, self._policy).raise_if_invalid()
        return updated_session

    def _fingerprint_for_session(self, session: CallSession) -> str:
        return stable_fingerprint(
            {
                "provider": session.provider.value,
                "provider_call_id": session.provider_call_id,
                "provider_assistant_id": session.provider_assistant_id,
                "state": session.state.value,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "requested_at": session.requested_at,
                "started_at": session.started_at,
                "answered_at": session.answered_at,
                "ended_at": session.ended_at,
                "failure_code": session.failure_code,
                "failure_message": session.failure_message,
                "provider_ended_reason": session.provider_ended_reason,
                "artifacts": session.artifacts,
                "processed_event_ids": session.processed_event_ids,
                "latest_provider_event_at": session.latest_provider_event_at,
                "traceability": session.traceability,
                "metadata": session.metadata,
                "schema_version": session.schema_version,
            },
            prefix="call_session",
        )

    def _save_if_configured(self, session: CallSession) -> None:
        if self._repository is not None:
            self._repository.save(session)

    def _result(
        self,
        *,
        session: CallSession,
        event_identity: str,
        previous_state: CallSessionState,
        applied: bool,
        duplicate: bool,
        processed_at: datetime,
        was_terminal: bool,
    ) -> CallSessionUpdateResult:
        terminal = is_terminal_state(session.state)
        return CallSessionUpdateResult(
            session=session,
            event_identity=event_identity,
            previous_state=previous_state,
            current_state=session.state,
            applied=applied,
            duplicate=duplicate,
            terminal=terminal,
            became_terminal=terminal and not was_terminal,
            processed_at=processed_at,
        )


def event_processing_identity(event: CallLifecycleEvent) -> str:
    """Return stable event identity: provider event ID first, else fingerprint.

    The fallback fingerprint uses provider, provider_call_id, event type,
    occurred_at, sequence, terminal details, artifact references, and metadata.
    It intentionally excludes received_at so duplicate deliveries at different
    receipt times still collapse to the same identity.
    """

    if event.provider_event_id is not None:
        return f"provider-event:{event.provider.value}:{event.provider_event_id}"

    if event.event_fingerprint is not None:
        return event.event_fingerprint

    return stable_fingerprint(
        {
            "provider": event.provider.value,
            "provider_call_id": event.provider_call_id,
            "event_type": event.event_type.value,
            "occurred_at": event.occurred_at,
            "sequence": event.sequence,
            "ended_reason": event.ended_reason,
            "failure_code": event.failure_code,
            "failure_message": event.failure_message,
            "transcript_artifact_uri": event.transcript_artifact_uri,
            "recording_artifact_uri": event.recording_artifact_uri,
            "summary_artifact_uri": event.summary_artifact_uri,
            "metadata": event.metadata,
        },
        prefix="call_event",
    )


def _invalid_transition(
    *,
    current_state: CallSessionState,
    event_type: CallLifecycleEventType,
    target_state: CallSessionState | None,
) -> InvalidCallTransitionError:
    target = target_state.value if target_state is not None else "none"
    return InvalidCallTransitionError(
        CallSessionValidationResult.from_issues(
            (
                CallSessionIssue(
                    code="invalid_call_transition",
                    message=(
                        "Invalid call lifecycle transition from "
                        f"{current_state.value} using {event_type.value} "
                        f"toward {target}."
                    ),
                    path=("state",),
                ),
            ),
        ),
    )


def _redact_phone_number(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) < 4:
        return "redacted"
    return f"redacted-***{digits[-4:]}"


def _latest_datetime(first: datetime | None, second: datetime) -> datetime:
    if first is None or second > first:
        return second
    return first


def _utc_now() -> datetime:
    return datetime.now(UTC)
