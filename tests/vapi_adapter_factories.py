from __future__ import annotations

from conversation_contracts import ConversationContract, ConversationContractBuilder
from tests.conversation_contract_factories import scenario_instance


def conversation_contract() -> ConversationContract:
    return ConversationContractBuilder().build(scenario_instance())
