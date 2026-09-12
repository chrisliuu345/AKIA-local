"""PluginHost — 插件可访问的主应用门面（v3.8.1）。

只暴露稳定、只读的能力：数据表 / 分析结果 / 项目上下文 / 主题字体 / 通知 / 跳转，
插件不应直接操作主窗口内部状态。放在 ui/ 层避免 core 反向依赖 ui。
"""
from __future__ import annotations

import logging

logger = logging.getLogger("QA-Tool.Plugin")


class PluginHost:
    def __init__(self, main_window=None):
        self._main_window = main_window

    @property
    def main_window(self):
        """受信任插件的逃生舱（仅高级用途；常规场景请用下面的只读方法）。"""
        return self._main_window

    def data_frames(self) -> dict:
        """当前导入的数据表 {表名: DataFrame}。"""
        try:
            current = getattr(self._main_window, "current_data", None) or {}
            raw = current.get("raw_data") or {}
            if not raw:
                loader = getattr(self._main_window, "data_loader", None)
                raw = getattr(loader, "raw_data", {}) or {}
            return dict(raw)
        except Exception:
            logger.debug("PluginHost 数据表读取失败", exc_info=True)
            return {}

    def analyses(self) -> dict:
        return dict(getattr(self._main_window, "analyses", {}) or {})

    def project_context(self):
        return getattr(self._main_window, "project_context", None)

    def theme(self, widget=None) -> dict:
        from ui.theme import colors
        return colors(widget)

    def ui_font(self, size: int = 10, weight: int | None = None):
        from PySide6.QtGui import QFont
        from ui.font_config import get_ui_font
        return QFont(get_ui_font(), size, weight) if weight is not None \
            else QFont(get_ui_font(), size)

    def notify(self, message: str, timeout: int = 5000):
        window = self._main_window
        if window is None:
            return
        try:
            window.statusBar().showMessage(str(message), int(timeout))
        except Exception:
            logger.debug("PluginHost 通知失败", exc_info=True)

    def switch_tab(self, index: int):
        window = self._main_window
        if window is not None and hasattr(window, "_switch_tab"):
            window._switch_tab(int(index))
