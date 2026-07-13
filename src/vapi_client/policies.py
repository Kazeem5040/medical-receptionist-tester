"""Policy defaults for Vapi HTTP communication."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VapiClientPolicy(BaseModel):
    """Configurable HTTP settings for the Vapi API client."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_url: str = Field(default="https://api.vapi.ai", min_length=1)
    api_version: str = "v1"
    create_assistant_path: str = "/assistant"
    user_agent: str = "ai-receptionist-tester/0.1"
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    backoff_initial_seconds: float = Field(default=0.1, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1)


DEFAULT_VAPI_CLIENT_POLICY = VapiClientPolicy()
