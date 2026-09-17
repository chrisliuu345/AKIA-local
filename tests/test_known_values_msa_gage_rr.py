"""MSA Gage R&R 已知值 — 均值-极差法（v4.2.0 P1 批次 2）。

来源: AIAG MSA 4th ed. 均值-极差法；查表常数 d2(r=2)=1.128、d2*(m=2)=1.41。
构造数据（2 零件 × 2 操作员 × 2 重复，单元内极差均为 2）:
  A/P1=[10,12] A/P2=[14,16] B/P1=[12,14] B/P2=[16,18]
  → 零件均值 12/16，操作员均值 13/15，EV=R̄/d2=2/1.128
"""

import math

import pandas as pd

from analysis.msa.gage_rr import analyze_crossed
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase(
    case_id="aiag-msa-average-range-2x2x2",
    source="AIAG MSA 4th ed.（均值-极差法）",
    reference="2×2×2 构造数据：R̄=2，操作员极差 2，零件极差 4",
    rel_tol=1e-9,
    abs_tol=1e-6,
    notes="引擎输出 6 位小数；期望值为 AIAG 公式的独立手算值",
)

_PCT_CASE = KnownValueCase.with_preset(
    "aiag-msa-percentages", "AIAG MSA 4th ed.",
    preset="rounded_2dp",
    reference="%EV/%AV/%GRR/%PV = 各分量/总变差（2 位小数）",
)


def _dataset() -> pd.DataFrame:
    rows = []
    for operator, values in (
        ("A", [("P1", 10.0), ("P1", 12.0), ("P2", 14.0), ("P2", 16.0)]),
        ("B", [("P1", 12.0), ("P1", 14.0), ("P2", 16.0), ("P2", 18.0)]),
    ):
        for part, value in values:
            rows.append({"operator": operator, "part": part, "value": value})
    return pd.DataFrame(rows)


class TestGageRrKnownValues:
    def test_variance_components(self):
        result = analyze_crossed(_dataset(), "value", "part", "operator")
        ev = 2.0 / 1.128
        av = math.sqrt((2.0 / 1.41) ** 2 - ev ** 2 / (2 * 2))
        grr = math.sqrt(ev ** 2 + av ** 2)
        pv = 4.0 / 1.41
        tv = math.sqrt(grr ** 2 + pv ** 2)
        components = result["variance_components"]

        assert_close(components["ev"], ev, _CASE, context="EV = R̄/d2")
        assert_close(components["av"], av, _CASE, context="AV（操作员极差修正）")
        assert_close(components["grr"], grr, _CASE, context="GRR = √(EV²+AV²)")
        assert_close(components["pv"], pv, _CASE, context="PV = Rp/d2*")
        assert_close(components["tv"], tv, _CASE, context="TV = √(GRR²+PV²)")
        assert_close(result["ndc"], 1.0, _CASE, context="ndc = 1.41·PV/GRR")

    def test_percentages(self):
        result = analyze_crossed(_dataset(), "value", "part", "operator")
        ev = 2.0 / 1.128
        av = math.sqrt((2.0 / 1.41) ** 2 - ev ** 2 / (2 * 2))
        grr = math.sqrt(ev ** 2 + av ** 2)
        pv = 4.0 / 1.41
        tv = math.sqrt(grr ** 2 + pv ** 2)
        percentages = result["percentages"]

        assert_close(percentages["ev_pct"], ev / tv * 100, _PCT_CASE, context="%EV")
        assert_close(percentages["av_pct"], av / tv * 100, _PCT_CASE, context="%AV")
        assert_close(percentages["grr_pct_tv"], grr / tv * 100, _PCT_CASE, context="%GRR")
        assert_close(percentages["pv_pct"], pv / tv * 100, _PCT_CASE, context="%PV")
