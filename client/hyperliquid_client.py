"""Self-built Hyperliquid API client — no official/community SDK dependency.

Covers: account query, place order, cancel order, order query, position query.
All exchange (write) actions use EIP-712 phantom-agent signing.
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
    """Thin, reusable wrapper around the Hyperliquid REST API."""

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._wallet = Account.from_key(config.private_key)
        # trust_env=False 避免使用环境变量中的 HTTP_PROXY/HTTPS_PROXY，直连 API（否则易出现代理 403）
        self._http = httpx.Client(
            timeout=config.request_timeout,
            headers={"Content-Type": "application/json"},
            trust_env=False,
        )
        self._asset_map: dict[str, int] | None = None

    def close(self) -> None:
        self._http.close()

    # ── Info helpers (read-only, safe to retry) ────────────────────────

    @retry(max_attempts=3, delay=1.0, exceptions=(httpx.HTTPError, HyperliquidTimeoutError))
    def _post_info(self, payload: dict) -> Any:
        logger.debug("POST %s  body=%s", self._cfg.info_url, _safe_repr(payload))
        with allure.step(f"API Info: {payload.get('type', 'unknown')}"):
            allure.attach(json.dumps(payload, indent=2), name="Request Payload", attachment_type=allure.attachment_type.JSON)
            resp = self._http.post(self._cfg.info_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("Response: %s", _safe_repr(data))
            allure.attach(json.dumps(data, indent=2), name="Response Data", attachment_type=allure.attachment_type.JSON)
            return data

    # ── Exchange helpers (write, NO auto-retry) ────────────────────────

    def _post_exchange(self, action: dict, nonce: int | None = None) -> dict:
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

    # ── Asset index resolution ─────────────────────────────────────────

    def get_meta(self) -> dict:
        return self._post_info({"type": "meta"})

    def resolve_asset(self, coin: str) -> int:
        """Return the numeric asset index for a perpetual coin name."""
        if self._asset_map is None:
            meta = self.get_meta()
            self._asset_map = {
                item["name"]: idx for idx, item in enumerate(meta["universe"])
            }
        if coin not in self._asset_map:
            raise HyperliquidValidationError(f"Unknown coin '{coin}'. Available: {list(self._asset_map.keys())[:20]}")
        return self._asset_map[coin]

    def get_sz_decimals(self, coin: str) -> int:
        meta = self.get_meta()
        for item in meta["universe"]:
            if item["name"] == coin:
                return item["szDecimals"]
        raise HyperliquidValidationError(f"Cannot find szDecimals for '{coin}'")

    # ── Account ────────────────────────────────────────────────────────

    def get_clearinghouse_state(self, user: str | None = None) -> dict:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "clearinghouseState", "user": user})

    def get_account_value(self, user: str | None = None) -> float:
        state = self.get_clearinghouse_state(user)
        return float(state["marginSummary"]["accountValue"])

    # ── Orders ─────────────────────────────────────────────────────────

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
        """Place a single order. Returns the raw exchange response."""
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

    # ── Positions ──────────────────────────────────────────────────────

    def get_positions(self, user: str | None = None) -> list[dict]:
        state = self.get_clearinghouse_state(user)
        return state.get("assetPositions", [])

    def get_position_for_coin(self, coin: str, user: str | None = None) -> dict | None:
        for pos in self.get_positions(user):
            if pos.get("position", {}).get("coin") == coin:
                return pos
        return None

    # ── Market data ────────────────────────────────────────────────────

    def get_all_mids(self) -> dict[str, str]:
        return self._post_info({"type": "allMids"})

    def get_mid_price(self, coin: str) -> float:
        mids = self.get_all_mids()
        if coin not in mids:
            raise HyperliquidValidationError(f"No mid price for '{coin}'")
        return float(mids[coin])

    def get_l2_book(self, coin: str) -> dict:
        return self._post_info({"type": "l2Book", "coin": coin})

    # ── Leverage ───────────────────────────────────────────────────────

    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> dict:
        asset = self.resolve_asset(coin)
        action = {
            "type": "updateLeverage",
            "asset": asset,
            "isCross": is_cross,
            "leverage": leverage,
        }
        return self._post_exchange(action)

    # ── User fills / history ───────────────────────────────────────────

    def get_user_fills(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "userFills", "user": user})

    def get_historical_orders(self, user: str | None = None) -> list[dict]:
        user = user or self._cfg.wallet_address
        return self._post_info({"type": "historicalOrders", "user": user})

    # ── Cleanup utilities ──────────────────────────────────────────────

    def cancel_all_open_orders(self) -> list[dict]:
        """Best-effort cancel of every open order. Returns cancel results."""
        open_orders = self.get_open_orders()
        results = []
        for order in open_orders:
            try:
                result = self.cancel_order(order["coin"], order["oid"])
                results.append(result)
            except Exception as exc:
                logger.warning("Failed to cancel order %s: %s", order["oid"], exc)
        return results

    # ── Internal ───────────────────────────────────────────────────────

    @staticmethod
    def _exchange_error_message(resp: httpx.Response, data: dict | Any) -> str:
        """Build error message from 4xx exchange response."""
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
        """Raise HyperliquidApiError if the exchange response contains an error."""
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
        """Extract the order ID from a place-order response."""
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
    """Truncated repr that avoids leaking full private keys in logs."""
    s = repr(obj)
    if len(s) > max_len:
        return s[:max_len] + "…"
    return s
