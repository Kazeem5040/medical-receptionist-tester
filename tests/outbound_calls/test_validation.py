from __future__ import annotations

import pytest

from call_execution import ExecutionStatus
from call_orchestrator import CallOrchestrator
from outbound_calls import (
    OutboundCallCreationPolicy,
    validate_outbound_call_creation_request,
)
from tests.call_orchestrator_factories import call_policy, call_preparation_request
from tests.outbound_call_factories import (
    valid_creation_request,
    valid_prepared_call,
    valid_submission_result,
)


@pytest.mark.asyncio
async def test_real_calls_are_blocked_unless_enabled() -> None:
    request = await valid_creation_request()

    result = validate_outbound_call_creation_request(
        request,
        OutboundCallCreationPolicy(
            allowed_destination_phone_numbers=("+18054398008",),
        ),
    )

    assert "real_calls_disabled" in {issue.code for issue in result.errors}


@pytest.mark.asyncio
async def test_destination_must_be_allowlisted() -> None:
    request = await valid_creation_request()

    result = validate_outbound_call_creation_request(
        request,
        OutboundCallCreationPolicy(
            real_calls_enabled=True,
            allowed_destination_phone_numbers=("+15550000000",),
        ),
    )

    assert "destination_not_allowlisted" in {issue.code for issue in result.errors}


@pytest.mark.asyncio
async def test_destination_must_be_phone_number_not_identifier() -> None:
    prepared = CallOrchestrator(policy=call_policy()).prepare_call(
        call_preparation_request(),
    )
    submission = await valid_submission_result(valid_prepared_call())
    request = (await valid_creation_request()).model_copy(
        update={
            "prepared_call": prepared,
            "call_submission_result": submission,
        },
    )

    result = validate_outbound_call_creation_request(
        request,
        OutboundCallCreationPolicy(
            real_calls_enabled=True,
            allowed_destination_phone_numbers=("+18054398008",),
        ),
    )

    codes = {issue.code for issue in result.errors}
    assert "destination_not_e164" in codes
    assert "preparation_id_mismatch" in codes


@pytest.mark.asyncio
async def test_submission_must_be_accepted() -> None:
    request = await valid_creation_request()
    rejected_submission = request.call_submission_result.model_copy(
        update={"execution_status": ExecutionStatus.REJECTED},
    )
    request = request.model_copy(
        update={"call_submission_result": rejected_submission},
    )

    result = validate_outbound_call_creation_request(
        request,
        OutboundCallCreationPolicy(
            real_calls_enabled=True,
            allowed_destination_phone_numbers=("+18054398008",),
        ),
    )

    assert "submission_not_accepted" in {issue.code for issue in result.errors}


@pytest.mark.asyncio
async def test_metadata_cannot_leak_secrets() -> None:
    request = await valid_creation_request(metadata={"api_key": "secret"})

    result = validate_outbound_call_creation_request(
        request,
        OutboundCallCreationPolicy(
            real_calls_enabled=True,
            allowed_destination_phone_numbers=("+18054398008",),
        ),
    )

    assert "forbidden_metadata_key" in {issue.code for issue in result.errors}
