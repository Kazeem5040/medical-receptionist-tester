from __future__ import annotations

from tests.vapi_adapter_factories import conversation_contract
from vapi_adapter import VapiProviderAdapter


def test_canonical_snapshot_is_json_compatible() -> None:
    adapter = VapiProviderAdapter()
    configuration = adapter.build(conversation_contract())

    snapshot = adapter.create_canonical_snapshot(configuration)

    assert snapshot["assistant_identity"]["name"].startswith("ai-patient-")
    assert snapshot["model_configuration"]["provider"] == "openai"


def test_fingerprint_is_stable() -> None:
    adapter = VapiProviderAdapter()

    first = adapter.create_fingerprint(adapter.build(conversation_contract()))
    second = adapter.create_fingerprint(adapter.build(conversation_contract()))

    assert first == second
    assert first.startswith("sha256:")
