"""SPC 控制图已知值 — Xbar-R / I-MR / Nelson 判异（v4.2.0 P1）。

来源:
- NIST/SEMATECH e-Handbook of Statistical Methods, 6.3.2 (控制图常数表)
- Montgomery, Introduction to Statistical Quality Control, Appendix VI
- Nelson, L.S. (1984) "The Shewhart Control Chart — Tests for Special Causes"
"""

import numpy as np
import pandas as pd
import pytest

from analysis.spc._rules import check_all_nelson_rules
from analysis.spc.imr import analyze as imr_analyze
from analysis.spc.xbar_r import analyze as xbar_r_analyze
from tests.known_values import KnownValueCase, assert_close

_SOURCE = "NIST/SEMATECH e-Handbook 6.3.2 / Montgomery Appendix VI"

CHART_CASE = KnownValueCase.with_preset(
    "sematech-xbar-r-n2", _SOURCE, preset="rounded_6dp",
    reference="n=2 常数 A2=1.880, D3=0, D4=3.267, d2=1.128",
    notes="数据 [0,2,4,6] 两个子组：x̄=[1,5], R=[2,2]；期望值为查表常数的手算闭式值",
)


class TestXbarRKnownValues:
    def test_control_limits(self):
        result = xbar_r_analyze(pd.Series([0, 2, 4, 6]), subgroup_size=2)
        xbar, r_chart = result["xbar_chart"], result["r_chart"]

        assert_close(xbar["cl"], 3.0, CHART_CASE, context="xbar CL = x̄̄")
        assert_close(xbar["ucl"], 3.0 + 1.880 * 2.0, CHART_CASE,
                     context="xbar UCL = x̄̄ + A2·R̄")
        assert_close(xbar["lcl"], 3.0 - 1.880 * 2.0, CHART_CASE,
                     context="xbar LCL = x̄̄ − A2·R̄")
        assert_close(r_chart["cl"], 2.0, CHART_CASE, context="R CL")
        assert_close(r_chart["ucl"], 3.267 * 2.0, CHART_CASE, context="R UCL = D4·R̄")
        assert_close(r_chart["lcl"], 0.0, CHART_CASE, context="R LCL = D3·R̄ (D3=0)")
        assert_close(result["summary"]["sigma_hat"], 2.0 / 1.128, CHART_CASE,
                     context="σ̂ = R̄/d2")


class TestIMRKnownValues:
    def test_control_limits(self):
        result = imr_analyze(pd.Series([0, 2, 4, 6]))
        i_chart, mr_chart, summary = result["i_chart"], result["mr_chart"], result["summary"]
        sigma_hat = 2.0 / 1.128  # MR̄ = 2, d2 = 1.128（n=2 常数）

        assert_close(i_chart["cl"], 3.0, CHART_CASE, context="I CL = x̄")
        assert_close(i_chart["ucl"], 3.0 + 3.0 * sigma_hat, CHART_CASE,
                     context="I UCL = x̄ + 3σ̂")
        assert_close(i_chart["lcl"], 3.0 - 3.0 * sigma_hat, CHART_CASE,
                     context="I LCL = x̄ − 3σ̂")
        assert_close(mr_chart["ucl"], 3.267 * 2.0, CHART_CASE,
                     context="MR UCL = D4·MR̄")
        assert_close(summary["mr_bar"], 2.0, CHART_CASE, context="MR̄")


_RULE_CASES = [
    ("nelson-r1-beyond-3sigma", [0, 0, 0, 0, 0, 3.5], 0.0, 1.0, 1, 6),
    ("nelson-r2-nine-one-side", [1.0] * 9, 0.0, 1.0, 2, 9),
    ("nelson-r3-six-trend", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], 0.0, 1.0, 3, 6),
    ("nelson-r4-fourteen-alternating", [0, 1] * 7, 0.5, 1.0, 4, 14),
    ("nelson-r5-two-of-three-beyond-2sigma", [2.5, 2.5, 0.0], 0.0, 1.0, 5, 3),
    ("nelson-r6-four-of-five-beyond-1sigma", [1.5] * 4 + [0.0], 0.0, 1.0, 6, 5),
    ("nelson-r7-fifteen-within-1sigma",
     [0.5] * 5 + [-0.5] * 4 + [0.5] * 4 + [-0.5] * 2, 0.0, 1.0, 7, 15),
    ("nelson-r8-eight-outside-1sigma", [1.5, -1.5] * 4, 0.0, 1.0, 8, 8),
]


class TestNelsonRulesKnownValues:
    @pytest.mark.parametrize(
        "case_id, values, mean, sigma, expected_rule, expected_point",
        _RULE_CASES,
    )
    def test_rule_triggers_at_known_point(self, case_id, values, mean, sigma,
                                          expected_rule, expected_point):
        case = KnownValueCase(
            case_id=case_id,
            source="Nelson (1984) / AIAG SPC Manual",
            reference=f"规则 {expected_rule} 的定义模式",
            notes="构造序列只触发目标规则，期望点为规则定义的位置",
        )
        violations = check_all_nelson_rules(np.asarray(values, dtype=float), mean, sigma)
        assert len(violations) == 1, f"{case_id} 期望单一违规，实际 {violations}"
        assert_close(violations[0]["rule"], expected_rule, case, context="rule")
        assert_close(violations[0]["point"], expected_point, case, context="point")
