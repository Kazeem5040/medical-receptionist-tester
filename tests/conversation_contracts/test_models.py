from __future__ import annotations

import pytest
from pydantic import ValidationError

from conversation_contracts import ContractPatientIdentity


def test_contract_models_are_immutable() -> None:
    identity = ContractPatientIdentity(given_name="Jamie", family_name="Rivera")

    with pytest.raises(ValidationError):
        identity.given_name = "Alex"


def test_contract_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ContractPatientIdentity(
            given_name="Jamie",
            family_name="Rivera",
            provider_specific_prompt="Say hello exactly this way.",
        )
