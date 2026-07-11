from __future__ import annotations

from copy import deepcopy

import pytest

from call_orchestrator import (
    CallOrchestrationError,
    CallOrchestrator,
    CallWorkflowStatus,
)
from tests.call_orchestrator_factories import (
    call_policy,
    call_preparation_request,
)


def test_prepare_call_coordinates_completed_components() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())
    request = call_preparation_request()

    prepared = orchestrator.prepare_call(request)

    assert prepared.status == CallWorkflowStatus.PREPARED
    assert prepared.source_scenario_id == "scenario-1"
    assert prepared.scenario_seed == "seed-1"
    assert prepared.scenario_instance.source_scenario_id == "scenario-1"
    assert prepared.conversation_contract.source.scenario_instance_id == (
        prepared.scenario_instance.instance_id
    )
    assert prepared.vapi_configuration.source_traceability.contract_id == (
        prepared.conversation_contract.contract_id
    )


def test_prepared_call_exposes_provider_payload_without_network() -> None:
    prepared = CallOrchestrator(policy=call_policy()).prepare_call(
        call_preparation_request(),
    )

    payload = prepared.provider_payload()

    assert payload["model"]["provider"] == "openai"
    assert payload["voice"]["provider"] == "openai"
    assert "metadata" in payload


def test_prepare_call_is_deterministic_for_same_request() -> None:
    request = call_preparation_request()
    first = CallOrchestrator(policy=call_policy()).prepare_call(request)
    second = CallOrchestrator(policy=call_policy()).prepare_call(request)

    assert first.preparation_id == second.preparation_id
    assert first.request_fingerprint == second.request_fingerprint
    assert first.vapi_configuration_fingerprint == (
        second.vapi_configuration_fingerprint
    )


def test_orchestrator_does_not_mutate_request() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())
    request = call_preparation_request()
    before = deepcopy(request)

    orchestrator.prepare_call(request)

    assert request == before


def test_unallowlisted_destination_is_rejected() -> None:
    request = call_preparation_request()
    invalid = request.model_copy(
        update={
            "destination": request.destination.model_copy(
                update={"value": "not-approved"},
            ),
        },
    )

    with pytest.raises(CallOrchestrationError) as error:
        CallOrchestrator(policy=call_policy()).prepare_call(invalid)

    assert "destination_not_allowlisted" in {
        issue.code for issue in error.value.result.errors
    }


def test_duration_override_is_validated_and_warned_not_applied() -> None:
    request = call_preparation_request().model_copy(
        update={"requested_call_duration_seconds": 120},
    )

    prepared = CallOrchestrator(policy=call_policy()).prepare_call(request)

    assert "requested_duration_recorded_not_applied" in {
        warning.code for warning in prepared.warnings
    }
