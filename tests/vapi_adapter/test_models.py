from __future__ import annotations

import pytest
from pydantic import ValidationError

from vapi_adapter import VapiAssistantIdentity


def test_vapi_adapter_models_are_immutable() -> None:
    identity = VapiAssistantIdentity(name="ai-patient-test")

    with pytest.raises(ValidationError):
        identity.name = "changed"


def test_vapi_adapter_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VapiAssistantIdentity(name="ai-patient-test", api_key="not-allowed")
