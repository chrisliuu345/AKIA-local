"""实时SPC监控 Tab (33) — 文件变化自动重算控制图 (v2.4 E1)

- 选择待监控的 Excel 文件 → 启动后台 FileMonitor 守护线程轮询
- 文件内容变化 (mtime/大小) 且稳定确认后自动重新解析 + SPC 分析
- 工作线程通过 update_received 信号跨线程推送结果，UI 线程重绘
"""

import os

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QFileDialog, QGroupBox, QFormLayout,
    QApplication, QMessageBox, QPlainTextEdit,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib.pyplot as plt

from core.i18n import i18n
from core.file_watcher import FileMonitor
from core.alert_rules import AlertTracker, AlertLog, AlertRules, AlertState, format_alert_message
from output.chart_engine import create_control_chart
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH
from ui.tabs.base_tab import BaseAnalysisTab
from ui.font_config import get_ui_font

MONITOR_ANALYSIS_TYPE = "实时SPC监控"


class MonitorTab(BaseAnalysisTab):
    """文件监控 Tab — 外部 Excel 更新时实时刷新控制图"""

    update_received = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._monitor = None
        self._alert_tracker = AlertTracker()
        self._alert_log = AlertLog()
        self._setup_ui()
        self.update_received.connect(self._on_update)

    # ── UI ───────────────────────────────────────────────
    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel(i18n.tr("monitor.title"))
        title.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']}; background: transparent;")
        layout.addWidget(title)

        # 配置区
        cfg = QGroupBox(i18n.tr("monitor.config"))
        cfg.setStyleSheet(
            f"QGroupBox {{ color: {tc['text_secondary']}; border: 1px solid #3a3a3a;"
            f"border-radius: 8px; margin-top: 10px; padding-top: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; }}"
        )
        form = QFormLayout(cfg)
        form.setContentsMargins(12, 14, 12, 12)
        form.setSpacing(8)

        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText(i18n.tr("monitor.file_hint"))
        browse_btn = QPushButton(i18n.tr("monitor.browse"))
        browse_btn.setFixedHeight(32)
        browse_btn.clicked.connect(self._on_browse)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse_btn)
        form.addRow(i18n.tr("monitor.file"), file_row)

        self.subgroup_spin = QSpinBox()
        self.subgroup_spin.setRange(1, 25)
        self.subgroup_spin.setValue(1)
        self.subgroup_spin.setToolTip(i18n.tr("monitor.subgroup_hint"))
        form.addRow(i18n.tr("monitor.subgroup"), self.subgroup_spin)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(2)
        self.interval_spin.setSuffix(i18n.tr("monitor.seconds"))
        form.addRow(i18n.tr("monitor.interval"), self.interval_spin)

        layout.addWidget(cfg)

        # 控制行
        ctrl = QHBoxLayout()
        self.toggle_btn = QPushButton(i18n.tr("monitor.start"))
        self.toggle_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.toggle_btn.setFixedHeight(44)
        self.toggle_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._on_toggle)
        ctrl.addWidget(self.toggle_btn)
        self.status_label = QLabel(i18n.tr("monitor.status_idle"))
        self.status_label.setFont(QFont(get_ui_font(), 10))
        self.status_label.setStyleSheet(f"color: {tc['text_secondary']};")
        ctrl.addWidget(self.status_label)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # 告警横幅 (状态跳变时显示，红色=判异中 / 绿色=已解除)
        self.alert_banner = QLabel("")
        self.alert_banner.setAlignment(Qt.AlignCenter)
        self.alert_banner.setMinimumHeight(30)
        self.alert_banner.hide()
        layout.addWidget(self.alert_banner)

        # 告警日志面板
        log_group = QGroupBox(i18n.tr("alert.title"))
        log_group.setStyleSheet(
            f"QGroupBox {{ color: {tc['text_secondary']}; border: 1px solid #3a3a3a;"
            f"border-radius: 8px; margin-top: 10px; padding-top: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 12px; }}"
        )
        log_layout = QVBoxLayout(log_group)
        self.alert_log_view = QPlainTextEdit()
        self.alert_log_view.setReadOnly(True)
        self.alert_log_view.setFixedHeight(84)
        self.alert_log_view.setPlaceholderText(i18n.tr("alert.log_empty"))
        log_layout.addWidget(self.alert_log_view)
        layout.addWidget(log_group)

        # 图表区
        self.chart_layout = QVBoxLayout()
        self.chart_layout.setSpacing(0)
        layout.addLayout(self.chart_layout, 1)
        self._show_empty_hint()

    def _show_empty_hint(self):
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        hint = QLabel(i18n.tr("monitor.empty"))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #6e7080; font-size: 14px;")
        self.chart_layout.addWidget(hint)
        self.canvas = None
        self.current_figure = None

    # ── 交互 ─────────────────────────────────────────────
    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("monitor.choose_file"), "",
            "Excel (*.xlsx *.xls *.xlsm)"
        )
        if path:
            self.file_edit.setText(path)

    def _file_path(self):
        return self.file_edit.text().strip()

    def _on_toggle(self):
        if self._monitor is None:
            path = self._file_path()
            if not path:
                self.status_label.setText(i18n.tr("monitor.error_nofile"))
                self.status_label.setStyleSheet("color: #e74c3c;")
                return
            self._start_monitor(path)
        else:
            self._stop_monitor()

    def _start_monitor(self, path):
        self._alert_tracker.reset()
        monitor = FileMonitor(
            file_path=path,
            on_change=self.update_received.emit,
            interval=self.interval_spin.value(),
            subgroup_size=self.subgroup_spin.value(),
        )
        initial = monitor.check_once()
        self._monitor = monitor
        self._on_update(initial)
        monitor.start()
        self.toggle_btn.setText(i18n.tr("monitor.stop"))
        self.status_label.setStyleSheet("color: #27ae60;")

    def _stop_monitor(self):
        if self._monitor is not None:
            self._monitor.stop(timeout=5.0)
            self._monitor = None
        self.toggle_btn.setText(i18n.tr("monitor.start"))
        self.status_label.setText(i18n.tr("monitor.status_stopped"))
        self.status_label.setStyleSheet("color: #6e7080;")

    # ── 结果推送 (工作线程 → UI 线程) ─────────────────────
    def _on_update(self, payload: dict):
        tc = theme_colors()
        error = payload.get("error")
        if error:
            self.status_label.setText(i18n.tr("monitor.status_error") + " " + error)
            self.status_label.setStyleSheet("color: #e74c3c;")
            return

        spc = payload.get("spc")
        if not spc:
            self.status_label.setText(i18n.tr("monitor.error_empty"))
            self.status_label.setStyleSheet("color: #e74c3c;")
            return

        chart_type = spc.get("chart_type", "SPC")
        title = f"{os.path.basename(payload['file_path'])} — {payload['column']} ({chart_type})"
        fig = create_control_chart(spc, title=title)
        self._render_figure(fig)

        self.current_result = {
            "analysis_type": MONITOR_ANALYSIS_TYPE,
            "params": {
                "file_path": payload["file_path"],
                "sheet": payload["sheet"],
                "column": payload["column"],
                "subgroup_size": self.subgroup_spin.value(),
            },
            "result": spc,
        }
        self.analysis_completed.emit()

        viol = payload.get("violations", 0)
        self.status_label.setText(
            i18n.tr("monitor.last_update").format(time=payload["updated_at"])
            + "  " + i18n.tr("monitor.violations").format(n=viol)
        )
        self.status_label.setStyleSheet(f"color: {tc['text_secondary']};")

        self._check_alerts(viol, os.path.basename(payload["file_path"]))

    # ── 告警 (E3) ────────────────────────────────────────
    def _check_alerts(self, violations: int, file_name: str):
        min_v = AlertRules.min_violations()
        effective = violations if violations >= min_v else 0
        state = self._alert_tracker.update(effective)

        if state not in (AlertState.NEW, AlertState.CLEARED):
            return

        message = format_alert_message(state, violations, file_name)
        if state == AlertState.NEW:
            self.alert_banner.setText("⚠ " + message)
            self.alert_banner.setStyleSheet(
                "color: #fff; background: #e74c3c; border-radius: 6px;"
                "font-weight: bold; padding: 4px;")
            self.alert_banner.show()
            if AlertRules.sound_enabled():
                QApplication.beep()
            if AlertRules.popup_enabled():
                QMessageBox.warning(self, i18n.tr("alert.popup_title"), message)
        else:
            self.alert_banner.setText("✔ " + message)
            self.alert_banner.setStyleSheet(
                "color: #fff; background: #27ae60; border-radius: 6px;"
                "font-weight: bold; padding: 4px;")

        if AlertRules.log_enabled():
            self._alert_log.add(message)
            self._refresh_alert_log()

    def _refresh_alert_log(self):
        lines = [
            f"[{ts.strftime('%H:%M:%S')}] {msg}"
            for ts, msg in self._alert_log.entries()
        ]
        self.alert_log_view.setPlainText("\n".join(lines))

    def _render_figure(self, fig):
        if self.current_figure is not None:
            plt.close(self.current_figure)
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        canvas = FigureCanvasQTAgg(fig)
        canvas.setStyleSheet("background: transparent;")
        self.chart_layout.addWidget(canvas)
        self.canvas = canvas
        self.current_figure = fig

    def closeEvent(self, event):
        self._stop_monitor()
        super().closeEvent(event)
