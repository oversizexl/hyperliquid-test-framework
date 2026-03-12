"""Structured logging with automatic sensitive-data masking."""

from __future__ import annotations

import logging
import re
import sys

_SENSITIVE_PATTERNS = [
    (re.compile(r"(0x[0-9a-fA-F]{64})"), r"\1[:8]***"),
    (re.compile(r"(private[_-]?key[\"']?\s*[:=]\s*[\"']?)(0x)?[0-9a-fA-F]+", re.IGNORECASE), r"\1***REDACTED***"),
]


class MaskingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern, replacement in _SENSITIVE_PATTERNS:
            msg = pattern.sub(replacement, msg)
        return msg


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(f"hl.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = MaskingFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
