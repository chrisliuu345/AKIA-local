"""分析页配置区：按钮留出竖向间距，下拉用圆角按钮而不是系统箭头。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.tabs.capability_tab import CapabilityTab
from ui.tabs.spc_tab import SPCTab
from ui.theme import APP_STYLESHEET, CONFIG_BUTTON_GAP, ensure_combo_indicator

app = QApplication.instance() or QApplication([])
app.setStyle("Fusion")
ensure_combo_indicator()
app.setStyleSheet(APP_STYLESHEET)


def _show(tab):
    tab.resize(900, 700)
    tab.show()
    app.processEvents()
    return tab


def test_spc_action_buttons_are_spaced():
    tab = _show(SPCTab())
    gap = tab.save_png_btn.y() - (tab.run_btn.y() + tab.run_btn.height())
    assert gap >= CONFIG_BUTTON_GAP
    assert tab.export_btn.y() - (tab.root_cause_btn.y() + tab.root_cause_btn.height()) >= CONFIG_BUTTON_GAP
    tab.close()


def test_capability_uses_the_same_button_gap():
    tab = _show(CapabilityTab())
    gap = tab.export_btn.y() - (tab.save_png_btn.y() + tab.save_png_btn.height())
    assert gap >= CONFIG_BUTTON_GAP
    tab.close()


def test_analysis_combos_use_the_rounded_drop_button():
    tab = _show(SPCTab())
    assert tab.chart_type_combo.property("analysisCombo") is True
    assert tab.col_combo.property("analysisCombo") is True
    sheet = app.styleSheet()
    assert 'QComboBox[analysisCombo="true"]::drop-down' in sheet
    assert "border-radius: 8px" in sheet
    assert "akia:combo_chevron.png" in sheet
    tab.close()
