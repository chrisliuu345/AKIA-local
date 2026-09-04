"""属性一致性分析测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.msa.attribute_agree import (
    analyze,
    fleiss_kappa,
    _kappa_max,
    _calculate_bias_matrix,
    _calculate_cohen_kappa,
    _kappa_interpretation,
)


class TestAnalyze:
    """analyze 函数测试"""

    def test_basic_two_raters(self):
        """基本2评注者分析"""
        df = pd.DataFrame({
            "result": ["A", "B", "A", "A", "B", "B", "A", "B", "A", "B"],
            "standard": ["A", "B", "A", "A", "B", "A", "A", "B", "B", "B"],
        })
        result = analyze(df, "result", "standard")

        assert result["chart_type"] == "Attribute Agreement"
        assert result["total_assessments"] == 10
        assert 0 <= result["kappa"] <= 1
        assert "kappa_interpretation" in result
        assert "effective_kappa" in result
        assert result["method"] in ("cohen", "fleiss")

    def test_with_operators(self):
        """带评注者的分析"""
        df = pd.DataFrame({
            "result": ["A", "B", "A", "A", "B", "B", "A", "B", "A", "B",
                       "A", "A", "B", "A", "B", "B", "A", "B", "A", "B"],
            "standard": ["A", "B", "A", "A", "B", "A", "A", "B", "B", "B",
                         "A", "B", "A", "A", "B", "A", "A", "B", "B", "B"],
            "operator": ["Op1", "Op1", "Op1", "Op1", "Op1", "Op1", "Op1", "Op1", "Op1", "Op1",
                         "Op2", "Op2", "Op2", "Op2", "Op2", "Op2", "Op2", "Op2", "Op2", "Op2"],
        })
        result = analyze(df, "result", "standard", operator_col="operator")

        assert result["n_operators"] == 2
        assert "Op1" in result["operator_agreements"]
        assert "Op2" in result["operator_agreements"]
        assert result["method"] == "cohen"

    def test_three_operators_uses_fleiss(self):
        """3个评注者使用 Fleiss's Kappa"""
        df = pd.DataFrame({
            "result": ["A", "A", "A", "B", "B", "B", "A", "A", "A", "B", "B", "B"],
            "standard": ["A", "A", "A", "B", "B", "B", "A", "A", "A", "B", "B", "B"],
            "operator": ["Op1", "Op2", "Op3", "Op1", "Op2", "Op3", "Op1", "Op2", "Op3", "Op1", "Op2", "Op3"],
            "part": ["P1"] * 3 + ["P2"] * 3 + ["P3"] * 3 + ["P4"] * 3,
        })
        result = analyze(df, "result", "standard", operator_col="operator", method="auto")

        assert result["method"] == "fleiss"
        assert result["n_operators"] == 3

    def test_bias_matrix(self):
        """偏差矩阵生成"""
        df = pd.DataFrame({
            "result": ["A", "A", "B", "C", "A", "B", "B", "C", "A", "A"],
            "standard": ["A", "B", "B", "C", "A", "A", "B", "C", "A", "B"],
        })
        result = analyze(df, "result", "standard")

        assert "bias_matrix" in result
        assert "matrix" in result["bias_matrix"]
        assert "summary" in result["bias_matrix"]

    def test_effective_kappa(self):
        """有效 Kappa 计算"""
        df = pd.DataFrame({
            "result": ["A", "B", "A", "A", "B", "B", "A", "B", "A", "B"],
            "standard": ["A", "B", "A", "A", "B", "A", "A", "B", "B", "B"],
        })
        result = analyze(df, "result", "standard")

        assert "kappa_max" in result
        assert "effective_kappa" in result
        assert result["kappa_max"] > 0
        assert result["effective_kappa"] <= 1.0

    def test_insufficient_data(self):
        """数据量不足"""
        df = pd.DataFrame({
            "result": ["A", "B", "A"],
            "standard": ["A", "B", "A"],
        })
        with pytest.raises(ValueError, match="数据量不足"):
            analyze(df, "result", "standard")

    def test_acceptable_result(self):
        """可接受结果"""
        df = pd.DataFrame({
            "result": ["A"] * 50 + ["B"] * 50,
            "standard": ["A"] * 50 + ["B"] * 50,
        })
        result = analyze(df, "result", "standard")

        assert result["is_acceptable"] is True
        assert result["agreement_rate"] == 100.0
        assert result["kappa"] == 1.0

    def test_unacceptable_result(self):
        """不可接受结果"""
        np.random.seed(42)
        n = 100
        standard = np.random.choice(["A", "B", "C"], n)
        result = np.random.choice(["A", "B", "C"], n)
        df = pd.DataFrame({"result": result, "standard": standard})
        res = analyze(df, "result", "standard")

        assert res["is_acceptable"] is False


class TestFleissKappa:
    """Fleiss's Kappa 测试"""

    def test_perfect_agreement(self):
        """完美一致"""
        df = pd.DataFrame({
            "result": ["A", "A", "A", "B", "B", "B"],
            "standard": ["A", "A", "A", "B", "B", "B"],
            "operator": ["Op1", "Op2", "Op3", "Op1", "Op2", "Op3"],
            "part": ["P1", "P1", "P1", "P2", "P2", "P2"],
        })
        kappa = fleiss_kappa(df, "result", "standard", "operator", part_col="part")
        assert kappa == 1.0

    def test_random_agreement(self):
        """随机一致"""
        np.random.seed(42)
        n_subjects = 20
        n_raters = 4
        categories = ["A", "B", "C"]
        rows = []
        for i in range(n_subjects):
            standard = np.random.choice(categories)
            for j in range(n_raters):
                rows.append({
                    "result": np.random.choice(categories),
                    "standard": standard,
                    "operator": f"Op{j+1}",
                    "part": f"P{i+1}",
                })
        df = pd.DataFrame(rows)
        kappa = fleiss_kappa(df, "result", "standard", "operator", part_col="part")
        assert -1.0 <= kappa <= 1.0

    def test_insufficient_raters(self):
        """评注者不足"""
        df = pd.DataFrame({
            "result": ["A", "B", "A"],
            "standard": ["A", "B", "A"],
            "operator": ["Op1", "Op1", "Op1"],
            "part": ["P1", "P1", "P1"],
        })
        kappa = fleiss_kappa(df, "result", "standard", "operator", part_col="part")
        assert kappa == 0.0


class TestKappaMax:
    """Kappa_max 测试"""

    def test_balanced_categories(self):
        """平衡类别"""
        df = pd.DataFrame({
            "result": ["A"] * 50 + ["B"] * 50,
            "standard": ["A"] * 50 + ["B"] * 50,
        })
        kappa_max = _kappa_max(df, "result", "standard", ["A", "B"])
        assert 0 < kappa_max <= 1.0

    def test_imbalanced_categories(self):
        """不平衡类别"""
        df = pd.DataFrame({
            "result": ["A"] * 90 + ["B"] * 10,
            "standard": ["A"] * 50 + ["B"] * 50,
        })
        kappa_max = _kappa_max(df, "result", "standard", ["A", "B"])
        assert 0 < kappa_max <= 1.0


class TestBiasMatrix:
    """偏差矩阵测试"""

    def test_bias_matrix_basic(self):
        """基本偏差矩阵"""
        df = pd.DataFrame({
            "result": ["A", "A", "B", "C", "A", "B", "B", "C", "A", "A"],
            "standard": ["A", "B", "B", "C", "A", "A", "B", "C", "A", "B"],
            "operator": ["Op1", "Op1", "Op1", "Op1", "Op1", "Op2", "Op2", "Op2", "Op2", "Op2"],
        })
        operators = df["operator"].unique()
        categories = sorted(df["standard"].unique())
        result = _calculate_bias_matrix(df, "result", "standard", "operator", categories, operators)

        assert "matrix" in result
        assert "summary" in result
        assert "Op1" in result["matrix"]
        assert "Op2" in result["matrix"]
        for cat in categories:
            assert cat in result["matrix"]["Op1"]
            assert cat in result["matrix"]["Op2"]

    def test_bias_matrix_summary(self):
        """偏差矩阵汇总"""
        df = pd.DataFrame({
            "result": ["A", "A", "B", "C", "A", "B", "B", "C", "A", "A"],
            "standard": ["A", "B", "B", "C", "A", "A", "B", "C", "A", "B"],
        })
        categories = sorted(df["standard"].unique())
        result = _calculate_bias_matrix(df, "result", "standard", "", categories, np.array([]))

        assert "matrix" in result
        assert "summary" in result


class TestCohenKappa:
    """Cohen's Kappa 测试"""

    def test_perfect_agreement(self):
        """完美一致"""
        df = pd.DataFrame({
            "result": ["A", "B", "A", "A", "B"],
            "standard": ["A", "B", "A", "A", "B"],
        })
        kappa = _calculate_cohen_kappa(df, "result", "standard", ["A", "B"])
        assert kappa == 1.0

    def test_no_agreement(self):
        """完全不一致 (result和standard分布完全不同)"""
        df = pd.DataFrame({
            "result": ["A", "A", "A", "A", "A"],
            "standard": ["B", "B", "B", "B", "B"],
        })
        kappa = _calculate_cohen_kappa(df, "result", "standard", ["A", "B"])
        # When result and standard are completely different, pe = 0, so kappa = 0
        assert kappa == 0.0


class TestKappaInterpretation:
    """Kappa 解释测试"""

    def test_interpretation_levels(self):
        """解释等级"""
        assert _kappa_interpretation(-0.1) == "一致性极差"
        assert _kappa_interpretation(0.1) == "轻微一致"
        assert _kappa_interpretation(0.3) == "一般一致"
        assert _kappa_interpretation(0.5) == "中等一致"
        assert _kappa_interpretation(0.7) == "高度一致"
        assert _kappa_interpretation(0.9) == "几乎完全一致"

    def test_boundary_values(self):
        """边界值"""
        assert _kappa_interpretation(0.0) == "轻微一致"
        assert _kappa_interpretation(0.2) == "一般一致"
        assert _kappa_interpretation(0.4) == "中等一致"
        assert _kappa_interpretation(0.6) == "高度一致"
        assert _kappa_interpretation(0.8) == "几乎完全一致"
