from __future__ import annotations

from typing import Any

import pytest

from call_execution import (
    CallExecutionError,
    ExecutionStatus,
    ProviderName,
)
from tests.call_execution_factories import (
    FakeVapiClient,
    execution_service,
    fixed_timestamp,
    valid_prepared_call,
    vapi_success_response,
)
from vapi_client import (
    VapiCreateAssistantResponse,
    VapiTimeoutError,
)


@pytest.mark.asyncio
async def test_successful_execution_submits_prepared_call() -> None:
    client = FakeVapiClient(vapi_success_response())
    prepared = valid_prepared_call()

    result = await execution_service(client).execute(prepared)

    assert result.execution_status == ExecutionStatus.ACCEPTED
    assert result.provider_name == ProviderName.VAPI
    assert result.provider_response.provider_resource_id == "asst_123"
    assert result.provider_response.provider_call_id is None
    assert result.submission_timestamp == fixed_timestamp()
    assert len(client.calls) == 1
    assert client.calls[0] is prepared


@pytest.mark.asyncio
async def test_traceability_and_fingerprints_are_preserved() -> None:
    prepared = valid_prepared_call()

    result = await execution_service(FakeVapiClient()).execute(prepared)

    assert result.traceability.preparation_id == prepared.preparation_id
    assert result.traceability.scenario_template_fingerprint == (
        prepared.scenario_template_fingerprint
    )
    assert result.traceability.scenario_instance_fingerprint == (
        prepared.scenario_instance_fingerprint
    )
    assert result.traceability.conversation_contract_fingerprint == (
        prepared.conversation_contract_fingerprint
    )
    assert result.traceability.vapi_configuration_fingerprint == (
        prepared.vapi_configuration_fingerprint
    )
    assert result.traceability.request_fingerprint == prepared.request_fingerprint
    assert result.result_fingerprint.startswith("call_submission:")


@pytest.mark.asyncio
async def test_execution_is_deterministic_with_same_inputs_and_clock() -> None:
    prepared = valid_prepared_call()

    first = await execution_service(FakeVapiClient()).execute(prepared)
    second = await execution_service(FakeVapiClient()).execute(prepared)

    assert first.submission_id == second.submission_id
    assert first.result_fingerprint == second.result_fingerprint


@pytest.mark.asyncio
async def test_vapi_timeout_is_wrapped_as_execution_error() -> None:
    client = FakeVapiClient(error=VapiTimeoutError("timed out"))

    with pytest.raises(CallExecutionError) as error:
        await execution_service(client).execute(valid_prepared_call())

    assert "provider_timeout" in {issue.code for issue in error.value.result.errors}
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_executor_does_not_retry_beyond_vapi_client() -> None:
    client = FakeVapiClient(error=VapiTimeoutError("timed out"))

    with pytest.raises(CallExecutionError):
        await execution_service(client).execute(valid_prepared_call())

    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_invalid_provider_response_is_rejected() -> None:
    invalid_response = VapiCreateAssistantResponse.model_construct(
        assistant_id=type("AssistantId", (), {"value": ""})(),
        response_status=type("Status", (), {"value": "success"})(),
        provider_status=type("ProviderStatus", (), {"value": "created"})(),
        http_status=type(
            "HttpStatus",
            (),
            {"status_code": 201, "reason_phrase": "Created"},
        )(),
        provider_metadata=type("Metadata", (), {"values": {}})(),
        raw_response={},
    )

    with pytest.raises(CallExecutionError) as error:
        await execution_service(FakeVapiClient(invalid_response)).execute(
            valid_prepared_call(),
        )

    assert "missing_provider_resource_id" in {
        issue.code for issue in error.value.result.errors
    }


@pytest.mark.asyncio
async def test_no_mutation_of_prepared_call() -> None:
    prepared = valid_prepared_call()
    before = prepared.model_dump(mode="json")

    await execution_service(FakeVapiClient()).execute(prepared)

    assert prepared.model_dump(mode="json") == before


@pytest.mark.asyncio
async def test_result_does_not_handle_transcripts_recordings_or_database_data() -> None:
    result = await execution_service(FakeVapiClient()).execute(valid_prepared_call())
    serialized = result.model_dump(mode="json")

    assert "transcript" not in _all_keys(serialized)
    assert "recording" not in _all_keys(serialized)
    assert "database" not in _all_keys(serialized)


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
