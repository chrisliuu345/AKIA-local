"""Capability E2E 测试 — 过程能力分析全流程"""
import numpy as np
import pandas as pd


class TestNormalCapability:
    """正态过程能力分析全流程测试"""

    def test_full_normal_cap(self):
        """完整正态能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        from analysis.capability.normal_cap import analyze
        result = analyze(data, usl=115, lsl=85, target=100, subgroup_size=5)

        assert result["chart_type"] == "Normal Capability"
        assert "summary" in result
        assert "sample_size" in result["summary"]
        assert "mean" in result["summary"]
        assert "std_overall" in result["summary"]
        assert "std_within" in result["summary"]

        if "capability" in result:
            cap = result["capability"]
            assert "cp" in cap
            assert "cpk" in cap
            assert "pp" in cap
            assert "ppk" in cap


class TestNonNormalCapability:
    """非正态过程能力分析全流程测试"""

    def test_full_boxcox_cap(self):
        """完整 Box-Cox 能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(2, 0.5, 100))

        from analysis.capability.non_normal_cap import analyze
        result = analyze(data, usl=20, lsl=2, method="box_cox")

        assert result["chart_type"] == "Non-Normal Capability"
        assert result["method"] == "box_cox"

    def test_full_johnson_cap(self):
        """完整 Johnson 能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(2, 0.5, 100))

        from analysis.capability.non_normal_cap import analyze
        result = analyze(data, usl=20, lsl=2, method="johnson")

        assert result["chart_type"] == "Non-Normal Capability"
        assert result["method"] == "johnson"

    def test_full_percentile_cap(self):
        """完整百分位法能力分析"""
        np.random.seed(42)
        data = pd.Series(np.random.lognormal(2, 0.5, 100))

        from analysis.capability.non_normal_cap import analyze
        result = analyze(data, usl=20, lsl=2, method="percentile")

        assert result["chart_type"] == "Non-Normal Capability"
        assert result["method"] == "percentile"
        assert "percentiles" in result["summary"]


class TestJohnsonTransform:
    """Johnson 变换全流程测试"""

    def test_full_johnson_transform(self):
        """完整 Johnson 变换"""
        np.random.seed(42)
        data = np.random.lognormal(2, 0.5, 100)

        from analysis.capability.johnson_transform import johnson_transform
        result = johnson_transform(data, method="auto")

        assert result["type"] in ["SU", "SB", "SL", "LN", "constant"]
        assert "transformed" in result
        assert "params" in result

    def test_johnson_inverse(self):
        """Johnson 逆变换"""
        np.random.seed(42)
        data = np.random.lognormal(2, 0.5, 100)

        from analysis.capability.johnson_transform import johnson_transform, inverse_transform
        transform_result = johnson_transform(data, method="auto")
        transformed = transform_result["transformed"]
        params = transform_result["params"]
        j_type = transform_result["type"]

        if j_type not in ("constant", "LN"):
            inverse_result = inverse_transform(transformed, j_type, params)
            assert len(inverse_result) == len(data)
            np.testing.assert_allclose(inverse_result, data, rtol=1e-5)


class TestToleranceInterval:
    """公差区间全流程测试"""

    def test_full_normal_tolerance(self):
        """完整正态公差区间"""
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        from analysis.capability.tolerance_interval import tolerance_interval_normal
        result = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)

        assert result["method"] == "Normal Tolerance Interval"
        assert result["confidence"] == 0.95
        assert result["proportion"] == 0.99
        assert result["lower"] < result["upper"]
        assert result["width"] > 0

    def test_full_nonparam_tolerance(self):
        """完整非参数公差区间"""
        np.random.seed(42)
        data = np.random.exponential(2, 50)

        from analysis.capability.tolerance_interval import tolerance_interval_nonparam
        result = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        assert result["method"] == "Nonparametric Tolerance Interval"
        assert result["confidence"] == 0.95
        assert result["proportion"] == 0.99
        assert result["lower"] < result["upper"]


class TestDistributionFitting:
    """分布拟合全流程测试"""

    def test_full_normal_fit(self):
        """完整正态分布拟合"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(100, 5, 100))

        from analysis.distribution.fitting import fit_distribution, goodness_of_fit
        fit_result = fit_distribution(data, "normal")
        gof_result = goodness_of_fit(data, "normal")

        assert "params" in fit_result
        assert "distribution" in fit_result
        assert "tests" in gof_result
        assert "kolmogorov_smirnov" in gof_result["tests"]
