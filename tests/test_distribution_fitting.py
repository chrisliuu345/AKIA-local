"""分布拟合分析测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.distribution.fitting import (
    fit_distribution,
    goodness_of_fit,
    compare_distributions,
    SUPPORTED_DISTRIBUTIONS,
)


class TestFitDistribution:
    """分布拟合测试"""

    def test_normal_fit(self):
        """正态分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(5, 2, 100))
        result = fit_distribution(data, "normal")

        assert result["distribution"] == "normal"
        assert "mu" in result["params"]
        assert "sigma" in result["params"]
        assert abs(result["params"]["mu"] - 5) < 1

    def test_lognormal_fit(self):
        """对数正态分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(0, 0.5, 100))
        result = fit_distribution(data, "lognormal")

        assert result["distribution"] == "lognormal"
        assert "shape" in result["params"]

    def test_exponential_fit(self):
        """指数分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.exponential(2, 100))
        result = fit_distribution(data, "exponential")

        assert result["distribution"] == "exponential"
        assert "scale" in result["params"]

    def test_gamma_fit(self):
        """Gamma 分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.gamma(2, 1, 100))
        result = fit_distribution(data, "gamma")

        assert result["distribution"] == "gamma"
        assert "a" in result["params"]

    def test_weibull_fit(self):
        """Weibull 分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.weibull(2, 100))
        result = fit_distribution(data, "weibull")

        assert result["distribution"] == "weibull"
        assert "c" in result["params"]

    def test_insufficient_data(self):
        """数据量不足"""
        data = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="数据量不足"):
            fit_distribution(data, "normal")

    def test_unsupported_distribution(self):
        """不支持的分布"""
        data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        with pytest.raises(ValueError, match="不支持的分布"):
            fit_distribution(data, "invalid_dist")

    def test_negative_data_lognormal(self):
        """负数数据对数正态拟合（自动偏移）"""
        data = pd.Series([-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0])
        result = fit_distribution(data, "lognormal")

        assert result["params"]["shift"] > 0


class TestGoodnessOfFit:
    """拟合优度检验测试"""

    def test_normal_gof(self):
        """正态分布拟合优度"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = goodness_of_fit(data, "normal")

        assert result["distribution"] == "normal"
        assert "anderson_darling" in result["tests"]
        assert "kolmogorov_smirnov" in result["tests"]
        assert "chi_square" in result["tests"]

    def test_ks_test_structure(self):
        """KS 检验结构"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = goodness_of_fit(data, "normal", tests=["ks"])

        ks = result["tests"]["kolmogorov_smirnov"]
        assert "statistic" in ks
        assert "p_value" in ks
        assert 0 <= ks["p_value"] <= 1

    def test_chi2_test_structure(self):
        """卡方检验结构"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = goodness_of_fit(data, "normal", tests=["chi2"])

        chi2 = result["tests"]["chi_square"]
        assert "statistic" in chi2
        assert "df" in chi2
        assert "p_value" in chi2


class TestCompareDistributions:
    """分布比较测试"""

    def test_compare_all(self):
        """比较所有分布"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = compare_distributions(data)

        assert "comparisons" in result
        assert "best_fit" in result
        assert len(result["comparisons"]) == len(SUPPORTED_DISTRIBUTIONS)

    def test_compare_specific(self):
        """比较指定分布"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = compare_distributions(data, distributions=["normal", "exponential"])

        assert len(result["comparisons"]) == 2

    def test_best_fit_selection(self):
        """最佳拟合选择"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 200))
        result = compare_distributions(data)

        # 正态分布应该拟合最好
        assert result["best_fit"]["distribution"] == "normal"

    def test_aic_bic_calculation(self):
        """AIC/BIC 计算"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(0, 1, 100))
        result = compare_distributions(data, distributions=["normal"])

        normal_result = result["comparisons"][0]
        assert "aic" in normal_result
        assert "bic" in normal_result
        assert normal_result["aic"] < normal_result["bic"]


class TestSupportedDistributions:
    """支持的分布列表"""

    def test_supported_list(self):
        """支持的分布列表"""
        assert "normal" in SUPPORTED_DISTRIBUTIONS
        assert "lognormal" in SUPPORTED_DISTRIBUTIONS
        assert "exponential" in SUPPORTED_DISTRIBUTIONS
        assert "gamma" in SUPPORTED_DISTRIBUTIONS
        assert "weibull" in SUPPORTED_DISTRIBUTIONS
