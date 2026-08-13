"""车间大屏模式单测 — KPI 瓦片/图表轮播/空态 (v2.4 F4)"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import pytest
from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication, QLabel

from ui.dialogs.display_mode import DisplayModeWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class FakeTab:
    def __init__(self, fig=None):
        self.current_figure = fig


class FakeMain:
    """轻量 MainWindow 替身 — DisplayModeWindow 只依赖三个属性"""

    def __init__(self, analyses=None, tabs=None, file_path=""):
        self.analyses = analyses or {}
        self.current_data = {"file_path": file_path}
        self._tabs = tabs or {}

    def _get_tabs(self):
        return self._tabs


def _fig():
    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    ax.plot([1, 2, 3, 4])
    return fig


def _kpi_texts(win):
    return " | ".join(
        lbl.text() for lbl in win.findChildren(QLabel) if lbl.text()
    )


class TestKpiTiles:
    def test_oee_cpk_violations_tiles(self, app):
        main = FakeMain(analyses={
            2: {"analysis_type": "能力", "params": {},
                "result": {"capability": {"cpk": 1.42}}},
            10: {"analysis_type": "OEE", "params": {},
                 "result": {"overall": {"oee": 0.853}}},
            1: {"analysis_type": "SPC", "params": {},
                "result": {"xbar_chart": {"violations": [1, 2, 3]}}},
        })
        win = DisplayModeWindow(main)
        texts = _kpi_texts(win)
        assert "85.3%" in texts          # 综合 OEE
        assert "1.420" in texts          # 最优 Cpk
        assert "3" in texts              # 违规总数
        win.close()
        win.deleteLater()

    def test_empty_analyses_no_crash(self, app):
        win = DisplayModeWindow(FakeMain())
        texts = _kpi_texts(win)
        assert "暂无图表" in texts       # 空态提示
        win.close()
        win.deleteLater()


class TestCarousel:
    def test_charts_loaded_and_step(self, app):
        fig = _fig()
        main = FakeMain(
            analyses={
                2: {"analysis_type": "能力", "params": {},
                    "result": {"capability": {"cpk": 1.1}}},
                10: {"analysis_type": "OEE", "params": {},
                     "result": {"overall": {"oee": 0.8}}},
            },
            tabs={2: FakeTab(fig), 10: FakeTab(fig)},
        )
        win = DisplayModeWindow(main)
        assert len(win._charts) == 2
        assert win.chart_stack.count() == 2
        assert win._chart_idx == 0

        # 手动切换: 前进一步回绕
        win._step_chart(1)
        assert win._chart_idx == 1
        win._step_chart(1)
        assert win._chart_idx == 0
        # 后退一步回绕
        win._step_chart(-1)
        assert win._chart_idx == 1
        win.close()
        win.deleteLater()

    def test_tab_without_figure_skipped(self, app):
        main = FakeMain(
            analyses={
                2: {"analysis_type": "能力", "params": {},
                    "result": {"capability": {"cpk": 1.1}}},
                10: {"analysis_type": "OEE", "params": {},
                     "result": {"overall": {"oee": 0.8}}},
            },
            tabs={2: FakeTab(_fig()), 10: FakeTab(None)},
        )
        win = DisplayModeWindow(main)
        assert len(win._charts) == 1  # 无 figure 的 tab 被跳过
        win.close()
        win.deleteLater()
