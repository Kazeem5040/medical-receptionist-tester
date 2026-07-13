"""Validation helpers for runtime configuration."""

from __future__ import annotations

from collections.abc import Mapping

from .enums import RuntimeEnvironment, RuntimeValidationSeverity
from .errors import RuntimeConfigurationIssue, RuntimeConfigurationValidationResult
from .models import RuntimeConfiguration
from .policies import (
    DEFAULT_RUNTIME_CONFIGURATION_POLICY,
    RuntimeConfigurationPolicy,
)


def validate_required_environment(
    environ: Mapping[str, str],
    policy: RuntimeConfigurationPolicy = DEFAULT_RUNTIME_CONFIGURATION_POLICY,
) -> RuntimeConfigurationValidationResult:
    """Validate required runtime environment variables exist."""

    issues: list[RuntimeConfigurationIssue] = []
    for variable_name in policy.required_environment_variables:
        if not environ.get(variable_name, "").strip():
            issues.append(
                _issue(
                    code="missing_required_environment_variable",
                    message=f"Missing required environment variable: {variable_name}.",
                    path=("environment", variable_name),
                ),
            )

    return RuntimeConfigurationValidationResult.from_issues(issues)


def validate_runtime_configuration(
    configuration: RuntimeConfiguration,
) -> RuntimeConfigurationValidationResult:
    """Validate cross-field runtime configuration rules."""

    issues: list[RuntimeConfigurationIssue] = []

    if not configuration.vapi.api_key.get_secret_value().strip():
        issues.append(
            _issue(
                code="missing_vapi_api_key",
                message="Vapi API key must be configured.",
                path=("vapi", "api_key"),
            ),
        )

    if not configuration.openai.api_key.get_secret_value().strip():
        issues.append(
            _issue(
                code="missing_openai_api_key",
                message="OpenAI API key must be configured.",
                path=("openai", "api_key"),
            ),
        )

    if (
        configuration.application.environment == RuntimeEnvironment.PRODUCTION
        and configuration.application.debug_enabled
    ):
        issues.append(
            _issue(
                code="debug_enabled_in_production",
                message="Debug mode must not be enabled in production.",
                path=("application", "debug_enabled"),
            ),
        )

    if (
        configuration.application.environment == RuntimeEnvironment.PRODUCTION
        and configuration.features.real_calls_enabled
        and configuration.application.public_base_url is None
    ):
        issues.append(
            _issue(
                code="missing_public_base_url_for_real_calls",
                message=(
                    "Production real-call mode requires APP_PUBLIC_BASE_URL "
                    "for provider callbacks."
                ),
                path=("application", "public_base_url"),
            ),
        )

    return RuntimeConfigurationValidationResult.from_issues(issues)


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: RuntimeValidationSeverity = RuntimeValidationSeverity.ERROR,
) -> RuntimeConfigurationIssue:
    return RuntimeConfigurationIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
