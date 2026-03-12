"""可配置的重试装饰器，用于瞬时失败（网络、超时等）。"""

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
    """在指定异常时按指数退避重试。

    仅适用于幂等/只读操作；切勿用于写操作（如下单），否则可能重复执行。
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
