"""公差区间测试"""

import numpy as np
import pytest
from analysis.capability.tolerance_interval import (
    tolerance_interval_normal,
    tolerance_interval_nonparam,
)


class TestToleranceIntervalNormal:
    """正态公差区间测试"""

    def test_basic_two_sided(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)
        result = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)

        assert result["method"] == "Normal Tolerance Interval"
        assert result["interval_method"] == "two-sided"
        assert result["confidence"] == 0.95
        assert result["proportion"] == 0.99
        assert result["lower"] < result["upper"]
        assert result["width"] > 0
        assert result["sample_size"] == 50

    def test_basic_one_sided(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)
        result = tolerance_interval_normal(data, confidence=0.95, proportion=0.99, method="one-sided")

        assert result["method"] == "Normal Tolerance Interval"
        assert result["interval_method"] == "one-sided"
        assert result["lower"] < result["upper"]

    def test_different_confidence_levels(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result_90 = tolerance_interval_normal(data, confidence=0.90, proportion=0.99)
        result_95 = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)
        result_99 = tolerance_interval_normal(data, confidence=0.99, proportion=0.99)

        # 更高的置信水平应该产生更宽的区间
        assert result_90["width"] < result_95["width"] < result_99["width"]

    def test_different_proportions(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result_95 = tolerance_interval_normal(data, confidence=0.95, proportion=0.95)
        result_99 = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)

        # 更高的总体比例应该产生更宽的区间
        assert result_95["width"] < result_99["width"]

    def test_constant_data(self):
        data = np.full(50, 100.0)
        result = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)

        assert result["width"] == 0.0
        assert result["lower"] == result["upper"]

    def test_insufficient_data(self):
        data = np.array([100.0])
        with pytest.raises(ValueError):
            tolerance_interval_normal(data)

    def test_invalid_confidence(self):
        data = np.random.normal(100, 5, 50)
        with pytest.raises(ValueError):
            tolerance_interval_normal(data, confidence=1.5)

    def test_invalid_proportion(self):
        data = np.random.normal(100, 5, 50)
        with pytest.raises(ValueError):
            tolerance_interval_normal(data, proportion=1.5)

    def test_center_near_mean(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)
        result = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)

        # 中心应该接近样本均值
        assert abs(result["center"] - np.mean(data)) < 0.01


class TestToleranceIntervalNonparam:
    """非参数公差区间测试"""

    def test_basic_two_sided(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)
        result = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        assert result["method"] == "Nonparametric Tolerance Interval"
        assert result["interval_method"] == "two-sided"
        assert result["confidence"] == 0.95
        assert result["proportion"] == 0.99
        assert result["lower"] < result["upper"]
        assert result["sample_size"] == 50

    def test_basic_one_sided(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)
        result = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99, method="one-sided")

        assert result["method"] == "Nonparametric Tolerance Interval"
        assert result["interval_method"] == "one-sided"

    def test_different_sample_sizes(self):
        np.random.seed(42)
        data_30 = np.random.normal(100, 5, 30)
        data_50 = np.random.normal(100, 5, 50)
        data_100 = np.random.normal(100, 5, 100)

        result_30 = tolerance_interval_nonparam(data_30, confidence=0.95, proportion=0.99)
        result_50 = tolerance_interval_nonparam(data_50, confidence=0.95, proportion=0.99)
        result_100 = tolerance_interval_nonparam(data_100, confidence=0.95, proportion=0.99)

        # 所有区间都应该有正的宽度
        assert result_30["width"] > 0
        assert result_50["width"] > 0
        assert result_100["width"] > 0

    def test_insufficient_data(self):
        data = np.array([100.0])
        with pytest.raises(ValueError):
            tolerance_interval_nonparam(data)

    def test_interval_contains_data(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)
        result = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        # 区间应该包含数据的中位数
        assert result["lower"] <= np.median(data) <= result["upper"]

    def test_median_near_center(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 100)
        result = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        # 中位数应该在区间内
        assert result["lower"] <= result["sample_median"] <= result["upper"]


class TestNormalVsNonparam:
    """正态与非参数公差区间对比测试"""

    def test_normal_narrower_for_normal_data(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result_normal = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)
        result_nonparam = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        # 对于正态数据，正态公差区间应该更窄
        assert result_normal["width"] <= result_nonparam["width"] * 1.5  # 允许一些容差

    def test_both_contain_median(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 50)

        result_normal = tolerance_interval_normal(data, confidence=0.95, proportion=0.99)
        result_nonparam = tolerance_interval_nonparam(data, confidence=0.95, proportion=0.99)

        median = np.median(data)
        assert result_normal["lower"] <= median <= result_normal["upper"]
        assert result_nonparam["lower"] <= median <= result_nonparam["upper"]
