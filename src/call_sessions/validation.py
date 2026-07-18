"""Validation helpers for call lifecycle sessions and normalized events."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from call_execution import ProviderName
from outbound_calls import OutboundCallStartResult, OutboundCallStatus

from .enums import CallLifecycleEventType, CallSessionSeverity, CallSessionState
from .errors import CallSessionIssue, CallSessionValidationResult
from .models import CallLifecycleEvent, CallSession
from .policies import DEFAULT_CALL_SESSION_POLICY, CallSessionPolicy
from .transitions import is_terminal_state

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "auth",
        "bearer",
        "secret",
        "token",
        "password",
        "raw_payload",
        "vapi_payload",
        "transcript",
        "evaluation",
        "score",
        "bug_report",
        "diagnosis",
        "patient_record",
    },
)


def validate_outbound_call_start_for_session(
    result: OutboundCallStartResult,
    policy: CallSessionPolicy = DEFAULT_CALL_SESSION_POLICY,
) -> CallSessionValidationResult:
    """Validate that an outbound-call result can seed a lifecycle session."""

    issues: list[CallSessionIssue] = []

    if result.status != OutboundCallStatus.ACCEPTED:
        issues.append(
            _issue(
                code="outbound_call_not_accepted",
                message="Only accepted outbound calls can create call sessions.",
                path=("status",),
            ),
        )

    provider_call_id = result.provider_response.provider_call_id
    if policy.require_provider_call_id and not provider_call_id.strip():
        issues.append(
            _issue(
                code="missing_provider_call_id",
                message="A call session requires a provider call ID.",
                path=("provider_response", "provider_call_id"),
            ),
        )

    if result.provider_name != ProviderName.VAPI:
        issues.append(
            _issue(
                code="unsupported_provider",
                message="Call sessions currently support Vapi provider results.",
                path=("provider_name",),
            ),
        )

    _validate_utc_datetime(
        result.requested_at,
        issues,
        path=("requested_at",),
    )
    _validate_required_traceability(
        {
            "preparation_id": result.traceability.preparation_id,
            "submission_id": result.traceability.submission_id,
            "outbound_call_id": result.outbound_call_id,
            "scenario_template_fingerprint": (
                result.traceability.scenario_template_fingerprint
            ),
            "scenario_instance_fingerprint": (
                result.traceability.scenario_instance_fingerprint
            ),
            "conversation_contract_fingerprint": (
                result.traceability.conversation_contract_fingerprint
            ),
            "vapi_configuration_fingerprint": (
                result.traceability.vapi_configuration_fingerprint
            ),
            "prepared_call_request_fingerprint": (
                result.traceability.prepared_call_request_fingerprint
            ),
            "call_submission_fingerprint": (
                result.traceability.call_submission_fingerprint
            ),
            "outbound_call_fingerprint": result.result_fingerprint,
        },
        policy,
        issues,
    )
    _validate_metadata(result.metadata, policy, issues, path=("metadata",))

    return CallSessionValidationResult.from_issues(issues)


def validate_call_lifecycle_event(
    event: CallLifecycleEvent,
    policy: CallSessionPolicy = DEFAULT_CALL_SESSION_POLICY,
) -> CallSessionValidationResult:
    """Validate one normalized provider-neutral event before processing."""

    issues: list[CallSessionIssue] = []

    if not event.provider_call_id.strip():
        issues.append(
            _issue(
                code="missing_provider_call_id",
                message="Lifecycle events must include provider_call_id.",
                path=("provider_call_id",),
            ),
        )

    _validate_utc_datetime(event.occurred_at, issues, path=("occurred_at",))
    _validate_utc_datetime(event.received_at, issues, path=("received_at",))

    if event.event_type == CallLifecycleEventType.CALL_FAILED:
        if not (event.failure_code or event.failure_message):
            issues.append(
                _issue(
                    code="missing_failure_information",
                    message=(
                        "Failure events should include failure_code or "
                        "failure_message."
                    ),
                    path=("failure_code",),
                ),
            )

    if event.event_type == CallLifecycleEventType.CALL_CANCELLED:
        if event.failure_code is not None:
            issues.append(
                _issue(
                    code="cancelled_event_has_failure_code",
                    message="Cancelled events must not be mixed with failure codes.",
                    path=("failure_code",),
                ),
            )

    _validate_artifact_event_shape(event, issues)
    _validate_metadata(event.metadata, policy, issues, path=("metadata",))

    return CallSessionValidationResult.from_issues(issues)


def validate_call_session(
    session: CallSession,
    policy: CallSessionPolicy = DEFAULT_CALL_SESSION_POLICY,
) -> CallSessionValidationResult:
    """Validate an internal call session lifecycle record."""

    issues: list[CallSessionIssue] = []

    for field_name in (
        "created_at",
        "updated_at",
        "requested_at",
        "started_at",
        "answered_at",
        "ended_at",
        "latest_provider_event_at",
    ):
        value = getattr(session, field_name)
        if value is not None:
            _validate_utc_datetime(value, issues, path=(field_name,))

    if session.updated_at < session.created_at:
        issues.append(
            _issue(
                code="updated_before_created",
                message="Session updated_at cannot be earlier than created_at.",
                path=("updated_at",),
            ),
        )

    if (
        session.started_at is not None
        and session.ended_at is not None
        and session.ended_at < session.started_at
    ):
        issues.append(
            _issue(
                code="ended_before_started",
                message="Session ended_at cannot be earlier than started_at.",
                path=("ended_at",),
            ),
        )

    if len(set(session.processed_event_ids)) != len(session.processed_event_ids):
        issues.append(
            _issue(
                code="duplicate_processed_event_id",
                message="Processed event identifiers must be unique.",
                path=("processed_event_ids",),
            ),
        )

    if len(session.processed_event_ids) > policy.max_processed_event_ids:
        issues.append(
            _issue(
                code="too_many_processed_events",
                message="Processed event identifier count exceeds policy limit.",
                path=("processed_event_ids",),
            ),
        )

    if session.state == CallSessionState.COMPLETED:
        if session.failure_code is not None or session.failure_message is not None:
            issues.append(
                _issue(
                    code="completed_session_has_failure",
                    message="Completed sessions cannot also contain failure data.",
                    path=("failure_code",),
                ),
            )
        if session.ended_at is None:
            issues.append(
                _issue(
                    code="completed_session_missing_ended_at",
                    message="Completed sessions must include ended_at.",
                    path=("ended_at",),
                ),
            )

    if session.state == CallSessionState.FAILED:
        if session.ended_at is None:
            issues.append(
                _issue(
                    code="failed_session_missing_ended_at",
                    message="Failed sessions must include ended_at.",
                    path=("ended_at",),
                ),
            )
        if session.failure_code is None and session.failure_message is None:
            issues.append(
                _issue(
                    code="failed_session_missing_failure_information",
                    message=(
                        "Failed sessions must include failure_code or "
                        "failure_message."
                    ),
                    path=("failure_code",),
                ),
            )

    if session.state == CallSessionState.CANCELLED and session.ended_at is None:
        issues.append(
            _issue(
                code="cancelled_session_missing_ended_at",
                message="Cancelled sessions must include ended_at.",
                path=("ended_at",),
            ),
        )

    if is_terminal_state(session.state) and session.ended_at is None:
        issues.append(
            _issue(
                code="terminal_session_missing_ended_at",
                message="Terminal sessions must include ended_at.",
                path=("ended_at",),
            ),
        )

    _validate_metadata(session.metadata, policy, issues, path=("metadata",))

    return CallSessionValidationResult.from_issues(issues)


def validate_event_belongs_to_session(
    session: CallSession,
    event: CallLifecycleEvent,
) -> CallSessionValidationResult:
    """Validate provider and provider_call_id correlation."""

    issues: list[CallSessionIssue] = []

    if event.provider != session.provider:
        issues.append(
            _issue(
                code="event_provider_mismatch",
                message="Lifecycle event provider does not match session provider.",
                path=("provider",),
            ),
        )

    if event.provider_call_id != session.provider_call_id:
        issues.append(
            _issue(
                code="event_provider_call_id_mismatch",
                message=(
                    "Lifecycle event provider_call_id does not match session "
                    "provider_call_id."
                ),
                path=("provider_call_id",),
            ),
        )

    return CallSessionValidationResult.from_issues(issues)


def _validate_artifact_event_shape(
    event: CallLifecycleEvent,
    issues: list[CallSessionIssue],
) -> None:
    if (
        event.event_type == CallLifecycleEventType.TRANSCRIPT_AVAILABLE
        and event.transcript_artifact_uri is None
    ):
        issues.append(
            _issue(
                code="missing_transcript_artifact",
                message="Transcript artifact events must include a transcript URI.",
                path=("transcript_artifact_uri",),
            ),
        )

    if (
        event.event_type == CallLifecycleEventType.RECORDING_AVAILABLE
        and event.recording_artifact_uri is None
    ):
        issues.append(
            _issue(
                code="missing_recording_artifact",
                message="Recording artifact events must include a recording URI.",
                path=("recording_artifact_uri",),
            ),
        )

    if (
        event.event_type == CallLifecycleEventType.SUMMARY_AVAILABLE
        and event.summary_artifact_uri is None
    ):
        issues.append(
            _issue(
                code="missing_summary_artifact",
                message="Summary artifact events must include a summary URI.",
                path=("summary_artifact_uri",),
            ),
        )


def _validate_required_traceability(
    fields: Mapping[str, str],
    policy: CallSessionPolicy,
    issues: list[CallSessionIssue],
) -> None:
    if not policy.require_traceability_fingerprints:
        return

    for name, value in fields.items():
        if not value.strip():
            issues.append(
                _issue(
                    code="missing_traceability_field",
                    message=f"Missing call session traceability field: {name}.",
                    path=("traceability", name),
                ),
            )


def _validate_utc_datetime(
    value: datetime,
    issues: list[CallSessionIssue],
    *,
    path: tuple[str | int, ...],
) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        issues.append(
            _issue(
                code="timestamp_not_timezone_aware",
                message="Call session timestamps must be timezone-aware.",
                path=path,
            ),
        )
        return

    if value.utcoffset() != UTC.utcoffset(value):
        issues.append(
            _issue(
                code="timestamp_not_utc",
                message="Call session timestamps must be UTC-normalized.",
                path=path,
            ),
        )


def _validate_metadata(
    metadata: Mapping[str, str],
    policy: CallSessionPolicy,
    issues: list[CallSessionIssue],
    *,
    path: tuple[str | int, ...],
) -> None:
    if len(metadata) > policy.max_metadata_items:
        issues.append(
            _issue(
                code="too_many_metadata_items",
                message="Call session metadata exceeds the policy item limit.",
                path=path,
            ),
        )

    for key, value in metadata.items():
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in FORBIDDEN_METADATA_KEYS:
            issues.append(
                _issue(
                    code="forbidden_metadata_key",
                    message=f"Forbidden metadata key: {key}.",
                    path=path + (key,),
                ),
            )

        if len(key) > policy.max_metadata_key_length:
            issues.append(
                _issue(
                    code="metadata_key_too_long",
                    message=f"Metadata key is too long: {key}.",
                    path=path + (key,),
                ),
            )

        if len(value) > policy.max_metadata_value_length:
            issues.append(
                _issue(
                    code="metadata_value_too_long",
                    message=f"Metadata value is too long for key: {key}.",
                    path=path + (key,),
                ),
            )


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: CallSessionSeverity = CallSessionSeverity.ERROR,
) -> CallSessionIssue:
    return CallSessionIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
