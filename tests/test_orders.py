"""Order Lifecycle Tests — create, query, cancel, verify status transitions."""

import math

import allure
import pytest

from client.hyperliquid_client import HyperliquidClient
from client.exceptions import HyperliquidApiError
from support.ids import generate_cloid
from support.waiters import wait_until


def _far_limit_price(client: HyperliquidClient, coin: str, is_buy: bool) -> float:
    """Return a limit price far enough from mid to avoid immediate fill.

    For buy orders: 50 % below mid.
    For sell orders: 200 % above mid.
    """
    mid = client.get_mid_price(coin)
    if is_buy:
        return round(mid * 0.5, 1)
    return round(mid * 2.0, 1)


def _min_order_size(
    client: HyperliquidClient,
    coin: str,
    limit_px: float,
    notional_price: float | None = None,
) -> float:
    """Return order size that meets the $10 minimum notional.

    Exchange checks notional at mid (mark) price, not limit price. For sells
    limit_px can be 2*mid, so we must size using mid to get sz*mid >= $10.
    """
    sz_decimals = client.get_sz_decimals(coin)
    price_for_check = notional_price if notional_price is not None else limit_px
    min_notional = 12.0  # exchange minimum $10; 12 avoids float/rounding edge cases
    min_sz_raw = min_notional / price_for_check
    min_sz = math.ceil(min_sz_raw * (10**sz_decimals)) / (10**sz_decimals)
    return min_sz


@allure.feature("订单")
@allure.story("下单")
@pytest.mark.order
class TestPlaceOrder:
    """Test order creation."""

    @allure.title("下限价买单成功并返回 oid")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_place_limit_buy_order(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        resp = client.place_order(
            coin=default_coin, is_buy=True, sz=sz, limit_px=px,
        )
        oid = client.extract_oid(resp)
        assert oid is not None, f"Expected oid in response: {resp}"

    @allure.title("下限价卖单成功并返回 oid")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_place_limit_sell_order(self, client: HyperliquidClient, default_coin: str):
        mid = client.get_mid_price(default_coin)
        px = _far_limit_price(client, default_coin, is_buy=False)
        sz = _min_order_size(client, default_coin, px, notional_price=mid)

        resp = client.place_order(
            coin=default_coin, is_buy=False, sz=sz, limit_px=px,
        )
        oid = client.extract_oid(resp)
        assert oid is not None, f"Expected oid in response: {resp}"

    @allure.title("带 cloid 下单成功")
    def test_place_order_with_cloid(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)
        cloid = generate_cloid()

        resp = client.place_order(
            coin=default_coin, is_buy=True, sz=sz, limit_px=px, cloid=cloid,
        )
        oid = client.extract_oid(resp)
        assert oid is not None


@allure.feature("订单")
@allure.story("查询订单")
@pytest.mark.order
class TestQueryOrder:
    """Test order querying."""

    @allure.title("下单后 open_orders 中包含该订单")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_open_orders_contains_placed_order(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        resp = client.place_order(coin=default_coin, is_buy=True, sz=sz, limit_px=px)
        oid = client.extract_oid(resp)
        assert oid is not None

        def _find():
            orders = client.get_open_orders()
            return next((o for o in orders if o["oid"] == oid), None)

        found = wait_until(_find, description=f"order {oid} visible in open orders", timeout=15)
        assert found["coin"] == default_coin

    @allure.title("按 oid 查询订单状态为 open")
    def test_order_status_shows_open(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        resp = client.place_order(coin=default_coin, is_buy=True, sz=sz, limit_px=px)
        oid = client.extract_oid(resp)
        assert oid is not None

        def _status_open():
            status_resp = client.get_order_status(oid)
            if status_resp.get("status") == "order":
                order_info = status_resp.get("order", {})
                if order_info.get("status") == "open":
                    return order_info
            return None

        info = wait_until(_status_open, description=f"order {oid} status=open", timeout=15)
        assert info["order"]["coin"] == default_coin


@allure.feature("订单")
@allure.story("撤单")
@pytest.mark.order
class TestCancelOrder:
    """Test order cancellation."""

    @allure.title("按 oid 撤单成功")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_cancel_by_oid(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        place_resp = client.place_order(coin=default_coin, is_buy=True, sz=sz, limit_px=px)
        oid = client.extract_oid(place_resp)
        assert oid is not None

        cancel_resp = client.cancel_order(default_coin, oid)
        statuses = cancel_resp["response"]["data"]["statuses"]
        assert "success" in statuses

    @allure.title("按 cloid 撤单成功")
    def test_cancel_by_cloid(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)
        cloid = generate_cloid()

        place_resp = client.place_order(
            coin=default_coin, is_buy=True, sz=sz, limit_px=px, cloid=cloid,
        )
        oid = client.extract_oid(place_resp)
        assert oid is not None

        cancel_resp = client.cancel_order_by_cloid(default_coin, cloid)
        statuses = cancel_resp["response"]["data"]["statuses"]
        assert "success" in statuses

    @allure.title("重复撤单抛出 HyperliquidApiError")
    def test_cancel_already_canceled_order_returns_error(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        place_resp = client.place_order(coin=default_coin, is_buy=True, sz=sz, limit_px=px)
        oid = client.extract_oid(place_resp)
        assert oid is not None

        client.cancel_order(default_coin, oid)

        with pytest.raises(HyperliquidApiError):
            client.cancel_order(default_coin, oid)

    @allure.title("撤单后订单状态变为 canceled")
    def test_order_status_after_cancel(self, client: HyperliquidClient, default_coin: str):
        px = _far_limit_price(client, default_coin, is_buy=True)
        sz = _min_order_size(client, default_coin, px)

        place_resp = client.place_order(coin=default_coin, is_buy=True, sz=sz, limit_px=px)
        oid = client.extract_oid(place_resp)
        assert oid is not None

        client.cancel_order(default_coin, oid)

        def _status_canceled():
            status_resp = client.get_order_status(oid)
            if status_resp.get("status") == "order":
                order_info = status_resp.get("order", {})
                if order_info.get("status") == "canceled":
                    return order_info
            return None

        info = wait_until(_status_canceled, description=f"order {oid} status=canceled", timeout=15)
        assert info is not None
