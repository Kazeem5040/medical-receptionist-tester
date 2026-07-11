from __future__ import annotations

from conversation_contracts import ConversationContractBuilder
from tests.conversation_contract_factories import scenario_instance


def test_canonical_snapshot_is_json_compatible() -> None:
    builder = ConversationContractBuilder()
    contract = builder.build(scenario_instance())

    snapshot = builder.create_canonical_snapshot(contract)

    assert snapshot["patient_identity"]["given_name"] == "Jamie"
    assert (
        snapshot["source"]["scenario_instance_id"]
        == contract.source.scenario_instance_id
    )


def test_fingerprint_is_stable_for_equivalent_contracts() -> None:
    builder = ConversationContractBuilder()

    first = builder.create_fingerprint(builder.build(scenario_instance()))
    second = builder.create_fingerprint(builder.build(scenario_instance()))

    assert first == second
    assert first.startswith("sha256:")
