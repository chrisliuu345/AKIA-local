"""
图表参数定义单元测试
"""

from analysis.charts.chart_options import (
    ChartTypeOptions, SliderOption, RadioOption, CheckboxOption,
    get_chart_options, get_all_chart_types, get_default_options,
    options_to_json, options_from_json,
    PIE_OPTIONS, BAR_OPTIONS, PARETO_OPTIONS, SCATTER_OPTIONS,
    HISTOGRAM_OPTIONS, HEATMAP_OPTIONS, FACETING_OPTIONS,
)


class TestSliderOption:
    def test_creation(self):
        opt = SliderOption("fontsize", "字号", 8, 20, 11, 1, "pt")
        assert opt.key == "fontsize"
        assert opt.label == "字号"
        assert opt.min_val == 8
        assert opt.max_val == 20
        assert opt.default == 11
        assert opt.step == 1
        assert opt.unit == "pt"

    def test_defaults(self):
        opt = SliderOption("test", "Test", 0, 100, 50)
        assert opt.unit == ""


class TestRadioOption:
    def test_creation(self):
        opt = RadioOption("position", "位置", ["inside", "outside"], "outside")
        assert opt.key == "position"
        assert opt.options == ["inside", "outside"]
        assert opt.default == "outside"


class TestCheckboxOption:
    def test_creation(self):
        opt = CheckboxOption("show_grid", "显示网格", True)
        assert opt.key == "show_grid"
        assert opt.default is True


class TestChartTypeOptions:
    def test_get_defaults(self):
        opts = ChartTypeOptions(
            chart_type="test",
            sliders=[SliderOption("a", "A", 0, 10, 5)],
            radios=[RadioOption("b", "B", ["x", "y"], "x")],
            checkboxes=[CheckboxOption("c", "C", True)],
        )
        defaults = opts.get_defaults()
        assert defaults == {"a": 5, "b": "x", "c": True}

    def test_to_dict(self):
        opts = ChartTypeOptions(
            chart_type="test",
            sliders=[SliderOption("a", "A", 0, 10, 5)],
        )
        d = opts.to_dict()
        assert d["chart_type"] == "test"
        assert len(d["sliders"]) == 1
        assert d["sliders"][0]["key"] == "a"


class TestChartOptionsRegistry:
    def test_all_chart_types(self):
        types = get_all_chart_types()
        assert "饼图" in types
        assert "柱状图" in types
        assert "帕累托图" in types
        assert "散点图" in types
        assert "直方图" in types
        assert "箱线图" in types
        assert "矩阵图" in types
        assert "小多图" in types

    def test_get_chart_options(self):
        opts = get_chart_options("饼图")
        assert opts is not None
        assert opts.chart_type == "饼图"
        assert len(opts.sliders) > 0
        assert len(opts.checkboxes) > 0

    def test_get_chart_options_unknown(self):
        opts = get_chart_options("未知图表")
        assert opts is None

    def test_get_default_options(self):
        defaults = get_default_options("饼图")
        assert "label_fontsize" in defaults
        assert "min_slice_percent" in defaults
        assert "show_percentage" in defaults

    def test_get_default_options_unknown(self):
        defaults = get_default_options("未知图表")
        assert defaults == {}


class TestPieOptions:
    def test_has_required_options(self):
        opts = PIE_OPTIONS
        keys = [s.key for s in opts.sliders]
        assert "label_fontsize" in keys
        assert "min_slice_percent" in keys
        assert "explode_amount" in keys

    def test_label_position_options(self):
        opts = PIE_OPTIONS
        radio = [r for r in opts.radios if r.key == "label_position"][0]
        assert "inside" in radio.options
        assert "outside" in radio.options


class TestBarOptions:
    def test_has_rotation_slider(self):
        opts = BAR_OPTIONS
        keys = [s.key for s in opts.sliders]
        assert "label_rotation" in keys
        assert "bar_width" in keys


class TestParetoOptions:
    def test_has_cumulative_checkbox(self):
        opts = PARETO_OPTIONS
        keys = [c.key for c in opts.checkboxes]
        assert "show_cumulative" in keys


class TestScatterOptions:
    def test_has_regression_checkbox(self):
        opts = SCATTER_OPTIONS
        keys = [c.key for c in opts.checkboxes]
        assert "show_regression" in keys
        assert "show_confidence" in keys


class TestHistogramOptions:
    def test_has_bins_slider(self):
        opts = HISTOGRAM_OPTIONS
        keys = [s.key for s in opts.sliders]
        assert "bins" in keys

    def test_has_density_checkbox(self):
        opts = HISTOGRAM_OPTIONS
        keys = [c.key for c in opts.checkboxes]
        assert "show_density" in keys


class TestHeatmapOptions:
    def test_has_colormap_radio(self):
        opts = HEATMAP_OPTIONS
        radio = [r for r in opts.radios if r.key == "colormap"][0]
        assert "RdYlGn_r" in radio.options

    def test_has_significance_checkbox(self):
        opts = HEATMAP_OPTIONS
        keys = [c.key for c in opts.checkboxes]
        assert "show_significance" in keys


class TestFacetingOptions:
    def test_has_facet_mode_radio(self):
        opts = FACETING_OPTIONS
        radio = [r for r in opts.radios if r.key == "facet_mode"][0]
        assert "col" in radio.options
        assert "row" in radio.options
        assert "grid" in radio.options


class TestJsonSerialization:
    def test_options_to_json(self):
        options = {"fontsize": 12, "show_grid": True}
        json_str = options_to_json(options)
        assert "fontsize" in json_str
        assert "12" in json_str

    def test_options_from_json(self):
        json_str = '{"fontsize": 12, "show_grid": true}'
        options = options_from_json(json_str)
        assert options["fontsize"] == 12
        assert options["show_grid"] is True

    def test_roundtrip(self):
        original = {"a": 1, "b": "test", "c": True}
        json_str = options_to_json(original)
        restored = options_from_json(json_str)
        assert restored == original
