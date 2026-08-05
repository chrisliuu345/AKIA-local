"""
多语言翻译引擎 — 当前仅支持中文

注意：en.json (389 key) 已完整维护，语言切换功能预留。
如需启用英文模式，调用 i18n.set_language("en") 切换翻译源。
"""

import json
import os
from pathlib import Path
from typing import Dict


LOCALE_DIR = Path(__file__).parent.parent / "locales"


class I18n:
    """单例翻译管理器 — 当前仅支持中文"""

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
        self._current_lang = "zh"
        self._load("zh")
        self._initialized = True

    def tr(self, key: str, default: str = "") -> str:
        """获取翻译文字（当前仅返回中文）"""
        return self._translations.get(key, default or key)

    @property
    def current_language(self) -> str:
        """当前语言代码。'zh' = 中文，'en' = 英文（预留）。"""
        return self._current_lang

    def set_language(self, lang: str) -> bool:
        """切换语言（预留）。当前仅 'zh' 可用，切换 'en' 将保留中文回退。
        注意：切换后所有已显示的 UI 文字不会自动刷新，需重启应用生效。"""
        if lang == self._current_lang:
            return True
        self._load(lang)
        if self._translations:
            self._current_lang = lang
            return True
        # 英文加载失败时回退中文
        if lang != "zh":
            self._load("zh")
        return False

    def _load(self, lang: str) -> None:
        path = LOCALE_DIR / f"{lang}.json"
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
                if lang != "zh":
                    self._translations = {}


i18n = I18n()
