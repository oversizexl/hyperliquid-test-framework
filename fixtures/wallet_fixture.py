"""钱包与 API 客户端的 pytest fixture：session 级 config/client，每用例后清理未成交单。"""

from __future__ import annotations

import pytest

from client.hyperliquid_client import HyperliquidClient
from support.config import get_config
from support.logger import get_logger

logger = get_logger("fixture")


@pytest.fixture(scope="session")
def config():
    """Session 级配置单例（从 get_config 获取）。"""
    return get_config()


@pytest.fixture(scope="session")
def client(config):
    """Session 级 API 客户端，所有测试共享；session 结束时关闭连接。"""
    c = HyperliquidClient(config)
    logger.info("Client initialised for %s", config.base_url)
    yield c
    c.close()


@pytest.fixture(scope="session")
def default_coin(config) -> str:
    """默认交易对（如 ETH），来自配置。"""
    return config.default_coin


@pytest.fixture(autouse=True)
def _test_isolation(client: HyperliquidClient, request):
    """每个用例结束后撤销本用例产生的未成交订单，保证测试隔离；可用 skip_cleanup 标记跳过。"""
    yield
    if request.node.get_closest_marker("skip_cleanup"):
        return
    try:
        client.cancel_all_open_orders()
    except Exception as exc:
        logger.warning("Post-test cleanup failed: %s", exc)
