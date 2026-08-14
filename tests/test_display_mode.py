"""车间大屏模式单测 — KPI 瓦片/图表轮播/空态 (v2.4 F4)"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import pytest
from matplotlib.figure import Figure
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QPoint

from config import settings
from ui.dialogs.display_mode import DisplayModeWindow, ZoomPixmapView


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _anim_off():
    original = dict(settings._user_overrides)
    settings._user_overrides = {"animations_enabled": False}
    yield
    settings._user_overrides = original


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


class _FakeWheel:
    def __init__(self, dy):
        self._dy = dy
        self.accepted = False

    def angleDelta(self):
        return QPoint(0, self._dy)

    def accept(self):
        self.accepted = True


class TestZoomView:
    def test_widget_is_zoom_view(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={2: {"analysis_type": "能力", "params": {},
                          "result": {"capability": {"cpk": 1.1}}}},
            tabs={2: FakeTab(_fig())},
        ))
        view = win.chart_stack.widget(0)
        assert isinstance(view, ZoomPixmapView)
        win.close()
        win.deleteLater()

    def test_zoom_clamped_and_double_click_reset(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={2: {"analysis_type": "能力", "params": {},
                          "result": {"capability": {"cpk": 1.1}}}},
            tabs={2: FakeTab(_fig())},
        ))
        view = win.chart_stack.widget(0)
        view._fit()
        base_zoom = view._zoom
        assert base_zoom > 0

        view.wheelEvent(_FakeWheel(120))
        assert view._zoom > base_zoom

        for _ in range(100):
            view.wheelEvent(_FakeWheel(120))
        assert view._zoom <= ZoomPixmapView.MAX_ZOOM + 1e-9

        for _ in range(200):
            view.wheelEvent(_FakeWheel(-120))
        assert view._zoom >= ZoomPixmapView.MIN_ZOOM - 1e-9

        view.mouseDoubleClickEvent(None)
        assert abs(view._zoom - base_zoom) < 1e-9

        win.close()
        win.deleteLater()

    def _win_with_view(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={2: {"analysis_type": "能力", "params": {},
                          "result": {"capability": {"cpk": 1.1}}}},
            tabs={2: FakeTab(_fig())},
        ))
        win.show()
        QTest.qWait(50)
        view = win.chart_stack.widget(0)
        return win, view

    def test_refit_after_resize_keeps_aspect(self, app):
        win, view = self._win_with_view(app)
        view.resize(800, 600)
        QTest.qWait(50)

        m = view.transform()
        assert abs(m.m11() - m.m22()) < 1e-9          # 等比缩放, 无拉伸
        assert m.m11() > 0

        r = m.mapRect(view._item.boundingRect())      # 完整适配视口, 无遮挡
        vp = view.viewport()
        assert r.width() <= vp.width() + 1.0
        assert r.height() <= vp.height() + 1.0

        win.close()
        win.deleteLater()

    def test_resize_keeps_user_zoom(self, app):
        win, view = self._win_with_view(app)
        view._fit()
        view.wheelEvent(_FakeWheel(120))
        zoomed = view._zoom
        assert zoomed > 0

        view.resize(800, 600)
        QTest.qWait(50)
        assert abs(view._zoom - zoomed) < 1e-9       # 用户缩放不被 resize 覆盖

        win.close()
        win.deleteLater()

    def test_zero_size_viewport_then_refit(self, app):
        win, view = self._win_with_view(app)
        view.resize(0, 0)
        QTest.qWait(50)                              # 零尺寸视口不崩不产生 NaN

        view.resize(800, 600)
        QTest.qWait(50)
        m = view.transform()
        assert m.m11() > 0
        assert abs(m.m11() - m.m22()) < 1e-9

        win.close()
        win.deleteLater()

    def test_show_event_triggers_fit(self, app):
        win, view = self._win_with_view(app)
        pm = view._item.pixmap()
        win.close()
        win.deleteLater()

        v2 = ZoomPixmapView(pm)
        v2.show()
        QTest.qWait(30)
        v2.resize(800, 600)
        QTest.qWait(30)
        fitted = v2._zoom
        assert fitted > 0
        v2.resetTransform()
        v2._zoom = 1.0
        v2._user_zoomed = False
        v2.hide()
        v2.show()
        QTest.qWait(30)
        assert abs(v2._zoom - fitted) < 1e-6
        v2.deleteLater()


class TestAnimationsEnabled:
    def test_count_up_completes_after_wait(self, app):
        settings._user_overrides = {"animations_enabled": True}
        win = DisplayModeWindow(FakeMain(analyses={
            10: {"analysis_type": "OEE", "params": {},
                 "result": {"overall": {"oee": 0.853}}},
        }))
        QTest.qWait(1200)
        assert "85.3%" in _kpi_texts(win)
        win.close()
        win.deleteLater()

    def test_cross_fade_switches_after_wait(self, app):
        settings._user_overrides = {"animations_enabled": True}
        fig = _fig()
        win = DisplayModeWindow(FakeMain(
            analyses={
                2: {"analysis_type": "能力", "params": {},
                    "result": {"capability": {"cpk": 1.1}}},
                10: {"analysis_type": "OEE", "params": {},
                     "result": {"overall": {"oee": 0.8}}},
            },
            tabs={2: FakeTab(fig), 10: FakeTab(fig)},
        ))
        win._step_chart(1)
        QTest.qWait(600)
        assert win.chart_stack.currentIndex() == 1
        win.close()
        win.deleteLater()

    def test_cross_fade_disabled_switches_instantly(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={
                2: {"analysis_type": "能力", "params": {},
                    "result": {"capability": {"cpk": 1.1}}},
                10: {"analysis_type": "OEE", "params": {},
                     "result": {"overall": {"oee": 0.8}}},
            },
            tabs={2: FakeTab(_fig()), 10: FakeTab(_fig())},
        ))
        win._step_chart(1)
        assert win.chart_stack.currentIndex() == 1
        win.close()
        win.deleteLater()


class TestAspectRender:
    """方案A: 大屏按图表区比例专属渲染 (v2.4.1 fix)"""

    def test_render_matches_target_aspect(self, app):
        win = DisplayModeWindow(FakeMain())
        fig = _fig()
        pm_a = win._render_figure(fig, 800, 400)
        assert pm_a is not None
        ratio_a = pm_a.width() / pm_a.height()
        assert abs(ratio_a - 2.0) < 0.25

        pm_b = win._render_figure(fig, 800, 600)
        assert pm_b is not None
        ratio_b = pm_b.width() / pm_b.height()
        assert abs(ratio_b - 800 / 600) < 0.25
        assert ratio_a > ratio_b * 1.15
        win.close()
        win.deleteLater()

    def test_fit_fills_viewport_when_aspect_matches(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={2: {"analysis_type": "能力", "params": {},
                          "result": {"capability": {"cpk": 1.1}}}},
            tabs={2: FakeTab(_fig())},
        ))
        win.show()
        QTest.qWait(50)
        win.resize(1200, 800)
        QTest.qWait(400)
        view = win.chart_stack.widget(0)
        assert view is not None
        m = view.transform()
        assert abs(m.m11() - m.m22()) < 1e-9
        assert m.m11() > 0.9
        win.close()
        win.deleteLater()

    def test_resize_rerenders_to_new_viewport(self, app):
        win = DisplayModeWindow(FakeMain(
            analyses={2: {"analysis_type": "能力", "params": {},
                          "result": {"capability": {"cpk": 1.1}}}},
            tabs={2: FakeTab(_fig())},
        ))
        win.show()
        QTest.qWait(50)
        view0 = win.chart_stack.widget(0)
        old_pm = view0._item.pixmap()
        win.resize(1400, 900)
        QTest.qWait(500)
        view1 = win.chart_stack.widget(0)
        assert view1 is not view0
        new_pm = view1._item.pixmap()
        assert (new_pm.width(), new_pm.height()) != (old_pm.width(), old_pm.height())
        vp = win.chart_stack
        if vp.width() > 0 and vp.height() > 0:
            assert abs(new_pm.width() / new_pm.height()
                       - vp.width() / vp.height()) < 0.25
        win.close()
        win.deleteLater()
