"""Validation helpers for call monitoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from call_execution import CallSubmissionResult, ExecutionStatus

from .enums import (
    CallParticipant,
    MonitoringEventKind,
    MonitoringSeverity,
)
from .errors import CallMonitoringIssue, CallMonitoringValidationResult
from .models import CallSession, MonitoringInputEvent
from .policies import DEFAULT_CALL_MONITORING_POLICY, CallMonitoringPolicy

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
        "evaluation",
        "score",
        "bug_report",
        "diagnosis",
        "patient_record",
    },
)


def validate_call_submission_for_monitoring(
    submission: CallSubmissionResult,
    policy: CallMonitoringPolicy = DEFAULT_CALL_MONITORING_POLICY,
) -> CallMonitoringValidationResult:
    """Validate that a submitted call can be monitored."""

    issues: list[CallMonitoringIssue] = []

    if (
        policy.require_submission_acceptance
        and submission.execution_status != ExecutionStatus.ACCEPTED
    ):
        issues.append(
            _issue(
                code="submission_not_accepted",
                message="Only accepted call submissions can be monitored.",
                path=("execution_status",),
            ),
        )

    traceability = submission.traceability
    if policy.require_traceability_fingerprints:
        required_fingerprints = {
            "scenario_instance_fingerprint": (
                traceability.scenario_instance_fingerprint
            ),
            "conversation_contract_fingerprint": (
                traceability.conversation_contract_fingerprint
            ),
            "vapi_configuration_fingerprint": (
                traceability.vapi_configuration_fingerprint
            ),
            "prepared_call_request_fingerprint": traceability.request_fingerprint,
            "call_submission_fingerprint": submission.result_fingerprint,
        }
        for name, value in required_fingerprints.items():
            if not value.strip():
                issues.append(
                    _issue(
                        code="missing_traceability_fingerprint",
                        message=f"Missing monitoring traceability fingerprint: {name}.",
                        path=("traceability", name),
                    ),
                )

    _validate_metadata(submission.metadata, policy, issues, path=("metadata",))

    return CallMonitoringValidationResult.from_issues(issues)


def validate_monitoring_events(
    events: Sequence[MonitoringInputEvent],
    policy: CallMonitoringPolicy = DEFAULT_CALL_MONITORING_POLICY,
) -> CallMonitoringValidationResult:
    """Validate provider-independent event inputs before collection."""

    issues: list[CallMonitoringIssue] = []

    if len(events) > policy.max_events_per_session:
        issues.append(
            _issue(
                code="too_many_monitoring_events",
                message="Monitoring event count exceeds the policy limit.",
                path=("events",),
            ),
        )

    seen_event_ids: set[str] = set()
    for index, event in enumerate(events):
        event_path = ("events", index)
        if event.event_id in seen_event_ids:
            issues.append(
                _issue(
                    code="duplicate_event_id",
                    message=f"Duplicate monitoring event ID: {event.event_id}.",
                    path=event_path + ("event_id",),
                ),
            )
        seen_event_ids.add(event.event_id)

        _validate_event_shape(event, policy, issues, event_path)
        _validate_metadata(
            event.metadata,
            policy,
            issues,
            path=event_path + ("metadata",),
        )

    return CallMonitoringValidationResult.from_issues(issues)


def validate_call_session(
    session: CallSession,
    policy: CallMonitoringPolicy = DEFAULT_CALL_MONITORING_POLICY,
) -> CallMonitoringValidationResult:
    """Validate a collected call session before returning it."""

    issues: list[CallMonitoringIssue] = []

    if len(session.provider_events) > policy.max_events_per_session:
        issues.append(
            _issue(
                code="too_many_provider_events",
                message="Provider event count exceeds the policy limit.",
                path=("provider_events",),
            ),
        )

    if session.statistics.provider_event_count != len(session.provider_events):
        issues.append(
            _issue(
                code="provider_event_count_mismatch",
                message="Session provider event count does not match statistics.",
                path=("statistics", "provider_event_count"),
            ),
        )

    if session.statistics.transcript_turn_count != len(session.transcript):
        issues.append(
            _issue(
                code="transcript_turn_count_mismatch",
                message="Session transcript count does not match statistics.",
                path=("statistics", "transcript_turn_count"),
            ),
        )

    if session.ended_at is not None and session.started_at is not None:
        if session.ended_at < session.started_at:
            issues.append(
                _issue(
                    code="session_ended_before_started",
                    message="Call session ended before it started.",
                    path=("ended_at",),
                ),
            )

    _validate_metadata(session.metadata, policy, issues, path=("metadata",))

    return CallMonitoringValidationResult.from_issues(issues)


def _validate_event_shape(
    event: MonitoringInputEvent,
    policy: CallMonitoringPolicy,
    issues: list[CallMonitoringIssue],
    path: tuple[str | int, ...],
) -> None:
    if event.kind == MonitoringEventKind.LIFECYCLE:
        if event.lifecycle_state is None:
            issues.append(
                _issue(
                    code="missing_lifecycle_state",
                    message="Lifecycle events must include lifecycle_state.",
                    path=path + ("lifecycle_state",),
                ),
            )
        return

    if event.kind == MonitoringEventKind.TRANSCRIPT:
        if event.speaker not in {
            CallParticipant.AI_PATIENT,
            CallParticipant.RECEPTIONIST,
        }:
            issues.append(
                _issue(
                    code="invalid_transcript_speaker",
                    message=(
                        "Transcript events must identify the AI patient or "
                        "receptionist as speaker."
                    ),
                    path=path + ("speaker",),
                ),
            )
        if event.text is None or not event.text.strip():
            issues.append(
                _issue(
                    code="missing_transcript_text",
                    message="Transcript events must include utterance text.",
                    path=path + ("text",),
                ),
            )
        elif len(event.text) > policy.max_transcript_text_length:
            issues.append(
                _issue(
                    code="transcript_text_too_long",
                    message="Transcript event text exceeds the policy length limit.",
                    path=path + ("text",),
                ),
            )
        return

    if event.kind == MonitoringEventKind.INTERRUPTION:
        if event.interrupted_speaker is None:
            issues.append(
                _issue(
                    code="missing_interrupted_speaker",
                    message="Interruption events must include interrupted_speaker.",
                    path=path + ("interrupted_speaker",),
                ),
            )
        if event.interrupting_speaker is None:
            issues.append(
                _issue(
                    code="missing_interrupting_speaker",
                    message="Interruption events must include interrupting_speaker.",
                    path=path + ("interrupting_speaker",),
                ),
            )
        return

    if event.kind == MonitoringEventKind.SILENCE:
        if event.silence_duration_ms is None and event.ended_at is None:
            issues.append(
                _issue(
                    code="missing_silence_duration",
                    message=(
                        "Silence events must include silence_duration_ms or ended_at."
                    ),
                    path=path,
                ),
            )
        return

    if event.kind == MonitoringEventKind.ARTIFACT:
        if event.recording_url is None and event.transcript_url is None:
            issues.append(
                _issue(
                    code="missing_artifact_reference",
                    message=(
                        "Artifact events must include a recording_url or "
                        "transcript_url."
                    ),
                    path=path,
                ),
            )


def _validate_metadata(
    metadata: Mapping[str, str],
    policy: CallMonitoringPolicy,
    issues: list[CallMonitoringIssue],
    *,
    path: tuple[str | int, ...],
) -> None:
    if len(metadata) > policy.max_metadata_items:
        issues.append(
            _issue(
                code="too_many_metadata_items",
                message="Monitoring metadata exceeds the policy item limit.",
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
    severity: MonitoringSeverity = MonitoringSeverity.ERROR,
) -> CallMonitoringIssue:
    return CallMonitoringIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
