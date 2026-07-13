from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from runtime_config import (
    ApplicationConfiguration,
    OpenAIConfiguration,
    RuntimeEnvironment,
    VapiConfiguration,
)


def test_models_are_immutable() -> None:
    configuration = ApplicationConfiguration()

    with pytest.raises(ValidationError):
        configuration.environment = RuntimeEnvironment.PRODUCTION  # type: ignore[misc]


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ApplicationConfiguration(unexpected="nope")


def test_vapi_configuration_requires_positive_timeout() -> None:
    with pytest.raises(ValidationError):
        VapiConfiguration(
            api_key=SecretStr("test-vapi-key"),
            base_url="https://api.vapi.ai",
            request_timeout_seconds=0,
        )


def test_openai_configuration_requires_model_names() -> None:
    with pytest.raises(ValidationError):
        OpenAIConfiguration(
            api_key=SecretStr("test-openai-key"),
            base_url="https://api.openai.com/v1",
            realtime_model="",
            responses_model="gpt-5",
            request_timeout_seconds=30,
        )


def test_secret_values_are_accessible_only_explicitly() -> None:
    configuration = VapiConfiguration(
        api_key=SecretStr("test-vapi-key"),
        base_url="https://api.vapi.ai",
        request_timeout_seconds=30,
    )

    assert configuration.api_key.get_secret_value() == "test-vapi-key"
    assert "test-vapi-key" not in repr(configuration)
