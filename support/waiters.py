"""Polling-based wait utilities for eventually-consistent state."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from client.exceptions import HyperliquidTimeoutError
from support.logger import get_logger

logger = get_logger("waiter")

T = TypeVar("T")


def wait_until(
    condition: Callable[[], T | None],
    description: str = "condition",
    timeout: float = 30.0,
    interval: float = 1.0,
) -> T:
    """Poll *condition* until it returns a truthy value, or raise on timeout.

    Args:
        condition: Zero-arg callable. Return a truthy value to stop waiting,
                   or None/False to keep polling.
        description: Human-readable label for log messages.
        timeout: Maximum seconds to wait.
        interval: Seconds between polls.

    Returns:
        The first truthy value returned by *condition*.

    Raises:
        HyperliquidTimeoutError: If *timeout* is exceeded.
    """
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        result = condition()
        if result:
            logger.info("Condition '%s' met after %d polls", description, attempt)
            return result

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise HyperliquidTimeoutError(
                f"Timed out after {timeout}s waiting for: {description}"
            )
        time.sleep(min(interval, remaining))
