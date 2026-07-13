"""Immutable models for application runtime configuration."""

from __future__ import annotations

from typing import Annotated

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, SecretStr
from pydantic.types import StringConstraints

from .enums import DeploymentTarget, RuntimeEnvironment

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class RuntimeConfigurationModel(BaseModel):
    """Base class for immutable runtime configuration models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ApplicationConfiguration(RuntimeConfigurationModel):
    """Application-level runtime settings."""

    service_name: NonEmptyString = "ai-receptionist-tester"
    environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT
    deployment_target: DeploymentTarget = DeploymentTarget.LOCAL
    schema_version: NonEmptyString = "1.0"
    debug_enabled: bool = False
    deployment_region: NonEmptyString | None = None
    public_base_url: AnyUrl | None = None


class ProviderRetryConfiguration(RuntimeConfigurationModel):
    """Provider retry defaults shared by future infrastructure clients."""

    max_retries: int = Field(default=2, ge=0)
    backoff_initial_seconds: float = Field(default=0.1, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1)


class VapiConfiguration(RuntimeConfigurationModel):
    """Runtime settings required to communicate with Vapi."""

    api_key: SecretStr
    base_url: AnyUrl
    request_timeout_seconds: float = Field(gt=0)
    retry: ProviderRetryConfiguration = Field(
        default_factory=ProviderRetryConfiguration,
    )


class OpenAIConfiguration(RuntimeConfigurationModel):
    """Runtime settings required to communicate with OpenAI."""

    api_key: SecretStr
    base_url: AnyUrl
    realtime_model: NonEmptyString
    responses_model: NonEmptyString
    request_timeout_seconds: float = Field(gt=0)
    retry: ProviderRetryConfiguration = Field(
        default_factory=ProviderRetryConfiguration,
    )


class FeatureFlagConfiguration(RuntimeConfigurationModel):
    """Feature flags controlling runtime behavior."""

    real_calls_enabled: bool = False
    call_monitoring_enabled: bool = True
    transcript_evaluation_enabled: bool = False
    bug_reports_enabled: bool = False


class RuntimeConfiguration(RuntimeConfigurationModel):
    """Complete runtime configuration for dependency injection."""

    application: ApplicationConfiguration
    vapi: VapiConfiguration
    openai: OpenAIConfiguration
    features: FeatureFlagConfiguration = Field(
        default_factory=FeatureFlagConfiguration,
    )
