"""Unique identifier generators for test isolation."""

import uuid


def generate_cloid() -> str:
    """Generate a unique 128-bit hex client order ID.

    Format: 0x + 32 hex chars (128 bits), as required by Hyperliquid.
    """
    return "0x" + uuid.uuid4().hex
