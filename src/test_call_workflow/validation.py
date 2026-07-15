"""Use-case-level validation for the test-call workflow."""

from __future__ import annotations

from collections.abc import Mapping

from call_execution import CallSubmissionResult, ExecutionStatus
from call_orchestrator import CallPreparationRequest, PreparedCall

from .enums import (
    ProviderCapabilityState,
    TestCallWorkflowSeverity,
    TestCallWorkflowStatus,
)
from .errors import TestCallWorkflowIssue, TestCallWorkflowValidationResult
from .models import TestCallStartResult
from .policies import (
    DEFAULT_TEST_CALL_WORKFLOW_POLICY,
    TestCallWorkflowPolicy,
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
        "recording_url",
        "medical_record",
        "patient_record",
        "openai_api_key",
        "vapi_api_key",
    },
)


def validate_test_call_request(
    request: CallPreparationRequest,
    policy: TestCallWorkflowPolicy = DEFAULT_TEST_CALL_WORKFLOW_POLICY,
) -> TestCallWorkflowValidationResult:
    """Validate use-case-level request requirements."""

    issues: list[TestCallWorkflowIssue] = []

    if policy.require_real_calls_feature_flag and not policy.real_calls_enabled:
        issues.append(
            _issue(
                code="feature_disabled",
                message="Real test-call workflow submission is disabled by policy.",
                path=("policy", "real_calls_enabled"),
            ),
        )

    _validate_metadata(request.metadata, issues, path=("metadata",))

    return TestCallWorkflowValidationResult.from_issues(issues)


def validate_prepared_call_transition(
    prepared_call: PreparedCall | None,
    policy: TestCallWorkflowPolicy = DEFAULT_TEST_CALL_WORKFLOW_POLICY,
) -> TestCallWorkflowValidationResult:
    """Validate the transition from request to PreparedCall."""

    issues: list[TestCallWorkflowIssue] = []

    if prepared_call is None:
        issues.append(
            _issue(
                code="prepared_call_missing",
                message="CallOrchestrator did not return a PreparedCall.",
                path=("prepared_call",),
            ),
        )
        return TestCallWorkflowValidationResult.from_issues(issues)

    if policy.require_prepared_call and not prepared_call.preparation_id.strip():
        issues.append(
            _issue(
                code="prepared_call_not_executable",
                message="PreparedCall is missing preparation_id.",
                path=("prepared_call", "preparation_id"),
            ),
        )

    if prepared_call.vapi_configuration_fingerprint is None:
        issues.append(
            _issue(
                code="prepared_call_not_executable",
                message="PreparedCall is missing Vapi configuration fingerprint.",
                path=("prepared_call", "vapi_configuration_fingerprint"),
            ),
        )

    return TestCallWorkflowValidationResult.from_issues(issues)


def validate_submission_transition(
    prepared_call: PreparedCall,
    submission_result: CallSubmissionResult | None,
    policy: TestCallWorkflowPolicy = DEFAULT_TEST_CALL_WORKFLOW_POLICY,
) -> TestCallWorkflowValidationResult:
    """Validate the transition from PreparedCall to CallSubmissionResult."""

    issues: list[TestCallWorkflowIssue] = []

    if submission_result is None:
        issues.append(
            _issue(
                code="call_submission_failed",
                message="CallExecutionService did not return CallSubmissionResult.",
                path=("submission_result",),
            ),
        )
        return TestCallWorkflowValidationResult.from_issues(issues)

    if policy.require_submission_result and not submission_result.submission_id.strip():
        issues.append(
            _issue(
                code="call_submission_failed",
                message="CallSubmissionResult is missing submission_id.",
                path=("submission_result", "submission_id"),
            ),
        )

    _validate_preparation_submission_traceability(
        prepared_call,
        submission_result,
        issues,
    )

    if (
        not policy.allow_provider_rejected_result
        and submission_result.execution_status == ExecutionStatus.REJECTED
    ):
        issues.append(
            _issue(
                code="call_submission_failed",
                message="Provider-rejected results are not allowed by policy.",
                path=("submission_result", "execution_status"),
            ),
        )

    return TestCallWorkflowValidationResult.from_issues(issues)


def validate_test_call_start_result(
    result: TestCallStartResult,
    policy: TestCallWorkflowPolicy = DEFAULT_TEST_CALL_WORKFLOW_POLICY,
) -> TestCallWorkflowValidationResult:
    """Validate the final TestCallStartResult."""

    issues: list[TestCallWorkflowIssue] = []

    if policy.require_result_fingerprint and not result.result_fingerprint.strip():
        issues.append(
            _issue(
                code="workflow_result_invalid",
                message="TestCallStartResult is missing result_fingerprint.",
                path=("result_fingerprint",),
            ),
        )

    if result.workflow_id != result.traceability.workflow_id:
        issues.append(
            _issue(
                code="workflow_result_invalid",
                message="Workflow ID must match traceability workflow ID.",
                path=("traceability", "workflow_id"),
            ),
        )

    if result.status == TestCallWorkflowStatus.SUBMITTED:
        if result.submission_result.execution_status != ExecutionStatus.ACCEPTED:
            issues.append(
                _issue(
                    code="workflow_result_invalid",
                    message="Submitted workflow must have accepted provider result.",
                    path=("status",),
                ),
            )

    if result.status == TestCallWorkflowStatus.REJECTED:
        if result.submission_result.execution_status != ExecutionStatus.REJECTED:
            issues.append(
                _issue(
                    code="workflow_result_invalid",
                    message="Rejected workflow must have rejected provider result.",
                    path=("status",),
                ),
            )

    _validate_capability_state(result, policy, issues)
    _validate_metadata(result.metadata, issues, path=("metadata",))

    return TestCallWorkflowValidationResult.from_issues(issues)


def _validate_preparation_submission_traceability(
    prepared_call: PreparedCall,
    submission_result: CallSubmissionResult,
    issues: list[TestCallWorkflowIssue],
) -> None:
    traceability = submission_result.traceability
    expected_pairs = {
        "preparation_id": (
            prepared_call.preparation_id,
            traceability.preparation_id,
        ),
        "idempotency_key": (
            prepared_call.idempotency_key,
            traceability.idempotency_key,
        ),
        "source_scenario_id": (
            prepared_call.source_scenario_id,
            traceability.source_scenario_id,
        ),
        "source_scenario_version": (
            str(prepared_call.source_scenario_version),
            str(traceability.source_scenario_version),
        ),
        "scenario_instance_fingerprint": (
            prepared_call.scenario_instance_fingerprint or "",
            traceability.scenario_instance_fingerprint,
        ),
        "conversation_contract_fingerprint": (
            prepared_call.conversation_contract_fingerprint or "",
            traceability.conversation_contract_fingerprint,
        ),
        "vapi_configuration_fingerprint": (
            prepared_call.vapi_configuration_fingerprint or "",
            traceability.vapi_configuration_fingerprint,
        ),
        "request_fingerprint": (
            prepared_call.request_fingerprint,
            traceability.request_fingerprint,
        ),
        "scenario_seed": (
            prepared_call.scenario_seed,
            traceability.scenario_seed,
        ),
    }

    for field_name, (prepared_value, submission_value) in expected_pairs.items():
        if prepared_value != submission_value:
            issues.append(
                _issue(
                    code="preparation_submission_traceability_mismatch",
                    message=(
                        "PreparedCall and CallSubmissionResult traceability "
                        f"mismatch: {field_name}."
                    ),
                    path=("submission_result", "traceability", field_name),
                ),
            )


def _validate_capability_state(
    result: TestCallStartResult,
    policy: TestCallWorkflowPolicy,
    issues: list[TestCallWorkflowIssue],
) -> None:
    provider_call_id = result.submission_result.provider_response.provider_call_id
    provider_resource_id = (
        result.submission_result.provider_response.provider_resource_id
    )

    if result.provider_capability_state in {
        ProviderCapabilityState.OUTBOUND_CALL_SUBMITTED,
        ProviderCapabilityState.OUTBOUND_CALL_ID_AVAILABLE,
    } and provider_call_id is None:
        issues.append(
            _issue(
                code="provider_capability_misrepresented",
                message=(
                    "Result cannot claim outbound call submission or call ID "
                    "availability without provider_call_id."
                ),
                path=("provider_capability_state",),
            ),
        )

    if (
        policy.fail_if_outbound_call_not_created
        and result.provider_capability_state
        in {
            ProviderCapabilityState.ASSISTANT_CREATED,
            ProviderCapabilityState.OUTBOUND_CALL_NOT_YET_STARTED,
            ProviderCapabilityState.UNKNOWN,
        }
    ):
        issues.append(
            _issue(
                code="provider_capability_misrepresented",
                message="Policy requires a real outbound call submission.",
                path=("provider_capability_state",),
            ),
        )

    if (
        result.provider_capability_state == ProviderCapabilityState.ASSISTANT_CREATED
        and not provider_resource_id.strip()
    ):
        issues.append(
            _issue(
                code="provider_capability_misrepresented",
                message="Assistant-created capability requires provider_resource_id.",
                path=("submission_result", "provider_response", "provider_resource_id"),
            ),
        )


def _validate_metadata(
    metadata: Mapping[str, str],
    issues: list[TestCallWorkflowIssue],
    *,
    path: tuple[str | int, ...],
) -> None:
    for key in metadata:
        normalized_key = key.lower().replace("-", "_")
        if normalized_key in FORBIDDEN_METADATA_KEYS:
            issues.append(
                _issue(
                    code="forbidden_metadata",
                    message=f"Forbidden workflow metadata key: {key}.",
                    path=path + (key,),
                ),
            )


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: TestCallWorkflowSeverity = TestCallWorkflowSeverity.ERROR,
) -> TestCallWorkflowIssue:
    return TestCallWorkflowIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
