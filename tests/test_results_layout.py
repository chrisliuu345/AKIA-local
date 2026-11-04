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


def test_shared_text_pane_grows_with_the_table():
    """右侧文字区要能看见摘要和好几行表，行数再多也由页面滚动接住。"""
    from PySide6.QtCore import Qt

    tab = SPCTab()
    assert tab.data_pane.minimumHeight() >= 420
    assert tab.result_table.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    tab.result_text.setPlainText("摘要\n" * 6)
    tab.result_table.setColumnCount(2)
    tab.result_table.setRowCount(20)
    app.processEvents()
    assert tab.result_table.minimumHeight() >= 20 * 24
    assert tab.result_text.minimumHeight() >= 112
    assert tab.data_pane.minimumHeight() >= (
        tab.result_text.minimumHeight() + tab.result_table.minimumHeight()
    )
    tab.close()


def test_table_only_page_uses_the_same_tall_pane():
    tab = TimeStudyTab()
    assert tab.data_pane.minimumHeight() >= 420
    tab.result_table.setColumnCount(3)
    tab.result_table.setRowCount(12)
    app.processEvents()
    assert tab.result_table.minimumHeight() >= 12 * 24
    assert tab.data_pane.minimumHeight() >= tab.result_table.minimumHeight()
    tab.close()


def test_sampling_result_table_stays_with_the_current_mode():
    """结果表跟在当前抽样方式下面，不被最高的批检验表单顶到页面外。"""
    from PySide6.QtWidgets import QFrame, QScrollArea

    from ui.main_window_helpers import _CurrentPageStack
    from ui.tabs.sampling_tab import SamplingTab

    tab = SamplingTab()
    tab._do_aql()
    outer = _CurrentPageStack()
    outer.addWidget(tab)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(outer)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.resize(1100, 720)
    scroll.show()
    app.processEvents()

    assert tab.stack.height() < 280
    assert tab.result.minimumHeight() >= 180
    assert tab.result.height() >= 180
    assert tab.result.y() < tab.stack.y() + tab.stack.height() + 40
    bottom = tab.result.y() + tab.result.height()
    reach = scroll.verticalScrollBar().maximum() + scroll.viewport().height()
    assert reach + 4 >= bottom
    assert bottom <= tab.height() + 2
    tab.close()
    scroll.close()


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
