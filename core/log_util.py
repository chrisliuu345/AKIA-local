"""统一日志工具 — 所有 core/ 模块共享"""

import logging
import sys

_logger = None


def get_logger(name: str = "QA-Tool") -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.WARNING)
        if not _logger.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter(
                "[%(levelname)s] %(name)s.%(funcName)s: %(message)s"))
            _logger.addHandler(h)
    return _logger
