from __future__ import annotations

from call_orchestrator import ApprovedDestination, DestinationKind
from call_orchestrator.validation import validate_call_preparation_request
from tests.call_orchestrator_factories import (
    call_policy,
    call_preparation_request,
    phone_destination,
)


def test_allowlisted_phone_destination_is_valid() -> None:
    request = call_preparation_request().model_copy(
        update={"destination": phone_destination()},
    )

    result = validate_call_preparation_request(request, call_policy())

    assert result.is_valid


def test_invalid_e164_phone_destination_is_error() -> None:
    request = call_preparation_request().model_copy(
        update={
            "destination": ApprovedDestination(
                kind=DestinationKind.E164_PHONE_NUMBER,
                value="805-439-8008",
            ),
        },
    )

    result = validate_call_preparation_request(request, call_policy())

    assert not result.is_valid
    assert "invalid_e164_destination" in {issue.code for issue in result.errors}


def test_forbidden_metadata_key_is_error() -> None:
    request = call_preparation_request().model_copy(
        update={"metadata": {"api_key": "not-allowed"}},
    )

    result = validate_call_preparation_request(request, call_policy())

    assert not result.is_valid
    assert "forbidden_metadata_key" in {issue.code for issue in result.errors}


def test_requested_duration_over_policy_is_error() -> None:
    request = call_preparation_request().model_copy(
        update={"requested_call_duration_seconds": 9999},
    )

    result = validate_call_preparation_request(request, call_policy())

    assert not result.is_valid
    assert "requested_duration_too_high" in {issue.code for issue in result.errors}
