"""KPI 提取器单测 — 用真实引擎输出形状断言 (v2.4 F0, 审查修复版)

形状来源 (与引擎代码一致):
- gage_rr.py: percentages.grr_pct_tv 为 0-100 百分数
- linear_regression.py: 顶层 r_squared (无 model 键)
- p_chart.py/np_chart.py/c_chart.py/u_chart.py: 顶层 violations
- xbar_r.py: xbar_chart.violations / r_chart.violations
- oee.py: overall 嵌套; tpm.py: avg_oee 顶层
- line_balance.py: current.balance_rate 嵌套
- mtbf.py: MTBFResult dataclass asdict
"""

import pytest
from dataclasses import asdict

from core.kpi_extractor import extract_metrics, build_variable_namespace


def _entry(atype, result):
    return {"analysis_type": atype, "params": {}, "result": result}


class TestCapability:
    def test_capability_metrics(self):
        analyses = {2: _entry("过程能力分析", {
            "capability": {
                "cp": 1.35, "cpk": 1.28, "pp": 1.4, "ppk": 1.3,
                "grade": "B", "sigma_level": 4.1, "ppm_total": 1234.0,
            }
        })}
        out = extract_metrics(analyses)
        assert out["过程能力分析"]["cp"] == 1.35
        assert out["过程能力分析"]["grade"] == "B"

    def test_empty_result(self):
        assert extract_metrics({1: _entry("x", {})}) == {}


class TestSPC:
    def test_xbar_r_violations_nested(self):
        """XBar-R: 违规点嵌套在 xbar_chart/r_chart 下"""
        analyses = {1: _entry("XBar-R 控制图", {
            "xbar_chart": {"cl": 10.0, "violations": [3, 7, 12]},
            "r_chart": {"cl": 2.0, "violations": [5]},
        })}
        out = extract_metrics(analyses)
        assert out["XBar-R 控制图"]["violations"] == 4

    def test_p_chart_violations_top_level(self):
        """P 图: 违规点在顶层 (审查 Warning #3)"""
        analyses = {1: _entry("P Chart", {
            "violations": [2, 9], "p_bar": 0.05,
        })}
        out = extract_metrics(analyses)
        assert out["P Chart"]["violations"] == 2

    def test_i_mr_no_violations(self):
        analyses = {1: _entry("I-MR 控制图", {
            "i_chart": {"cl": 10.0, "violations": []},
            "mr_chart": {"cl": 1.0, "violations": []},
        })}
        assert extract_metrics(analyses)["I-MR 控制图"]["violations"] == 0


class TestOEE:
    def test_oee_overall(self):
        analyses = {10: _entry("OEE 设备综合效率", {
            "overall": {
                "label": "全部", "oee": 0.7234, "availability": 0.9,
                "performance": 0.85, "quality": 0.95, "grade": "良好",
            },
            "buckets": [], "warnings": [],
        })}
        out = extract_metrics(analyses)
        assert out["OEE 设备综合效率"]["oee"] == pytest.approx(0.7234)
        assert out["OEE 设备综合效率"]["grade"] == "良好"

    def test_tpm_flat_entry_tolerated(self):
        """TPM 历史形状: current_result 直接为 to_dict() 扁平 dict (提取器容忍)"""
        analyses = {31: {
            "avg_mtbf": 120.0, "avg_mttr": 2.5, "avg_oee": 0.81,
            "six_losses": {}, "record_count": 5,
        }}
        out = extract_metrics(analyses)
        assert out["analysis_31"]["oee"] == pytest.approx(0.81)
        assert out["analysis_31"]["mtbf"] == 120.0

    def test_tpm_wrapped_entry(self):
        """TPM v2.4 新形状: 统一包装"""
        analyses = {31: _entry("TPM 全面维护", {
            "avg_mtbf": 120.0, "avg_mttr": 2.5, "avg_oee": 0.81,
        })}
        out = extract_metrics(analyses)
        assert out["TPM 全面维护"]["oee"] == pytest.approx(0.81)
        assert out["TPM 全面维护"]["mtbf"] == 120.0


class TestMSA:
    def test_msa_grr_100_scale_normalized(self):
        """真实引擎 grr_pct_tv 是 0-100 百分数 (如 18.3), 提取归一化为 0.183"""
        analyses = {3: _entry("MSA 测量系统分析", {
            "variance_components": {},
            "percentages": {"grr_pct_tv": 18.3, "grr_pct_tol": 22.0},
            "ndc": 7, "acceptance": {"message": "测量系统可接受"},
        })}
        out = extract_metrics(analyses)
        assert out["MSA 测量系统分析"]["grr_pct"] == pytest.approx(0.183)
        assert out["MSA 测量系统分析"]["ndc"] == 7
        assert "可接受" in out["MSA 测量系统分析"]["acceptance"]


class TestHypothesisRegression:
    def test_hypothesis(self):
        analyses = {4: _entry("t检验", {"p_value": 0.0032, "is_significant": True})}
        out = extract_metrics(analyses)
        assert out["t检验"]["p_value"] == pytest.approx(0.0032)

    def test_two_way_anova_list_pvalue_skipped(self):
        """双因素 ANOVA: p_value 是 list, 非标量应跳过 (审查 Info #13)"""
        analyses = {4: _entry("双因素 ANOVA", {
            "p_value": [0.001, 0.04], "is_significant": [True, True],
        })}
        assert extract_metrics(analyses) == {}

    def test_regression_top_level_r2(self):
        """真实回归引擎: 顶层 r_squared (审查 Critical #2)"""
        analyses = {6: _entry("回归分析", {
            "r_squared": 0.873, "coefs": [1.2, -0.4],
        })}
        out = extract_metrics(analyses)
        assert out["回归分析"]["r_squared"] == pytest.approx(0.873)

    def test_regression_model_nested_compat(self):
        """兼容 model.r_squared 形状"""
        analyses = {6: _entry("回归分析", {"model": {"r_squared": 0.9}})}
        assert extract_metrics(analyses)["回归分析"]["r_squared"] == pytest.approx(0.9)


class TestReliabilityWeibull:
    def test_mtbf_dataclass_asdict(self):
        """MTBF 引擎: asdict(MTBFResult) 形状"""
        from analysis.reliability.mtbf import MTBFResult
        overall = MTBFResult(
            label="全部", n_failures=3, total_uptime=1500.0, total_downtime=12.6,
            mtbf=500.0, mttr=4.2, availability=0.992, failure_rate=0.002,
            laplace_stat=0.5, trend="stable",
            mtbf_ci_low=400.0, mtbf_ci_high=600.0,
        )
        analyses = {13: _entry("MTBF / MTTR", asdict(overall))}
        out = extract_metrics(analyses)
        assert out["MTBF / MTTR"]["mtbf"] == pytest.approx(500.0)
        assert out["MTBF / MTTR"]["mttr"] == pytest.approx(4.2)
        assert out["MTBF / MTTR"]["availability"] == pytest.approx(0.992)

    def test_weibull(self):
        analyses = {13: _entry("Weibull 寿命分析", {
            "beta": 2.1, "eta": 5000.0, "b10_life": 1710.0,
            "characteristic_life": 5000.0, "mean_life": 4428.0,
        })}
        out = extract_metrics(analyses)
        assert out["Weibull 寿命分析"]["b10_life"] == pytest.approx(1710.0)


class TestIE:
    def test_line_balance_nested_current(self):
        """线平衡: balance_rate 嵌套在 current 下 (审查 Warning #5)"""
        analyses = {9: _entry("生产线平衡", {
            "takt": None,
            "current": {"balance_rate": 0.82, "balance_loss": 0.18},
            "stations": [], "balanced": {"balance_rate": 0.95},
        })}
        out = extract_metrics(analyses)
        assert out["生产线平衡"]["balance_rate"] == pytest.approx(0.82)

    def test_vsm_va_ratio(self):
        analyses = {11: _entry("价值流分析 (VSM)", {
            "summary": {"va_ratio": 0.0135, "lead_time_days": 12.4},
        })}
        out = extract_metrics(analyses)
        assert out["价值流分析 (VSM)"]["va_ratio"] == pytest.approx(0.0135)

    def test_non_scalar_utilization_skipped(self):
        """工作抽样 utilization 是 dict, 提取器应跳过非标量"""
        analyses = {8: _entry("工作抽样", {
            "utilization": {"operating": 0.7, "idle": 0.3},
        })}
        assert extract_metrics(analyses) == {}


class TestNamespaceAndRobustness:
    def test_variable_namespace(self):
        analyses = {
            2: _entry("能力", {"capability": {"cp": 1.5, "grade": "A"}}),
            10: _entry("OEE", {"overall": {"oee": 0.75}}),
        }
        ns = build_variable_namespace(analyses)
        assert ns["cp"] == pytest.approx(1.5)
        assert ns["oee"] == pytest.approx(0.75)
        assert "grade" not in ns  # 字符串不进数值命名空间

    def test_invalid_entry_skipped(self):
        analyses = {1: "not a dict", 2: _entry("能力", {"capability": {"cp": 1.2}})}
        out = extract_metrics(analyses)
        assert list(out.keys()) == ["能力"]
