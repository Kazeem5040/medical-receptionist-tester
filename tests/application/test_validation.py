from __future__ import annotations

from datetime import UTC, datetime

from application import (
    Application,
    ApplicationMode,
    ApplicationServices,
    ApplicationStartupMetadata,
    StartupState,
    application_mode_from_runtime,
    bootstrap_application,
    validate_application,
)
from runtime_config import RuntimeEnvironment


def test_validate_application_accepts_bootstrapped_graph() -> None:
    application = bootstrap_application(environ=_required_env())

    result = validate_application(application)

    assert result.is_valid


def test_validate_application_detects_mode_mismatch() -> None:
    application = bootstrap_application(environ=_required_env(APP_ENV="production"))
    mismatched = application.model_copy(
        update={
            "startup_metadata": application.startup_metadata.model_copy(
                update={"mode": ApplicationMode.DEVELOPMENT},
            ),
        },
    )

    result = validate_application(mismatched)

    assert not result.is_valid
    assert "application_mode_mismatch" in {issue.code for issue in result.errors}


def test_validate_application_detects_invalid_startup_state() -> None:
    application = bootstrap_application(environ=_required_env())
    invalid = application.model_copy(
        update={
            "startup_metadata": application.startup_metadata.model_copy(
                update={"startup_state": StartupState.FAILED},
            ),
        },
    )

    result = validate_application(invalid)

    assert not result.is_valid
    assert "application_not_bootstrapped" in {issue.code for issue in result.errors}


def test_validate_application_detects_invalid_dependency_graph() -> None:
    application = bootstrap_application(environ=_required_env())
    invalid_services = ApplicationServices.model_construct(
        scenario_manager=object(),
        conversation_contract_builder=application.services.conversation_contract_builder,
        vapi_provider_adapter=application.services.vapi_provider_adapter,
        call_orchestrator=application.services.call_orchestrator,
        vapi_client=application.services.vapi_client,
        call_execution_service=application.services.call_execution_service,
        call_monitoring_collector=application.services.call_monitoring_collector,
        test_call_coordinator=application.services.test_call_coordinator,
    )
    invalid = Application.model_construct(
        runtime_config=application.runtime_config,
        services=invalid_services,
        startup_metadata=application.startup_metadata,
    )

    result = validate_application(invalid)

    assert not result.is_valid
    assert "invalid_dependency" in {issue.code for issue in result.errors}


def test_application_mode_mapping_matches_runtime_environment() -> None:
    assert application_mode_from_runtime(RuntimeEnvironment.DEVELOPMENT) == (
        ApplicationMode.DEVELOPMENT
    )
    assert application_mode_from_runtime(RuntimeEnvironment.PRODUCTION) == (
        ApplicationMode.PRODUCTION
    )


def test_startup_metadata_can_be_constructed_for_validation_tests() -> None:
    metadata = ApplicationStartupMetadata(
        application_version="0.1.0",
        bootstrap_policy_version="1.0",
        mode=ApplicationMode.TEST,
        startup_state=StartupState.BOOTSTRAPPED,
        bootstrapped_at=datetime.now(UTC),
    )

    assert metadata.mode == ApplicationMode.TEST


def _required_env(**overrides: str) -> dict[str, str]:
    env = {
        "VAPI_API_KEY": "test-vapi-key",
        "OPENAI_API_KEY": "test-openai-key",
        "APP_PUBLIC_BASE_URL": "https://tester.example.com",
    }
    env.update(overrides)
    return env
