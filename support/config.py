"""Centralized configuration management.

Loads settings from environment variables (highest priority),
falling back to config/config.yaml defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _load_yaml() -> dict:
    cfg_path = _PROJECT_ROOT / "config" / "config.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML = _load_yaml()
_TEST_YAML = _YAML.get("test", {})


class Config:
    """Immutable test configuration."""

    base_url: str = os.getenv("HL_BASE_URL", _YAML.get("base_url", "https://api.hyperliquid-testnet.xyz"))
    wallet_address: str = os.getenv("HL_WALLET_ADDRESS", "")
    private_key: str = os.getenv("HL_PRIVATE_KEY", "")
    is_mainnet: bool = os.getenv("HL_IS_MAINNET", str(_YAML.get("is_mainnet", False))).lower() in ("true", "1")

    default_coin: str = os.getenv("HL_DEFAULT_COIN", _TEST_YAML.get("default_coin", "ETH"))
    poll_interval: float = float(os.getenv("HL_POLL_INTERVAL", _TEST_YAML.get("poll_interval", 1.0)))
    max_wait_seconds: float = float(os.getenv("HL_MAX_WAIT_SECONDS", _TEST_YAML.get("max_wait_seconds", 30)))
    request_timeout: float = float(os.getenv("HL_REQUEST_TIMEOUT", _TEST_YAML.get("request_timeout", 15)))
    order_min_value_usd: float = float(_TEST_YAML.get("order_min_value_usd", 10))

    @property
    def info_url(self) -> str:
        return f"{self.base_url}/info"

    @property
    def exchange_url(self) -> str:
        return f"{self.base_url}/exchange"

    def validate(self) -> None:
        if not self.wallet_address:
            raise ValueError("HL_WALLET_ADDRESS is not configured")
        if not self.private_key:
            raise ValueError("HL_PRIVATE_KEY is not configured")


@lru_cache(maxsize=1)
def get_config() -> Config:
    cfg = Config()
    cfg.validate()
    return cfg
