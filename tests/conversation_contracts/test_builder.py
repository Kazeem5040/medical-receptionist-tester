from __future__ import annotations

from conversation_contracts import ConversationContractBuilder
from conversation_contracts.enums import KnowledgeBoundaryType
from tests.conversation_contract_factories import scenario_instance


def test_builder_consumes_scenario_instance() -> None:
    instance = scenario_instance()

    contract = ConversationContractBuilder().build(instance)

    assert contract.source.scenario_instance_id == instance.instance_id
    assert contract.patient_identity.given_name == "Jamie"
    assert contract.objectives[0].objective_id == "book-appointment"
    assert contract.known_information.facts[0].key == "preferred-day"
    assert contract.disclosure_rules[0].fact_key == "preferred-day"
    assert contract.fingerprint is not None


def test_builder_output_is_deterministic() -> None:
    instance = scenario_instance()
    builder = ConversationContractBuilder()

    first = builder.build(instance)
    second = builder.build(instance)

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert first.contract_id == second.contract_id


def test_contract_contains_behavioral_guardrails_not_provider_config() -> None:
    contract = ConversationContractBuilder().build(scenario_instance())

    boundary_types = {
        boundary.boundary_type for boundary in contract.knowledge_boundaries
    }
    forbidden_ids = {
        behavior.behavior_id for behavior in contract.forbidden_behaviors
    }

    assert KnowledgeBoundaryType.ALLOWED in boundary_types
    assert KnowledgeBoundaryType.UNKNOWN in boundary_types
    assert KnowledgeBoundaryType.FORBIDDEN in boundary_types
    assert "inventing-information" in forbidden_ids
    assert "giving-medical-advice" in forbidden_ids
