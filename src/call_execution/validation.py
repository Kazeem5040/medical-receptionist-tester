"""Validation helpers for call execution."""

from __future__ import annotations

from collections.abc import Mapping

from call_orchestrator import CallWorkflowStatus, PreparedCall
from vapi_client import VapiCreateAssistantResponse

from .enums import ExecutionSeverity, ProviderResponseState
from .errors import CallExecutionIssue, CallExecutionValidationResult
from .models import CallSubmissionResult
from .policies import DEFAULT_CALL_EXECUTION_POLICY, CallExecutionPolicy

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
        "recording_url",
        "patient_record",
    },
)


def validate_prepared_call_for_execution(
    prepared_call: PreparedCall,
    policy: CallExecutionPolicy = DEFAULT_CALL_EXECUTION_POLICY,
) -> CallExecutionValidationResult:
    """Validate that a prepared call is complete enough to submit."""

    issues: list[CallExecutionIssue] = []

    if prepared_call.status != CallWorkflowStatus.PREPARED:
        issues.append(
            _issue(
                code="prepared_call_not_ready",
                message="PreparedCall must have status 'prepared' before execution.",
                path=("status",),
            ),
        )

    if prepared_call.scenario_instance_fingerprint is None:
        issues.append(
            _issue(
                code="missing_scenario_instance_fingerprint",
                message="PreparedCall is missing scenario instance fingerprint.",
                path=("scenario_instance_fingerprint",),
            ),
        )

    if prepared_call.conversation_contract_fingerprint is None:
        issues.append(
            _issue(
                code="missing_conversation_contract_fingerprint",
                message="PreparedCall is missing conversation contract fingerprint.",
                path=("conversation_contract_fingerprint",),
            ),
        )

    if prepared_call.vapi_configuration_fingerprint is None:
        issues.append(
            _issue(
                code="missing_vapi_configuration_fingerprint",
                message="PreparedCall is missing Vapi configuration fingerprint.",
                path=("vapi_configuration_fingerprint",),
            ),
        )

    _validate_metadata(prepared_call.metadata, policy, issues)

    try:
        provider_payload = prepared_call.provider_payload()
    except Exception as error:
        issues.append(
            _issue(
                code="provider_payload_unavailable",
                message=(
                    "PreparedCall provider payload could not be extracted: "
                    f"{error}."
                ),
                path=("provider_payload",),
            ),
        )
    else:
        if not provider_payload:
            issues.append(
                _issue(
                    code="empty_provider_payload",
                    message="PreparedCall provider payload must not be empty.",
                    path=("provider_payload",),
                ),
            )

    return CallExecutionValidationResult.from_issues(issues)


def validate_provider_response(
    response: VapiCreateAssistantResponse,
) -> CallExecutionValidationResult:
    """Validate the provider response returned by the Vapi client."""

    issues: list[CallExecutionIssue] = []

    if not response.assistant_id.value.strip():
        issues.append(
            _issue(
                code="missing_provider_resource_id",
                message="Vapi response is missing a provider resource ID.",
                path=("assistant_id", "value"),
            ),
        )

    if not response.provider_status.value.strip():
        issues.append(
            _issue(
                code="missing_provider_status",
                message="Vapi response is missing provider status.",
                path=("provider_status",),
            ),
        )

    return CallExecutionValidationResult.from_issues(issues)


def validate_call_submission_result(
    result: CallSubmissionResult,
    policy: CallExecutionPolicy = DEFAULT_CALL_EXECUTION_POLICY,
) -> CallExecutionValidationResult:
    """Validate the final call submission result before returning it."""

    issues: list[CallExecutionIssue] = []

    if result.provider_response.provider_state not in policy.acceptable_provider_states:
        issues.append(
            _issue(
                code="unacceptable_provider_state",
                message="Provider response state is not acceptable for submission.",
                path=("provider_response", "provider_state"),
            ),
        )

    traceability = result.traceability
    required_fingerprints = {
        "scenario_template_fingerprint": traceability.scenario_template_fingerprint,
        "scenario_instance_fingerprint": traceability.scenario_instance_fingerprint,
        "conversation_contract_fingerprint": (
            traceability.conversation_contract_fingerprint
        ),
        "vapi_configuration_fingerprint": traceability.vapi_configuration_fingerprint,
        "request_fingerprint": traceability.request_fingerprint,
    }
    for name, value in required_fingerprints.items():
        if not value.strip():
            issues.append(
                _issue(
                    code="missing_traceability_fingerprint",
                    message=f"Traceability fingerprint is missing: {name}.",
                    path=("traceability", name),
                ),
            )

    _validate_metadata(result.metadata, policy, issues)

    return CallExecutionValidationResult.from_issues(issues)


def normalize_provider_state(
    response: VapiCreateAssistantResponse,
) -> ProviderResponseState:
    """Convert a Vapi client response into an execution-level provider state."""

    if response.response_status.value == "success":
        return ProviderResponseState.ACCEPTED
    if response.response_status.value == "failed":
        return ProviderResponseState.REJECTED
    return ProviderResponseState.UNKNOWN


def _validate_metadata(
    metadata: Mapping[str, str],
    policy: CallExecutionPolicy,
    issues: list[CallExecutionIssue],
) -> None:
    if len(metadata) > policy.max_metadata_items:
        issues.append(
            _issue(
                code="too_many_metadata_items",
                message="Execution metadata exceeds the policy item limit.",
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


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: ExecutionSeverity = ExecutionSeverity.ERROR,
) -> CallExecutionIssue:
    return CallExecutionIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
