"""Controlled vocabulary for the Vapi provider adapter."""

from __future__ import annotations

from enum import StrEnum


class VapiValidationSeverity(StrEnum):
    """Severity level for Vapi adapter validation issues."""

    ERROR = "error"
    WARNING = "warning"
    UNSUPPORTED_FEATURE = "unsupported_feature"


class VapiModelProvider(StrEnum):
    """Supported Vapi model providers used by this adapter."""

    OPENAI = "openai"
    VAPI = "vapi"


class VapiVoiceProvider(StrEnum):
    """Supported Vapi voice providers used by this adapter."""

    OPENAI = "openai"
    VAPI = "vapi"


class VapiTranscriberProvider(StrEnum):
    """Supported Vapi transcriber providers used by this adapter."""

    DEEPGRAM = "deepgram"
    OPENAI = "openai"
    VAPI = "vapi"


class VapiFirstMessageMode(StrEnum):
    """Vapi first-message modes."""

    ASSISTANT_SPEAKS_FIRST = "assistant-speaks-first"
    ASSISTANT_SPEAKS_FIRST_WITH_MODEL_GENERATED_MESSAGE = (
        "assistant-speaks-first-with-model-generated-message"
    )
    ASSISTANT_WAITS_FOR_USER = "assistant-waits-for-user"


class VapiMappingStatus(StrEnum):
    """How a contract section was represented in Vapi configuration."""

    DIRECT = "direct"
    GENERATED_INSTRUCTIONS = "generated_instructions"
    METADATA = "metadata"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED_WITH_WARNING = "unsupported_with_warning"
