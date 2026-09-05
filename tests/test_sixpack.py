"""Capability Sixpack 测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.capability.sixpack import (
    analyze,
    _estimate_within_sigma,
    _control_chart_data,
    _histogram_data,
    _probability_plot_data,
    _statistics_data,
    _percent_defective_data,
    _capability_plot_data,
    _capability_grade,
)


class TestSixpackAnalyze:
    """analyze 函数测试"""

    def test_basic_sixpack(self):
        """基本 Sixpack 分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        result = analyze(data, usl=115, lsl=85, target=100, subgroup_size=1)

        assert result["chart_type"] == "Capability Sixpack"
        assert "summary" in result
        assert "control_chart" in result
        assert "histogram" in result
        assert "probability_plot" in result
        assert "statistics" in result
        assert "percent_defective" in result
        assert "capability_plot" in result

    def test_sixpack_with_subgroup(self):
        """带子组的 Sixpack 分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        result = analyze(data, usl=115, lsl=85, subgroup_size=5)

        assert result["control_chart"]["type"] == "Xbar-R"
        assert "xbar" in result["control_chart"]
        assert "range" in result["control_chart"]

    def test_sixpack_individual(self):
        """Individual 控制图"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 50))

        result = analyze(data, usl=115, lsl=85, subgroup_size=1)

        assert result["control_chart"]["type"] == "I-MR"
        assert "individual" in result["control_chart"]
        assert "moving_range" in result["control_chart"]

    def test_sixpack_without_spec(self):
        """无规格限的 Sixpack"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        result = analyze(data, subgroup_size=1)

        assert result["chart_type"] == "Capability Sixpack"
        assert result["percent_defective"]["ppm_total"] == 0

    def test_sixpack_insufficient_data(self):
        """数据量不足"""
        data = pd.Series([1, 2, 3])

        with pytest.raises(ValueError, match="数据量不足"):
            analyze(data, usl=10, lsl=0)


class TestControlChartData:
    """控制图数据测试"""

    def test_imr_control_chart(self):
        """I-MR 控制图数据"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result = _control_chart_data(data, subgroup_size=1)

        assert result["type"] == "I-MR"
        assert len(result["individual"]["data"]) == 50
        assert result["individual"]["ucl"] > result["individual"]["center"]
        assert result["individual"]["lcl"] < result["individual"]["center"]

    def test_xbar_r_control_chart(self):
        """Xbar-R 控制图数据"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _control_chart_data(data, subgroup_size=5)

        assert result["type"] == "Xbar-R"
        assert len(result["xbar"]["data"]) == 20
        assert result["xbar"]["ucl"] > result["xbar"]["center"]


class TestHistogramData:
    """直方图数据测试"""

    def test_histogram_basic(self):
        """基本直方图数据"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _histogram_data(data, usl=115, lsl=85, mean=100, std=5)

        assert "counts" in result
        assert "bin_edges" in result
        assert "x_range" in result
        assert "normal_curve" in result
        assert result["usl"] == 115
        assert result["lsl"] == 85


class TestProbabilityPlotData:
    """概率图数据测试"""

    def test_probability_plot_basic(self):
        """基本概率图数据"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _probability_plot_data(data, mean=100, std=5)

        assert "observed" in result
        assert "theoretical" in result
        assert "ks_statistic" in result
        assert "ks_p_value" in result
        assert "is_normal" in result
        assert len(result["observed"]) == 100


class TestStatisticsData:
    """统计量数据测试"""

    def test_statistics_with_spec(self):
        """带规格限的统计量"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _statistics_data(data, 100, 5, 5, 115, 85, 100, 1)

        assert "cp" in result
        assert "cpk" in result
        assert "pp" in result
        assert "ppk" in result
        assert "grade" in result

    def test_statistics_without_spec(self):
        """无规格限的统计量"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _statistics_data(data, 100, 5, 5, None, None, None, 1)

        assert "cp" not in result
        assert "cpk" not in result


class TestPercentDefectiveData:
    """不合格品率数据测试"""

    def test_percent_defective_with_spec(self):
        """带规格限的不合格品率"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _percent_defective_data(data, usl=115, lsl=85, mean=100, std=5)

        assert "ppm_total" in result
        assert "pct_total" in result
        assert result["ppm_total"] >= 0

    def test_percent_defective_without_spec(self):
        """无规格限的不合格品率"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _percent_defective_data(data, usl=None, lsl=None, mean=100, std=5)

        assert result["ppm_total"] == 0
        assert result["pct_total"] == 0


class TestCapabilityPlotData:
    """能力图数据测试"""

    def test_capability_plot_basic(self):
        """基本能力图数据"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _capability_plot_data(data, usl=115, lsl=85, mean=100, std_within=5, std_overall=5)

        assert "indices" in result
        assert "values" in result
        assert len(result["indices"]) == 4
        assert len(result["values"]) == 4
        assert result["indices"] == ["Cp", "Cpk", "Pp", "Ppk"]


class TestCapabilityGrade:
    """能力等级测试"""

    def test_grade_a_plus(self):
        """A+ 等级"""
        assert _capability_grade(1.67) == "A+ (优秀)"
        assert _capability_grade(2.0) == "A+ (优秀)"

    def test_grade_a(self):
        """A 等级"""
        assert _capability_grade(1.33) == "A (良好)"
        assert _capability_grade(1.5) == "A (良好)"

    def test_grade_b(self):
        """B 等级"""
        assert _capability_grade(1.0) == "B (可接受)"
        assert _capability_grade(1.2) == "B (可接受)"

    def test_grade_c(self):
        """C 等级"""
        assert _capability_grade(0.67) == "C (边缘)"
        assert _capability_grade(0.8) == "C (边缘)"

    def test_grade_d(self):
        """D 等级"""
        assert _capability_grade(0.5) == "D (差)"
        assert _capability_grade(0.0) == "D (差)"


class TestEstimateWithinSigma:
    """组内标准差估计测试"""

    def test_individual_mr(self):
        """Individual-MR 方法"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result = _estimate_within_sigma(data, subgroup_size=1)

        assert result > 0
        assert abs(result - 5) < 1

    def test_xbar_r(self):
        """Xbar-R 方法"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _estimate_within_sigma(data, subgroup_size=5)

        assert result > 0
        assert abs(result - 5) < 1
