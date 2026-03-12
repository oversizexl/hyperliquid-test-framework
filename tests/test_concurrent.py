"""Concurrent Tests (optional) — submit multiple orders simultaneously."""

import concurrent.futures

import allure
import pytest

from client.hyperliquid_client import HyperliquidClient
from support.logger import get_logger

logger = get_logger("test.concurrent")

NUM_CONCURRENT = 5


def _place_far_limit(client: HyperliquidClient, coin: str, idx: int) -> dict | Exception:
    """Place one far-limit buy order. Returns response or exception."""
    try:
        mid = client.get_mid_price(coin)
        px = round(mid * 0.5, 1)
        sz_decimals = client.get_sz_decimals(coin)
        sz = round(11.0 / px, sz_decimals)
        return client.place_order(coin=coin, is_buy=True, sz=sz, limit_px=px)
    except Exception as exc:
        logger.warning("Concurrent order #%d failed: %s", idx, exc)
        return exc


@allure.feature("并发")
@allure.story("并发下单")
@pytest.mark.concurrent
class TestConcurrentOrders:

    @allure.title("并发提交 5 个限价单，成功率 ≥ 60%")
    @allure.severity(allure.severity_level.NORMAL)
    def test_concurrent_limit_orders(self, client: HyperliquidClient, default_coin: str):
        """Submit N orders in parallel; verify majority succeed."""
        results: list[dict | Exception] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CONCURRENT) as pool:
            futures = [
                pool.submit(_place_far_limit, client, default_coin, i)
                for i in range(NUM_CONCURRENT)
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        successes = [r for r in results if isinstance(r, dict)]
        failures = [r for r in results if isinstance(r, Exception)]

        logger.info(
            "Concurrent results: %d success, %d failure out of %d",
            len(successes),
            len(failures),
            NUM_CONCURRENT,
        )

        # At least 60 % should succeed; testnet may have rate limits
        assert len(successes) >= NUM_CONCURRENT * 0.6, (
            f"Too many failures: {len(failures)}/{NUM_CONCURRENT}"
        )

        # All successes should have valid oids
        for resp in successes:
            oid = client.extract_oid(resp)
            assert oid is not None
