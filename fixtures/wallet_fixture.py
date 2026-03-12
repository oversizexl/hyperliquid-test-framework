"""Pytest fixtures for wallet / client lifecycle management."""

from __future__ import annotations

import pytest

from client.hyperliquid_client import HyperliquidClient
from support.config import get_config
from support.logger import get_logger

logger = get_logger("fixture")


@pytest.fixture(scope="session")
def config():
    """Session-scoped configuration singleton."""
    return get_config()


@pytest.fixture(scope="session")
def client(config):
    """Session-scoped API client (shared across all tests)."""
    c = HyperliquidClient(config)
    logger.info("Client initialised for %s", config.base_url)
    yield c
    c.close()


@pytest.fixture(scope="session")
def default_coin(config) -> str:
    return config.default_coin


@pytest.fixture(autouse=True)
def _test_isolation(client: HyperliquidClient, request):
    """Per-test cleanup: cancel any open orders created during the test.

    Runs after each test to avoid polluting shared state.
    """
    yield
    if request.node.get_closest_marker("skip_cleanup"):
        return
    try:
        client.cancel_all_open_orders()
    except Exception as exc:
        logger.warning("Post-test cleanup failed: %s", exc)
