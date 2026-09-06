"""卡方检验与比例检验测试"""
import pytest
import pandas as pd
from analysis.hypothesis.proportion import (
    chi_square_gof,
    chi_square_independence,
    two_proportion_test,
)


class TestChiSquareGOF:
    """卡方拟合优度检验测试"""

    def test_uniform_distribution(self):
        """均匀分布检验"""
        observed = pd.Series([10, 12, 8, 10, 11, 9])
        result = chi_square_gof(observed)

        assert result["test_type"] == "Chi-Square Goodness of Fit"
        assert result["categories"] == 6
        assert result["df"] == 5
        assert "chi2_statistic" in result
        assert "p_value" in result

    def test_expected_frequencies(self):
        """指定期望频数"""
        observed = pd.Series([50, 30, 20])
        expected = pd.Series([40, 40, 20])
        result = chi_square_gof(observed, expected=expected)

        assert result["categories"] == 3
        assert result["total_count"] == 100

    def test_probabilities(self):
        """指定概率"""
        observed = pd.Series([100, 50, 50])
        probabilities = [0.5, 0.25, 0.25]
        result = chi_square_gof(observed, probabilities=probabilities)

        assert result["categories"] == 3

    def test_insufficient_categories(self):
        """类别数不足"""
        observed = pd.Series([10])
        with pytest.raises(ValueError, match="类别数不足"):
            chi_square_gof(observed)

    def test_zero_total(self):
        """频数总和为零"""
        observed = pd.Series([0, 0, 0])
        with pytest.raises(ValueError, match="频数总和必须大于"):
            chi_square_gof(observed)


class TestChiSquareIndependence:
    """卡方独立性检验测试"""

    def test_basic_independence(self):
        """基本独立性检验"""
        data = pd.DataFrame({
            "Gender": ["M", "M", "M", "F", "F", "F", "M", "M", "F", "F"] * 10,
            "Preference": ["A", "B", "A", "B", "A", "A", "B", "A", "B", "B"] * 10,
        })
        result = chi_square_independence(data, "Gender", "Preference")

        assert result["test_type"] == "Chi-Square Test of Independence"
        assert "contingency_table" in result
        assert "chi2_statistic" in result
        assert "cramers_v" in result

    def test_strong_association(self):
        """强关联性"""
        # 构建强关联数据
        data = pd.DataFrame({
            "A": ["X"] * 50 + ["Y"] * 50,
            "B": ["P"] * 50 + ["Q"] * 50,
        })
        result = chi_square_independence(data, "A", "B")

        assert result["cramers_v"] > 0.9
        assert result["is_significant"]


class TestTwoProportionTest:
    """双样本比例检验测试"""

    def test_basic_two_proportion(self):
        """基本双样本比例检验"""
        result = two_proportion_test(30, 100, 20, 100)

        assert result["test_type"] == "Two-Proportion Z-Test"
        assert result["group1"]["proportion"] == 0.3
        assert result["group2"]["proportion"] == 0.2
        assert result["difference"] == 0.1

    def test_equal_proportions(self):
        """相同比例"""
        result = two_proportion_test(50, 100, 50, 100)

        assert abs(result["difference"]) < 0.001
        assert result["p_value"] > 0.05

    def test_one_sided_greater(self):
        """单侧检验（大于）"""
        result = two_proportion_test(40, 100, 20, 100, alternative="greater")

        assert result["alternative"] == "greater"
        assert result["is_significant"]

    def test_one_sided_less(self):
        """单侧检验（小于）"""
        result = two_proportion_test(20, 100, 40, 100, alternative="less")

        assert result["alternative"] == "less"
        assert result["is_significant"]

    def test_invalid_sample_size(self):
        """无效样本量"""
        with pytest.raises(ValueError, match="样本量必须大于"):
            two_proportion_test(10, 0, 10, 100)

    def test_invalid_successes(self):
        """无效成功数"""
        with pytest.raises(ValueError, match="成功数不能超过"):
            two_proportion_test(150, 100, 10, 100)
