"""告警中心（v3.8.0-③）— 等级筛选 / 确认 / 导出，对标 Enact 应用内告警。

数据源为 AlertJournal（data/alerts.jsonl）；确认动作写回日志文件并记审计。
"""
import csv
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from core.i18n import i18n
from core.streaming.alert_journal import (
    SEVERITY_COLORS, SEVERITY_CRITICAL, SEVERITY_INFO, SEVERITY_WARNING,
    severity_label,
)
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY

_COLUMNS = ("时间", "等级", "设备", "通道", "类型", "描述", "值", "状态", "确认人")
_SEVERITY_ITEMS = (
    ("全部等级", None),
    ("严重", SEVERITY_CRITICAL),
    ("警告", SEVERITY_WARNING),
    ("预告", SEVERITY_INFO),
)


class AlertCenterDialog(QDialog):
    """告警中心 — 只读展示 + 确认 + 导出。"""

    def __init__(self, journal, parent=None, auto_refresh_ms: int = 5000,
                 case_resolver=None, open_case=None):
        super().__init__(parent)
        self.journal = journal
        self.case_resolver = case_resolver     # alert_id -> case_id | None
        self.open_case = open_case             # case_id -> None（打开案例工作台）
        self.setWindowTitle(i18n.tr("alert_center.title"))
        self.resize(980, 520)
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

        bar = QHBoxLayout()
        bar.addWidget(QLabel(i18n.tr("alert_center.severity")))
        self.severity_combo = QComboBox()
        for label, value in _SEVERITY_ITEMS:
            self.severity_combo.addItem(label, value)
        self.severity_combo.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.severity_combo)

        self.unacked_only = QCheckBox(i18n.tr("alert_center.unacked_only"))
        self.unacked_only.setChecked(True)
        self.unacked_only.toggled.connect(self.refresh)
        bar.addWidget(self.unacked_only)
        bar.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        bar.addWidget(self.count_label)
        layout.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(list(_COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        btn_bar = QHBoxLayout()
        for key, slot in (("alert_center.refresh", self.refresh),
                          ("alert_center.ack", self._on_ack),
                          ("alert_center.ack_all", self._on_ack_all),
                          ("alert_center.export", self._on_export)):
            btn = QPushButton(i18n.tr(key))
            btn.setStyleSheet(BUTTON_SECONDARY)
            btn.clicked.connect(slot)
            btn_bar.addWidget(btn)
        self.case_btn = QPushButton("打开改善案例")
        self.case_btn.setStyleSheet(BUTTON_SECONDARY)
        self.case_btn.setToolTip("打开该告警自动立案的改善案例（v4.4.0 B1）")
        self.case_btn.clicked.connect(self._on_open_case)
        btn_bar.addWidget(self.case_btn)
        btn_bar.addStretch()
        close_btn = QPushButton(i18n.tr("alert_center.close"))
        close_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        close_btn.clicked.connect(self.accept)
        btn_bar.addWidget(close_btn)
        layout.addLayout(btn_bar)

    # ---------- 数据 ----------
    def _filter(self):
        return {
            "severity": self.severity_combo.currentData(),
            "unacked_only": self.unacked_only.isChecked(),
        }

    def refresh(self):
        entries = self.journal.entries(limit=500, **self._filter())
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = (
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.ts)),
                severity_label(entry.severity),
                entry.device,
                entry.channel,
                entry.kind,
                entry.desc,
                f"{entry.value:.3f}",
                "已确认" if entry.ack else "未确认",
                entry.ack_by,
            )
            color = QColor(SEVERITY_COLORS.get(entry.severity, "#d8dce2"))
            for col, text in enumerate(values):
                item = QTableWidgetItem(str(text))
                item.setData(Qt.UserRole, entry.id)
                if col == 1 or (col == 7 and not entry.ack):
                    item.setForeground(color)
                self.table.setItem(row, col, item)
            if entry.note:
                self.table.item(row, 5).setToolTip(entry.note)
        self.count_label.setText(
            i18n.tr("alert_center.count").format(
                n=len(entries),
                unacked=self.journal.unacked_count()))

    def _selected_ids(self) -> list[str]:
        ids = []
        for idx in self.table.selectionModel().selectedRows():
            item = self.table.item(idx.row(), 0)
            if item is not None:
                entry_id = item.data(Qt.UserRole)
                if entry_id:
                    ids.append(str(entry_id))
        return ids

    # ---------- 槽 ----------
    def _on_ack(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, self.windowTitle(),
                                    i18n.tr("alert_center.select_hint"))
            return
        done = sum(1 for eid in ids if self.journal.ack(eid, "user"))
        self.refresh()
        self.count_label.setText(
            i18n.tr("alert_center.acked").format(n=done))

    def _on_ack_all(self):
        severity = self.severity_combo.currentData()
        done = self.journal.ack_all("user", severity=severity)
        self.refresh()
        self.count_label.setText(i18n.tr("alert_center.acked").format(n=done))

    def _on_open_case(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, self.windowTitle(),
                                    i18n.tr("alert_center.select_hint"))
            return
        if not callable(self.case_resolver) or not callable(self.open_case):
            QMessageBox.information(self, "改善案例", "当前入口未接入案例定位")
            return
        case_id = self.case_resolver(ids[0])
        if not case_id:
            QMessageBox.information(self, "改善案例", "该告警未关联自动立案案例")
            return
        self.open_case(case_id)

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("alert_center.export"), "alerts.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_COLUMNS)
                for entry in self.journal.entries(limit=10000):
                    writer.writerow([
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.ts)),
                        severity_label(entry.severity), entry.device, entry.channel,
                        entry.kind, entry.desc, f"{entry.value:.6g}",
                        "已确认" if entry.ack else "未确认", entry.ack_by,
                    ])
        except OSError as e:
            QMessageBox.warning(self, self.windowTitle(), str(e))
            return
        self.count_label.setText(i18n.tr("alert_center.exported").format(path=path))
