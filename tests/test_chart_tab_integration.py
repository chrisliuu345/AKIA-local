"""
ChartTab 全链路集成测试 — 数据→图库选型→配置→运行→实时编辑→导出

覆盖 P1–P5 在真实 UI 流程中的协同，防止回归
"""

import numpy as np
import pandas as pd
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")


@pytest.fixture
def chart_tab():
    np.random.seed(11)
    parts = []
    for g in ["A线", "B线", "C线"] * 4:
        parts.append(pd.DataFrame({
            "直径": np.random.normal(50.0, 0.9, 60),
            "长度": np.random.normal(120.0, 1.5, 60),
            "班组": g,
            "标签": [f"L{i % 3}" for i in range(60)],
        }))
    df = pd.concat(parts, ignore_index=True)
    from ui.tabs.chart_tab import ChartTab
    tab = ChartTab()
    tab.set_data(df, {})
    yield tab


def _qwait(ms=260):
    QApplication.instance().processEvents()
    QTest.qWait(ms)
    QApplication.instance().processEvents()


class TestChartTabFlow:
    def test_histogram_full_flow(self, chart_tab):
        tab = chart_tab
        w = tab._col_widgets[0]
        w.setCurrentText("直径")
        result = tab.run_and_display()
        assert result is not None and result["chart_type"] == "直方图"
        assert tab.canvas is not None
        assert tab._chart_editor_panel._current_chart_type == "直方图"
        assert tab._chart_toolbar is not None

    def test_gallery_switch_to_scatter_runs(self, chart_tab):
        tab = chart_tab
        tab.chart_gallery.expand()
        tab.chart_gallery._tile_buttons["散点图"].click()
        _qwait(50)
        assert len(tab._col_widgets) == 2
        for w, col in zip(tab._col_widgets, ["直径", "长度"]):
            w.setCurrentText(col)
        ok, msg = tab.validate_params()
        assert ok is True, msg
        result = tab.run_and_display()
        assert result["chart_type"] == "散点图"

    def test_faceting_summary_has_groups(self, chart_tab):
        tab = chart_tab
        tab.chart_gallery.expand()
        tab.chart_gallery._tile_buttons["小多图"].click()
        _qwait(50)
        for w, col in zip(tab._col_widgets, ["直径", "班组"]):
            w.setCurrentText(col)
        tab.run_and_display()
        text = tab.result_text.toPlainText()
        assert "分组变量 班组" in text
        assert "3 组" in text

    def test_editor_change_triggers_redraw(self, chart_tab):
        tab = chart_tab
        w = tab._col_widgets[0]
        w.setCurrentText("直径")
        tab.run_and_display()
        fig_before = tab.current_figure
        editor = tab._chart_editor_panel
        editor.set_expanded(True)
        _qwait(50)
        editor._controls["bins"].setValue(45)
        _qwait(300)  # 防抖 150ms + 渲染
        assert tab.current_figure is not None
        assert fig_before is not tab.current_figure  # 已用新选项重绘

    def test_options_survive_rerun_same_type(self, chart_tab):
        tab = chart_tab
        w = tab._col_widgets[0]
        w.setCurrentText("直径")
        tab.run_and_display()
        editor = tab._chart_editor_panel
        editor.set_expanded(True)
        _qwait(30)
        editor._controls["bins"].setValue(35)
        _qwait(300)
        value_after_tweak = editor.get_options()["bins"]
        assert value_after_tweak == 35
        # 再次运行同类型：面板选项保持，不被默认值覆盖
        tab.run_and_display()
        assert editor.get_options()["bins"] == 35

    def test_export_png_hires_and_svg(self, chart_tab, tmp_path, monkeypatch):
        tab = chart_tab
        w = tab._col_widgets[0]
        w.setCurrentText("直径")
        tab.run_and_display()

        def fake_dialog(_self=None, *a, **k):
            return "", ""

        # 用户取消：不报错
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(fake_dialog))
        tab._on_save_figure("PNG (*.png)", "png", dpi=300)
        assert len(list(tmp_path.glob("*.png"))) == 0

        target_png = str(tmp_path / "chart_hires.png")
        target_svg = str(tmp_path / "chart_vec.svg")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (target_png, "PNG (*.png)")))
        tab._on_save_figure("PNG 高清 300 DPI (*.png)", "png", dpi=300)
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (target_svg, "SVG 矢量图 (*.svg)")))
        tab._on_save_svg()
        assert tmp_path.joinpath("chart_hires.png").exists()
        assert tmp_path.joinpath("chart_vec.svg").exists()
        assert tmp_path.joinpath("chart_hires.png").stat().st_size > 0
        # 导出后画布仍可交互（尺寸已还原）
        assert tab.canvas is not None and tab.current_figure is not None

    def test_gallery_highlights_synced_from_combo(self, chart_tab):
        tab = chart_tab
        tab.chart_type_combo.setCurrentText("箱线图")
        _qwait(50)
        assert tab.chart_gallery.current_type() == "箱线图"


class TestLiveRefreshStability:
    """参数实时刷新不重建布局/不跳滚动（回归：canvas 复用热替换）"""

    def _prepare(self, chart_tab):
        tab = chart_tab
        w = tab._col_widgets[0]
        w.setCurrentText("直径")
        tab.run_and_display()
        return tab

    def test_refresh_swaps_canvas_keeps_panel_and_binding(self, chart_tab):
        tab = self._prepare(chart_tab)
        canvas_before = tab.canvas
        panel_before = tab._chart_editor_panel
        editor = tab._chart_editor_panel
        editor._controls["bins"].setValue(60)
        _qwait(300)
        assert tab.canvas is not canvas_before  # canvas 换新（QtAgg 不可跨 figure 复用）
        assert tab.current_figure is not None
        assert tab.canvas.figure is tab.current_figure
        assert tab.current_figure.canvas is tab.canvas  # 双向绑定完好（导出/右键依赖）
        assert tab._chart_editor_panel is panel_before  # 编辑面板行保持原位
        assert tab.chart_layout.count() == 2  # canvas + 编辑面板，无多余操作栏行

    def test_scroll_position_kept_after_refresh(self, chart_tab):
        tab = self._prepare(chart_tab)
        from PySide6.QtWidgets import QScrollArea, QStackedWidget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        stack = QStackedWidget()
        stack.addWidget(tab)
        scroll.setWidget(stack)
        scroll.resize(900, 500)
        scroll.show()
        _qwait(100)
        bar = scroll.verticalScrollBar()
        assert bar.maximum() > 0  # 内容超出视口才有意义
        bar.setValue(bar.maximum())
        pos_before = tab._chart_editor_panel.mapTo(tab, tab._chart_editor_panel.rect().topLeft()).y()
        value_before = bar.value()

        editor = tab._chart_editor_panel
        editor._controls["bins"].setValue(40)
        _qwait(320)

        # bins 调整不改变图表高度 → 内容总高不变 → 滚动值不变、编辑器位置不变
        assert bar.value() == value_before
        pos_after = tab._chart_editor_panel.mapTo(tab, tab._chart_editor_panel.rect().topLeft()).y()
        assert pos_after == pos_before

    def test_spc_grid_and_limits_toggles_rerender(self):
        """SPC 控制图：显示网格/显示控制限开关必须真正影响渲染结果"""
        np.random.seed(3)
        df = pd.DataFrame({"v": np.random.normal(50, 2, 120)})
        from ui.tabs.spc_tab import SPCTab
        tab = SPCTab()
        tab.set_data(df, {})
        tab.col_combo.setCurrentText("v")
        tab.subgroup_spin.setValue(5)
        tab.chart_type_combo.setCurrentText("XBar-R")
        tab.run_and_display()
        assert tab.canvas is not None

        def _probe():
            fig = tab.current_figure
            grids = [sum(1 for l in a.get_xgridlines() if l.get_visible()) > 0
                     for a in fig.axes]
            limits = sum(
                1 for a in fig.axes for l in a.lines
                if l.get_label().startswith(("UCL", "LCL", "Steady", "h=", "-h="))
            )
            return grids, limits

        editor = tab._chart_editor_panel
        g0, l0 = _probe()
        assert all(g0) and l0 > 0

        editor._controls["show_grid"].setChecked(False)
        _qwait(350)
        g1, l1 = _probe()
        assert not any(g1) and l1 == l0

        editor._controls["show_limits"].setChecked(False)
        _qwait(350)
        g2, l2 = _probe()
        assert not any(g2) and l2 == 0

        editor._controls["show_grid"].setChecked(True)
        editor._controls["show_limits"].setChecked(True)
        _qwait(350)
        g3, l3 = _probe()
        assert all(g3) and l3 > 0
