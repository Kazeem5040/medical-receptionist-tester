from __future__ import annotations

from application import ApplicationMode, StartupState, bootstrap_application
from call_execution import CallExecutionService
from call_monitoring import CallSessionCollector
from call_orchestrator import CallOrchestrator
from conversation_contracts import ConversationContractBuilder
from runtime_config import RuntimeEnvironment, load_runtime_configuration
from scenarios import ScenarioManager
from vapi_adapter import VapiProviderAdapter
from vapi_client import VapiApiClient


def test_bootstrap_application_assembles_completed_services() -> None:
    application = bootstrap_application(environ=_required_env())

    assert isinstance(application.services.scenario_manager, ScenarioManager)
    assert isinstance(
        application.services.conversation_contract_builder,
        ConversationContractBuilder,
    )
    assert isinstance(application.services.vapi_provider_adapter, VapiProviderAdapter)
    assert isinstance(application.services.call_orchestrator, CallOrchestrator)
    assert isinstance(application.services.vapi_client, VapiApiClient)
    assert isinstance(
        application.services.call_execution_service,
        CallExecutionService,
    )
    assert isinstance(
        application.services.call_monitoring_collector,
        CallSessionCollector,
    )


def test_bootstrap_uses_runtime_configuration_values_for_vapi_client() -> None:
    application = bootstrap_application(
        environ=_required_env(
            VAPI_BASE_URL="https://vapi.example.com",
            VAPI_TIMEOUT_SECONDS="12",
            VAPI_MAX_RETRIES="5",
            VAPI_BACKOFF_INITIAL_SECONDS="0.25",
            VAPI_BACKOFF_MULTIPLIER="3",
        ),
    )

    assert application.services.vapi_client.policy.base_url == (
        "https://vapi.example.com"
    )
    assert application.services.vapi_client.policy.timeout_seconds == 12
    assert application.services.vapi_client.policy.max_retries == 5
    assert application.services.vapi_client.policy.backoff_initial_seconds == 0.25
    assert application.services.vapi_client.policy.backoff_multiplier == 3


def test_bootstrap_accepts_preloaded_runtime_configuration() -> None:
    runtime_config = load_runtime_configuration(
        _required_env(APP_ENV="test"),
    )

    application = bootstrap_application(runtime_config=runtime_config)

    assert application.runtime_config is runtime_config
    assert application.runtime_config.application.environment == RuntimeEnvironment.TEST
    assert application.startup_metadata.mode == ApplicationMode.TEST


def test_bootstrap_records_startup_metadata() -> None:
    application = bootstrap_application(environ=_required_env(APP_ENV="staging"))

    assert application.startup_metadata.application_version == "0.1.0"
    assert application.startup_metadata.bootstrap_policy_version == "1.0"
    assert application.startup_metadata.mode == ApplicationMode.STAGING
    assert application.startup_metadata.startup_state == StartupState.BOOTSTRAPPED
    assert application.startup_metadata.bootstrapped_at.tzinfo is not None


def test_bootstrap_does_not_execute_calls_or_monitor_sessions() -> None:
    application = bootstrap_application(environ=_required_env())

    assert hasattr(application.services.call_orchestrator, "prepare_call")
    assert hasattr(application.services.call_execution_service, "execute")
    assert hasattr(application.services.call_monitoring_collector, "collect")


def _required_env(**overrides: str) -> dict[str, str]:
    env = {
        "VAPI_API_KEY": "test-vapi-key",
        "OPENAI_API_KEY": "test-openai-key",
    }
    env.update(overrides)
    return env
