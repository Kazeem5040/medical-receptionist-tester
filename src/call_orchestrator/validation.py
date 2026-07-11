"""Orchestration-level validation for call preparation requests."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .enums import CallOrchestrationValidationSeverity, DestinationKind
from .errors import CallOrchestrationIssue, CallOrchestrationValidationResult
from .models import CallPreparationRequest, PreparedCall
from .policies import DEFAULT_CALL_ORCHESTRATION_POLICY, CallOrchestrationPolicy

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
        "provider_payload",
        "vapi_payload",
        "openai_prompt",
        "evaluator_instruction",
        "transcript",
        "recording",
        "patient_record",
    },
)
E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


def validate_call_preparation_request(
    request: CallPreparationRequest,
    policy: CallOrchestrationPolicy = DEFAULT_CALL_ORCHESTRATION_POLICY,
) -> CallOrchestrationValidationResult:
    """Validate only orchestration-level request concerns."""

    issues: list[CallOrchestrationIssue] = []

    _validate_destination(request, policy, issues)
    _validate_requested_duration(request, policy, issues)
    _validate_metadata(request.metadata, policy, issues)

    return CallOrchestrationValidationResult.from_issues(issues)


def validate_prepared_call(
    prepared_call: PreparedCall,
) -> CallOrchestrationValidationResult:
    """Validate a prepared call artifact before returning it."""

    issues: list[CallOrchestrationIssue] = []

    if prepared_call.scenario_instance_fingerprint is None:
        issues.append(
            _issue(
                code="missing_scenario_instance_fingerprint",
                message="Prepared call must preserve scenario instance fingerprint.",
                path=("scenario_instance_fingerprint",),
            ),
        )

    if prepared_call.conversation_contract_fingerprint is None:
        issues.append(
            _issue(
                code="missing_conversation_contract_fingerprint",
                message=(
                    "Prepared call must preserve conversation contract fingerprint."
                ),
                path=("conversation_contract_fingerprint",),
            ),
        )

    if prepared_call.vapi_configuration_fingerprint is None:
        issues.append(
            _issue(
                code="missing_vapi_configuration_fingerprint",
                message="Prepared call must preserve Vapi configuration fingerprint.",
                path=("vapi_configuration_fingerprint",),
            ),
        )

    _validate_no_forbidden_provider_payload_keys(
        prepared_call.provider_payload(),
        issues,
    )

    return CallOrchestrationValidationResult.from_issues(issues)


def _validate_destination(
    request: CallPreparationRequest,
    policy: CallOrchestrationPolicy,
    issues: list[CallOrchestrationIssue],
) -> None:
    destination = request.destination

    if destination.kind == DestinationKind.E164_PHONE_NUMBER:
        if E164_PATTERN.fullmatch(destination.value) is None:
            issues.append(
                _issue(
                    code="invalid_e164_destination",
                    message="Destination phone number must be valid E.164.",
                    path=("destination", "value"),
                ),
            )
        if destination.value not in policy.allowed_destination_phone_numbers:
            issues.append(
                _issue(
                    code="destination_not_allowlisted",
                    message="Destination phone number is not allowlisted.",
                    path=("destination", "value"),
                ),
            )
        return

    if destination.value not in policy.allowed_destination_identifiers:
        issues.append(
            _issue(
                code="destination_not_allowlisted",
                message="Destination identifier is not allowlisted.",
                path=("destination", "value"),
            ),
        )


def _validate_requested_duration(
    request: CallPreparationRequest,
    policy: CallOrchestrationPolicy,
    issues: list[CallOrchestrationIssue],
) -> None:
    duration = request.requested_call_duration_seconds
    if duration is None:
        return

    if duration < policy.min_requested_call_duration_seconds:
        issues.append(
            _issue(
                code="requested_duration_too_low",
                message=(
                    "Requested call duration is below the orchestration policy "
                    "minimum."
                ),
                path=("requested_call_duration_seconds",),
            ),
        )

    if duration > policy.max_requested_call_duration_seconds:
        issues.append(
            _issue(
                code="requested_duration_too_high",
                message=(
                    "Requested call duration exceeds the orchestration policy "
                    "maximum."
                ),
                path=("requested_call_duration_seconds",),
            ),
        )


def _validate_metadata(
    metadata: Mapping[str, str],
    policy: CallOrchestrationPolicy,
    issues: list[CallOrchestrationIssue],
) -> None:
    if len(metadata) > policy.max_metadata_items:
        issues.append(
            _issue(
                code="too_many_metadata_items",
                message="Request metadata exceeds the policy item limit.",
                path=("metadata",),
            ),
        )

    for key, value in metadata.items():
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in FORBIDDEN_METADATA_KEYS:
            issues.append(
                _issue(
                    code="forbidden_metadata_key",
                    message=f"Forbidden metadata key: {key}.",
                    path=("metadata", key),
                ),
            )

        if len(key) > policy.max_metadata_key_length:
            issues.append(
                _issue(
                    code="metadata_key_too_long",
                    message=f"Metadata key is too long: {key}.",
                    path=("metadata", key),
                ),
            )

        if len(value) > policy.max_metadata_value_length:
            issues.append(
                _issue(
                    code="metadata_value_too_long",
                    message=f"Metadata value is too long for key: {key}.",
                    path=("metadata", key),
                ),
            )


def _validate_no_forbidden_provider_payload_keys(
    payload: object,
    issues: list[CallOrchestrationIssue],
) -> None:
    forbidden_keys = {
        "apiKey",
        "api_key",
        "authorization",
        "secret",
        "token",
        "destination",
        "destinationPhoneNumber",
        "phoneNumber",
        "phoneNumberId",
        "customer",
        "server",
        "serverUrl",
        "credentials",
        "credentialIds",
    }
    for key in sorted(_payload_keys(payload).intersection(forbidden_keys)):
        issues.append(
            _issue(
                code="forbidden_provider_payload_key",
                message=f"Forbidden provider payload key is present: {key}.",
                path=("provider_payload", key),
            ),
        )


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        payload_keys = {str(key) for key in value}
        for item in value.values():
            payload_keys.update(_payload_keys(item))
        return payload_keys

    if isinstance(value, list | tuple):
        payload_keys = set()
        for item in value:
            payload_keys.update(_payload_keys(item))
        return payload_keys

    return set()


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: CallOrchestrationValidationSeverity = (
        CallOrchestrationValidationSeverity.ERROR
    ),
) -> CallOrchestrationIssue:
    return CallOrchestrationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
