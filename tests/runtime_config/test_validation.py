from __future__ import annotations

from pydantic import SecretStr

from runtime_config import (
    ApplicationConfiguration,
    FeatureFlagConfiguration,
    OpenAIConfiguration,
    RuntimeConfiguration,
    RuntimeEnvironment,
    VapiConfiguration,
    validate_required_environment,
    validate_runtime_configuration,
)


def test_validate_required_environment_accepts_required_keys() -> None:
    result = validate_required_environment(
        {
            "VAPI_API_KEY": "test-vapi-key",
            "OPENAI_API_KEY": "test-openai-key",
        },
    )

    assert result.is_valid


def test_validate_required_environment_reports_missing_keys() -> None:
    result = validate_required_environment({})

    assert not result.is_valid
    assert {
        issue.path for issue in result.errors
    } == {
        ("environment", "VAPI_API_KEY"),
        ("environment", "OPENAI_API_KEY"),
    }


def test_validate_runtime_configuration_accepts_safe_configuration() -> None:
    result = validate_runtime_configuration(_runtime_configuration())

    assert result.is_valid


def test_validate_runtime_configuration_blocks_production_debug() -> None:
    configuration = _runtime_configuration(
        application=ApplicationConfiguration(
            environment=RuntimeEnvironment.PRODUCTION,
            debug_enabled=True,
        ),
    )

    result = validate_runtime_configuration(configuration)

    assert not result.is_valid
    assert "debug_enabled_in_production" in {
        issue.code for issue in result.errors
    }


def test_validate_runtime_configuration_requires_public_url_for_real_calls() -> None:
    configuration = _runtime_configuration(
        application=ApplicationConfiguration(
            environment=RuntimeEnvironment.PRODUCTION,
            debug_enabled=False,
        ),
        features=FeatureFlagConfiguration(real_calls_enabled=True),
    )

    result = validate_runtime_configuration(configuration)

    assert not result.is_valid
    assert "missing_public_base_url_for_real_calls" in {
        issue.code for issue in result.errors
    }


def _runtime_configuration(
    *,
    application: ApplicationConfiguration | None = None,
    features: FeatureFlagConfiguration | None = None,
) -> RuntimeConfiguration:
    return RuntimeConfiguration(
        application=application or ApplicationConfiguration(),
        vapi=VapiConfiguration(
            api_key=SecretStr("test-vapi-key"),
            base_url="https://api.vapi.ai",
            request_timeout_seconds=30,
        ),
        openai=OpenAIConfiguration(
            api_key=SecretStr("test-openai-key"),
            base_url="https://api.openai.com/v1",
            realtime_model="gpt-realtime",
            responses_model="gpt-5",
            request_timeout_seconds=60,
        ),
        features=features or FeatureFlagConfiguration(),
    )
