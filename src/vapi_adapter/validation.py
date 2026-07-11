"""Validation for generated Vapi assistant configuration."""

from __future__ import annotations

from .enums import VapiMappingStatus, VapiValidationSeverity
from .errors import VapiConfigurationIssue, VapiConfigurationValidationResult
from .models import VapiAssistantConfiguration

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
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
    },
)

CRITICAL_CONTRACT_SECTIONS = frozenset(
    {
        "patient_identity",
        "objectives",
        "known_information",
        "unknown_information",
        "disclosure_rules",
        "termination_rules",
        "safety_instruction",
        "knowledge_boundaries",
        "forbidden_behaviors",
    },
)


def validate_vapi_configuration(
    configuration: VapiAssistantConfiguration,
) -> VapiConfigurationValidationResult:
    """Validate generated Vapi configuration and return structured issues."""

    issues: list[VapiConfigurationIssue] = []

    if configuration.source_traceability.conversation_contract_fingerprint is None:
        issues.append(
            _issue(
                code="missing_contract_fingerprint",
                message="Vapi configuration must preserve contract fingerprint.",
                path=("source_traceability", "conversation_contract_fingerprint"),
            ),
        )

    if not configuration.generated_instructions.system_message.strip():
        issues.append(
            _issue(
                code="missing_generated_instructions",
                message="Vapi configuration must include generated instructions.",
                path=("generated_instructions", "system_message"),
            ),
        )

    _validate_required_coverage(configuration, issues)
    _validate_no_forbidden_payload_keys(configuration, issues)

    return VapiConfigurationValidationResult.from_issues(issues)


def _validate_required_coverage(
    configuration: VapiAssistantConfiguration,
    issues: list[VapiConfigurationIssue],
) -> None:
    coverage_by_section = {
        item.contract_section: item for item in configuration.mapping_coverage
    }
    for section in sorted(CRITICAL_CONTRACT_SECTIONS):
        coverage = coverage_by_section.get(section)
        if coverage is None:
            issues.append(
                _issue(
                    code="missing_mapping_coverage",
                    message=f"Contract section is not represented: {section}.",
                    path=("mapping_coverage", section),
                ),
            )
            continue

        if coverage.status == VapiMappingStatus.NOT_APPLICABLE:
            issues.append(
                _issue(
                    code="critical_section_not_represented",
                    message=f"Critical contract section is not represented: {section}.",
                    path=("mapping_coverage", section),
                ),
            )


def _validate_no_forbidden_payload_keys(
    configuration: VapiAssistantConfiguration,
    issues: list[VapiConfigurationIssue],
) -> None:
    payload = configuration.to_vapi_payload()
    found = sorted(_find_forbidden_keys(payload))
    for key in found:
        issues.append(
            _issue(
                code="forbidden_provider_payload_key",
                message=f"Forbidden key must not appear in adapter output: {key}.",
                path=("to_vapi_payload", key),
            ),
        )


def _find_forbidden_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        matching_keys = {
            str(key) for key in value if str(key) in FORBIDDEN_PAYLOAD_KEYS
        }
        for item in value.values():
            matching_keys.update(_find_forbidden_keys(item))
        return matching_keys

    if isinstance(value, list | tuple):
        matching_keys = set()
        for item in value:
            matching_keys.update(_find_forbidden_keys(item))
        return matching_keys

    return set()


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: VapiValidationSeverity = VapiValidationSeverity.ERROR,
) -> VapiConfigurationIssue:
    return VapiConfigurationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
