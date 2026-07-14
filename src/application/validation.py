"""Validation helpers for the assembled application graph."""

from __future__ import annotations

from call_execution import CallExecutionService
from call_monitoring import CallSessionCollector
from call_orchestrator import CallOrchestrator
from conversation_contracts import ConversationContractBuilder
from runtime_config import RuntimeConfiguration, RuntimeEnvironment
from scenarios import ScenarioManager
from vapi_adapter import VapiProviderAdapter
from vapi_client import VapiApiClient

from .enums import ApplicationMode, BootstrapSeverity, StartupState
from .errors import ApplicationBootstrapIssue, ApplicationBootstrapValidationResult
from .models import Application
from .policies import (
    DEFAULT_APPLICATION_BOOTSTRAP_POLICY,
    ApplicationBootstrapPolicy,
)


def validate_application(
    application: Application,
    policy: ApplicationBootstrapPolicy = DEFAULT_APPLICATION_BOOTSTRAP_POLICY,
) -> ApplicationBootstrapValidationResult:
    """Validate that the application dependency graph is complete and coherent."""

    issues: list[ApplicationBootstrapIssue] = []

    if policy.require_runtime_configuration and not isinstance(
        application.runtime_config,
        RuntimeConfiguration,
    ):
        issues.append(
            _issue(
                code="missing_runtime_configuration",
                message="Application must include RuntimeConfiguration.",
                path=("runtime_config",),
            ),
        )

    if application.startup_metadata.startup_state != StartupState.BOOTSTRAPPED:
        issues.append(
            _issue(
                code="application_not_bootstrapped",
                message="Application startup state must be bootstrapped.",
                path=("startup_metadata", "startup_state"),
            ),
        )

    expected_mode = application_mode_from_runtime(
        application.runtime_config.application.environment,
    )
    if application.startup_metadata.mode != expected_mode:
        issues.append(
            _issue(
                code="application_mode_mismatch",
                message="Application mode must match runtime environment.",
                path=("startup_metadata", "mode"),
            ),
        )

    _validate_services(application, policy, issues)
    _validate_runtime_compatibility(application, issues)

    return ApplicationBootstrapValidationResult.from_issues(issues)


def application_mode_from_runtime(
    environment: RuntimeEnvironment,
) -> ApplicationMode:
    """Convert runtime environment into application mode."""

    return ApplicationMode(environment.value)


def _validate_services(
    application: Application,
    policy: ApplicationBootstrapPolicy,
    issues: list[ApplicationBootstrapIssue],
) -> None:
    services = application.services

    if policy.require_domain_services:
        _require_instance(
            services.scenario_manager,
            ScenarioManager,
            "scenario_manager",
            issues,
        )
        _require_instance(
            services.conversation_contract_builder,
            ConversationContractBuilder,
            "conversation_contract_builder",
            issues,
        )
        _require_instance(
            services.vapi_provider_adapter,
            VapiProviderAdapter,
            "vapi_provider_adapter",
            issues,
        )

    if policy.require_workflow_services:
        _require_instance(
            services.call_orchestrator,
            CallOrchestrator,
            "call_orchestrator",
            issues,
        )
        _require_instance(
            services.call_execution_service,
            CallExecutionService,
            "call_execution_service",
            issues,
        )

    if policy.require_vapi_client:
        _require_instance(
            services.vapi_client,
            VapiApiClient,
            "vapi_client",
            issues,
        )

    if policy.require_monitoring_services:
        _require_instance(
            services.call_monitoring_collector,
            CallSessionCollector,
            "call_monitoring_collector",
            issues,
        )


def _validate_runtime_compatibility(
    application: Application,
    issues: list[ApplicationBootstrapIssue],
) -> None:
    runtime_environment = application.runtime_config.application.environment

    if runtime_environment == RuntimeEnvironment.PRODUCTION:
        if application.runtime_config.application.debug_enabled:
            issues.append(
                _issue(
                    code="production_debug_enabled",
                    message=(
                        "Bootstrapped production application must not enable debug."
                    ),
                    path=("runtime_config", "application", "debug_enabled"),
                ),
            )


def _require_instance(
    value: object,
    expected_type: type[object],
    field_name: str,
    issues: list[ApplicationBootstrapIssue],
) -> None:
    if isinstance(value, expected_type):
        return

    issues.append(
        _issue(
            code="invalid_dependency",
            message=f"Application dependency has invalid type: {field_name}.",
            path=("services", field_name),
        ),
    )


def _issue(
    *,
    code: str,
    message: str,
    path: tuple[str | int, ...],
    severity: BootstrapSeverity = BootstrapSeverity.ERROR,
) -> ApplicationBootstrapIssue:
    return ApplicationBootstrapIssue(
        code=code,
        message=message,
        path=path,
        severity=severity,
    )
