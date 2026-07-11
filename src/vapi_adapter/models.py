"""Immutable Vapi adapter output models.

The top-level configuration is our internal adapter artifact. Its
``to_vapi_payload`` method emits the actual CreateAssistantDTO-shaped payload
for a future network client.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .enums import (
    VapiFirstMessageMode,
    VapiMappingStatus,
    VapiModelProvider,
    VapiTranscriberProvider,
    VapiValidationSeverity,
    VapiVoiceProvider,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AssistantName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=40),
]


class VapiAdapterModel(BaseModel):
    """Base class for immutable adapter models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class VapiSourceTraceability(VapiAdapterModel):
    """Traceability back to the source scenario and conversation contract."""

    contract_id: NonEmptyString
    conversation_contract_fingerprint: NonEmptyString | None = None
    scenario_instance_id: NonEmptyString
    scenario_instance_fingerprint: NonEmptyString | None = None
    source_scenario_id: NonEmptyString
    source_scenario_version: int = Field(ge=1)
    adapter_version: NonEmptyString
    adapter_policy_version: NonEmptyString


class VapiAssistantIdentity(VapiAdapterModel):
    """Vapi assistant identity fields."""

    name: AssistantName


class VapiMessage(VapiAdapterModel):
    """Vapi/OpenAI-style model message used in model.messages."""

    role: Literal["system", "assistant", "user"]
    content: NonEmptyString


class VapiModelConfiguration(VapiAdapterModel):
    """Vapi model configuration."""

    provider: VapiModelProvider
    model: NonEmptyString
    messages: tuple[VapiMessage, ...] = Field(min_length=1)
    temperature: float = Field(ge=0, le=2)
    max_tokens: int = Field(alias="maxTokens", ge=1)


class VapiVoiceConfiguration(VapiAdapterModel):
    """Vapi voice configuration."""

    provider: VapiVoiceProvider
    voice_id: NonEmptyString = Field(alias="voiceId")


class VapiTranscriberConfiguration(VapiAdapterModel):
    """Optional Vapi transcriber configuration for non-realtime models."""

    provider: VapiTranscriberProvider
    model: NonEmptyString | None = None


class VapiGeneratedInstructions(VapiAdapterModel):
    """Structured adapter-owned instruction artifact."""

    system_message: NonEmptyString
    represented_sections: tuple[NonEmptyString, ...] = Field(min_length=1)


class VapiConversationConfiguration(VapiAdapterModel):
    """Vapi conversation-level assistant fields."""

    first_message: NonEmptyString | None = Field(default=None, alias="firstMessage")
    first_message_mode: VapiFirstMessageMode = Field(alias="firstMessageMode")
    first_message_interruptions_enabled: bool = Field(
        alias="firstMessageInterruptionsEnabled",
    )
    max_duration_seconds: int = Field(alias="maxDurationSeconds", ge=10, le=43200)


class VapiInterruptionConfiguration(VapiAdapterModel):
    """Adapter-owned view of interruption-related Vapi settings."""

    first_message_interruptions_enabled: bool = Field(
        alias="firstMessageInterruptionsEnabled",
    )


class VapiSilenceTimeoutConfiguration(VapiAdapterModel):
    """Vapi silence timeout field."""

    silence_timeout_seconds: int = Field(alias="silenceTimeoutSeconds", ge=5, le=3600)


class VapiTerminationConfiguration(VapiAdapterModel):
    """Vapi termination-related fields."""

    end_call_message: NonEmptyString | None = Field(
        default=None,
        alias="endCallMessage",
    )
    end_call_phrases: tuple[NonEmptyString, ...] = Field(
        default_factory=tuple,
        alias="endCallPhrases",
    )
    max_duration_seconds: int = Field(alias="maxDurationSeconds", ge=10, le=43200)


class VapiProviderMetadata(VapiAdapterModel):
    """Metadata stored on the Vapi assistant, not patient-facing instructions."""

    values: dict[str, str]


class VapiMappingCoverage(VapiAdapterModel):
    """Records how a contract section was represented."""

    contract_section: NonEmptyString
    status: VapiMappingStatus
    target: NonEmptyString
    critical: bool = True


class VapiConfigurationWarning(VapiAdapterModel):
    """Non-blocking adapter warning."""

    code: NonEmptyString
    message: NonEmptyString
    severity: VapiValidationSeverity = VapiValidationSeverity.WARNING


class VapiUnsupportedFeature(VapiAdapterModel):
    """Unsupported Vapi direct field that was handled explicitly."""

    code: NonEmptyString
    message: NonEmptyString
    preserved_as: NonEmptyString
    severity: VapiValidationSeverity = VapiValidationSeverity.UNSUPPORTED_FEATURE


class VapiAssistantConfiguration(VapiAdapterModel):
    """Complete adapter output for a future Vapi API client."""

    adapter_version: NonEmptyString
    configuration_schema_version: NonEmptyString
    source_traceability: VapiSourceTraceability
    assistant_identity: VapiAssistantIdentity
    model_configuration: VapiModelConfiguration
    generated_instructions: VapiGeneratedInstructions
    voice_configuration: VapiVoiceConfiguration
    transcriber_configuration: VapiTranscriberConfiguration | None = None
    conversation_configuration: VapiConversationConfiguration
    interruption_configuration: VapiInterruptionConfiguration
    silence_and_timeout_configuration: VapiSilenceTimeoutConfiguration
    termination_configuration: VapiTerminationConfiguration
    provider_metadata: VapiProviderMetadata
    mapping_coverage: tuple[VapiMappingCoverage, ...] = Field(min_length=1)
    unsupported_features: tuple[VapiUnsupportedFeature, ...] = Field(
        default_factory=tuple,
    )
    warnings: tuple[VapiConfigurationWarning, ...] = Field(default_factory=tuple)
    configuration_fingerprint: NonEmptyString | None = None

    def to_vapi_payload(self) -> dict[str, Any]:
        """Return a CreateAssistantDTO-shaped payload for a future Vapi client."""

        payload: dict[str, Any] = {
            "name": self.assistant_identity.name,
            "model": self.model_configuration.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            ),
            "voice": self.voice_configuration.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            ),
            "firstMessage": self.conversation_configuration.first_message,
            "firstMessageMode": self.conversation_configuration.first_message_mode,
            "firstMessageInterruptionsEnabled": (
                self.conversation_configuration.first_message_interruptions_enabled
            ),
            "maxDurationSeconds": (
                self.conversation_configuration.max_duration_seconds
            ),
            "silenceTimeoutSeconds": (
                self.silence_and_timeout_configuration.silence_timeout_seconds
            ),
            "endCallMessage": self.termination_configuration.end_call_message,
            "endCallPhrases": self.termination_configuration.end_call_phrases,
            "metadata": self.provider_metadata.values,
        }

        if self.transcriber_configuration is not None:
            payload["transcriber"] = self.transcriber_configuration.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            )

        return {key: value for key, value in payload.items() if value not in (None, ())}
