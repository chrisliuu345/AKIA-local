"""
图表编辑面板 — 实时调整图表参数

支持的控件类型：滑块、单选、复选
默认展开常显，直接调整即实时生效
"""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QRadioButton, QCheckBox, QButtonGroup,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from analysis.charts.chart_options import (
    SliderOption, RadioOption, CheckboxOption,
    get_chart_options, get_default_options,
)
from ui.font_config import get_ui_font


class ChartEditorPanel(QWidget):
    """图表编辑面板 — 常显展开，实时调整图表参数"""

    options_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_chart_type: Optional[str] = None
        self._options: Dict[str, Any] = {}
        self._controls: Dict[str, QWidget] = {}
        self._slider_scales: Dict[str, int] = {}
        self._is_expanded = True
        self._building = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(10, 6, 10, 6)

        icon_label = QLabel("⚙")
        icon_label.setFont(QFont(get_ui_font(), 14))
        header.addWidget(icon_label)

        title = QLabel("图表选项")
        title.setFont(QFont(get_ui_font(), 12, QFont.Weight.Bold))
        header.addWidget(title)

        header.addStretch()

        layout.addLayout(header)

        self._content_frame = QFrame()
        self._content_frame.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border: 1px solid #3a3a48;
                border-radius: 6px;
            }
        """)
        self._content_layout = QVBoxLayout(self._content_frame)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(10)

        self._placeholder = QLabel("选择图表类型后显示编辑选项")
        self._placeholder.setStyleSheet("color: #6e7080; font-size: 12px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._placeholder)

        self._content_frame.setVisible(True)
        layout.addWidget(self._content_frame)
        self._sync_minimum_height()

    def _sync_minimum_height(self):
        """按内容自然高锁定最小高度，使页面滚动承接扩展，而不是挤压图表"""
        content_h = self._content_layout.sizeHint().height()
        if content_h <= 0:
            self._content_frame.adjustSize()
            content_h = self._content_frame.sizeHint().height()
        self.setMinimumHeight(content_h + 68)

    def set_chart_type(self, chart_type: str):
        if chart_type == self._current_chart_type:
            return

        self._current_chart_type = chart_type
        self._options = get_default_options(chart_type)
        self._build_controls()

    def _build_controls(self):
        self._building = True
        try:
            while self._content_layout.count():
                item = self._content_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)

            opts = get_chart_options(self._current_chart_type)
            self._controls.clear()
            self._slider_scales.clear()
            if not opts:
                self._placeholder = QLabel("该图表类型暂不支持编辑")
                self._placeholder.setStyleSheet("color: #6e7080; font-size: 11px;")
                self._content_layout.addWidget(self._placeholder)
                return

            for slider in opts.sliders:
                self._add_slider_control(slider)

            for radio in opts.radios:
                self._add_radio_control(radio)

            for checkbox in opts.checkboxes:
                self._add_checkbox_control(checkbox)

            self._content_layout.addStretch()
        finally:
            self._building = False
        if self._is_expanded:
            self._sync_minimum_height()

    @staticmethod
    def _scale_for_step(step: float) -> int:
        """QSlider 只支持整数，步长 <1 时按 10/100 倍数放大，取值时再还原为小数"""
        return 1 if step >= 1 else round(1.0 / step)

    @staticmethod
    def _fmt_value(value: float) -> str:
        return f"{value:.4f}".rstrip("0").rstrip(".")

    def _add_slider_control(self, opt: SliderOption):
        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel(opt.label)
        label.setFont(QFont(get_ui_font(), 10))
        label.setFixedWidth(96)
        row.addWidget(label)

        scale = self._scale_for_step(opt.step)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(opt.min_val * scale))
        slider.setMaximum(int(opt.max_val * scale))
        slider.setValue(int(round(opt.default * scale)))
        slider.setSingleStep(max(1, int(round(opt.step * scale))))
        slider.setFixedHeight(24)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #3a3a48;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -7px 0;
                background: #4da6ff;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #7fc1ff;
            }
        """)
        slider.valueChanged.connect(
            lambda val, key=opt.key, s=scale: self._on_slider_changed(key, val, s))
        row.addWidget(slider, 1)

        value_label = QLabel(f"{self._fmt_value(opt.default)}{opt.unit}")
        value_label.setFont(QFont(get_ui_font(), 10))
        value_label.setFixedWidth(64)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(value_label)

        slider.valueChanged.connect(
            lambda val, lbl=value_label, unit=opt.unit, s=scale:
                lbl.setText(f"{self._fmt_value(val / s)}{unit}"))

        self._controls[opt.key] = slider
        self._slider_scales[opt.key] = scale
        self._content_layout.addLayout(row)

    def _add_radio_control(self, opt: RadioOption):
        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel(opt.label)
        label.setFont(QFont(get_ui_font(), 10))
        label.setFixedWidth(96)
        row.addWidget(label)

        btn_group = QButtonGroup(self)
        for _i, option_text in enumerate(opt.options):
            rb = QRadioButton(option_text)
            rb.setFont(QFont(get_ui_font(), 10))
            rb.setStyleSheet("""
                QRadioButton { color: #e1e2e6; padding: 2px 4px; }
                QRadioButton::indicator { width: 16px; height: 16px; }
            """)
            if option_text == opt.default:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, key=opt.key, val=option_text: self._on_radio_changed(key, val, checked))
            btn_group.addButton(rb)
            row.addWidget(rb)

        self._controls[opt.key] = btn_group
        self._content_layout.addLayout(row)

    def _add_checkbox_control(self, opt: CheckboxOption):
        cb = QCheckBox(opt.label)
        cb.setFont(QFont(get_ui_font(), 10))
        cb.setChecked(opt.default)
        cb.setStyleSheet("""
            QCheckBox { color: #e1e2e6; padding: 2px 4px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)
        cb.stateChanged.connect(lambda state, key=opt.key: self._on_checkbox_changed(key, state))

        self._controls[opt.key] = cb
        self._content_layout.addWidget(cb)

    def _on_slider_changed(self, key: str, value: int, scale: int = 1):
        if getattr(self, "_building", False):
            return
        self._options[key] = round(value / scale, 6)
        self.options_changed.emit(self._options.copy())

    def _on_radio_changed(self, key: str, value: str, checked: bool):
        if getattr(self, "_building", False):
            return
        if checked:
            self._options[key] = value
            self.options_changed.emit(self._options.copy())

    def _on_checkbox_changed(self, key: str, state: int):
        if getattr(self, "_building", False):
            return
        self._options[key] = state == Qt.CheckState.Checked.value
        self.options_changed.emit(self._options.copy())

    def get_options(self) -> Dict[str, Any]:
        return self._options.copy()

    def set_options(self, options: Dict[str, Any]):
        self._options = options.copy()
        self._update_controls_from_options()

    def _update_controls_from_options(self):
        self._building = True
        try:
            for key, value in self._options.items():
                ctrl = self._controls.get(key)
                if ctrl is None:
                    continue
                if isinstance(ctrl, QSlider):
                    scale = self._slider_scales.get(key, 1)
                    ctrl.setValue(int(round(value * scale)))
                elif isinstance(ctrl, QButtonGroup):
                    for btn in ctrl.buttons():
                        if btn.text() == value:
                            btn.setChecked(True)
                            break
                elif isinstance(ctrl, QCheckBox):
                    ctrl.setChecked(bool(value))
        finally:
            self._building = False

    def is_expanded(self) -> bool:
        """面板常显展开，无折叠状态"""
        return True

    def set_expanded(self, expanded: bool):
        """兼容旧调用：面板不可折叠，恒展开"""
        return
