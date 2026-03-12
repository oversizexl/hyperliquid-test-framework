"""基于轮询的等待工具，用于 testnet 最终一致状态（如订单可见、仓位归零）。"""

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
    """轮询 condition()，直到返回真值或超时。

    condition: 无参可调用，返回真值表示条件满足并停止等待，None/False 则继续轮询。
    description: 用于日志的可读描述。
    timeout: 最大等待秒数。
    interval: 每次轮询间隔秒数。
    返回: condition 首次返回的真值。
    超时则抛出 HyperliquidTimeoutError。
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
