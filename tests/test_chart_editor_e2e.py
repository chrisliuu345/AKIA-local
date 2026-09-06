"""
图表编辑面板 E2E 测试

测试图表参数化、编辑面板、选项持久化完整流程
"""

import numpy as np
from analysis.charts.chart_options import (
    get_default_options, options_to_json, options_from_json,
)
from output.chart_engine import create_pareto_chart, create_pie_chart


class TestPieChartOptions:
    """饼图参数化测试"""

    def test_default_options(self):
        defaults = get_default_options("饼图")
        assert defaults["label_fontsize"] == 11
        assert defaults["min_slice_percent"] == 5
        assert defaults["show_percentage"] is True

    def test_create_pie_with_defaults(self):
        labels = ["A", "B", "C"]
        values = [50, 30, 20]
        fig = create_pie_chart(labels, values, title="测试饼图")
        assert fig is not None
        assert len(fig.axes) > 0

    def test_create_pie_with_custom_options(self):
        labels = ["A", "B", "C", "D", "E"]
        values = [40, 25, 20, 10, 5]
        options = {
            "label_fontsize": 14,
            "min_slice_percent": 8,
            "show_percentage": True,
            "explode_amount": 5,
        }
        fig = create_pie_chart(labels, values, options=options)
        assert fig is not None

    def test_small_slice_merged(self):
        labels = ["大类", "中类", "小类1", "小类2", "小类3"]
        values = [50, 30, 8, 7, 5]
        options = {"min_slice_percent": 10}
        fig = create_pie_chart(labels, values, options=options)
        assert fig is not None
        ax = fig.axes[0]
        assert len(ax.patches) <= 4

    def test_label_position_inside(self):
        labels = ["A", "B", "C"]
        values = [50, 30, 20]
        options = {"label_position": "inside", "show_percentage": False}
        fig = create_pie_chart(labels, values, options=options)
        assert fig is not None

    def test_empty_data(self):
        fig = create_pie_chart([], [], title="空图")
        assert fig is not None


class TestParetoChartOptions:
    """帕累托图参数化测试"""

    def test_default_options(self):
        defaults = get_default_options("帕累托图")
        assert defaults["label_rotation"] == 45
        assert defaults["show_cumulative"] is True
        assert defaults["show_grid"] is True

    def test_create_pareto_with_defaults(self):
        labels = ["缺陷A", "缺陷B", "缺陷C", "缺陷D"]
        values = [45, 30, 15, 10]
        fig = create_pareto_chart(labels, values, title="测试帕累托图")
        assert fig is not None
        assert len(fig.axes) == 2

    def test_create_pareto_with_custom_options(self):
        labels = ["缺陷A", "缺陷B", "缺陷C", "缺陷D"]
        values = [45, 30, 15, 10]
        options = {
            "label_rotation": 0,
            "label_fontsize": 12,
            "show_cumulative": False,
            "show_grid": False,
        }
        fig = create_pareto_chart(labels, values, options=options)
        assert fig is not None
        assert len(fig.axes) == 1

    def test_pareto_no_grid(self):
        labels = ["A", "B", "C"]
        values = [60, 30, 10]
        options = {"show_grid": False}
        fig = create_pareto_chart(labels, values, options=options)
        assert fig is not None


class TestChartOptionsPersistence:
    """图表选项持久化测试"""

    def test_options_to_json(self):
        options = {"label_fontsize": 12, "show_percentage": True}
        json_str = options_to_json(options)
        assert "label_fontsize" in json_str

    def test_options_from_json(self):
        json_str = '{"label_fontsize": 12, "show_percentage": true}'
        options = options_from_json(json_str)
        assert options["label_fontsize"] == 12
        assert options["show_percentage"] is True

    def test_roundtrip(self):
        original = get_default_options("饼图")
        json_str = options_to_json(original)
        restored = options_from_json(json_str)
        assert restored == original

    def test_project_context_chart_options(self):
        from core.project_context import ProjectContext
        ctx = ProjectContext(project_name="test")
        chart_id = "spc_tab_pie"
        options = get_default_options("饼图")
        ctx.set_chart_options(chart_id, options)
        restored = ctx.get_chart_options(chart_id)
        assert restored == options

    def test_project_context_roundtrip(self):
        from core.project_context import ProjectContext
        ctx = ProjectContext(project_name="test")
        ctx.set_chart_options("chart1", {"a": 1, "b": "test"})
        d = ctx.to_dict()
        ctx2 = ProjectContext.from_dict(d)
        assert ctx2.get_chart_options("chart1") == {"a": 1, "b": "test"}


class TestChartEditorWidget:
    """图表编辑面板控件测试"""

    def test_editor_creation(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        assert panel is not None
        assert panel.is_expanded() is True  # 面板常显展开，无折叠
        assert panel._content_frame.isHidden() is False

    def test_editor_set_chart_type(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        panel.set_chart_type("饼图")
        assert panel._current_chart_type == "饼图"
        assert "label_fontsize" in panel._options

    def test_editor_get_options(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        panel.set_chart_type("饼图")
        opts = panel.get_options()
        assert "label_fontsize" in opts
        assert "min_slice_percent" in opts

    def test_editor_set_options(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        panel.set_chart_type("饼图")
        new_opts = {"label_fontsize": 16, "min_slice_percent": 10}
        panel.set_options(new_opts)
        assert panel.get_options()["label_fontsize"] == 16

    def test_editor_always_expanded(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        panel.set_expanded(True)
        assert panel.is_expanded() is True
        panel.set_expanded(False)  # 无折叠能力，保持展开
        assert panel.is_expanded() is True

    def test_editor_float_slider_precision(self):
        from ui.widgets.chart_editor import ChartEditorPanel
        panel = ChartEditorPanel()
        panel.set_chart_type("柱状图")
        slider = panel._controls["bar_width"]
        assert slider.minimum() == 5 and slider.maximum() == 10
        slider.setValue(7)
        assert panel.get_options()["bar_width"] == 0.7
        panel.set_options({"bar_width": 0.5})
        assert slider.value() == 5
        panel.set_chart_type("散点图")
        alpha = panel._controls["point_alpha"]
        alpha.setValue(3)
        assert panel.get_options()["point_alpha"] == 0.3


class TestChartBuilderIntegration:
    """图表构建器集成测试"""

    def test_build_pareto_with_options(self):
        import pandas as pd
        from analysis.charts.chart_generator import BUILDERS

        df = pd.DataFrame({
            "缺陷类型": ["划痕", "气泡", "变色", "变形"],
            "数量": [45, 30, 15, 10],
        })
        data = {"df": df, "columns": ["缺陷类型", "数量"]}
        options = {
            "title": "帕累托图",
            "chart_options": {"label_rotation": 30, "show_cumulative": True},
        }
        fig = BUILDERS["帕累托图"](data, options)
        assert fig is not None

    def test_build_histogram_with_options(self):
        import pandas as pd
        from analysis.charts.chart_generator import BUILDERS

        np.random.seed(42)
        df = pd.DataFrame({"数值": np.random.normal(100, 15, 200)})
        data = {"df": df, "columns": ["数值"]}
        options = {"title": "直方图", "chart_options": {"bins": 15, "show_density": True}}
        fig = BUILDERS["直方图"](data, options)
        assert fig is not None

    def test_build_boxplot_matrix_residual_with_options(self):
        import pandas as pd
        from analysis.charts.chart_generator import BUILDERS

        np.random.seed(42)
        df = pd.DataFrame({
            "A": np.random.normal(100, 15, 80),
            "B": np.random.normal(105, 20, 80),
            "C": np.random.normal(98, 10, 80),
            "预测": np.random.normal(100, 15, 80),
        })
        df["实际"] = df["预测"] + np.random.normal(0, 5, 80)

        box_fig = BUILDERS["箱线图"](
            {"df": df, "columns": ["A", "B", "C"]},
            {"chart_options": {"show_mean": False, "show_grid": False}})
        assert box_fig is not None

        mat_fig = BUILDERS["矩阵图"](
            {"df": df, "columns": ["A", "B", "C"]},
            {"chart_options": {"colormap": "viridis", "show_annotations": False}})
        assert mat_fig is not None

        res_fig = BUILDERS["残差图"](
            {"df": df, "columns": ["实际", "预测"]},
            {"chart_options": {"point_size": 20, "point_alpha": 0.3, "show_grid": False}})
        assert res_fig is not None

        sm_fig = BUILDERS["散点矩阵图"](
            {"df": df, "columns": ["A", "B", "C"]},
            {"chart_options": {"point_size": 15, "show_regression": False}})
        assert sm_fig is not None
