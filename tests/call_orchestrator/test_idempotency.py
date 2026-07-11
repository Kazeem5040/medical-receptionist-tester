from __future__ import annotations

import pytest

from call_orchestrator import CallOrchestrationError, CallOrchestrator
from tests.call_orchestrator_factories import (
    call_policy,
    call_preparation_request,
)


def test_same_idempotency_key_returns_existing_prepared_call() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())
    request = call_preparation_request()

    first = orchestrator.prepare_call(request)
    second = orchestrator.prepare_call(request)

    assert first.preparation_id == second.preparation_id
    assert "idempotent_result_reused" in {
        warning.code for warning in second.warnings
    }


def test_same_idempotency_key_with_different_request_is_error() -> None:
    orchestrator = CallOrchestrator(policy=call_policy())
    first_request = call_preparation_request(idempotency_key="idem-key-0001")
    second_request = call_preparation_request(
        idempotency_key="idem-key-0001",
        scenario_seed="different-seed",
    )

    orchestrator.prepare_call(first_request)

    with pytest.raises(CallOrchestrationError) as error:
        orchestrator.prepare_call(second_request)

    assert "idempotency_key_reused_with_different_request" in {
        issue.code for issue in error.value.result.errors
    }
