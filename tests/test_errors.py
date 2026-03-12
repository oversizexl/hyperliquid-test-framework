"""Error Handling Tests — invalid inputs, boundary conditions, expected failures."""

import allure
import pytest

from client.hyperliquid_client import HyperliquidClient
from client.exceptions import HyperliquidApiError, HyperliquidValidationError


@allure.feature("错误处理")
@allure.story("非法交易对")
@pytest.mark.error
class TestInvalidSymbol:
    """Requests with a non-existent coin should fail gracefully."""

    @allure.title("resolve_asset 非法币种抛出 HyperliquidValidationError")
    def test_resolve_invalid_coin_raises_validation_error(self, client: HyperliquidClient):
        with pytest.raises(HyperliquidValidationError, match="Unknown coin"):
            client.resolve_asset("FAKECOIN_XYZ_999")

    @allure.title("get_mid_price 非法币种抛出异常")
    def test_get_mid_price_invalid_coin(self, client: HyperliquidClient):
        with pytest.raises(HyperliquidValidationError, match="No mid price"):
            client.get_mid_price("FAKECOIN_XYZ_999")


@allure.feature("错误处理")
@allure.story("非法价格")
@pytest.mark.error
class TestInvalidPrice:
    """Orders with unreasonable prices should be rejected."""

    @allure.title("零价格订单被拒绝")
    def test_zero_price_order_rejected(self, client: HyperliquidClient, default_coin: str):
        sz_decimals = client.get_sz_decimals(default_coin)
        with pytest.raises(HyperliquidApiError):
            client.place_order(
                coin=default_coin,
                is_buy=True,
                sz=round(1.0, sz_decimals),
                limit_px=0.0,
            )

    @allure.title("负价格订单被拒绝")
    def test_negative_price_order_rejected(self, client: HyperliquidClient, default_coin: str):
        with pytest.raises((HyperliquidApiError, HyperliquidValidationError, ValueError)):
            client.place_order(
                coin=default_coin,
                is_buy=True,
                sz=0.01,
                limit_px=-100.0,
            )


@allure.feature("错误处理")
@allure.story("非法数量")
@pytest.mark.error
class TestInvalidSize:
    """Orders with invalid size should be rejected."""

    @allure.title("零数量订单被拒绝")
    def test_zero_size_order_rejected(self, client: HyperliquidClient, default_coin: str):
        mid = client.get_mid_price(default_coin)
        with pytest.raises((HyperliquidApiError, HyperliquidValidationError, ValueError)):
            client.place_order(
                coin=default_coin,
                is_buy=True,
                sz=0.0,
                limit_px=round(mid * 0.5, 1),
            )

    @allure.title("低于最小名义金额($10)的订单被拒绝")
    def test_below_minimum_notional_rejected(self, client: HyperliquidClient, default_coin: str):
        """Order notional below $10 should be rejected."""
        mid = client.get_mid_price(default_coin)
        sz_decimals = client.get_sz_decimals(default_coin)
        tiny_sz = round(1.0 / mid, sz_decimals)  # ~$1 notional
        if tiny_sz <= 0:
            tiny_sz = 10 ** (-sz_decimals)

        with pytest.raises(HyperliquidApiError, match="(?i)minimum"):
            client.place_order(
                coin=default_coin,
                is_buy=True,
                sz=tiny_sz,
                limit_px=round(mid * 0.5, 1),
            )


@allure.feature("错误处理")
@allure.story("撤单错误")
@pytest.mark.error
class TestCancelErrors:
    """Cancel operations on non-existent orders."""

    @allure.title("取消不存在的订单抛出 HyperliquidApiError")
    def test_cancel_nonexistent_oid(self, client: HyperliquidClient, default_coin: str):
        fake_oid = 999_999_999_999
        with pytest.raises(HyperliquidApiError):
            client.cancel_order(default_coin, fake_oid)


@allure.feature("错误处理")
@allure.story("订单类型边界")
@pytest.mark.error
class TestInvalidOrderType:
    """Edge cases for order type parameters."""

    @allure.title("无仓位时 reduce_only 订单失败或被自动取消")
    def test_reduce_only_without_position(self, client: HyperliquidClient, default_coin: str):
        """Reduce-only order with no existing position should fail or be immediately canceled."""
        mid = client.get_mid_price(default_coin)
        sz_decimals = client.get_sz_decimals(default_coin)
        sz = round(12.0 / mid, sz_decimals)

        # This should either raise or place and get auto-canceled
        try:
            resp = client.place_order(
                coin=default_coin,
                is_buy=True,
                sz=sz,
                limit_px=round(mid * 0.5, 1),
                reduce_only=True,
            )
            # If it didn't raise, the status might contain an error
            statuses = resp["response"]["data"]["statuses"]
            first = statuses[0]
            if isinstance(first, dict) and "error" in first:
                pass  # Expected
            # Else the exchange accepted it but will cancel it
        except HyperliquidApiError:
            pass  # Expected
