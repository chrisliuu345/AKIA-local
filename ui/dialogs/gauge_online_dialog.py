"""量具在线监控对话框（v4.4.0 B2）— 标准件重复性/偏倚滚动监控与 MPC 图。

数据入口：默认经主窗口测量管线（MeasurementEvent → MeasurementStore →
GaugeMonitor），保证与四通道测量事件同源；未接入时回退为直接喂入监控器
（测试/独立使用）。
"""

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QInputDialog, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from core.gauge_study import GaugeMonitor, GaugeStudyPolicy
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY

_STATE_LABELS = {"ok": "正常", "watch": "关注", "drift": "漂移"}
_STATE_COLORS = {"ok": "#2ecc71", "watch": "#f39c12", "drift": "#e74c3c"}


def _parse_optional_float(text: str, name: str) -> float | None:
    value = str(text or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} 必须为数值或留空: {value!r}") from exc


class GaugeOnlineDialog(QDialog):
    """量具在线监控：策略配置 + 状态/健康分 + 偏倚历史 + MPC 控制图。"""

    def __init__(self, monitor: GaugeMonitor, parent=None,
                 submit_measurement=None):
        super().__init__(parent)
        self.monitor = monitor
        self.submit_measurement = submit_measurement
        self.setWindowTitle("量具在线监控")
        self.resize(1040, 640)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal, self)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("量具列表"))
        self.gauge_list = QListWidget()
        self.gauge_list.currentRowChanged.connect(lambda *_: self._load_selected())
        left_layout.addWidget(self.gauge_list, 1)
        left_row = QHBoxLayout()
        self.new_button = QPushButton("新建")
        self.new_button.setStyleSheet(BUTTON_SECONDARY)
        self.new_button.clicked.connect(self._on_new)
        self.delete_button = QPushButton("删除")
        self.delete_button.setStyleSheet(BUTTON_SECONDARY)
        self.delete_button.clicked.connect(self._on_delete)
        left_row.addWidget(self.new_button)
        left_row.addWidget(self.delete_button)
        left_layout.addLayout(left_row)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(QLabel("策略配置"))
        form = QFormLayout()
        self.gauge_id_edit = QLineEdit()
        self.gauge_id_edit.setPlaceholderText("设备:通道，例如 caliper-1:value")
        form.addRow("量具 ID:", self.gauge_id_edit)
        self.expected_spin = QDoubleSpinBox()
        self.expected_spin.setRange(-1e12, 1e12)
        self.expected_spin.setDecimals(6)
        form.addRow("标准件参考值:", self.expected_spin)
        self.window_spin = QSpinBox()
        self.window_spin.setRange(2, 1000)
        self.window_spin.setValue(10)
        form.addRow("滚动窗口 N:", self.window_spin)
        self.bias_limit_edit = QLineEdit()
        self.bias_limit_edit.setPlaceholderText("留空 = 不判定偏倚限")
        form.addRow("偏倚容忍限:", self.bias_limit_edit)
        self.ucl_edit = QLineEdit()
        self.ucl_edit.setPlaceholderText("留空 = 不配置")
        form.addRow("MPC 上参考限:", self.ucl_edit)
        self.lcl_edit = QLineEdit()
        self.lcl_edit.setPlaceholderText("留空 = 不配置")
        form.addRow("MPC 下参考限:", self.lcl_edit)
        self.standard_ref_edit = QLineEdit()
        self.standard_ref_edit.setPlaceholderText("标准件标准记录 ID（可选）")
        form.addRow("标准件引用:", self.standard_ref_edit)
        self.enabled_check = QCheckBox("启用监控")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)
        center_layout.addLayout(form)

        self.save_button = QPushButton("保存策略")
        self.save_button.setStyleSheet(BUTTON_SECONDARY)
        self.save_button.clicked.connect(self._on_save_policy)
        center_layout.addWidget(self.save_button)
        self.record_button = QPushButton("录入测量值")
        self.record_button.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.record_button.clicked.connect(self._on_record)
        center_layout.addWidget(self.record_button)
        center_layout.addStretch()
        splitter.addWidget(center)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("滚动状态"))
        self.status_label = QLabel("…")
        right_layout.addWidget(self.status_label)
        self.history_table = QTableWidget(0, 3)
        self.history_table.setHorizontalHeaderLabels(["时间", "偏倚", "重复性 σ"])
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.history_table, 1)
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.chart_container, 2)
        splitter.addWidget(right)
        splitter.setSizes([220, 330, 490])
        layout.addWidget(splitter)

        buttons = QDialogButtonBox(self)
        self.refresh_button = buttons.addButton("刷新", QDialogButtonBox.ActionRole)
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------ 数据
    def refresh(self) -> None:
        current = self._selected_gauge()
        self.gauge_list.blockSignals(True)
        self.gauge_list.clear()
        for gauge_id in sorted(self.monitor.policies):
            self.gauge_list.addItem(gauge_id)
        self.gauge_list.blockSignals(False)
        if current:
            items = [self.gauge_list.item(i).text()
                     for i in range(self.gauge_list.count())]
            if current in items:
                self.gauge_list.setCurrentRow(items.index(current))
        if self.gauge_list.count() and self.gauge_list.currentRow() < 0:
            self.gauge_list.setCurrentRow(0)
        self._refresh_status()

    def _selected_gauge(self) -> str:
        item = self.gauge_list.currentItem()
        return item.text() if item is not None else ""

    def _load_selected(self) -> None:
        gauge_id = self._selected_gauge()
        policy = self.monitor.policies.get(gauge_id)
        if policy is None:
            return
        self.gauge_id_edit.setText(policy.gauge_id)
        self.expected_spin.setValue(policy.expected_value)
        self.window_spin.setValue(policy.window_n)
        self.bias_limit_edit.setText(_fmt_optional(policy.drift_rule.get("bias_limit")))
        self.ucl_edit.setText(_fmt_optional(policy.drift_rule.get("ucl")))
        self.lcl_edit.setText(_fmt_optional(policy.drift_rule.get("lcl")))
        self.standard_ref_edit.setText(policy.standard_ref)
        self.enabled_check.setChecked(policy.enabled)
        self._refresh_status()

    def _on_new(self) -> None:
        self.gauge_list.setCurrentRow(-1)
        self.gauge_id_edit.clear()
        self.expected_spin.setValue(0.0)
        self.window_spin.setValue(10)
        self.bias_limit_edit.clear()
        self.ucl_edit.clear()
        self.lcl_edit.clear()
        self.standard_ref_edit.clear()
        self.enabled_check.setChecked(True)
        self._refresh_status()

    def _on_save_policy(self) -> None:
        try:
            policy = self._policy_from_form()
        except ValueError as exc:
            QMessageBox.warning(self, "策略无效", str(exc))
            return
        self.monitor.set_policy(policy)
        self.refresh()
        self.gauge_list.setCurrentRow(
            [self.gauge_list.item(i).text()
             for i in range(self.gauge_list.count())].index(policy.gauge_id))

    def _policy_from_form(self) -> GaugeStudyPolicy:
        gauge_id = self.gauge_id_edit.text().strip()
        if not gauge_id:
            raise ValueError("量具 ID 不能为空（建议 设备:通道）")
        rule: dict[str, float] = {}
        bias_limit = _parse_optional_float(self.bias_limit_edit.text(), "偏倚容忍限")
        ucl = _parse_optional_float(self.ucl_edit.text(), "MPC 上参考限")
        lcl = _parse_optional_float(self.lcl_edit.text(), "MPC 下参考限")
        if bias_limit is not None:
            rule["bias_limit"] = bias_limit
        if ucl is not None:
            rule["ucl"] = ucl
        if lcl is not None:
            rule["lcl"] = lcl
        return GaugeStudyPolicy(
            gauge_id=gauge_id, expected_value=self.expected_spin.value(),
            window_n=self.window_spin.value(), drift_rule=rule,
            standard_ref=self.standard_ref_edit.text().strip(),
            enabled=self.enabled_check.isChecked())

    def _on_delete(self) -> None:
        gauge_id = self._selected_gauge()
        if not gauge_id:
            QMessageBox.information(self, "删除量具", "请先选择量具")
            return
        reply = QMessageBox.question(
            self, "删除量具", f"删除「{gauge_id}」的策略与滚动状态？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.monitor.remove_policy(gauge_id)
        self.refresh()
        self._on_new()

    # ------------------------------------------------------------ 录入
    def _on_record(self) -> None:
        gauge_id = self._selected_gauge()
        if not gauge_id:
            QMessageBox.information(self, "录入测量值", "请先保存/选择量具策略")
            return
        value, ok = QInputDialog.getDouble(self, "录入测量值",
                                           f"{gauge_id} 测量值:",
                                           0.0, -1e12, 1e12, 6)
        if not ok:
            return
        self._record_value(float(value))

    def _record_value(self, value: float):
        """录入一个测量值（经主窗口测量管线或直接喂入监控器）。"""
        gauge_id = self._selected_gauge()
        if not gauge_id:
            raise ValueError("未选择量具")
        if callable(self.submit_measurement):
            outcome = self.submit_measurement(gauge_id, float(value))
        else:
            outcome = self.monitor.ingest_values(gauge_id, [float(value)])
        self._refresh_status()
        return outcome

    # ------------------------------------------------------------ 状态渲染
    def _refresh_status(self) -> None:
        gauge_id = self._selected_gauge()
        record = next((row for row in self.monitor.snapshot()
                       if row["gauge_id"] == gauge_id), None)
        if record is None:
            self.status_label.setText("暂无监控数据 — 保存策略并录入测量值")
            self.history_table.setRowCount(0)
            self._render_chart()
            return
        state = record["state"]
        color = _STATE_COLORS.get(state, "#a0a3ae")
        self.status_label.setText(
            f"{gauge_id} · "
            f"<span style='color:{color};font-weight:bold'>"
            f"{_STATE_LABELS.get(state, state)}</span>"
            f" · 健康分 {record['health_score']:.1f}"
            f" · n={record['n']}"
            f" · σ={record['repeatability_sigma']:.6g}"
            f" · 偏倚={record['bias']:.6g}"
            + (f" · 最近提示 {record['last_prompt_at']}"
               if record.get("last_prompt_at") else ""))
        state_obj = self.monitor.states.get(gauge_id)
        history = list(state_obj.bias_history[-12:]) if state_obj else []
        self.history_table.setRowCount(len(history))
        for row, item in enumerate(reversed(history)):
            values = (str(item.get("at", "")),
                      f"{float(item.get('bias', 0.0)):.6g}",
                      f"{float(item.get('sigma', 0.0)):.6g}")
            for column, text in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(text))
        self.history_table.resizeColumnsToContents()
        self._render_chart()

    def _render_chart(self) -> None:
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        gauge_id = self._selected_gauge()
        frame = self.monitor.frame_for(gauge_id) if gauge_id else None
        if frame is None or not getattr(frame, "data", None):
            self.chart_layout.addWidget(QLabel("暂无偏倚序列（录入测量值后显示 MPC 图）"))
            return
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

            from output.chart_engine import create_control_chart
        except ImportError:  # matplotlib 可选（B5 启动加固口径）
            self.chart_layout.addWidget(
                QLabel("缺少图表依赖（pip install matplotlib），MPC 数值仍可用"))
            return
        try:
            figure = create_control_chart(
                frame.as_chart_data("imr"), title=f"{gauge_id} 偏倚 MPC 图",
                figsize=(8, 4.0))
        except Exception:  # 图表渲染失败不影响监控主体
            self.chart_layout.addWidget(QLabel("MPC 图渲染失败（数值判定不受影响）"))
            return
        self.chart_layout.addWidget(FigureCanvasQTAgg(figure))


def _fmt_optional(value) -> str:
    return "" if value is None else f"{float(value):g}"


__all__ = ["GaugeOnlineDialog"]
