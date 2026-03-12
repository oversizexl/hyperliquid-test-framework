"""Position Tests — open, query, validate size/entryPx, close."""

import time

import allure
import pytest

from client.hyperliquid_client import HyperliquidClient
from support.waiters import wait_until
from support.logger import get_logger

logger = get_logger("test.positions")


def _market_buy(client: HyperliquidClient, coin: str, sz: float) -> dict:
    """Place an aggressive IOC buy that should fill immediately."""
    mid = client.get_mid_price(coin)
    aggressive_px = round(mid * 1.05, 1)  # 5 % above mid
    return client.place_order(
        coin=coin,
        is_buy=True,
        sz=sz,
        limit_px=aggressive_px,
        order_type={"limit": {"tif": "Ioc"}},
    )


def _market_sell(client: HyperliquidClient, coin: str, sz: float) -> dict:
    """Place an aggressive IOC sell that should fill immediately."""
    mid = client.get_mid_price(coin)
    aggressive_px = round(mid * 0.95, 1)  # 5 % below mid
    return client.place_order(
        coin=coin,
        is_buy=False,
        sz=sz,
        limit_px=aggressive_px,
        order_type={"limit": {"tif": "Ioc"}},
    )


def _min_fill_size(client: HyperliquidClient, coin: str) -> float:
    """Smallest size that exceeds $10 minimum notional at current price."""
    mid = client.get_mid_price(coin)
    sz_decimals = client.get_sz_decimals(coin)
    raw = 12.0 / mid  # slightly over $10
    return round(raw, sz_decimals)


@allure.feature("仓位")
@allure.story("开仓")
@pytest.mark.position
class TestOpenPosition:
    """Verify position appears after a fill."""

    @allure.title("市价买入后出现多仓且 entryPx > 0")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_long_position_created_after_buy(self, client: HyperliquidClient, default_coin: str):
        sz = _min_fill_size(client, default_coin)
        resp = _market_buy(client, default_coin, sz)

        oid = client.extract_oid(resp)
        # The order may have filled (no oid in "resting"), so we check positions
        statuses = resp["response"]["data"]["statuses"]
        first = statuses[0]
        filled = "filled" in first

        if not filled:
            pytest.skip("IOC order did not fill — likely no liquidity on testnet")

        def _has_position():
            pos = client.get_position_for_coin(default_coin)
            if pos and float(pos["position"]["szi"]) > 0:
                return pos
            return None

        pos = wait_until(_has_position, description=f"long position for {default_coin}", timeout=20)
        assert float(pos["position"]["szi"]) > 0
        assert float(pos["position"]["entryPx"]) > 0

        # Cleanup: close the position
        _market_sell(client, default_coin, float(pos["position"]["szi"]))

    @allure.title("成交后 entry price 与 mid 偏差在 10% 内")
    def test_position_has_valid_entry_price(self, client: HyperliquidClient, default_coin: str):
        sz = _min_fill_size(client, default_coin)
        resp = _market_buy(client, default_coin, sz)

        statuses = resp["response"]["data"]["statuses"]
        if "filled" not in statuses[0]:
            pytest.skip("IOC order did not fill")

        avg_px = float(statuses[0]["filled"]["avgPx"])
        mid = client.get_mid_price(default_coin)

        # Entry price should be within 10 % of current mid
        assert abs(avg_px - mid) / mid < 0.10, (
            f"avgPx={avg_px} deviates too far from mid={mid}"
        )

        # Cleanup
        pos = client.get_position_for_coin(default_coin)
        if pos and float(pos["position"]["szi"]) > 0:
            _market_sell(client, default_coin, float(pos["position"]["szi"]))


@allure.feature("仓位")
@allure.story("平仓")
@pytest.mark.position
class TestClosePosition:
    """Verify position reduces after closing."""

    @allure.title("市价卖出后仓位归零")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_position_reduces_after_sell(self, client: HyperliquidClient, default_coin: str):
        sz = _min_fill_size(client, default_coin)
        buy_resp = _market_buy(client, default_coin, sz)

        if "filled" not in buy_resp["response"]["data"]["statuses"][0]:
            pytest.skip("Buy IOC did not fill")

        filled_sz = float(buy_resp["response"]["data"]["statuses"][0]["filled"]["totalSz"])

        sell_resp = _market_sell(client, default_coin, filled_sz)

        if "filled" not in sell_resp["response"]["data"]["statuses"][0]:
            pytest.skip("Sell IOC did not fill")

        def _position_cleared():
            pos = client.get_position_for_coin(default_coin)
            if pos is None:
                return True
            if abs(float(pos["position"]["szi"])) < 1e-8:
                return True
            return None

        wait_until(_position_cleared, description="position closed", timeout=20)


@allure.feature("仓位")
@allure.story("查询仓位")
@pytest.mark.position
class TestQueryPositions:
    """Verify position query endpoints."""

    @allure.title("get_positions 返回列表")
    def test_get_positions_returns_list(self, client: HyperliquidClient):
        positions = client.get_positions()
        assert isinstance(positions, list)

    @allure.title("仓位条目包含 coin/entryPx/szi/leverage/unrealizedPnl/positionValue")
    def test_position_entry_structure(self, client: HyperliquidClient, default_coin: str):
        sz = _min_fill_size(client, default_coin)
        resp = _market_buy(client, default_coin, sz)

        if "filled" not in resp["response"]["data"]["statuses"][0]:
            pytest.skip("IOC order did not fill")

        def _has_position():
            pos = client.get_position_for_coin(default_coin)
            if pos and float(pos["position"]["szi"]) > 0:
                return pos
            return None

        pos = wait_until(_has_position, description="position visible", timeout=20)
        p = pos["position"]

        assert "coin" in p
        assert "entryPx" in p
        assert "szi" in p
        assert "leverage" in p
        assert "unrealizedPnl" in p
        assert "positionValue" in p

        # Cleanup
        _market_sell(client, default_coin, float(p["szi"]))
