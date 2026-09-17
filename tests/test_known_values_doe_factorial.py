"""DOE 全因子已知值 — 2² 主效应 / 平方和 / R²（v4.2.0 P1）。

来源: Montgomery, Design and Analysis of Experiments, ch.6（效应与平方和定义）。
构造 Y = 10 + 2A + 3B，A,B ∈ {−1,+1}，全部落在设计点上，误差项为 0。
"""

import pandas as pd

from analysis.doe.factorial import analyze_factorial, generate_design
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase.with_preset(
    "montgomery-2k-effects", "Montgomery DOE ch.6",
    preset="rounded_4dp",
    reference="Y = 10 + 2A + 3B：效应 = 2×系数（A=4, B=6）",
    notes="完全拟合（SSE=0），效应与 SS 为设计矩阵的闭式值",
)


def _design_with_response() -> pd.DataFrame:
    design = generate_design(["A", "B"])
    design["Y"] = 10.0 + 2.0 * design["A"] + 3.0 * design["B"]
    return design[["A", "B", "Y"]]


class TestFactorialKnownValues:
    def test_effects_and_sums_of_squares(self):
        result = analyze_factorial(_design_with_response(), "Y", ["A", "B"])

        assert_close(result["grand_mean"], 10.0, _CASE, context="grand mean")
        assert_close(result["effects"]["A"], 4.0, _CASE, context="A 效应 = 2·2")
        assert_close(result["effects"]["B"], 6.0, _CASE, context="B 效应 = 2·3")
        assert_close(result["anova"]["ss"][0], 16.0, _CASE, context="SS_A = 4·(4/2)²")
        assert_close(result["anova"]["ss"][1], 36.0, _CASE, context="SS_B = 4·(6/2)²")
        assert_close(result["anova"]["ss"][2], 0.0, _CASE, context="SS_Error = 0")
        assert_close(result["anova"]["ss"][3], 52.0, _CASE, context="SS_Total = 52")
        assert_close(result["model_r_squared"], 1.0, _CASE, context="R² = 1")
