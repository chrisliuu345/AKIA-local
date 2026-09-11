"""连接器健康页（v3.8.0-⑦）— 数据源状态 / 自动重连 / 插件可用性。

数据来源: connectors.health.HealthRegistry 快照（采集线程实时写入）+
connectors.registry 插件清单（协议库是否安装）。重连按钮直接调用
IngestRunner.reconnect()，无需重启采集。
"""
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout,
)

from connectors.health import STATUS_COLORS, STATUS_LABELS
from core.i18n import i18n
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY

_HEALTH_COLUMNS = ("数据源", "类型", "状态", "连续失败", "累计样本",
                   "最近成功", "最近错误", "下次重试")
_PLUGIN_COLUMNS = ("插件", "类别", "可用", "说明")


def _fmt_ts(ts: float) -> str:
    if not ts:
        return "—"
    return time.strftime("%H:%M:%S", time.localtime(ts))


class ConnectorHealthDialog(QDialog):
    """连接健康度 — 运行时状态 + 插件清单 + 手动重连。"""

    def __init__(self, registry=None, runner=None, parent=None,
                 auto_refresh_ms: int = 3000):
        super().__init__(parent)
        self.registry = registry
        self.runner = runner
        self.setWindowTitle(i18n.tr("connector_health.title"))
        self.resize(880, 480)
        self._setup_ui()
        self.refresh()
        if auto_refresh_ms:
            self._timer = QTimer(self)
            self._timer.setInterval(auto_refresh_ms)
            self._timer.timeout.connect(self.refresh)
            self._timer.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.health_table = self._make_table(list(_HEALTH_COLUMNS))
        self.plugin_table = self._make_table(list(_PLUGIN_COLUMNS))
        self.tabs.addTab(self.health_table, i18n.tr("connector_health.tab_runtime"))
        self.tabs.addTab(self.plugin_table, i18n.tr("connector_health.tab_plugins"))
        layout.addWidget(self.tabs, 1)

        bar = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        bar.addWidget(self.status_label)
        bar.addStretch()
        for key, slot in (("connector_health.refresh", self.refresh),
                          ("connector_health.reconnect", self._on_reconnect)):
            btn = QPushButton(i18n.tr(key))
            btn.setStyleSheet(BUTTON_SECONDARY)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        close_btn = QPushButton(i18n.tr("connector_health.close"))
        close_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        close_btn.clicked.connect(self.accept)
        bar.addWidget(close_btn)
        layout.addLayout(bar)

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    # ---------- 刷新 ----------
    def refresh(self):
        self._refresh_health()
        self._refresh_plugins()

    def _refresh_health(self):
        snapshot = self.registry.snapshot() if self.registry is not None else {}
        self.health_table.setRowCount(0)
        now = time.time()
        for name, state in sorted(snapshot.items()):
            row = self.health_table.rowCount()
            self.health_table.insertRow(row)
            retry_in = max(0.0, float(state.get("next_retry_ts", 0.0)) - now)
            values = (
                name,
                state.get("kind", "connector"),
                STATUS_LABELS.get(state.get("status", ""), state.get("status", "")),
                str(state.get("consecutive_errors", 0)),
                str(state.get("samples", 0)),
                _fmt_ts(state.get("last_ok_ts", 0.0)),
                state.get("last_error", "") or "—",
                f"{retry_in:.1f}s" if retry_in > 0 else "—",
            )
            color = QColor(STATUS_COLORS.get(state.get("status", ""), "#d8dce2"))
            for col, text in enumerate(values):
                item = QTableWidgetItem(str(text))
                item.setData(Qt.UserRole, name)
                if col in (0, 2):
                    item.setForeground(color)
                self.health_table.setItem(row, col, item)
        if not snapshot:
            self.status_label.setText(i18n.tr("connector_health.empty"))
        else:
            bad = sum(1 for s in snapshot.values()
                      if s.get("status") in ("error", "degraded"))
            self.status_label.setText(
                i18n.tr("connector_health.summary").format(n=len(snapshot), bad=bad))

    def _refresh_plugins(self):
        try:
            from connectors.registry import discover
            infos = discover()
        except Exception:
            infos = {}
        self.plugin_table.setRowCount(0)
        for name, info in sorted(infos.items()):
            row = self.plugin_table.rowCount()
            self.plugin_table.insertRow(row)
            values = (name, info.category,
                      "✓" if info.available else "✗", info.description)
            for col, text in enumerate(values):
                item = QTableWidgetItem(str(text))
                if col == 2:
                    item.setForeground(QColor("#27ae60" if info.available
                                              else "#e74c3c"))
                self.plugin_table.setItem(row, col, item)

    # ---------- 槽 ----------
    def _selected_names(self) -> list[str]:
        rows = self.health_table.selectionModel().selectedRows()
        names = []
        for idx in rows:
            item = self.health_table.item(idx.row(), 0)
            if item is not None:
                names.append(item.data(Qt.UserRole) or item.text())
        return names

    def _on_reconnect(self):
        names = self._selected_names()
        if not names:
            self.status_label.setText(i18n.tr("connector_health.select_hint"))
            return
        if self.runner is None:
            self.status_label.setText(i18n.tr("connector_health.no_runner"))
            return
        done = sum(1 for name in names if self.runner.reconnect(str(name)))
        self.refresh()
        self.status_label.setText(i18n.tr("connector_health.reconnected").format(n=done))
