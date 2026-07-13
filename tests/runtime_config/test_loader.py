from __future__ import annotations

import pytest

from runtime_config import (
    DeploymentTarget,
    RuntimeConfigurationError,
    RuntimeEnvironment,
    load_runtime_configuration,
)


def test_loader_reads_required_environment_and_defaults() -> None:
    configuration = load_runtime_configuration(_required_env())

    assert configuration.application.service_name == "ai-receptionist-tester"
    assert configuration.application.environment == RuntimeEnvironment.DEVELOPMENT
    assert configuration.application.deployment_target == DeploymentTarget.LOCAL
    assert configuration.application.debug_enabled is False
    assert str(configuration.vapi.base_url) == "https://api.vapi.ai/"
    assert configuration.vapi.request_timeout_seconds == 30.0
    assert configuration.vapi.retry.max_retries == 2
    assert str(configuration.openai.base_url) == "https://api.openai.com/v1"
    assert configuration.openai.realtime_model == "gpt-realtime"
    assert configuration.openai.responses_model == "gpt-5"
    assert configuration.features.call_monitoring_enabled is True


def test_loader_applies_environment_overrides() -> None:
    env = _required_env(
        APP_SERVICE_NAME="medical-ai-receptionist-tester",
        APP_ENV="staging",
        APP_DEPLOYMENT_TARGET="docker",
        APP_DEBUG="true",
        APP_DEPLOYMENT_REGION="us-east-1",
        APP_PUBLIC_BASE_URL="https://tester.example.com",
        VAPI_BASE_URL="https://vapi.example.com",
        VAPI_TIMEOUT_SECONDS="12.5",
        VAPI_MAX_RETRIES="4",
        VAPI_BACKOFF_INITIAL_SECONDS="0.5",
        VAPI_BACKOFF_MULTIPLIER="3",
        OPENAI_BASE_URL="https://openai.example.com/v1",
        OPENAI_REALTIME_MODEL="gpt-realtime-test",
        OPENAI_RESPONSES_MODEL="gpt-5-test",
        OPENAI_TIMEOUT_SECONDS="20",
        FEATURE_REAL_CALLS_ENABLED="yes",
        FEATURE_CALL_MONITORING_ENABLED="no",
        FEATURE_TRANSCRIPT_EVALUATION_ENABLED="on",
        FEATURE_BUG_REPORTS_ENABLED="1",
    )

    configuration = load_runtime_configuration(env)

    assert configuration.application.service_name == "medical-ai-receptionist-tester"
    assert configuration.application.environment == RuntimeEnvironment.STAGING
    assert configuration.application.deployment_target == DeploymentTarget.DOCKER
    assert configuration.application.debug_enabled is True
    assert configuration.application.deployment_region == "us-east-1"
    assert str(configuration.application.public_base_url) == (
        "https://tester.example.com/"
    )
    assert str(configuration.vapi.base_url) == "https://vapi.example.com/"
    assert configuration.vapi.request_timeout_seconds == 12.5
    assert configuration.vapi.retry.max_retries == 4
    assert configuration.vapi.retry.backoff_initial_seconds == 0.5
    assert configuration.vapi.retry.backoff_multiplier == 3
    assert str(configuration.openai.base_url) == "https://openai.example.com/v1"
    assert configuration.openai.realtime_model == "gpt-realtime-test"
    assert configuration.openai.responses_model == "gpt-5-test"
    assert configuration.openai.request_timeout_seconds == 20
    assert configuration.features.real_calls_enabled is True
    assert configuration.features.call_monitoring_enabled is False
    assert configuration.features.transcript_evaluation_enabled is True
    assert configuration.features.bug_reports_enabled is True


def test_loader_rejects_missing_required_api_keys() -> None:
    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration({})

    assert "missing_required_environment_variable" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_rejects_invalid_boolean_value() -> None:
    env = _required_env(APP_DEBUG="maybe")

    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration(env)

    assert "invalid_environment_value" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_rejects_invalid_provider_url() -> None:
    env = _required_env(VAPI_BASE_URL="not-a-url")

    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration(env)

    assert "invalid_runtime_configuration" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_rejects_negative_timeout() -> None:
    env = _required_env(OPENAI_TIMEOUT_SECONDS="-1")

    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration(env)

    assert "invalid_runtime_configuration" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_rejects_debug_mode_in_production() -> None:
    env = _required_env(APP_ENV="production", APP_DEBUG="true")

    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration(env)

    assert "debug_enabled_in_production" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_rejects_production_real_calls_without_public_base_url() -> None:
    env = _required_env(
        APP_ENV="production",
        FEATURE_REAL_CALLS_ENABLED="true",
    )

    with pytest.raises(RuntimeConfigurationError) as error:
        load_runtime_configuration(env)

    assert "missing_public_base_url_for_real_calls" in {
        issue.code for issue in error.value.result.errors
    }


def test_loader_does_not_expose_secret_values_in_model_dump() -> None:
    configuration = load_runtime_configuration(_required_env())
    dumped = str(configuration.model_dump())

    assert "test-vapi-key" not in dumped
    assert "test-openai-key" not in dumped


def _required_env(**overrides: str) -> dict[str, str]:
    env = {
        "VAPI_API_KEY": "test-vapi-key",
        "OPENAI_API_KEY": "test-openai-key",
    }
    env.update(overrides)
    return env
