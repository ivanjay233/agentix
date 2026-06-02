"""Retry and timeout utilities for pipeline stages."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger("agentix")

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T],
    timeout: float = 300.0,
    stage_name: str = "unknown",
) -> T:
    """Run a coroutine with a timeout.

    Parameters
    ----------
    coro : Awaitable
        The coroutine to execute.
    timeout : float
        Maximum seconds to wait before raising TimeoutError (default: 300).
    stage_name : str
        Human-readable stage name for logging.

    Returns
    -------
    T
        The result of the coroutine.

    Raises
    ------
    asyncio.TimeoutError
        If the coroutine does not complete within ``timeout`` seconds.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("Stage '%s' timed out after %.1fs", stage_name, timeout)
        raise


async def run_with_retry(
    coro_factory: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    stage_name: str = "unknown",
) -> T:
    """Run a coroutine with retry on failure.

    Parameters
    ----------
    coro_factory : callable -> Awaitable
        A callable that returns a new coroutine for each attempt.
    max_retries : int
        Maximum number of attempts (default: 3).
    delay : float
        Initial delay between retries in seconds (default: 1.0).
    backoff : float
        Multiplier applied to delay after each failure (default: 2.0).
    stage_name : str
        Human-readable stage name for logging.

    Returns
    -------
    T
        The result of the successful coroutine execution.

    Raises
    ------
    Exception
        The last exception raised if all retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    current_delay = delay

    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Stage '%s' attempt %d/%d failed: %s",
                stage_name,
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise Exception(
        f"Stage '{stage_name}' failed after {max_retries} retries: {last_exc}"
    ) from last_exc
