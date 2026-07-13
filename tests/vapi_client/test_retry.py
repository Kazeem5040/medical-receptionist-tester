from __future__ import annotations

import httpx
import pytest

from vapi_client.retry import retry_async, should_retry_status


def test_should_retry_status_only_retries_transient_statuses() -> None:
    assert should_retry_status(429)
    assert should_retry_status(500)
    assert should_retry_status(503)
    assert not should_retry_status(400)
    assert not should_retry_status(401)
    assert not should_retry_status(404)


@pytest.mark.asyncio
async def test_retry_async_retries_transient_exceptions() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timeout")
        return "ok"

    result = await retry_async(
        operation,
        max_retries=1,
        backoff_initial_seconds=0,
        backoff_multiplier=2,
    )

    assert result == "ok"
    assert attempts == 2
