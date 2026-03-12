"""Account Tests — clearinghouse state, balances, field structure validation."""

import allure
import pytest

from client.hyperliquid_client import HyperliquidClient


@allure.feature("账户")
@allure.story("Clearinghouse 状态")
@pytest.mark.smoke
class TestAccountInfo:
    """Verify account query endpoints return well-formed data."""

    @allure.title("clearinghouse 状态包含 marginSummary/crossMarginSummary/withdrawable/assetPositions")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_clearinghouse_state_returns_required_fields(self, client: HyperliquidClient):
        state = client.get_clearinghouse_state()

        assert "marginSummary" in state
        assert "crossMarginSummary" in state
        assert "withdrawable" in state
        assert "assetPositions" in state

    @allure.title("marginSummary 包含 accountValue/totalNtlPos/totalRawUsd/totalMarginUsed 且为可解析数字")
    def test_margin_summary_structure(self, client: HyperliquidClient):
        state = client.get_clearinghouse_state()
        summary = state["marginSummary"]

        required = {"accountValue", "totalNtlPos", "totalRawUsd", "totalMarginUsed"}
        assert required.issubset(summary.keys()), f"Missing keys: {required - summary.keys()}"

        for key in required:
            val = summary[key]
            assert isinstance(val, str), f"{key} should be string, got {type(val)}"
            float(val)  # must be parseable as numeric

    @allure.title("crossMarginSummary 结构正确且数值可解析")
    def test_cross_margin_summary_structure(self, client: HyperliquidClient):
        state = client.get_clearinghouse_state()
        summary = state["crossMarginSummary"]

        for key in ("accountValue", "totalNtlPos", "totalRawUsd", "totalMarginUsed"):
            assert key in summary
            float(summary[key])

    @allure.title("账户价值非负")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_account_value_is_non_negative(self, client: HyperliquidClient):
        value = client.get_account_value()
        assert value >= 0, f"Account value should be >= 0, got {value}"

    @allure.title("withdrawable 为可解析的非负数字字符串")
    def test_withdrawable_is_string_numeric(self, client: HyperliquidClient):
        state = client.get_clearinghouse_state()
        withdrawable = state["withdrawable"]
        assert isinstance(withdrawable, str)
        assert float(withdrawable) >= 0

    @allure.title("assetPositions 为列表类型")
    def test_asset_positions_is_list(self, client: HyperliquidClient):
        state = client.get_clearinghouse_state()
        positions = state["assetPositions"]
        assert isinstance(positions, list)


@allure.feature("账户")
@allure.story("元数据")
@pytest.mark.smoke
class TestMetaData:
    """Verify market metadata endpoints."""

    @allure.title("get_meta 返回 universe 且非空")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_meta_returns_universe(self, client: HyperliquidClient):
        meta = client.get_meta()
        assert "universe" in meta
        assert len(meta["universe"]) > 0

    @allure.title("universe 条目包含 name/szDecimals/maxLeverage")
    def test_universe_entry_structure(self, client: HyperliquidClient):
        meta = client.get_meta()
        first = meta["universe"][0]

        assert "name" in first
        assert "szDecimals" in first
        assert "maxLeverage" in first
        assert isinstance(first["szDecimals"], int)
        assert isinstance(first["maxLeverage"], int)

    @allure.title("resolve_asset 对已知币种返回非负整数")
    def test_resolve_known_coin(self, client: HyperliquidClient, default_coin: str):
        asset_idx = client.resolve_asset(default_coin)
        assert isinstance(asset_idx, int)
        assert asset_idx >= 0

    @allure.title("get_all_mids 返回非空字典")
    def test_all_mids_returns_dict(self, client: HyperliquidClient):
        mids = client.get_all_mids()
        assert isinstance(mids, dict)
        assert len(mids) > 0

    @allure.title("get_mid_price 对默认币种返回正数")
    def test_mid_price_for_default_coin(self, client: HyperliquidClient, default_coin: str):
        price = client.get_mid_price(default_coin)
        assert price > 0
