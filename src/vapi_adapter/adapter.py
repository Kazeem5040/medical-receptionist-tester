"""Pure Vapi provider adapter.

This module translates ConversationContract objects into immutable Vapi
assistant configuration artifacts. It never performs network I/O.
"""

from __future__ import annotations

from typing import Any

from conversation_contracts import ConversationContract

from .canonicalization import canonical_snapshot, stable_fingerprint
from .enums import VapiMappingStatus, VapiValidationSeverity
from .instructions import build_vapi_system_instruction, represented_contract_sections
from .models import (
    VapiAssistantConfiguration,
    VapiAssistantIdentity,
    VapiConfigurationWarning,
    VapiConversationConfiguration,
    VapiGeneratedInstructions,
    VapiInterruptionConfiguration,
    VapiMappingCoverage,
    VapiMessage,
    VapiModelConfiguration,
    VapiProviderMetadata,
    VapiSilenceTimeoutConfiguration,
    VapiSourceTraceability,
    VapiTerminationConfiguration,
    VapiTranscriberConfiguration,
    VapiUnsupportedFeature,
    VapiVoiceConfiguration,
)
from .policies import DEFAULT_VAPI_ADAPTER_POLICY, VapiAdapterPolicy
from .validation import validate_vapi_configuration


class VapiProviderAdapter:
    """Translate ConversationContract into VapiAssistantConfiguration."""

    def __init__(
        self,
        policy: VapiAdapterPolicy = DEFAULT_VAPI_ADAPTER_POLICY,
    ) -> None:
        self._policy = policy

    @property
    def policy(self) -> VapiAdapterPolicy:
        """Policy used by this adapter."""

        return self._policy

    def build(self, contract: ConversationContract) -> VapiAssistantConfiguration:
        """Build and validate a Vapi assistant configuration."""

        instructions = build_vapi_system_instruction(contract)
        max_duration_seconds = self._max_duration_seconds(contract)
        configuration_without_fingerprint = VapiAssistantConfiguration(
            adapter_version=self._policy.adapter_version,
            configuration_schema_version=self._policy.configuration_schema_version,
            source_traceability=self._source_traceability(contract),
            assistant_identity=self._assistant_identity(contract),
            model_configuration=VapiModelConfiguration(
                provider=self._policy.model_provider,
                model=self._policy.model_name,
                messages=(VapiMessage(role="system", content=instructions),),
                temperature=self._policy.model_temperature,
                maxTokens=self._policy.model_max_tokens,
            ),
            generated_instructions=VapiGeneratedInstructions(
                system_message=instructions,
                represented_sections=represented_contract_sections(),
            ),
            voice_configuration=VapiVoiceConfiguration(
                provider=self._policy.voice_provider,
                voiceId=self._policy.voice_id,
            ),
            transcriber_configuration=self._transcriber_configuration(),
            conversation_configuration=VapiConversationConfiguration(
                firstMessage=None,
                firstMessageMode=self._policy.first_message_mode,
                firstMessageInterruptionsEnabled=(
                    self._policy.first_message_interruptions_enabled
                ),
                maxDurationSeconds=max_duration_seconds,
            ),
            interruption_configuration=VapiInterruptionConfiguration(
                firstMessageInterruptionsEnabled=(
                    self._policy.first_message_interruptions_enabled
                ),
            ),
            silence_and_timeout_configuration=VapiSilenceTimeoutConfiguration(
                silenceTimeoutSeconds=self._policy.default_silence_timeout_seconds,
            ),
            termination_configuration=VapiTerminationConfiguration(
                endCallMessage=self._end_call_message(contract),
                endCallPhrases=(),
                maxDurationSeconds=max_duration_seconds,
            ),
            provider_metadata=self._provider_metadata(contract),
            mapping_coverage=self._mapping_coverage(),
            unsupported_features=self._unsupported_features(),
            warnings=self._warnings(),
        )

        validation_result = validate_vapi_configuration(
            configuration_without_fingerprint,
        )
        validation_result.raise_if_invalid()

        return configuration_without_fingerprint.model_copy(
            update={
                "configuration_fingerprint": self.create_fingerprint(
                    configuration_without_fingerprint,
                ),
            },
        )

    def validate(self, configuration: VapiAssistantConfiguration) -> Any:
        """Validate a generated Vapi configuration."""

        return validate_vapi_configuration(configuration)

    def create_canonical_snapshot(self, value: Any) -> dict[str, Any]:
        """Create a canonical JSON-compatible snapshot."""

        return canonical_snapshot(value)

    def create_fingerprint(self, value: Any) -> str:
        """Create a stable fingerprint for a Vapi configuration object."""

        return stable_fingerprint(value)

    def _source_traceability(
        self,
        contract: ConversationContract,
    ) -> VapiSourceTraceability:
        return VapiSourceTraceability(
            contract_id=contract.contract_id,
            conversation_contract_fingerprint=contract.fingerprint,
            scenario_instance_id=contract.source.scenario_instance_id,
            scenario_instance_fingerprint=(
                contract.source.scenario_instance_fingerprint
            ),
            source_scenario_id=contract.source.source_scenario_id,
            source_scenario_version=contract.source.source_scenario_version,
            adapter_version=self._policy.adapter_version,
            adapter_policy_version=self._policy.policy_version,
        )

    def _assistant_identity(
        self,
        contract: ConversationContract,
    ) -> VapiAssistantIdentity:
        suffix = stable_fingerprint(
            {
                "contract_id": contract.contract_id,
                "contract_fingerprint": contract.fingerprint,
                "adapter_version": self._policy.adapter_version,
            },
        ).split(":", maxsplit=1)[1][:8]
        name = f"{self._policy.assistant_name_prefix}-{suffix}"[:40]
        return VapiAssistantIdentity(name=name)

    def _transcriber_configuration(self) -> VapiTranscriberConfiguration | None:
        if self._policy.transcriber_provider is None:
            return None
        return VapiTranscriberConfiguration(
            provider=self._policy.transcriber_provider,
            model=self._policy.transcriber_model,
        )

    def _provider_metadata(
        self,
        contract: ConversationContract,
    ) -> VapiProviderMetadata:
        values = {
            "component": "vapi_provider_adapter",
            "adapter_version": self._policy.adapter_version,
            "adapter_policy_version": self._policy.policy_version,
            "configuration_schema_version": (
                self._policy.configuration_schema_version
            ),
            "conversation_contract_id": contract.contract_id,
            "conversation_contract_fingerprint": contract.fingerprint or "",
            "scenario_instance_id": contract.source.scenario_instance_id,
            "scenario_instance_fingerprint": (
                contract.source.scenario_instance_fingerprint or ""
            ),
            "source_scenario_id": contract.source.source_scenario_id,
            "source_scenario_version": str(
                contract.source.source_scenario_version,
            ),
        }
        return VapiProviderMetadata(values=values)

    def _mapping_coverage(self) -> tuple[VapiMappingCoverage, ...]:
        coverage = [
            VapiMappingCoverage(
                contract_section="patient_identity",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="objectives",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="known_information",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="unknown_information",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="disclosure_rules",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="conversation_style",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="milestones",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
                critical=False,
            ),
            VapiMappingCoverage(
                contract_section="recovery_rules",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
                critical=False,
            ),
            VapiMappingCoverage(
                contract_section="clarification_rules",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
                critical=False,
            ),
            VapiMappingCoverage(
                contract_section="steering_rules",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
                critical=False,
            ),
            VapiMappingCoverage(
                contract_section="termination_rules",
                status=VapiMappingStatus.DIRECT,
                target="maxDurationSeconds and model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="safety_instruction",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="behavioral_constraints",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
                critical=False,
            ),
            VapiMappingCoverage(
                contract_section="knowledge_boundaries",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
            VapiMappingCoverage(
                contract_section="forbidden_behaviors",
                status=VapiMappingStatus.GENERATED_INSTRUCTIONS,
                target="model.messages[0].content",
            ),
        ]
        return tuple(coverage)

    def _unsupported_features(self) -> tuple[VapiUnsupportedFeature, ...]:
        return (
            VapiUnsupportedFeature(
                code="contract_sections_without_direct_vapi_fields",
                message=(
                    "Recovery, clarification, steering, milestones, knowledge "
                    "boundaries, and forbidden behaviors do not have dedicated "
                    "CreateAssistantDTO fields."
                ),
                preserved_as="model.messages[0].content",
            ),
            VapiUnsupportedFeature(
                code="realtime_transcriber_not_applicable",
                message=(
                    "OpenAI realtime models handle speech-to-speech natively, so "
                    "no transcriber configuration is emitted by default."
                ),
                preserved_as="explicit None transcriber_configuration",
            ),
        )

    def _warnings(self) -> tuple[VapiConfigurationWarning, ...]:
        return (
            VapiConfigurationWarning(
                code="no_first_message_script",
                message=(
                    "No fixed firstMessage is emitted; Vapi should let the model "
                    "generate the first patient utterance from instructions."
                ),
                severity=VapiValidationSeverity.WARNING,
            ),
        )

    def _max_duration_seconds(self, contract: ConversationContract) -> int:
        durations = [
            rule.max_call_seconds
            for rule in contract.termination_rules
            if rule.max_call_seconds is not None
        ]
        if not durations:
            return self._policy.default_max_duration_seconds
        return max(10, min(min(durations), 43200))

    @staticmethod
    def _end_call_message(contract: ConversationContract) -> str:
        return (
            "End the call naturally and politely when the patient objective is "
            f"complete or a termination rule is met for {contract.contract_id}."
        )
