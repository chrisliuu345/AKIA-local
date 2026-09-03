"""
设置对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QDialogButtonBox, QCheckBox, QTabWidget, QWidget,
)

from config.settings import (
    FONT_FAMILY, CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_NDC_THRESHOLD, get_setting,
    DEPARTMENTS, TEAMS,
)
from ui.theme import colors as theme_colors


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setMinimumSize(520, 430)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.font_combo = QComboBox()
        self.font_combo.addItems(FONT_FAMILY)
        saved_font = get_setting("font_family", FONT_FAMILY[0])
        if saved_font in [self.font_combo.itemText(i) for i in range(self.font_combo.count())]:
            self.font_combo.setCurrentText(saved_font)
        general_layout.addRow("默认字体:", self.font_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 300)
        self.dpi_spin.setValue(get_setting("chart_dpi", CHART_DPI))
        general_layout.addRow("图表DPI:", self.dpi_spin)

        self.animations_check = QCheckBox("界面动画效果 (淡入/数字滚动)")
        self.animations_check.setChecked(get_setting("animations_enabled", True))
        general_layout.addRow("动画:", self.animations_check)

        tabs.addTab(general_tab, "通用")

        rules_tab = QWidget()
        rules_layout = QFormLayout(rules_tab)

        self.nelson_check = QCheckBox("启用Nelson判异规则")
        self.nelson_check.setChecked(get_setting("nelson_rules_enabled", True))
        rules_layout.addRow(self.nelson_check)

        tabs.addTab(rules_tab, "判异规则")

        msa_tab = QWidget()
        msa_layout = QFormLayout(msa_tab)

        self.grr_accept = QDoubleSpinBox()
        self.grr_accept.setRange(0, 0.5)
        self.grr_accept.setValue(get_setting("msa_grr_acceptable", MSA_GRR_ACCEPTABLE))
        self.grr_accept.setSingleStep(0.01)
        msa_layout.addRow("%GRR 可接受阈值:", self.grr_accept)

        self.ndc_spin = QSpinBox()
        self.ndc_spin.setRange(1, 10)
        self.ndc_spin.setValue(get_setting("msa_ndc_threshold", MSA_NDC_THRESHOLD))
        msa_layout.addRow("NDC 阈值:", self.ndc_spin)

        tabs.addTab(msa_tab, "MSA")

        alert_tab = QWidget()
        alert_layout = QFormLayout(alert_tab)

        self.alert_min_spin = QSpinBox()
        self.alert_min_spin.setRange(0, 100)
        self.alert_min_spin.setValue(get_setting("alert_min_violations", 1))
        self.alert_min_spin.setToolTip("判异点数达到该阈值才触发告警")
        alert_layout.addRow("最小判异点数:", self.alert_min_spin)

        self.alert_popup_check = QCheckBox("弹窗告警")
        self.alert_popup_check.setChecked(get_setting("alert_popup_enabled", True))
        alert_layout.addRow(self.alert_popup_check)

        self.alert_sound_check = QCheckBox("声音提醒")
        self.alert_sound_check.setChecked(get_setting("alert_sound_enabled", True))
        alert_layout.addRow(self.alert_sound_check)

        self.alert_log_check = QCheckBox("告警日志")
        self.alert_log_check.setChecked(get_setting("alert_log_enabled", True))
        alert_layout.addRow(self.alert_log_check)

        tabs.addTab(alert_tab, "告警")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> dict:
        """返回所有用户设置值"""
        return {
            "font_family": self.font_combo.currentText(),
            "chart_dpi": self.dpi_spin.value(),
            "animations_enabled": self.animations_check.isChecked(),
            "nelson_rules_enabled": self.nelson_check.isChecked(),
            "msa_grr_acceptable": self.grr_accept.value(),
            "msa_ndc_threshold": self.ndc_spin.value(),
            "alert_min_violations": self.alert_min_spin.value(),
            "alert_popup_enabled": self.alert_popup_check.isChecked(),
            "alert_sound_enabled": self.alert_sound_check.isChecked(),
            "alert_log_enabled": self.alert_log_check.isChecked(),
        }
