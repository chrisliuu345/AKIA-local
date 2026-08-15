"""
翻译引擎 — 固定中文界面

从 locales/zh.json 加载界面文案，tr(key) 获取中文显示文字。
软件仅提供中文界面，不提供语言切换。
"""

import json
import os
from pathlib import Path
from typing import Dict


LOCALE_DIR = Path(__file__).parent.parent / "locales"


class I18n:
    """单例翻译管理器 — 固定中文"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._translations: Dict[str, str] = {}
        self._load()
        self._initialized = True

    def tr(self, key: str, default: str = "") -> str:
        """获取中文界面文字"""
        return self._translations.get(key, default or key)

    def _load(self) -> None:
        path = LOCALE_DIR / "zh.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if loaded:
                        self._translations = loaded
            except Exception:
                import logging
                logging.getLogger("QA-Tool").warning(
                    f"加载语言文件失败: {path}")


i18n = I18n()
