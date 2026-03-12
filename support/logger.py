"""结构化日志，并对私钥、长 hex 等敏感内容自动脱敏。"""

from __future__ import annotations

import logging
import re
import sys

# 日志输出前替换：64 位 hex 只保留前 8 位；private_key 等整段替换为 ***REDACTED***
_SENSITIVE_PATTERNS = [
    (re.compile(r"(0x[0-9a-fA-F]{64})"), r"\1[:8]***"),
    (re.compile(r"(private[_-]?key[\"']?\s*[:=]\s*[\"']?)(0x)?[0-9a-fA-F]+", re.IGNORECASE), r"\1***REDACTED***"),
]


class MaskingFormatter(logging.Formatter):
    """在 format 时对消息内容做敏感信息替换，避免泄露到日志。"""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern, replacement in _SENSITIVE_PATTERNS:
            msg = pattern.sub(replacement, msg)
        return msg


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取名为 hl.<name> 的 logger，使用 MaskingFormatter 输出到 stdout。"""
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
