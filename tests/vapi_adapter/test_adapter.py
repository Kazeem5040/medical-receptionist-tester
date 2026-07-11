from __future__ import annotations

from copy import deepcopy

from tests.vapi_adapter_factories import conversation_contract
from vapi_adapter import VapiFirstMessageMode, VapiProviderAdapter
from vapi_adapter.enums import VapiMappingStatus, VapiModelProvider, VapiVoiceProvider


def test_valid_conversation_contract_produces_vapi_configuration() -> None:
    contract = conversation_contract()

    configuration = VapiProviderAdapter().build(contract)

    assert configuration.source_traceability.contract_id == contract.contract_id
    assert configuration.model_configuration.provider == VapiModelProvider.OPENAI
    assert configuration.voice_configuration.provider == VapiVoiceProvider.OPENAI
    assert configuration.configuration_fingerprint is not None


def test_vapi_payload_uses_real_create_assistant_concepts() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())

    payload = configuration.to_vapi_payload()

    assert payload["name"] == configuration.assistant_identity.name
    assert payload["model"]["provider"] == "openai"
    assert payload["model"]["model"] == "gpt-realtime-2025-08-28"
    assert payload["model"]["messages"][0]["role"] == "system"
    assert payload["voice"] == {"provider": "openai", "voiceId": "alloy"}
    assert payload["firstMessageMode"] == (
        VapiFirstMessageMode.ASSISTANT_SPEAKS_FIRST_WITH_MODEL_GENERATED_MESSAGE
    )
    assert "transcriber" not in payload


def test_patient_identity_objective_and_facts_are_preserved() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    instructions = configuration.generated_instructions.system_message

    assert "Jamie Rivera" in instructions
    assert "Book a primary care appointment." in instructions
    assert "preferred-day: Tuesday morning" in instructions


def test_unknown_forbidden_and_disclosure_rules_are_restricted() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    instructions = configuration.generated_instructions.system_message

    assert "Do not invent appointment times" in instructions
    assert "timing=when_asked" in instructions
    assert "Inventing patient facts" in instructions
    assert "Providing diagnosis, triage, or treatment recommendations" in instructions


def test_behavioral_rules_are_not_converted_to_rigid_first_message_script() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    payload = configuration.to_vapi_payload()

    assert "firstMessage" not in payload
    assert "exact_script" not in payload
    assert "say_this" not in payload
    assert "Use natural, varied language" in (
        configuration.generated_instructions.system_message
    )


def test_safety_and_termination_rules_are_preserved() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    payload = configuration.to_vapi_payload()
    instructions = configuration.generated_instructions.system_message

    assert payload["maxDurationSeconds"] == 600
    assert "Safety" in instructions
    assert "Termination Behavior" in instructions
    assert "End the call naturally and politely" in payload["endCallMessage"]


def test_important_contract_sections_have_mapping_coverage() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    coverage = {
        item.contract_section: item.status for item in configuration.mapping_coverage
    }

    assert coverage["objectives"] == VapiMappingStatus.GENERATED_INSTRUCTIONS
    assert coverage["known_information"] == VapiMappingStatus.GENERATED_INSTRUCTIONS
    assert coverage["termination_rules"] == VapiMappingStatus.DIRECT
    assert coverage["forbidden_behaviors"] == (
        VapiMappingStatus.GENERATED_INSTRUCTIONS
    )


def test_unsupported_features_are_explicit() -> None:
    configuration = VapiProviderAdapter().build(conversation_contract())
    codes = {feature.code for feature in configuration.unsupported_features}

    assert "contract_sections_without_direct_vapi_fields" in codes
    assert "realtime_transcriber_not_applicable" in codes


def test_source_contract_is_not_mutated() -> None:
    contract = conversation_contract()
    before = deepcopy(contract)

    VapiProviderAdapter().build(contract)

    assert contract == before


def test_same_contract_and_policy_produce_same_fingerprint() -> None:
    adapter = VapiProviderAdapter()
    contract = conversation_contract()

    first = adapter.build(contract)
    second = adapter.build(contract)

    assert first == second
    assert first.configuration_fingerprint == second.configuration_fingerprint


def test_changed_contract_changes_configuration_fingerprint() -> None:
    adapter = VapiProviderAdapter()
    contract = conversation_contract()
    changed_identity = contract.patient_identity.model_copy(
        update={"given_name": "Alex"},
    )
    changed_contract = contract.model_copy(
        update={"patient_identity": changed_identity},
    )

    first = adapter.build(contract)
    second = adapter.build(changed_contract)

    assert first.configuration_fingerprint != second.configuration_fingerprint


def test_payload_contains_no_secrets_or_phone_numbers() -> None:
    payload = VapiProviderAdapter().build(conversation_contract()).to_vapi_payload()
    forbidden_keys = {
        "apiKey",
        "api_key",
        "authorization",
        "secret",
        "token",
        "destination",
        "destinationPhoneNumber",
        "phoneNumber",
        "phone_number",
        "phoneNumberId",
        "serverUrl",
    }

    assert _payload_keys(payload).isdisjoint(forbidden_keys)


def _payload_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_payload_keys(item))
        return keys
    if isinstance(value, list | tuple):
        keys: set[str] = set()
        for item in value:
            keys.update(_payload_keys(item))
        return keys
    return set()
