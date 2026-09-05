"""MSA E2E 测试 — 测量系统分析全流程"""
import pytest
import numpy as np
import pandas as pd


class TestMSACrossedGRR:
    """交叉 Gage R&R 全流程测试"""

    def test_full_crossed_grr(self):
        """完整交叉 Gage R&R 分析"""
        np.random.seed(42)
        n_parts = 10
        n_operators = 3
        n_replicates = 3

        rows = []
        for i in range(n_parts):
            part_true = 100 + i * 2
            for j in range(n_operators):
                for k in range(n_replicates):
                    measurement = part_true + np.random.normal(0, 0.5)
                    rows.append({
                        "part": f"P{i+1}",
                        "operator": f"Op{j+1}",
                        "measurement": measurement,
                    })

        df = pd.DataFrame(rows)

        from analysis.msa.gage_rr import analyze_crossed
        result = analyze_crossed(df, "measurement", "part", "operator", tolerance=5.0)

        assert result["chart_type"] == "Gage R&R (Crossed)"
        assert result["design"]["parts"] == n_parts
        assert result["design"]["operators"] == n_operators
        assert result["design"]["replicates"] == n_replicates
        assert "variance_components" in result
        assert "percentages" in result
        assert "variance_chart" in result
        assert "interaction_chart" in result
        assert "uncertainty" in result

        vc = result["variance_components"]
        assert vc["ev"] >= 0
        assert vc["av"] >= 0
        assert vc["grr"] >= 0
        assert vc["pv"] >= 0
        assert vc["tv"] >= 0


class TestMSAEMPMethod:
    """EMP 方法全流程测试"""

    def test_full_emp_analysis(self):
        """完整 EMP 分析"""
        np.random.seed(42)
        n_parts = 10
        n_operators = 3
        n_replicates = 3

        rows = []
        for i in range(n_parts):
            part_true = 100 + i * 2
            for j in range(n_operators):
                for k in range(n_replicates):
                    measurement = part_true + np.random.normal(0, 0.5)
                    rows.append({
                        "part": f"P{i+1}",
                        "operator": f"Op{j+1}",
                        "measurement": measurement,
                    })

        df = pd.DataFrame(rows)

        from analysis.msa.emp import analyze_crossed
        result = analyze_crossed(df, "measurement", "part", "operator", tolerance=5.0)

        assert result["chart_type"] == "EMP Crossed"
        assert result["method"] == "EMP"
        assert result["design"]["parts"] == n_parts
        assert result["design"]["operators"] == n_operators
        assert "variance_components" in result
        assert "percentages" in result
        assert "ndc" in result
        assert "discrimination_grade" in result
        assert "wheeler_criteria" in result

        dg = result["discrimination_grade"]
        assert dg["grade"] in [1, 2, 3, 4]
        assert dg["level"] in ["unacceptable", "marginal", "acceptable", "excellent"]

        assert len(result["wheeler_criteria"]) == 8


class TestMSAAttributeAgreement:
    """属性一致性分析全流程测试"""

    def test_full_attribute_analysis(self):
        """完整属性一致性分析"""
        np.random.seed(42)
        n_samples = 50

        standard = np.random.choice(["A", "B", "C"], n_samples)
        result = np.random.choice(["A", "B", "C"], n_samples)

        df = pd.DataFrame({
            "result": result,
            "standard": standard,
            "operator": np.random.choice(["Op1", "Op2", "Op3"], n_samples),
        })

        from analysis.msa.attribute_agree import analyze
        result_dict = analyze(df, "result", "standard", operator_col="operator")

        assert result_dict["chart_type"] == "Attribute Agreement"
        assert result_dict["total_assessments"] == n_samples
        assert "kappa" in result_dict
        assert "effective_kappa" in result_dict
        assert "bias_matrix" in result_dict
        assert result_dict["method"] in ["cohen", "fleiss"]


class TestMSAType1Study:
    """Type 1 量具研究全流程测试"""

    def test_full_type1_study(self):
        """完整 Type 1 量具研究"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(10.0, 0.1, 50))

        from analysis.msa.type1_study import analyze
        result = analyze(data, reference=10.0, tolerance=0.5)

        assert result["chart_type"] == "Type 1 Gage Study"
        assert "capability" in result
        assert "cg" in result["capability"]
        assert "cgk" in result["capability"]
        assert "acceptance" in result


class TestMSABiasAnalysis:
    """偏倚分析全流程测试"""

    def test_full_bias_analysis(self):
        """完整偏倚分析"""
        np.random.seed(42)
        data = pd.Series(np.random.normal(10.2, 0.1, 50))

        from analysis.msa.linearity_bias import analyze_bias
        result = analyze_bias(data, reference=10.0)

        assert result["chart_type"] == "Bias Study"
        assert "mean_bias" in result
        assert "p_value" in result
        assert "is_significant" in result


class TestMSALinearityAnalysis:
    """线性分析全流程测试"""

    def test_full_linearity_analysis(self):
        """完整线性分析"""
        np.random.seed(42)
        n_points = 50
        reference = np.linspace(5, 15, n_points)
        measurement = reference + np.random.normal(0, 0.2, n_points) + 0.1 * (reference - 10)

        df = pd.DataFrame({
            "measurement": measurement,
            "reference": reference,
        })

        from analysis.msa.linearity_bias import analyze_linearity
        result = analyze_linearity(df, "measurement", "reference")

        assert result["chart_type"] == "Linearity Study"
        assert "slope" in result
        assert "intercept" in result
        assert "p_value" in result
