"""自研 Hyperliquid API 客户端，不依赖官方/社区 SDK。

覆盖：账户查询、下单、撤单、订单查询、仓位查询、市场数据等。
所有 exchange（写操作）均使用 EIP-712 phantom-agent 签名。
"""

from __future__ import annotations

import json
import time
from typing import Any

import allure
import httpx
from eth_account import Account

from client.exceptions import (
    HyperliquidApiError,
    HyperliquidTimeoutError,
    HyperliquidValidationError,
)
from client.signer import float_to_wire, sign_l1_action
from support.config import Config
from support.logger import get_logger
from support.retry import retry

logger = get_logger("client")


class HyperliquidClient:
    """对 Hyperliquid REST API 的轻量封装，可在多处复用。"""

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._wallet = Account.from_key(config.private_key)
        # trust_env=False：不使用环境变量中的 HTTP_PROXY/HTTPS_PROXY，直连 API，避免代理 403
        self._http = httpx.Client(
            timeout=config.request_timeout,
            headers={"Content-Type": "application/json"},
            trust_env=False,
        )
        self._asset_map: dict[str, int] | None = None

    def close(self) -> None:
        self._http.close()

    # ── Info 接口（只读，可安全重试）────────────────────────────────

    @retry(max_attempts=3, delay=1.0, exceptions=(httpx.HTTPError, HyperliquidTimeoutError))
    def _post_info(self, payload: dict) -> Any:
        """向 /info 发 POST，用于查询类请求，带重试与 Allure 附件。"""
        logger.debug("POST %s  body=%s", self._cfg.info_url, _safe_repr(payload))
        with allure.step(f"API Info: {payload.get('type', 'unknown')}"):
            allure.attach(json.dumps(payload, indent=2), name="Request Payload", attachment_type=allure.attachment_type.JSON)
            resp = self._http.post(self._cfg.info_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("Response: %s", _safe_repr(data))
            allure.attach(json.dumps(data, indent=2), name="Response Data", attachment_type=allure.attachment_type.JSON)
            return data

    # ── Exchange 接口（写操作，不自动重试）──────────────────────────────

    def _post_exchange(self, action: dict, nonce: int | None = None) -> dict:
        """向 /exchange 发 POST，带 EIP-712 签名，不重试以防重复下单。"""
        if nonce is None:
            nonce = _timestamp_ms()
        signature = sign_l1_action(
            wallet=self._wallet,
            action=action,
            vault_address=None,
            nonce=nonce,
            is_mainnet=self._cfg.is_mainnet,
        )
        body = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
        }
        logger.info("POST %s  action.type=%s", self._cfg.exchange_url, action.get("type"))
        logger.debug("Exchange body: %s", _safe_repr(body))
        
        with allure.step(f"API Exchange: {action.get('type', 'unknown')}"):
            safe_body = body.copy()
            safe_body["signature"] = {"r": "***", "s": "***", "v": "***"} if isinstance(signature, dict) else "***"
            allure.attach(json.dumps(safe_body, indent=2), name="Request Action", attachment_type=allure.attachment_type.JSON)
            
            resp = self._http.post(self._cfg.exchange_url, json=body)
            try:
                data = resp.json()
            except Exception:
                data = {}
            logger.debug("Exchange response: %s", _safe_repr(data))

            if resp.status_code >= 400:
                msg = self._exchange_error_message(resp, data)
                raise HyperliquidApiError(msg, raw_response=data)
            allure.attach(json.dumps(data, indent=2), name="Response Data", attachment_type=allure.attachment_type.JSON)
            self._check_exchange_response(data)
            return data

    # ── 资产索引解析 ───────────────────────────────────────────────────

    def get_meta(self) -> dict:
        """获取合约元数据（universe 等）。"""
        return self._post_info({"type": "meta"})

    def resolve_asset(self, coin: str) -> int:
        """根据永续合约名称返回对应的数字资产索引。"""
        if self._asset_map is None:
            meta = self.get_meta()
            self._asset_map = {
                item["name"]: idx for idx, item in enumerate(meta["universe"])
            }
        if coin not in self._asset_map:
            raise HyperliquidValidationError(f"Unknown coin '{coin}'. Available: {list(self._asset_map.keys())[:20]}")
        return self._asset_map[coin]

    def get_sz_decimals(self, coin: str) -> int:
        """获取指定合约的数量小数位数。"""
        meta = self.get_meta()
        for item in meta["universe"]:
            if item["name"] == coin:
                return item["szDecimals"]
        raise HyperliquidValidationError(f"Cannot find szDecimals for '{coin}'")

    # ── 账户 ────────────────────────────────────────────────────────────

    def get_clearinghouse_state(self, user: str | None = None) -> dict:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "clearinghouseState", "user": user})

    def get_account_value(self, user: str | None = None) -> float:
        state = self.get_clearinghouse_state(user)
        return float(state["marginSummary"]["accountValue"])

    # ── 订单 ───────────────────────────────────────────────────────────

    def get_open_orders(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "openOrders", "user": user})

    def get_frontend_open_orders(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "frontendOpenOrders", "user": user})

    def get_order_status(self, oid: int, user: str | None = None) -> dict:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "orderStatus", "user": user, "oid": oid})

    def place_order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: dict | None = None,
        reduce_only: bool = False,
        cloid: str | None = None,
    ) -> dict:
        """下一个单笔订单，返回 exchange 原始响应。"""
        asset = self.resolve_asset(coin)
        if order_type is None:
            order_type = {"limit": {"tif": "Gtc"}}

        order_wire: dict[str, Any] = {
            "a": asset,
            "b": is_buy,
            "p": float_to_wire(limit_px),
            "s": float_to_wire(sz),
            "r": reduce_only,
            "t": order_type,
        }
        if cloid is not None:
            order_wire["c"] = cloid

        action = {
            "type": "order",
            "orders": [order_wire],
            "grouping": "na",
        }
        return self._post_exchange(action)

    def cancel_order(self, coin: str, oid: int) -> dict:
        asset = self.resolve_asset(coin)
        action = {
            "type": "cancel",
            "cancels": [{"a": asset, "o": oid}],
        }
        return self._post_exchange(action)

    def cancel_order_by_cloid(self, coin: str, cloid: str) -> dict:
        asset = self.resolve_asset(coin)
        action = {
            "type": "cancelByCloid",
            "cancels": [{"asset": asset, "cloid": cloid}],
        }
        return self._post_exchange(action)

    # ── 仓位 ────────────────────────────────────────────────────────────

    def get_positions(self, user: str | None = None) -> list[dict]:
        state = self.get_clearinghouse_state(user)
        return state.get("assetPositions", [])

    def get_position_for_coin(self, coin: str, user: str | None = None) -> dict | None:
        for pos in self.get_positions(user):
            if pos.get("position", {}).get("coin") == coin:
                return pos
        return None

    # ── 市场数据 ────────────────────────────────────────────────────────

    def get_all_mids(self) -> dict[str, str]:
        return self._post_info({"type": "allMids"})

    def get_mid_price(self, coin: str) -> float:
        mids = self.get_all_mids()
        if coin not in mids:
            raise HyperliquidValidationError(f"No mid price for '{coin}'")
        return float(mids[coin])

    def get_l2_book(self, coin: str) -> dict:
        return self._post_info({"type": "l2Book", "coin": coin})

    # ── 杠杆 ────────────────────────────────────────────────────────────

    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> dict:
        asset = self.resolve_asset(coin)
        action = {
            "type": "updateLeverage",
            "asset": asset,
            "isCross": is_cross,
            "leverage": leverage,
        }
        return self._post_exchange(action)

    # ── 成交与历史 ─────────────────────────────────────────────────────

    def get_user_fills(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "userFills", "user": user})

    def get_historical_orders(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "historicalOrders", "user": user})

    # ── 清理工具 ────────────────────────────────────────────────────────

    def cancel_all_open_orders(self) -> int:
        """尽最大努力撤销所有未成交订单；返回成功撤销的订单数量。优先批量撤单，失败时逐单撤。"""
        raw = self.get_open_orders()
        if isinstance(raw, list):
            open_orders = raw
        elif isinstance(raw, dict):
            open_orders = raw.get("data", raw.get("orders", raw.get("result", raw.get("openOrders", []))))
        else:
            open_orders = []
        if not isinstance(open_orders, list):
            open_orders = []
        to_cancel: list[tuple[str, int]] = []
        for order in open_orders:
            if not isinstance(order, dict):
                continue
            coin = order.get("coin")
            oid = order.get("oid")
            if coin is None or oid is None:
                logger.warning("Skip order with missing coin/oid: %s", order)
                continue
            to_cancel.append((coin, oid))
        if not to_cancel:
            return 0
        # 优先一次请求批量撤单，减少失败和限流
        try:
            cancels = [{"a": self.resolve_asset(coin), "o": oid} for coin, oid in to_cancel]
            action = {"type": "cancel", "cancels": cancels}
            self._post_exchange(action)
            logger.info("Cancelled %s open order(s) in one request", len(to_cancel))
            return len(to_cancel)
        except Exception as exc:
            logger.warning("Batch cancel failed (%s), falling back to per-order cancel: %s", len(to_cancel), exc)
        cancelled = 0
        for coin, oid in to_cancel:
            try:
                self.cancel_order(coin, oid)
                cancelled += 1
            except Exception as exc:
                logger.warning("Failed to cancel order %s: %s", oid, exc)
        return cancelled

    # ── 内部方法 ─────────────────────────────────────────────────────────

    @staticmethod
    def _exchange_error_message(resp: httpx.Response, data: dict | Any) -> str:
        """从 4xx 的 exchange 响应中提取可读错误信息。"""
        if isinstance(data, dict) and data:
            err = data.get("error") or data.get("message") or data.get("detail")
            if isinstance(err, str):
                return err
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])
            if data.get("response", {}).get("data", {}).get("statuses"):
                statuses = data["response"]["data"]["statuses"]
                if statuses and isinstance(statuses[0], dict) and "error" in statuses[0]:
                    return str(statuses[0]["error"])
        return f"HTTP {resp.status_code} {resp.reason_phrase}"

    @staticmethod
    def _check_exchange_response(data: dict) -> None:
        """若 exchange 响应中包含错误则抛出 HyperliquidApiError。"""
        if data.get("status") != "ok":
            raise HyperliquidApiError(
                f"Exchange returned non-ok status: {data}",
                raw_response=data,
            )
        resp = data.get("response", {})
        resp_data = resp.get("data", {})
        statuses = resp_data.get("statuses", [])
        for s in statuses:
            if isinstance(s, dict) and "error" in s:
                raise HyperliquidApiError(
                    s["error"],
                    raw_response=data,
                )

    @staticmethod
    def extract_oid(response: dict) -> int | None:
        """从下单响应中解析出订单 ID。"""
        try:
            statuses = response["response"]["data"]["statuses"]
            first = statuses[0]
            if "resting" in first:
                return first["resting"]["oid"]
            if "filled" in first:
                return first["filled"]["oid"]
        except (KeyError, IndexError):
            pass
        return None


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def _safe_repr(obj: Any, max_len: int = 500) -> str:
    """截断的 repr，避免在日志中泄露完整私钥等敏感内容。"""
    s = repr(obj)
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s
