"""自动能力分析测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.capability.auto_cap import (
    analyze,
    _fit_all_distributions,
    _select_best_distribution,
    _select_transform,
    _calculate_capability,
    _capability_grade,
)


class TestAutoCapAnalyze:
    """analyze 函数测试"""

    def test_basic_auto_cap(self):
        """基本自动能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 200))

        result = analyze(data, usl=115, lsl=85, target=100)

        assert result["chart_type"] == "Auto Capability Analysis"
        assert result["sample_size"] == 200
        assert "best_distribution" in result
        assert "fit_results" in result
        assert "transform" in result
        assert "capability" in result

    def test_auto_cap_lognormal(self):
        """对数正态分布自动能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(2, 0.5, 200))

        result = analyze(data, usl=20, lsl=2)

        assert result["chart_type"] == "Auto Capability Analysis"
        assert "best_distribution" in result
        assert result["best_distribution"]["distribution"] in ["lognormal", "normal"]

    def test_auto_cap_without_spec(self):
        """无规格限的自动能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        result = analyze(data)

        assert result["chart_type"] == "Auto Capability Analysis"
        assert "error" in result["capability"]

    def test_auto_cap_insufficient_data(self):
        """数据量不足"""
        data = pd.Series([1, 2, 3, 4, 5])

        with pytest.raises(ValueError, match="数据量不足"):
            analyze(data, usl=10, lsl=0)


class TestFitDistributions:
    """分布拟合测试"""

    def test_fit_all_distributions(self):
        """拟合所有分布"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        results = _fit_all_distributions(data)

        assert len(results) > 0
        assert all("distribution" in r for r in results)
        assert all("aic" in r for r in results)
        assert all("bic" in r for r in results)

    def test_fit_results_sorted_by_aic(self):
        """拟合结果按 AIC 排序"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        results = _fit_all_distributions(data)

        aics = [r["aic"] for r in results]
        assert aics == sorted(aics)


class TestSelectBestDistribution:
    """选择最佳分布测试"""

    def test_select_best(self):
        """选择最佳分布"""
        fit_results = [
            {"distribution": "normal", "name": "正态", "params": (100, 5), "aic": 500, "bic": 510, "ks_statistic": 0.05, "ks_p_value": 0.8},
            {"distribution": "lognormal", "name": "对数正态", "params": (2, 0.5), "aic": 600, "bic": 610, "ks_statistic": 0.1, "ks_p_value": 0.5},
        ]

        best = _select_best_distribution(fit_results)

        assert best["distribution"] == "normal"
        assert best["aic"] == 500

    def test_select_best_empty(self):
        """空结果选择最佳分布"""
        best = _select_best_distribution([])

        assert best["distribution"] == "normal"
        assert best["aic"] == float('inf')


class TestSelectTransform:
    """选择变换测试"""

    def test_select_transform_normal(self):
        """正态数据选择无变换"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        result = _select_transform(data)

        assert result["method"] == "none"

    def test_select_transform_skewed(self):
        """偏态数据选择 Box-Cox"""
        np.random.seed(42)
        data = np.random.lognormal(2, 0.5, 100)

        result = _select_transform(data)

        assert result["method"] in ["boxcox", "boxcox_inverse", "none"]


class TestCalculateCapability:
    """计算能力指数测试"""

    def test_calculate_capability(self):
        """计算能力指数"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)

        transform_result = {"method": "none", "transformed": data, "params": {}, "skewness": 0, "kurtosis": 0}
        best_dist = {"distribution": "normal", "name": "正态", "params": (100, 5), "aic": 500, "bic": 510, "ks_statistic": 0.05, "ks_p_value": 0.8}

        result = _calculate_capability(data, 115, 85, 100, transform_result, best_dist)

        assert "cp" in result
        assert "cpk" in result
        assert "ppm_total" in result
        assert "grade" in result


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
