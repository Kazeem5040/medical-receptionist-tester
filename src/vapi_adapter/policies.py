"""Policy defaults for translating contracts into Vapi assistant config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    VapiFirstMessageMode,
    VapiModelProvider,
    VapiTranscriberProvider,
    VapiVoiceProvider,
)


class VapiAdapterPolicy(BaseModel):
    """Configurable adapter defaults kept outside translation logic."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter_version: str = "1.0"
    configuration_schema_version: str = "1.0"
    policy_version: str = "1.0"
    assistant_name_prefix: str = Field(default="ai-patient", max_length=20)
    model_provider: VapiModelProvider = VapiModelProvider.OPENAI
    model_name: str = "gpt-realtime-2025-08-28"
    model_temperature: float = Field(default=0.6, ge=0, le=2)
    model_max_tokens: int = Field(default=300, ge=1)
    voice_provider: VapiVoiceProvider = VapiVoiceProvider.OPENAI
    voice_id: str = "alloy"
    transcriber_provider: VapiTranscriberProvider | None = None
    transcriber_model: str | None = None
    first_message_mode: VapiFirstMessageMode = (
        VapiFirstMessageMode.ASSISTANT_SPEAKS_FIRST_WITH_MODEL_GENERATED_MESSAGE
    )
    first_message_interruptions_enabled: bool = False
    default_max_duration_seconds: int = Field(default=600, ge=10, le=43200)
    default_silence_timeout_seconds: int = Field(default=30, ge=5, le=3600)
    require_contract_fingerprint: bool = True
    fail_on_unrepresented_critical_sections: bool = True


DEFAULT_VAPI_ADAPTER_POLICY = VapiAdapterPolicy()
