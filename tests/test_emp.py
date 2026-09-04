"""EMP 方法量具研究测试"""
import pytest
import numpy as np
import pandas as pd
from analysis.msa.emp import (
    analyze_crossed,
    analyze_nested,
    _discrimination_grade,
    _wheeler_criteria,
    _calculate_interaction,
    _emp_acceptance,
)


class TestAnalyzeCrossed:
    """analyze_crossed 函数测试"""

    def test_basic_crossed(self):
        """基本交叉 EMP 分析"""
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
        result = analyze_crossed(df, "measurement", "part", "operator")

        assert result["chart_type"] == "EMP Crossed"
        assert result["method"] == "EMP"
        assert result["design"]["parts"] == n_parts
        assert result["design"]["operators"] == n_operators
        assert result["design"]["replicates"] == n_replicates
        assert "variance_components" in result
        assert "percentages" in result
        assert "ndc" in result
        assert "discrimination_grade" in result
        assert "wheeler_criteria" in result
        assert "acceptance" in result

    def test_with_tolerance(self):
        """带公差的 EMP 分析"""
        np.random.seed(42)
        rows = []
        for i in range(8):
            part_true = 50 + i
            for j in range(2):
                for k in range(3):
                    measurement = part_true + np.random.normal(0, 0.3)
                    rows.append({
                        "part": f"P{i+1}",
                        "operator": f"Op{j+1}",
                        "measurement": measurement,
                    })

        df = pd.DataFrame(rows)
        result = analyze_crossed(df, "measurement", "part", "operator", tolerance=2.0)

        assert result["percentages"]["grr_pct_tol"] is not None
        assert result["percentages"]["grr_pct_tol"] > 0

    def test_insufficient_parts(self):
        """零件不足"""
        df = pd.DataFrame({
            "part": ["P1", "P1", "P1", "P1"],
            "operator": ["Op1", "Op2", "Op1", "Op2"],
            "measurement": [10, 10.1, 10.2, 10.3],
        })
        with pytest.raises(ValueError, match="需要至少2个零件和2个操作员"):
            analyze_crossed(df, "measurement", "part", "operator")

    def test_insufficient_operators(self):
        """操作员不足"""
        df = pd.DataFrame({
            "part": ["P1", "P2", "P3", "P4"],
            "operator": ["Op1", "Op1", "Op1", "Op1"],
            "measurement": [10, 10.1, 10.2, 10.3],
        })
        with pytest.raises(ValueError, match="需要至少2个零件和2个操作员"):
            analyze_crossed(df, "measurement", "part", "operator")


class TestAnalyzeNested:
    """analyze_nested 函数测试"""

    def test_basic_nested(self):
        """基本嵌套 EMP 分析"""
        np.random.seed(42)
        n_parts = 8
        n_operators = 2
        n_replicates = 3

        rows = []
        for i in range(n_parts):
            part_true = 100 + i * 2
            op_idx = i % n_operators
            for k in range(n_replicates):
                measurement = part_true + np.random.normal(0, 0.5)
                rows.append({
                    "part": f"P{i+1}",
                    "operator": f"Op{op_idx+1}",
                    "measurement": measurement,
                })

        df = pd.DataFrame(rows)
        result = analyze_nested(df, "measurement", "part", "operator")

        assert result["chart_type"] == "EMP Nested"
        assert result["method"] == "EMP"
        assert result["design"]["parts"] == n_parts
        assert result["design"]["operators"] == n_operators


class TestDiscriminationGrade:
    """分辨力分级测试"""

    def test_grade_1(self):
        """1级 — 不可接受"""
        grade = _discrimination_grade(1)
        assert grade["grade"] == 1
        assert grade["level"] == "unacceptable"

    def test_grade_2(self):
        """2级 — 边缘"""
        grade = _discrimination_grade(3)
        assert grade["grade"] == 2
        assert grade["level"] == "marginal"

    def test_grade_3(self):
        """3级 — 可接受"""
        grade = _discrimination_grade(5)
        assert grade["grade"] == 3
        assert grade["level"] == "acceptable"

    def test_grade_4(self):
        """4级 — 优秀"""
        grade = _discrimination_grade(8)
        assert grade["grade"] == 4
        assert grade["level"] == "excellent"


class TestWheelerCriteria:
    """Wheeler 判异准则测试"""

    def test_all_pass(self):
        """所有准则通过"""
        criteria = _wheeler_criteria(ev=0.1, av=0.1, grr=0.14, pv=1.0, tv=1.01, ndc=10, grr_pct=14)
        assert len(criteria) == 8
        pass_count = sum(1 for c in criteria if c["status"] == "pass")
        assert pass_count >= 6

    def test_all_fail(self):
        """所有准则失败"""
        criteria = _wheeler_criteria(ev=1.0, av=1.0, grr=1.41, pv=0.1, tv=1.42, ndc=1, grr_pct=99)
        fail_count = sum(1 for c in criteria if c["status"] == "fail")
        assert fail_count >= 5


class TestCalculateInteraction:
    """交互效应计算测试"""

    def test_interaction_basic(self):
        """基本交互效应"""
        df = pd.DataFrame({
            "part": ["P1", "P1", "P2", "P2", "P1", "P1", "P2", "P2"],
            "operator": ["Op1", "Op1", "Op1", "Op1", "Op2", "Op2", "Op2", "Op2"],
            "measurement": [10, 10.1, 20, 20.1, 10.2, 10.3, 20.2, 20.3],
        })
        result = _calculate_interaction(df, "measurement", "part", "operator")

        assert "operators" in result
        assert "parts" in result
        assert "data" in result
        assert len(result["data"]) == 2


class TestEmpAcceptance:
    """EMP 接收准则测试"""

    def test_excellent(self):
        """优秀"""
        acceptance = _emp_acceptance(grr_pct=8, ndc=12, discrimination_grade={"grade": 4})
        assert acceptance["level"] == "excellent"

    def test_acceptable(self):
        """可接受"""
        acceptance = _emp_acceptance(grr_pct=20, ndc=6, discrimination_grade={"grade": 3})
        assert acceptance["level"] == "acceptable"

    def test_marginal(self):
        """边缘"""
        acceptance = _emp_acceptance(grr_pct=40, ndc=4, discrimination_grade={"grade": 2})
        assert acceptance["level"] == "marginal"

    def test_unacceptable(self):
        """不可接受"""
        acceptance = _emp_acceptance(grr_pct=60, ndc=2, discrimination_grade={"grade": 1})
        assert acceptance["level"] == "unacceptable"
