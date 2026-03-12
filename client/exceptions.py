"""Hyperliquid API 客户端统一异常体系。"""


class HyperliquidError(Exception):
    """所有与 Hyperliquid 相关错误的基类。"""


class HyperliquidApiError(HyperliquidError):
    """API 返回业务层错误时抛出（如 HTTP 200 但响应中 status 含 error）。"""

    def __init__(self, message: str, status_code: int = 200, raw_response: dict | None = None):
        self.status_code = status_code
        self.raw_response = raw_response or {}
        super().__init__(message)


class HyperliquidValidationError(HyperliquidError):
    """请求发出前的客户端校验失败（如非法 coin、价格/数量不合规）。"""


class HyperliquidTimeoutError(HyperliquidError):
    """API 请求或轮询等待超时时抛出。"""


class HyperliquidSigningError(HyperliquidError):
    """EIP-712 签名失败时抛出。"""
