"""v4.1.0 B1 — 统一图表风格层（output/chart_style.py）与两入口一致性。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
import matplotlib.colors

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from output import chart_style
from output.chart_engine import (
    create_capability_chart,
    create_control_chart,
    create_correlation_heatmap,
    create_histogram,
    create_pareto_chart,
    create_pie_chart,
)


@pytest.fixture(autouse=True)
def _reset_style():
    yield
    chart_style.apply_chart_style(chart_style.THEME_DARK)
    plt.close("all")


def _apply(theme):
    chart_style.apply_chart_style(theme)
    return chart_style.semantic(theme)


# ---------------- 主题与 rcParams ----------------

class TestThemeAndRcParams:

    def test_dark_and_light_semantic_sets(self):
        dark = chart_style.semantic(chart_style.THEME_DARK)
        light = chart_style.semantic(chart_style.THEME_LIGHT)
        assert dark["figure_bg"] != light["figure_bg"]
        assert dark["text"] != light["text"]
        for key in ("data", "center", "limit", "spec", "fit", "violation"):
            assert key in dark and key in light
        # 语义色必须互不相同：控制限 / 规格限 / 拟合线不能再同色
        assert len({dark["data"], dark["center"], dark["limit"],
                    dark["spec"], dark["fit"]}) == 5

    def test_apply_sets_unified_rcparams(self):
        _apply(chart_style.THEME_DARK)
        rc = plt.rcParams
        assert rc["axes.grid"] is True
        assert rc["axes.spines.top"] is False
        assert rc["axes.spines.right"] is False
        assert rc["legend.frameon"] is False
        assert float(rc["axes.titlesize"]) >= 14
        cycle = list(rc["axes.prop_cycle"])
        assert cycle and all(entry["color"].upper() in
                             [c.upper() for c in chart_style.PALETTE]
                             for entry in cycle)
        # 不得残留 matplotlib 默认色 #ff7f0e / #2ca02c 等
        assert all(entry["color"].upper() not in ("#FF7F0E", "#2CA02C", "#1F77B4")
                   for entry in cycle)

    def test_theme_switch_changes_facecolors(self):
        _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        assert ax.get_facecolor()[:3] != (1.0, 1.0, 1.0)
        plt.close(fig)

        light = chart_style.semantic(chart_style.THEME_LIGHT)
        _apply(chart_style.THEME_LIGHT)
        fig, ax = plt.subplots()
        assert plt.rcParams["figure.facecolor"] == light["figure_bg"]
        assert plt.rcParams["axes.facecolor"] == light["panel"]
        plt.close(fig)

    def test_current_theme_from_settings(self, monkeypatch):
        import config.settings as settings
        monkeypatch.setattr(settings, "get_effective",
                            lambda key, default=None: "light")
        assert chart_style.current_theme() == chart_style.THEME_LIGHT

    def test_palette_cycles_when_more_colors_than_palette(self):
        colors = chart_style.palette(len(chart_style.PALETTE) + 3)
        assert len(colors) == len(chart_style.PALETTE) + 3
        assert colors[0] == colors[len(chart_style.PALETTE)]


# ---------------- 工具函数 ----------------

class TestHelpers:

    def test_smart_ylim_keeps_flat_series_visible(self):
        _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        values = np.full(50, 10.0) + np.linspace(-0.05, 0.05, 50)
        lo, hi = chart_style.smart_ylim(ax, values)
        assert lo > 9.0 and hi < 11.0          # 不再 0 锚定
        assert hi - lo < 1.0
        plt.close(fig)

    def test_smart_ylim_include_zero_for_bars(self):
        _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        lo, _hi = chart_style.smart_ylim(ax, [3, 5, 4], include_zero=True)
        assert lo == 0.0
        plt.close(fig)

    def test_smart_ylim_empty_values(self):
        _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        assert chart_style.smart_ylim(ax, []) is None
        plt.close(fig)

    def test_add_limit_lines_semantics(self):
        s = _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        values = chart_style.add_limit_lines(ax, cl=10.0, ucl=10.3, lcl=9.7,
                                             usl=10.5, lsl=9.5)
        assert sorted(values) == [9.5, 9.7, 10.0, 10.3, 10.5]
        line_colors = [line.get_color() for line in ax.lines]
        assert s["limit"] in line_colors and s["spec"] in line_colors
        labels = [line.get_label() for line in ax.lines]
        assert any(label.startswith("UCL") for label in labels)
        assert any(label.startswith("USL") for label in labels)
        plt.close(fig)

    def test_vertical_limit_lines(self):
        _apply(chart_style.THEME_LIGHT)
        fig, ax = plt.subplots()
        values = chart_style.add_limit_lines(ax, usl=10.5, lsl=9.5, orientation="v")
        assert sorted(values) == [9.5, 10.5]
        assert len(ax.lines) == 2
        plt.close(fig)

    def test_mark_violations_hollow_ring(self):
        s = _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        chart_style.mark_violations(ax, [3, 7], [10.4, 9.6], annotate=["规则1", "规则2"])
        assert len(ax.lines) == 1
        assert ax.lines[0].get_markerfacecolor() in ("none", (0, 0, 0, 0))
        assert ax.lines[0].get_markeredgecolor() == s["violation"]
        assert len(ax.texts) == 2
        plt.close(fig)

    def test_style_for_export_switches_to_light(self):
        _apply(chart_style.THEME_DARK)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 2, 3])
        chart_style.style_for_export(fig, theme=chart_style.THEME_LIGHT)
        light = chart_style.semantic(chart_style.THEME_LIGHT)
        assert matplotlib.colors.to_hex(fig.get_facecolor()).lower() == \
            light["figure_bg"].lower()
        plt.close(fig)


# ---------------- 两入口一致性 ----------------

def _assert_unified(fig, theme=chart_style.THEME_DARK):
    s = chart_style.semantic(theme)
    axes = [ax for ax in fig.get_axes()
            if ax.get_visible() and ax.get_label() != "<colorbar>"]
    assert axes, "图形应至少包含一个坐标轴"
    for ax in axes:
        face = matplotlib.colors.to_hex(ax.get_facecolor())
        assert face.lower() == s["panel"].lower(), f"子图背景未统一: {face}"
        if ax.spines:
            for side in ("top", "right"):
                if side in ax.spines:
                    assert not ax.spines[side].get_visible(), f"{side} 脊线应隐藏"


class TestChartEntryPoints:

    def _control_data(self):
        rng = np.random.default_rng(3)
        xbar = list(rng.normal(10, 0.08, 25))
        rr = list(rng.normal(0.5, 0.05, 25))
        return {"chart_type": "XBar-R",
                "xbar_chart": {"data": xbar, "cl": 10.0, "ucl": 10.25, "lcl": 9.75,
                               "violations": [{"point": 20, "rule": "1"}]},
                "r_chart": {"data": rr, "cl": 0.5, "ucl": 0.9, "lcl": 0.1,
                            "violations": []},
                "spec": {"usl": 10.5, "lsl": 9.5}}

    def test_control_chart_uses_unified_style(self):
        _apply(chart_style.THEME_DARK)
        fig = create_control_chart(self._control_data(), title="控制图")
        _assert_unified(fig)
        labels = [line.get_label() for ax in fig.get_axes() for line in ax.lines]
        assert any(lbl.startswith("USL") for lbl in labels)   # 规格限已绘制
        plt.close(fig)

    def test_capability_histogram_pareto_pie(self):
        _apply(chart_style.THEME_DARK)
        rng = np.random.default_rng(5)
        values = rng.normal(10, 0.12, 80)
        cap = {"summary": {"mean": float(values.mean()),
                           "std_overall": float(values.std(ddof=1))},
               "capability": {"cp": 1.4, "cpk": 1.1, "usl": 10.5, "lsl": 9.5,
                              "ppm_total": 1200}}
        for fig in (create_capability_chart(cap, values, title="能力"),
                    create_histogram(values, title="直方图"),
                    create_pareto_chart(["A", "B", "C"], [10, 6, 3], title="帕累托"),
                    create_pie_chart(["A", "B"], [70, 30], title="饼图")):
            _assert_unified(fig)
            plt.close(fig)

    def test_heatmap_uses_diverging_map_and_masked_diagonal(self):
        _apply(chart_style.THEME_DARK)
        rng = np.random.default_rng(7)
        df = pd.DataFrame({"a": rng.normal(size=40), "b": rng.normal(size=40),
                           "c": rng.normal(size=40)})
        fig = create_correlation_heatmap(df, ["a", "b", "c"], title="相关矩阵")
        _assert_unified(fig)
        plt.close(fig)

    def test_gallery_builders_share_style(self):
        from analysis.charts.chart_generator import generate_chart

        _apply(chart_style.THEME_DARK)
        rng = np.random.default_rng(11)
        df = pd.DataFrame({
            "x": rng.normal(size=60), "y": rng.normal(size=60),
            "z": rng.normal(size=60), "g": rng.choice(["A", "B"], 60),
            "日期": pd.date_range("2026-01-01", periods=60, freq="D"),
        })
        cases = [
            ("直方图", {"df": df, "columns": ["x"]}),
            ("箱线图", {"df": df, "columns": ["x", "y"]}),
            ("散点图", {"df": df, "columns": ["x", "y"]}),
            ("时间序列图", {"df": df, "columns": ["日期", "x"]}),
            ("帕累托图", {"df": df.assign(cat=["A", "B", "C"] * 20),
                        "columns": ["cat", "x"]}),
            ("矩阵图", {"df": df, "columns": ["x", "y", "z"]}),
            ("散点矩阵图", {"df": df, "columns": ["x", "y", "z"]}),
            ("小多图", {"df": df, "columns": ["x", "g"]}),
            ("概率图", {"df": df, "columns": ["x"]}),
            ("瀑布图", {"df": df.assign(cat=["A", "B", "C"] * 20),
                       "columns": ["cat", "x"]}),
        ]
        for chart_type, data in cases:
            fig = generate_chart(chart_type, data, {"dark_mode": True,
                                                    "title": chart_type})
            try:
                _assert_unified(fig)
            finally:
                plt.close(fig)
