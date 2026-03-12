"""EIP-712 signing utilities for Hyperliquid exchange endpoint.

Implements the phantom-agent signing flow required by L1 actions
(order, cancel, updateLeverage, etc.) without using the official SDK.
"""

from decimal import Decimal

import msgpack
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_hex


PHANTOM_DOMAIN = {
    "chainId": 1337,
    "name": "Exchange",
    "verifyingContract": "0x0000000000000000000000000000000000000000",
    "version": "1",
}

AGENT_TYPES = {
    "Agent": [
        {"name": "source", "type": "string"},
        {"name": "connectionId", "type": "bytes32"},
    ],
    "EIP712Domain": [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
        {"name": "verifyingContract", "type": "address"},
    ],
}


def float_to_wire(x: float) -> str:
    rounded = f"{x:.8f}"
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError(f"float_to_wire causes rounding: {x}")
    normalized = Decimal(rounded).normalize()
    return f"{normalized:f}"


def _address_to_bytes(address: str) -> bytes:
    return bytes.fromhex(address[2:] if address.startswith("0x") else address)


def _action_hash(
    action: dict | list,
    vault_address: str | None,
    nonce: int,
    expires_after: int | None = None,
) -> bytes:
    data = msgpack.packb(action)
    data += nonce.to_bytes(8, "big")
    if vault_address is None:
        data += b"\x00"
    else:
        data += b"\x01"
        data += _address_to_bytes(vault_address)
    if expires_after is not None:
        data += b"\x00"
        data += expires_after.to_bytes(8, "big")
    return keccak(data)


def sign_l1_action(
    wallet: Account,
    action: dict | list,
    vault_address: str | None,
    nonce: int,
    is_mainnet: bool,
    expires_after: int | None = None,
) -> dict:
    """Sign an L1 action (order, cancel, updateLeverage, etc.)."""
    hash_val = _action_hash(action, vault_address, nonce, expires_after)
    phantom_agent = {
        "source": "a" if is_mainnet else "b",
        "connectionId": hash_val,
    }
    payload = {
        "domain": PHANTOM_DOMAIN,
        "types": AGENT_TYPES,
        "primaryType": "Agent",
        "message": phantom_agent,
    }
    structured = encode_typed_data(full_message=payload)
    signed = wallet.sign_message(structured)
    return {"r": to_hex(signed["r"]), "s": to_hex(signed["s"]), "v": signed["v"]}
