from __future__ import annotations

import pytest
from pydantic import ValidationError

from vapi_client import VapiAssistantId


def test_vapi_client_models_are_immutable() -> None:
    assistant_id = VapiAssistantId(value="asst_123")

    with pytest.raises(ValidationError):
        assistant_id.value = "changed"


def test_vapi_client_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VapiAssistantId(value="asst_123", api_key="not-allowed")
