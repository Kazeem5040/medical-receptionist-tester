from __future__ import annotations

from typing import Any

import pytest

from outbound_calls import (
    OutboundCallCreationError,
    OutboundCallStatus,
    ProviderCallState,
)
from tests.outbound_call_factories import (
    FakeVapiOutboundCallClient,
    creator,
    fixed_timestamp,
    valid_creation_request,
    vapi_call_success_response,
)
from vapi_client import VapiTimeoutError


@pytest.mark.asyncio
async def test_successful_outbound_call_creation_submits_vapi_call_payload() -> None:
    client = FakeVapiOutboundCallClient()
    request = await valid_creation_request()

    result = await creator(client).create_call(request)

    assert result.status == OutboundCallStatus.ACCEPTED
    assert result.provider_response.provider_call_id == "call_123"
    assert result.provider_response.provider_assistant_id == "asst_123"
    assert result.provider_response.phone_number_id == "vapi-phone-number-123"
    assert result.provider_response.provider_state == ProviderCallState.QUEUED
    assert result.requested_at == fixed_timestamp()
    assert result.statistics.elapsed_milliseconds == 45
    assert result.result_fingerprint.startswith("outbound_call:")
    assert len(client.calls) == 1
    assert client.idempotency_keys == [request.prepared_call.idempotency_key]


@pytest.mark.asyncio
async def test_vapi_payload_uses_assistant_phone_number_customer_and_metadata() -> None:
    client = FakeVapiOutboundCallClient()
    request = await valid_creation_request()

    await creator(client).create_call(request)

    payload = client.calls[0]
    assert payload["assistantId"] == "asst_123"
    assert payload["phoneNumberId"] == "vapi-phone-number-123"
    assert payload["customer"] == {"number": "+18054398008"}
    assert payload["serverUrl"] == "https://example.test/vapi/webhook"
    assert payload["metadata"]["preparation_id"] == request.prepared_call.preparation_id
    assert payload["metadata"]["submission_id"] == (
        request.call_submission_result.submission_id
    )


@pytest.mark.asyncio
async def test_traceability_preserves_prior_component_fingerprints() -> None:
    request = await valid_creation_request()

    result = await creator(FakeVapiOutboundCallClient()).create_call(request)

    assert result.traceability.preparation_id == request.prepared_call.preparation_id
    assert result.traceability.submission_id == (
        request.call_submission_result.submission_id
    )
    assert result.traceability.scenario_template_fingerprint == (
        request.prepared_call.scenario_template_fingerprint
    )
    assert result.traceability.scenario_instance_fingerprint == (
        request.prepared_call.scenario_instance_fingerprint
    )
    assert result.traceability.conversation_contract_fingerprint == (
        request.prepared_call.conversation_contract_fingerprint
    )
    assert result.traceability.vapi_configuration_fingerprint == (
        request.prepared_call.vapi_configuration_fingerprint
    )
    assert result.traceability.call_submission_fingerprint == (
        request.call_submission_result.result_fingerprint
    )


@pytest.mark.asyncio
async def test_provider_timeout_is_wrapped_as_outbound_call_error() -> None:
    client = FakeVapiOutboundCallClient(error=VapiTimeoutError("timed out"))

    with pytest.raises(OutboundCallCreationError) as error:
        await creator(client).create_call(await valid_creation_request())

    assert "provider_timeout" in {issue.code for issue in error.value.result.errors}
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_no_mutation_of_request() -> None:
    request = await valid_creation_request()
    before = request.model_dump(mode="json")

    await creator(FakeVapiOutboundCallClient()).create_call(request)

    assert request.model_dump(mode="json") == before


@pytest.mark.asyncio
async def test_monitor_urls_are_preserved_when_provider_returns_them() -> None:
    result = await creator(FakeVapiOutboundCallClient()).create_call(
        await valid_creation_request(),
    )

    assert result.provider_response.monitor_listen_url == "wss://example.test/listen"
    assert result.provider_response.monitor_control_url == (
        "https://example.test/control"
    )


@pytest.mark.asyncio
async def test_result_does_not_contain_transcript_evaluation_or_bug_report() -> None:
    result = await creator(FakeVapiOutboundCallClient()).create_call(
        await valid_creation_request(),
    )
    serialized = result.model_dump(mode="json")

    keys = _all_keys(serialized)
    assert "transcript" not in keys
    assert "evaluation" not in keys
    assert "bug_report" not in keys


@pytest.mark.asyncio
async def test_changed_provider_call_id_changes_fingerprint() -> None:
    request = await valid_creation_request()
    first = await creator(
        FakeVapiOutboundCallClient(vapi_call_success_response(call_id="call_123")),
    ).create_call(request)
    second = await creator(
        FakeVapiOutboundCallClient(vapi_call_success_response(call_id="call_456")),
    ).create_call(request)

    assert first.result_fingerprint != second.result_fingerprint


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_keys(item))
        return keys
    return set()
