"""Validation helpers for real outbound call creation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from call_execution import CallSubmissionResult, ExecutionStatus
from call_orchestrator import DestinationKind, PreparedCall
from vapi_client import VapiCreateCallResponse

from .enums import (
    OutboundCallCreationSeverity,
    OutboundCallStatus,
    ProviderCallState,
)
from .errors import OutboundCallCreationIssue, OutboundCallCreationValidationResult
from .models import OutboundCallCreationRequest, OutboundCallStartResult
from .policies import (
    DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
    OutboundCallCreationPolicy,
)

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
        "transcript",
        "recording",
        "evaluation",
        "score",
        "bug_report",
        "diagnosis",
        "patient_record",
    },
)


def validate_outbound_call_creation_request(
    request: OutboundCallCreationRequest,
    policy: OutboundCallCreationPolicy = DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
) -> OutboundCallCreationValidationResult:
    """Validate a request before a real outbound call can be dialed."""

    issues: list[OutboundCallCreationIssue] = []

    if not policy.real_calls_enabled:
        issues.append(
            _issue(
                code="real_calls_disabled",
                message="Real outbound calls must be explicitly enabled by policy.",
                path=("policy", "real_calls_enabled"),
            ),
        )

    _validate_submission_pair(
        request.prepared_call,
        request.call_submission_result,
        policy,
        issues,
    )
    _validate_destination(request.prepared_call, policy, issues)
    _validate_metadata(request.metadata, policy, issues, path=("metadata",))

    return OutboundCallCreationValidationResult.from_issues(issues)


def validate_provider_call_response(
    response: VapiCreateCallResponse,
    policy: OutboundCallCreationPolicy = DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
) -> OutboundCallCreationValidationResult:
    """Validate the provider response before converting it into a domain result."""

    issues: list[OutboundCallCreationIssue] = []

    if policy.require_provider_call_id and not response.call_id.value.strip():
        issues.append(
            _issue(
                code="missing_provider_call_id",
                message="Vapi call creation response must include a provider call ID.",
                path=("call_id",),
            ),
        )

    return OutboundCallCreationValidationResult.from_issues(issues)


def validate_outbound_call_start_result(
    result: OutboundCallStartResult,
    policy: OutboundCallCreationPolicy = DEFAULT_OUTBOUND_CALL_CREATION_POLICY,
) -> OutboundCallCreationValidationResult:
    """Validate the final outbound call start result before returning it."""

    issues: list[OutboundCallCreationIssue] = []

    if result.status == OutboundCallStatus.ACCEPTED:
        if not result.provider_response.provider_call_id.strip():
            issues.append(
                _issue(
                    code="accepted_call_missing_provider_call_id",
                    message="Accepted outbound calls must include a provider call ID.",
                    path=("provider_response", "provider_call_id"),
                ),
            )

    if (
        result.traceability.provider_assistant_id
        != result.provider_response.provider_assistant_id
    ):
        issues.append(
            _issue(
                code="assistant_id_traceability_mismatch",
                message="Traceability assistant ID does not match provider metadata.",
                path=("traceability", "provider_assistant_id"),
            ),
        )

    _validate_metadata(result.metadata, policy, issues, path=("metadata",))

    return OutboundCallCreationValidationResult.from_issues(issues)


def normalize_provider_call_state(
    response: VapiCreateCallResponse,
) -> ProviderCallState:
    """Normalize Vapi call response status into our provider-independent state."""

    raw_status = _response_status(response.raw_response)
    if raw_status in {"queued", "scheduled"}:
        return ProviderCallState.QUEUED
    if raw_status in {"ringing"}:
        return ProviderCallState.RINGING
    if raw_status in {"in-progress", "in_progress", "active"}:
        return ProviderCallState.IN_PROGRESS
    if raw_status in {"ended", "completed"}:
        return ProviderCallState.ENDED
    if 200 <= response.http_status.status_code <= 299:
        return ProviderCallState.ACCEPTED
    return ProviderCallState.UNKNOWN


def _validate_submission_pair(
    prepared_call: PreparedCall,
    submission: CallSubmissionResult,
    policy: OutboundCallCreationPolicy,
    issues: list[OutboundCallCreationIssue],
) -> None:
    if (
        policy.require_accepted_submission
        and submission.execution_status != ExecutionStatus.ACCEPTED
    ):
        issues.append(
            _issue(
                code="submission_not_accepted",
                message="Only accepted call submissions can create outbound calls.",
                path=("call_submission_result", "execution_status"),
            ),
        )

    provider_assistant_id = submission.provider_response.provider_resource_id
    if not provider_assistant_id.strip():
        issues.append(
            _issue(
                code="missing_provider_assistant_id",
                message="Outbound call creation requires a provider assistant ID.",
                path=(
                    "call_submission_result",
                    "provider_response",
                    "provider_resource_id",
                ),
            ),
        )

    if prepared_call.preparation_id != submission.traceability.preparation_id:
        issues.append(
            _issue(
                code="preparation_id_mismatch",
                message="Prepared call and submission result do not match.",
                path=("call_submission_result", "traceability", "preparation_id"),
            ),
        )

    if prepared_call.idempotency_key != submission.traceability.idempotency_key:
        issues.append(
            _issue(
                code="idempotency_key_mismatch",
                message="Prepared call and submission idempotency keys do not match.",
                path=("call_submission_result", "traceability", "idempotency_key"),
            ),
        )

    if policy.require_traceability_fingerprints:
        required = {
            "scenario_instance_fingerprint": (
                submission.traceability.scenario_instance_fingerprint
            ),
            "conversation_contract_fingerprint": (
                submission.traceability.conversation_contract_fingerprint
            ),
            "vapi_configuration_fingerprint": (
                submission.traceability.vapi_configuration_fingerprint
            ),
            "prepared_call_request_fingerprint": (
                submission.traceability.request_fingerprint
            ),
            "call_submission_fingerprint": submission.result_fingerprint,
        }
        for name, value in required.items():
            if not value.strip():
                issues.append(
                    _issue(
                        code="missing_traceability_fingerprint",
                        message=(
                            "Missing outbound call traceability fingerprint: "
                            f"{name}."
                        ),
                        path=("traceability", name),
                    ),
                )


def _validate_destination(
    prepared_call: PreparedCall,
    policy: OutboundCallCreationPolicy,
    issues: list[OutboundCallCreationIssue],
) -> None:
    destination = prepared_call.destination

    if (
        policy.require_destination_e164
        and destination.kind != DestinationKind.E164_PHONE_NUMBER
    ):
        issues.append(
            _issue(
                code="destination_not_e164",
                message=(
                    "Real outbound calls require an E.164 phone number "
                    "destination."
                ),
                path=("prepared_call", "destination", "kind"),
            ),
        )

    if (
        policy.require_destination_allowlist
        and destination.value not in policy.allowed_destination_phone_numbers
    ):
        issues.append(
            _issue(
                code="destination_not_allowlisted",
                message="Destination phone number is not allowlisted for real calls.",
                path=("prepared_call", "destination", "value"),
            ),
        )


def _validate_metadata(
    metadata: Mapping[str, str],
    policy: OutboundCallCreationPolicy,
    issues: list[OutboundCallCreationIssue],
    *,
    path: tuple[str | int, ...],
) -> None:
    if len(metadata) > policy.max_metadata_items:
        issues.append(
            _issue(
                code="too_many_metadata_items",
                message="Outbound call metadata exceeds the policy item limit.",
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


def _response_status(raw_response: Mapping[str, Any]) -> str:
    status = raw_response.get("status")
    if not isinstance(status, str):
        status = raw_response.get("state")
    if not isinstance(status, str):
        return ""
    return status.strip().lower()


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: OutboundCallCreationSeverity = OutboundCallCreationSeverity.ERROR,
) -> OutboundCallCreationIssue:
    return OutboundCallCreationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
