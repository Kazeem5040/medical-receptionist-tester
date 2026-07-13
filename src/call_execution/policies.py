"""Policy defaults for submitting prepared calls."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import ProviderResponseState, RetryStrategy


class CallExecutionPolicy(BaseModel):
    """Configurable execution-level rules and traceability settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_version: str = "1.0"
    policy_version: str = "1.0"
    request_timeout_seconds: float = Field(default=30.0, gt=0)
    retries_enabled: bool = True
    maximum_retries: int = Field(default=2, ge=0)
    retry_strategy: RetryStrategy = RetryStrategy.PROVIDER_CLIENT_MANAGED
    acceptable_provider_states: tuple[ProviderResponseState, ...] = (
        ProviderResponseState.ACCEPTED,
    )
    max_metadata_items: int = Field(default=30, ge=0)
    max_metadata_key_length: int = Field(default=64, ge=1)
    max_metadata_value_length: int = Field(default=512, ge=1)


DEFAULT_CALL_EXECUTION_POLICY = CallExecutionPolicy()
