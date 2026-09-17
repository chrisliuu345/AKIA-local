"""Tab 数据路由与空状态分类回归 — 防止新 Tab 漏接线 / 自包含工具被遮罩。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

#: 应通过「导入数据文件」收到工作簿数据的分析型 Tab
DATA_TABS = (1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18, 19, 20,
             23, 24, 25, 26, 28, 36, 37)
#: 自包含工具 Tab（手工录入 / 预设 / 表单驱动），不应出现导入遮罩
SELF_CONTAINED_TABS = (8, 14, 16, 17, 21, 22, 25, 26, 29, 30, 31, 32)


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    QApplication.processEvents()
    yield win
    win.close()
    win.deleteLater()


@pytest.fixture
def sample_raw():
    return {"Sheet1": pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0, 5.0],
        "y": [2.0, 4.0, 6.0, 8.0, 10.0],
        "label": ["a", "b", "a", "b", "a"],
    })}


class TestWorksheetDataRouting:
    def test_all_analysis_tabs_receive_data(self, window, sample_raw):
        window._route_sheets_to_tabs(sample_raw, worksheet_mode=True)
        QApplication.processEvents()

        missing = []
        for idx in DATA_TABS:
            tab = window.stack.widget(idx)
            df = getattr(tab, "df", None)
            if df is None or len(df) == 0:
                missing.append(f"{idx}:{type(tab).__name__}")
        assert not missing, f"导入后未收到数据的 Tab: {missing}"

    def test_time_series_and_predictive_hide_overlay_after_import(self, window, sample_raw):
        window._route_sheets_to_tabs(sample_raw, worksheet_mode=True)
        QApplication.processEvents()

        for idx in (36, 37):
            tab = window.stack.widget(idx)
            overlay = getattr(tab, "_empty_overlay", None)
            assert overlay is None or not overlay.isVisible(), \
                f"Tab {idx} 导入后仍显示空状态遮罩"


class TestSelfContainedTabs:
    def test_no_import_overlay(self, window):
        for idx in SELF_CONTAINED_TABS:
            window._switch_tab(idx)
            QApplication.processEvents()
            tab = window.stack.widget(idx)
            overlay = getattr(tab, "_empty_overlay", None)
            assert overlay is None or not overlay.isVisible(), \
                f"自包含工具 Tab {idx} 被导入遮罩挡住"

    def test_fmea_to_control_plan_chain_not_blocked(self, window):
        ok = window._import_cp_from_fmea([
            ["OP01", "车削", "轴径", "10±0.02", "千分尺", "5", "每小时", "XBar-R", "隔离"],
        ])
        assert ok
        cp = window.stack.widget(17)
        assert cp is not None
        assert cp._rows[-1][0] == "OP01"
        overlay = getattr(cp, "_empty_overlay", None)
        assert overlay is None or not overlay.isVisible()
