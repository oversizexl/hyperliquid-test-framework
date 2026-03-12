"""集中配置管理。

优先从环境变量读取，未设置时回退到 config/config.yaml 的默认值。
本地开发可用 .env，CI 使用 GitHub Secrets 注入。
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

# 项目根目录，用于加载 .env 和 config.yaml
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _load_yaml() -> dict:
    """加载 config/config.yaml，不存在或为空则返回空字典。"""
    cfg_path = _PROJECT_ROOT / "config" / "config.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_YAML = _load_yaml()
_TEST_YAML = _YAML.get("test", {})


class Config:
    """不可变的测试配置：API 地址、钱包、超时、默认合约等。"""

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
        """只读接口 /info 的完整 URL。"""
        return f"{self.base_url}/info"

    @property
    def exchange_url(self) -> str:
        """写操作接口 /exchange 的完整 URL。"""
        return f"{self.base_url}/exchange"

    def validate(self) -> None:
        """校验必填项（钱包地址与私钥），未配置时抛出 ValueError。"""
        if not self.wallet_address:
            raise ValueError("HL_WALLET_ADDRESS is not configured")
        if not self.private_key:
            raise ValueError("HL_PRIVATE_KEY is not configured")


@lru_cache(maxsize=1)
def get_config() -> Config:
    """获取单例 Config 并校验，供 fixture 等使用。"""
    cfg = Config()
    cfg.validate()
    return cfg
