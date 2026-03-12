"""Configurable retry decorator for transient failures."""

from __future__ import annotations

import time
import functools
from typing import Callable, Type

from support.logger import get_logger

logger = get_logger("retry")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Retry a function on specified exceptions with exponential backoff.

    Only safe for idempotent / read operations. Never use on write operations
    that may cause duplicate side-effects (e.g. placing orders).
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.warning(
                            "All %d attempts exhausted for %s: %s",
                            max_attempts,
                            func.__name__,
                            exc,
                        )
                        raise
                    logger.info(
                        "Attempt %d/%d for %s failed (%s), retrying in %.1fs",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
