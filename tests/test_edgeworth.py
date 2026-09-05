"""Edgeworth 近似能力分析测试"""
import pytest
import numpy as np
from analysis.capability.edgeworth import (
    analyze,
    _edgeworth_pp,
    _edgeworth_cap_index,
    _edgeworth_interpretation,
)


class TestEdgeworthAnalyze:
    """analyze 函数测试"""

    def test_basic_edgeworth(self):
        """基本 Edgeworth 分析"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = analyze(data, usl=115, lsl=85)

        assert result["chart_type"] == "Edgeworth Approximation"
        assert result["sample_size"] == 100
        assert "mean" in result
        assert "std" in result
        assert "skewness" in result
        assert "kurtosis" in result
        assert "cp_edgeworth" in result
        assert "cpk_edgeworth" in result
        assert "ppm_total" in result

    def test_edgeworth_with_target(self):
        """带目标值的 Edgeworth 分析"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = analyze(data, usl=115, lsl=85, target=100)

        assert result["chart_type"] == "Edgeworth Approximation"
        assert result["usl"] == 115
        assert result["lsl"] == 85

    def test_edgeworth_without_spec(self):
        """无规格限的 Edgeworth 分析"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = analyze(data)

        assert result["chart_type"] == "Edgeworth Approximation"
        assert "error" in result

    def test_edgeworth_insufficient_data(self):
        """数据量不足"""
        data = np.random.normal(100, 5, 10)

        with pytest.raises(ValueError, match="数据量不足"):
            analyze(data, usl=115, lsl=85)

    def test_edgeworth_skewed_data(self):
        """偏态数据的 Edgeworth 分析"""
        np.random.seed(42)
        data = np.random.lognormal(2, 0.5, 200)

        result = analyze(data, usl=20, lsl=2)

        assert result["chart_type"] == "Edgeworth Approximation"
        assert abs(result["skewness"]) > 0.5


class TestEdgeworthPP:
    """Edgeworth 尾部概率测试"""

    def test_pp_standard_normal(self):
        """标准正态分布的尾部概率"""
        pp = _edgeworth_pp(1.96, 0, 0)

        assert abs(pp - 0.025) < 0.01

    def test_pp_with_skewness(self):
        """带偏度的尾部概率"""
        pp = _edgeworth_pp(1.96, 0.5, 0)

        assert 0 < pp < 1

    def test_pp_with_kurtosis(self):
        """带峰度的尾部概率"""
        pp = _edgeworth_pp(1.96, 0, 1)

        assert 0 < pp < 1

    def test_pp_bounded(self):
        """尾部概率在 [0, 1] 范围内"""
        for z in [-3, -2, -1, 0, 1, 2, 3]:
            for skew in [-1, 0, 1]:
                for kurt in [-1, 0, 1]:
                    pp = _edgeworth_pp(z, skew, kurt)
                    assert 0 <= pp <= 1, f"pp={pp} for z={z}, skew={skew}, kurt={kurt}"


class TestEdgeworthCapIndex:
    """Edgeworth 能力指数测试"""

    def test_cap_index_upper(self):
        """上规格限能力指数"""
        cp = _edgeworth_cap_index(115, 85, 100, 5, 0, 0)

        assert cp > 0

    def test_cap_index_lower(self):
        """下规格限能力指数"""
        cp = _edgeworth_cap_index(115, 85, 100, 5, 0, 0, side="lower")

        assert cp > 0

    def test_cap_index_zero_std(self):
        """零标准差"""
        cp = _edgeworth_cap_index(115, 85, 100, 0, 0, 0)

        assert cp == float('inf')


class TestEdgeworthInterpretation:
    """Edgeworth 解释测试"""

    def test_excellent(self):
        """优秀"""
        assert "优秀" in _edgeworth_interpretation(2.0)
        assert "优秀" in _edgeworth_interpretation(1.67)

    def test_good(self):
        """良好"""
        assert "良好" in _edgeworth_interpretation(1.33)

    def test_acceptable(self):
        """可接受"""
        assert "可接受" in _edgeworth_interpretation(1.0)

    def test_marginal(self):
        """边缘"""
        assert "边缘" in _edgeworth_interpretation(0.67)

    def test_poor(self):
        """差"""
        assert "差" in _edgeworth_interpretation(0.5)
