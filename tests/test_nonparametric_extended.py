"""扩展非参数检验测试 — Mood中位数检验 + Friedman检验"""

import numpy as np
import pytest
from analysis.hypothesis.nonparametric import mood_median_test, friedman_test


class TestMoodMedianTest:
    """Mood 中位数检验测试"""

    def test_basic_mood_median(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)
        c = np.random.normal(110, 5, 30)
        result = mood_median_test(a, b, c)

        assert result["test"] == "Mood's Median"
        assert result["n_groups"] == 3
        assert result["n_total"] == 90
        assert "p_value" in result
        assert "chi2_statistic" in result
        assert "significant" in result

    def test_mood_median_two_groups(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)
        result = mood_median_test(a, b)

        assert result["test"] == "Mood's Median"
        assert result["n_groups"] == 2

    def test_mood_median_identical_groups(self):
        np.random.seed(42)
        data = np.random.normal(100, 5, 30)
        result = mood_median_test(data, data.copy())

        assert result["test"] == "Mood's Median"
        assert result["significant"] == False

    def test_mood_median_different_medians(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 50)
        b = np.random.normal(120, 5, 50)  # 明显不同的中位数
        result = mood_median_test(a, b)

        assert result["test"] == "Mood's Median"
        assert result["significant"] == True

    def test_mood_median_with_nan(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)
        a[5] = np.nan
        b[10] = np.nan
        result = mood_median_test(a, b)

        assert result["test"] == "Mood's Median"
        assert result["n_total"] == 58

    def test_mood_median_insufficient_groups(self):
        data = np.random.normal(100, 5, 30)
        result = mood_median_test(data)

        assert "error" in result

    def test_mood_median_single_group(self):
        data = np.random.normal(100, 5, 30)
        result = mood_median_test(data)

        assert "error" in result

    def test_mood_median_medians_calculation(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)
        result = mood_median_test(a, b)

        assert len(result["group_medians"]) == 2
        assert result["group_medians"][0] < result["group_medians"][1]

    def test_mood_median_contingency_table(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)
        result = mood_median_test(a, b)

        assert "contingency_table" in result
        contingency = np.array(result["contingency_table"])
        assert contingency.shape[0] == 2  # 2组
        assert contingency.shape[1] == 2  # 大于/小于中位数


class TestFriedmanTest:
    """Friedman 检验测试"""

    def test_basic_friedman(self):
        np.random.seed(42)
        # 完全区组设计：10个受试者，3种处理
        n_subjects = 10
        a = np.random.normal(100, 5, n_subjects)
        b = np.random.normal(105, 5, n_subjects)
        c = np.random.normal(110, 5, n_subjects)
        result = friedman_test(a, b, c)

        assert result["test"] == "Friedman"
        assert result["n_blocks"] == n_subjects
        assert result["n_treatments"] == 3
        assert result["n_total"] == 30
        assert "p_value" in result
        assert "chi2_statistic" in result
        assert "mean_ranks" in result
        assert "significant" in result

    def test_friedman_two_treatments(self):
        np.random.seed(42)
        n_subjects = 15
        a = np.random.normal(100, 5, n_subjects)
        b = np.random.normal(105, 5, n_subjects)
        result = friedman_test(a, b)

        assert "Friedman" in result["test"]
        assert result["n_treatments"] == 2

    def test_friedman_identical_treatments(self):
        np.random.seed(42)
        n_subjects = 10
        data = np.random.normal(100, 5, n_subjects)
        result = friedman_test(data, data.copy(), data.copy())

        assert result["test"] == "Friedman"
        assert result["significant"] == False

    def test_friedman_different_treatments(self):
        np.random.seed(42)
        n_subjects = 20
        a = np.random.normal(100, 5, n_subjects)
        b = np.random.normal(110, 5, n_subjects)  # 明显不同
        c = np.random.normal(120, 5, n_subjects)  # 明显不同
        result = friedman_test(a, b, c)

        assert result["test"] == "Friedman"
        assert result["significant"] == True

    def test_friedman_with_nan(self):
        np.random.seed(42)
        n_subjects = 10
        a = np.random.normal(100, 5, n_subjects)
        b = np.random.normal(105, 5, n_subjects)
        a[2] = np.nan
        b[5] = np.nan
        result = friedman_test(a, b)

        assert "Friedman" in result["test"]
        # NaN会被过滤，样本量减少

    def test_friedman_insufficient_groups(self):
        data = np.random.normal(100, 5, 10)
        result = friedman_test(data)

        assert "error" in result

    def test_friedman_unequal_sample_sizes(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 10)
        b = np.random.normal(105, 5, 15)  # 不同样本量
        result = friedman_test(a, b)

        assert "error" in result  # 完全区组设计要求相同样本量

    def test_friedman_mean_ranks(self):
        np.random.seed(42)
        n_subjects = 10
        a = np.random.normal(100, 5, n_subjects)
        b = np.random.normal(105, 5, n_subjects)
        c = np.random.normal(110, 5, n_subjects)
        result = friedman_test(a, b, c)

        assert len(result["mean_ranks"]) == 3
        # 平均秩应该在1-3之间
        for rank in result["mean_ranks"]:
            assert 1 <= rank <= 3

    def test_friedman_vs_kruskal_wallis(self):
        """对比Friedman和Kruskal-Wallis（当数据独立时应给出相似结果）"""
        np.random.seed(42)
        n = 20
        a = np.random.normal(100, 5, n)
        b = np.random.normal(105, 5, n)
        c = np.random.normal(110, 5, n)

        result_friedman = friedman_test(a, b, c)
        from analysis.hypothesis.nonparametric import kruskal_wallis
        result_kruskal = kruskal_wallis(a, b, c)

        # 两者都应该能检测到差异
        assert result_friedman["test"] == "Friedman"
        assert result_kruskal["test"] == "Kruskal-Wallis H"


class TestNonparametricIntegration:
    """非参数检验集成测试"""

    def test_all_nonparametric_functions(self):
        np.random.seed(42)
        a = np.random.normal(100, 5, 30)
        b = np.random.normal(105, 5, 30)

        from analysis.hypothesis.nonparametric import (
            mann_whitney,
            wilcoxon_signed_rank,
            kruskal_wallis,
            mood_median_test,
            friedman_test,
        )

        result_mw = mann_whitney(a, b)
        result_w = wilcoxon_signed_rank(a, b)
        result_kw = kruskal_wallis(a, b)
        result_mood = mood_median_test(a, b)

        # 对于配对数据（至少3个处理）
        paired_a = np.random.normal(100, 5, 30)
        paired_b = paired_a + np.random.normal(0, 2, 30)
        paired_c = paired_a + np.random.normal(0, 3, 30)
        result_friedman = friedman_test(paired_a, paired_b, paired_c)

        assert result_mw["test"] == "Mann-Whitney U"
        assert result_w["test"] == "Wilcoxon Signed-Rank (paired)"
        assert result_kw["test"] == "Kruskal-Wallis H"
        assert result_mood["test"] == "Mood's Median"
        assert result_friedman["test"] == "Friedman"
