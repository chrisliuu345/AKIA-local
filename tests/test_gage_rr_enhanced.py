"""Gage R&R 增强功能测试"""
import numpy as np
import pandas as pd
from analysis.msa.gage_rr import (
    analyze_crossed,
    _variance_component_data,
    _interaction_chart_data,
    _uncertainty_budget,
    _uncertainty_interpretation,
    _grr_acceptance,
)


class TestVarianceComponentData:
    """方差分量图数据测试"""

    def test_variance_component_basic(self):
        """基本方差分量数据"""
        result = _variance_component_data(ev=0.1, av=0.15, pv=1.0, grr=0.18, tv=1.02)

        assert "components" in result
        assert "standard_deviation" in result
        assert len(result["components"]) == 5
        assert len(result["standard_deviation"]) == 5

        names = [c["name"] for c in result["components"]]
        assert "EV (重复性)" in names
        assert "AV (再现性)" in names
        assert "GRR (量具R&R)" in names
        assert "PV (零件间)" in names
        assert "TV (总变异)" in names

    def test_variance_component_percentages(self):
        """方差分量百分比"""
        result = _variance_component_data(ev=0.1, av=0.1, pv=1.0, grr=0.14, tv=1.01)

        tv_comp = next(c for c in result["components"] if c["name"] == "TV (总变异)")
        assert tv_comp["pct"] == 100.0

        grr_comp = next(c for c in result["components"] if c["name"] == "GRR (量具R&R)")
        assert 0 < grr_comp["pct"] < 100


class TestInteractionChartData:
    """交互效应图数据测试"""

    def test_interaction_chart_basic(self):
        """基本交互效应图数据"""
        df = pd.DataFrame({
            "part": ["P1", "P1", "P2", "P2", "P1", "P1", "P2", "P2"],
            "operator": ["Op1", "Op1", "Op1", "Op1", "Op2", "Op2", "Op2", "Op2"],
            "measurement": [10, 10.1, 20, 20.1, 10.2, 10.3, 20.2, 20.3],
        })
        result = _interaction_chart_data(df, "measurement", "part", "operator")

        assert "categories" in result
        assert "series" in result
        assert "overall_means" in result
        assert len(result["categories"]) == 2
        assert len(result["series"]) == 2
        assert len(result["overall_means"]) == 2

    def test_interaction_chart_series(self):
        """交互效应图系列数据"""
        df = pd.DataFrame({
            "part": ["P1", "P1", "P2", "P2"],
            "operator": ["Op1", "Op2", "Op1", "Op2"],
            "measurement": [10, 10.2, 20, 20.2],
        })
        result = _interaction_chart_data(df, "measurement", "part", "operator")

        for series in result["series"]:
            assert "name" in series
            assert "data" in series
            assert len(series["data"]) == 2


class TestUncertaintyBudget:
    """不确定度预算测试"""

    def test_uncertainty_basic(self):
        """基本不确定度预算"""
        result = _uncertainty_budget(
            ev=0.1, av=0.1, pv=1.0, grr=0.14, tv=1.01,
            p=10, o=3, r=3, tolerance=2.0,
        )

        assert "standard_uncertainty" in result
        assert "combined_uncertainty" in result
        assert "coverage_factor" in result
        assert "expanded_uncertainty" in result
        assert "tolerance_ratio" in result
        assert "interpretation" in result

        assert result["coverage_factor"] == 2
        assert result["expanded_uncertainty"] > 0
        assert result["tolerance_ratio"] is not None

    def test_uncertainty_without_tolerance(self):
        """无公差的不确定度预算"""
        result = _uncertainty_budget(
            ev=0.1, av=0.1, pv=1.0, grr=0.14, tv=1.01,
            p=10, o=3, r=3, tolerance=None,
        )

        assert result["tolerance_ratio"] is None
        assert "未提供公差" in result["interpretation"]

    def test_uncertainty_excellent(self):
        """优秀不确定度"""
        result = _uncertainty_budget(
            ev=0.01, av=0.01, pv=1.0, grr=0.014, tv=1.0,
            p=10, o=3, r=3, tolerance=10.0,
        )

        assert result["tolerance_ratio"] < 0.1
        assert "极小" in result["interpretation"]


class TestUncertaintyInterpretation:
    """不确定度解释测试"""

    def test_excellent(self):
        """优秀"""
        assert "极小" in _uncertainty_interpretation(0.05, 2.0)

    def test_good(self):
        """良好"""
        assert "较小" in _uncertainty_interpretation(0.2, 2.0)

    def test_acceptable(self):
        """可接受"""
        assert "适中" in _uncertainty_interpretation(0.4, 2.0)

    def test_marginal(self):
        """边缘"""
        assert "较大" in _uncertainty_interpretation(0.7, 2.0)

    def test_unacceptable(self):
        """不可接受"""
        assert "过大" in _uncertainty_interpretation(1.5, 2.0)

    def test_no_tolerance(self):
        """无公差"""
        assert "未提供公差" in _uncertainty_interpretation(0.1, None)


class TestGrrAcceptance:
    """GRR 接收准则测试"""

    def test_acceptable(self):
        """可接受"""
        result = _grr_acceptance(grr_pct=8, ndc=10)
        assert result["level"] == "acceptable"

    def test_marginal(self):
        """边缘"""
        result = _grr_acceptance(grr_pct=25, ndc=4)
        assert result["level"] == "marginal"

    def test_unacceptable(self):
        """不可接受"""
        result = _grr_acceptance(grr_pct=60, ndc=2)
        assert result["level"] == "unacceptable"


class TestAnalyzeCrossedEnhanced:
    """analyze_crossed 增强功能测试"""

    def test_enhanced_output(self):
        """增强输出包含新字段"""
        np.random.seed(42)
        rows = []
        for i in range(8):
            part_true = 50 + i
            for j in range(3):
                for _k in range(3):
                    measurement = part_true + np.random.normal(0, 0.3)
                    rows.append({
                        "part": f"P{i+1}",
                        "operator": f"Op{j+1}",
                        "measurement": measurement,
                    })

        df = pd.DataFrame(rows)
        result = analyze_crossed(df, "measurement", "part", "operator", tolerance=2.0)

        assert "variance_chart" in result
        assert "interaction_chart" in result
        assert "uncertainty" in result

        assert "components" in result["variance_chart"]
        assert "categories" in result["interaction_chart"]
        assert "expanded_uncertainty" in result["uncertainty"]
