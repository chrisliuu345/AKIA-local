"""分析结果区不再用图表/数据开关，三块圆角框同时可见。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QVBoxLayout

from ui.tabs.base_tab import BaseAnalysisTab
from ui.tabs.spc_tab import SPCTab
from ui.tabs.time_study_tab import TimeStudyTab

app = QApplication.instance() or QApplication([])


def test_toggle_strings_are_gone_from_analysis_tabs():
    from pathlib import Path
    for path in Path("ui/tabs").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "btn_view_chart" not in text, path.name
        assert "tab.view_chart" not in text, path.name


def test_spc_results_have_three_panes():
    tab = SPCTab()
    assert tab.chart_pane is not None and not tab.chart_pane.isHidden()
    assert tab.options_pane is not None and tab.options_pane.isHidden()
    assert tab.data_pane is not None and not tab.data_pane.isHidden()
    assert tab.result_text is not None and tab.result_table is not None
    for pane in (tab.chart_pane, tab.options_pane, tab.data_pane):
        assert pane.objectName() == "resultPane"
        assert "border-radius: 9px" in pane.styleSheet()
    tab._reveal_options_pane("XBar-R")
    assert not tab.options_pane.isHidden()
    tab.close()


def test_time_study_omits_text_pane_but_keeps_table():
    """时间研究只有表格，没有文字结果框。"""
    tab = TimeStudyTab()
    assert not tab.chart_pane.isHidden()
    assert not tab.data_pane.isHidden()
    assert tab.result_text is None
    assert tab.result_table is not None
    assert tab.options_pane is not None and tab.options_pane.isHidden()
    tab.close()


def test_chart_only_page_omits_empty_panes():
    class _ChartOnly(BaseAnalysisTab):
        def __init__(self):
            super().__init__()
            root = QVBoxLayout(self)
            self.mount_results(root, text=False, table=False, options=False)

    tab = _ChartOnly()
    assert not tab.chart_pane.isHidden()
    assert tab.options_pane is None
    assert tab.data_pane is None
    tab.close()
