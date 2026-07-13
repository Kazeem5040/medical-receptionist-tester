"""Retry helpers for transient Vapi HTTP failures."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


def should_retry_status(status_code: int) -> bool:
    """Return whether an HTTP status is a safe transient retry candidate."""

    return status_code == 429 or 500 <= status_code <= 599


def should_retry_exception(error: BaseException) -> bool:
    """Return whether an exception is a transient retry candidate."""

    error_name = type(error).__name__
    return error_name in {
        "ConnectError",
        "NetworkError",
        "ReadError",
        "RemoteProtocolError",
        "TimeoutException",
        "ConnectTimeout",
        "ReadTimeout",
        "PoolTimeout",
        "TimeoutError",
        "WriteTimeout",
    }


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    backoff_initial_seconds: float,
    backoff_multiplier: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an async operation with exponential backoff retries."""

    attempt = 0
    delay = backoff_initial_seconds
    while True:
        try:
            return await operation()
        except Exception as error:
            if attempt >= max_retries or not should_retry_exception(error):
                raise
            if delay > 0:
                await sleep(delay)
            delay *= backoff_multiplier
            attempt += 1
