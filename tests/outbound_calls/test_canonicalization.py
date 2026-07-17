from __future__ import annotations

import pytest

from outbound_calls import canonical_snapshot, stable_fingerprint
from tests.outbound_call_factories import valid_creation_request


@pytest.mark.asyncio
async def test_canonical_snapshot_is_stable() -> None:
    request = await valid_creation_request()

    first = canonical_snapshot(request)
    second = canonical_snapshot(request)

    assert first == second


@pytest.mark.asyncio
async def test_stable_fingerprint_is_deterministic() -> None:
    request = await valid_creation_request()

    first = stable_fingerprint(request, prefix="outbound_test")
    second = stable_fingerprint(request, prefix="outbound_test")

    assert first == second
    assert first.startswith("outbound_test:")
