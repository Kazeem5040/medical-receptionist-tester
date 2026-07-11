from __future__ import annotations

from conversation_contracts import ConversationContractBuilder
from conversation_contracts.validation import validate_conversation_contract
from tests.conversation_contract_factories import scenario_instance


def test_valid_contract_has_no_validation_errors() -> None:
    contract = ConversationContractBuilder().build(scenario_instance())

    result = validate_conversation_contract(contract)

    assert result.is_valid
    assert result.errors == ()


def test_disclosure_rule_must_reference_known_fact() -> None:
    contract = ConversationContractBuilder().build(scenario_instance())
    invalid = contract.model_copy(
        update={
            "known_information": contract.known_information.model_copy(
                update={"facts": ()},
            ),
        },
    )

    result = validate_conversation_contract(invalid)

    assert not result.is_valid
    assert "disclosure_rule_unknown_fact" in {issue.code for issue in result.errors}


def test_contract_requires_knowledge_boundaries() -> None:
    contract = ConversationContractBuilder().build(scenario_instance())
    invalid = contract.model_copy(update={"knowledge_boundaries": ()})

    result = validate_conversation_contract(invalid)

    assert not result.is_valid
    assert "missing_knowledge_boundaries" in {issue.code for issue in result.errors}
