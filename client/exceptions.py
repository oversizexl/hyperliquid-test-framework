"""Unified exception hierarchy for Hyperliquid API client."""


class HyperliquidError(Exception):
    """Base exception for all Hyperliquid-related errors."""


class HyperliquidApiError(HyperliquidError):
    """Raised when the API returns a business-level error (HTTP 200 but status contains error)."""

    def __init__(self, message: str, status_code: int = 200, raw_response: dict | None = None):
        self.status_code = status_code
        self.raw_response = raw_response or {}
        super().__init__(message)


class HyperliquidValidationError(HyperliquidError):
    """Raised for client-side validation failures before sending request."""


class HyperliquidTimeoutError(HyperliquidError):
    """Raised when an API request or polling operation times out."""


class HyperliquidSigningError(HyperliquidError):
    """Raised when EIP-712 signing fails."""
