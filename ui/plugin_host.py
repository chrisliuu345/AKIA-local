"""PluginHost — 插件可访问的主应用门面（v3.8.1）。

只暴露稳定、只读的能力：数据表 / 分析结果 / 项目上下文 / 主题字体 / 通知 / 跳转，
插件不应直接操作主窗口内部状态。放在 ui/ 层避免 core 反向依赖 ui。
"""
from __future__ import annotations

import logging

logger = logging.getLogger("AKIA.Plugin")


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

    # ------------------------------------------------------------ 数据源（v2.1）
    def measurement_events(self) -> list[dict]:
        """当前项目的测量事件（只读快照）。"""
        store = getattr(self._main_window, "measurement_store", None)
        return store.to_dicts() if store is not None else []

    def submit_measurements(self, events, plugin_id: str = "") -> list[str]:
        """受控注入测量事件：先整体校验，再幂等写入项目集合。

        插件异步推送（如视觉流）应使用本方法；返回值新增/更新的事件 ID。
        """
        from core.measurement_event import MeasurementEvent

        store = getattr(self._main_window, "measurement_store", None)
        if store is None:
            raise RuntimeError("主窗口未启用测量事件集合")
        items = list(events) if isinstance(events, (list, tuple)) else [events]
        normalized = []
        for index, item in enumerate(items):
            try:
                event = (item if isinstance(item, MeasurementEvent)
                         else MeasurementEvent.from_dict(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"第 {index + 1} 条测量事件无效: {exc}") from exc
            if plugin_id:
                event.source_kind = "plugin"
                event.source_id = str(plugin_id)
                if event.raw_ref.startswith(("inline://", "manual://")):
                    event.raw_ref = f"plugin://{plugin_id}/{event.event_id}"
            normalized.append(event)
        return [store.add(event).event_id for event in normalized]

    def connector_topics(self) -> list[str]:
        bus = getattr(self._main_window, "stream_bus", None)
        return bus.topics() if bus is not None else []

    def recent_measurements(self, topic: str, n: int = 1000) -> list:
        """把连接器总线最近样本转为 MeasurementEvent（不写库）。"""
        from core.measurement_event import MeasurementEvent

        bus = getattr(self._main_window, "stream_bus", None)
        if bus is None:
            return []
        samples = bus.recent(str(topic), int(n))
        if not samples:
            return []
        return MeasurementEvent.events_from_samples(
            samples, source_kind="connector",
            source_id=str(topic), source_name=str(topic))
