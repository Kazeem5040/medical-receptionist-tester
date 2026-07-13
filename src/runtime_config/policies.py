"""Default runtime configuration policy and environment variable names."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import DeploymentTarget, RuntimeEnvironment


class RuntimeConfigurationPolicy(BaseModel):
    """Defaults and environment variable names used by the runtime loader."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    default_service_name: str = "ai-receptionist-tester"
    default_environment: RuntimeEnvironment = RuntimeEnvironment.DEVELOPMENT
    default_deployment_target: DeploymentTarget = DeploymentTarget.LOCAL
    default_vapi_base_url: str = "https://api.vapi.ai"
    default_openai_base_url: str = "https://api.openai.com/v1"
    default_vapi_timeout_seconds: float = Field(default=30.0, gt=0)
    default_openai_timeout_seconds: float = Field(default=60.0, gt=0)
    default_max_retries: int = Field(default=2, ge=0)
    default_backoff_initial_seconds: float = Field(default=0.1, ge=0)
    default_backoff_multiplier: float = Field(default=2.0, ge=1)
    default_openai_realtime_model: str = "gpt-realtime"
    default_openai_responses_model: str = "gpt-5"
    required_environment_variables: tuple[str, ...] = (
        "VAPI_API_KEY",
        "OPENAI_API_KEY",
    )


DEFAULT_RUNTIME_CONFIGURATION_POLICY = RuntimeConfigurationPolicy()
