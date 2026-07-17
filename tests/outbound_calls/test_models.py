from __future__ import annotations

import pytest
from pydantic import ValidationError

from outbound_calls import OutboundCallCreationRequest
from tests.outbound_call_factories import valid_creation_request


@pytest.mark.asyncio
async def test_creation_request_is_immutable() -> None:
    request = await valid_creation_request()

    with pytest.raises(ValidationError):
        request.phone_number_id = "different"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_creation_request_rejects_unknown_fields() -> None:
    request = await valid_creation_request()

    with pytest.raises(ValidationError):
        OutboundCallCreationRequest.model_validate(
            {
                **request.model_dump(),
                "unexpected": "nope",
            },
        )
