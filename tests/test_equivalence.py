"""TOST 等价检验测试"""
import pytest
import pandas as pd
from analysis.hypothesis.equivalence import one_sample_tost, two_sample_tost


class TestOneSampleTOST:
    """单样本 TOST 等价检验测试"""

    def test_equivalent_data(self):
        """等价数据（差异小）"""
        data = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1])
        result = one_sample_tost(data, target_mean=10.0, margin=0.5)

        assert result["test_type"] == "One-Sample TOST"
        assert result["is_equivalent"]
        assert result["interpretation"] == "等价"

    def test_non_equivalent_data(self):
        """不等价数据（差异大）"""
        data = pd.Series([11.0, 11.1, 10.9, 11.0, 11.1, 10.9, 11.0, 11.1])
        result = one_sample_tost(data, target_mean=10.0, margin=0.5)

        assert not result["is_equivalent"]
        assert result["interpretation"] == "不等价"

    def test_margin_parameter(self):
        """边界参数测试"""
        data = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1])

        # 宽边界 → 等价
        result_wide = one_sample_tost(data, target_mean=10.0, margin=1.0)
        assert result_wide["is_equivalent"]

        # 窄边界 → 可能不等价
        result_narrow = one_sample_tost(data, target_mean=10.0, margin=0.01)
        assert not result_narrow["is_equivalent"]

    def test_insufficient_data(self):
        """数据量不足"""
        data = pd.Series([10.0])
        with pytest.raises(ValueError, match="数据量不足"):
            one_sample_tost(data, target_mean=10.0, margin=0.5)

    def test_ci_includes_zero(self):
        """置信区间包含零"""
        data = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1])
        result = one_sample_tost(data, target_mean=10.0, margin=0.5)

        # 差异应接近 0
        assert abs(result["difference"]) < 0.1
        # 置信区间应包含 0
        assert result["ci_lower"] < 0 < result["ci_upper"]


class TestTwoSampleTOST:
    """双样本 TOST 等价检验测试"""

    def test_equivalent_groups(self):
        """等价组"""
        g1 = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1])
        g2 = pd.Series([10.0, 9.9, 10.1, 10.0, 9.9])
        result = two_sample_tost(g1, g2, margin=0.5)

        assert result["test_type"] == "Two-Sample TOST"
        assert result["is_equivalent"]

    def test_non_equivalent_groups(self):
        """不等价组"""
        g1 = pd.Series([11.0, 11.1, 10.9, 11.0, 11.1])
        g2 = pd.Series([10.0, 9.9, 10.1, 10.0, 9.9])
        result = two_sample_tost(g1, g2, margin=0.5)

        assert not result["is_equivalent"]

    def test_equal_variance(self):
        """等方差假设"""
        g1 = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1])
        g2 = pd.Series([10.0, 9.9, 10.1, 10.0, 9.9])
        result = two_sample_tost(g1, g2, margin=0.5, equal_var=True)

        assert result["equal_variance"]

    def test_welch_correction(self):
        """Welch 校正"""
        g1 = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1])
        g2 = pd.Series([10.0, 9.9, 10.1, 10.0, 9.9])
        result = two_sample_tost(g1, g2, margin=0.5, equal_var=False)

        assert not result["equal_variance"]

    def test_insufficient_data(self):
        """数据量不足"""
        g1 = pd.Series([10.0])
        g2 = pd.Series([10.0, 10.1])
        with pytest.raises(ValueError, match="两组数据量均需"):
            two_sample_tost(g1, g2, margin=0.5)

    def test_p_values(self):
        """P 值测试"""
        g1 = pd.Series([10.0, 10.1, 9.9, 10.0, 10.1, 9.9, 10.0, 10.1])
        g2 = pd.Series([10.0, 9.9, 10.1, 10.0, 9.9, 10.1, 10.0, 9.9])
        result = two_sample_tost(g1, g2, margin=0.5)

        assert 0 <= result["p_value"] <= 1
        assert 0 <= result["p_value_low"] <= 1
        assert 0 <= result["p_value_high"] <= 1
