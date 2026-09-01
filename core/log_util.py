"""统一日志工具 — 所有 core/ 模块共享"""

import logging
import sys

_configured = set()


def get_logger(name: str = "QA-Tool") -> logging.Logger:
    logger = logging.getLogger(name)
    if name not in _configured:
        logger.setLevel(logging.WARNING)
        if not logger.handlers:
            h = logging.StreamHandler(sys.stderr)
            h.setFormatter(logging.Formatter(
                "[%(levelname)s] %(name)s.%(funcName)s: %(message)s"))
            logger.addHandler(h)
        _configured.add(name)
    return logger
