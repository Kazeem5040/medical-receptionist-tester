"""Application composition root.

This module assembles completed production components into one immutable
Application object. It does not start servers, expose routes, run workers,
perform calls, or evaluate transcripts.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from call_execution import CallExecutionService
from call_monitoring import CallSessionCollector
from call_orchestrator import CallOrchestrator
from conversation_contracts import ConversationContractBuilder
from runtime_config import RuntimeConfiguration, load_runtime_configuration
from scenarios import ScenarioManager
from vapi_adapter import VapiProviderAdapter
from vapi_client import VapiApiClient, VapiClientPolicy

from .enums import StartupState
from .models import Application, ApplicationServices, ApplicationStartupMetadata
from .policies import (
    DEFAULT_APPLICATION_BOOTSTRAP_POLICY,
    ApplicationBootstrapPolicy,
)
from .validation import application_mode_from_runtime, validate_application


def bootstrap_application(
    *,
    runtime_config: RuntimeConfiguration | None = None,
    environ: Mapping[str, str] | None = None,
    policy: ApplicationBootstrapPolicy = DEFAULT_APPLICATION_BOOTSTRAP_POLICY,
) -> Application:
    """Assemble and validate the production application dependency graph."""

    resolved_runtime_config = runtime_config or load_runtime_configuration(environ)

    scenario_manager = ScenarioManager()
    conversation_contract_builder = ConversationContractBuilder()
    vapi_provider_adapter = VapiProviderAdapter()
    call_orchestrator = CallOrchestrator(
        scenario_manager=scenario_manager,
        contract_builder=conversation_contract_builder,
        vapi_adapter=vapi_provider_adapter,
    )
    vapi_client = VapiApiClient(
        api_key=resolved_runtime_config.vapi.api_key.get_secret_value(),
        policy=_vapi_client_policy(resolved_runtime_config),
    )
    call_execution_service = CallExecutionService(vapi_client=vapi_client)
    call_monitoring_collector = CallSessionCollector()

    application = Application(
        runtime_config=resolved_runtime_config,
        services=ApplicationServices(
            scenario_manager=scenario_manager,
            conversation_contract_builder=conversation_contract_builder,
            vapi_provider_adapter=vapi_provider_adapter,
            call_orchestrator=call_orchestrator,
            vapi_client=vapi_client,
            call_execution_service=call_execution_service,
            call_monitoring_collector=call_monitoring_collector,
        ),
        startup_metadata=ApplicationStartupMetadata(
            application_version=policy.application_version,
            bootstrap_policy_version=policy.bootstrap_policy_version,
            mode=application_mode_from_runtime(
                resolved_runtime_config.application.environment,
            ),
            startup_state=StartupState.BOOTSTRAPPED,
            bootstrapped_at=datetime.now(UTC),
        ),
    )
    validate_application(application, policy).raise_if_invalid()
    return application


def _vapi_client_policy(configuration: RuntimeConfiguration) -> VapiClientPolicy:
    vapi = configuration.vapi
    return VapiClientPolicy(
        base_url=str(vapi.base_url).rstrip("/"),
        timeout_seconds=vapi.request_timeout_seconds,
        max_retries=vapi.retry.max_retries,
        backoff_initial_seconds=vapi.retry.backoff_initial_seconds,
        backoff_multiplier=vapi.retry.backoff_multiplier,
    )
