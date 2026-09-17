"""CART 已知值 — 完全可分数据的决策树（v4.2.0 P1 批次 2）。

来源: Breiman et al. (1984) CART；完全可分数据在 Gini 不纯度下的最优单分裂
位于两类边界中点 x=10.5，训练/测试准确率均为 1。
"""

import pandas as pd

from analysis.ml.trees import analyze as cart_analyze
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase.with_preset(
    "cart1984-perfect-split", "Breiman et al. (1984)",
    preset="closed_form",
    reference="x=1..20，y=low×10+high×10，max_depth=1：阈值 10.5，准确率 1",
)


class TestCartKnownValues:
    def test_perfect_single_split(self):
        df = pd.DataFrame({"x": [float(v) for v in range(1, 21)],
                           "y": ["low"] * 10 + ["high"] * 10})
        result = cart_analyze(df, "y", features=["x"], max_depth=1, cv=2)

        assert result["task"] == "classification"
        assert_close(result["metrics"]["train"]["accuracy"], 1.0, _CASE,
                     context="训练准确率")
        assert_close(result["metrics"]["test"]["accuracy"], 1.0, _CASE,
                     context="测试准确率（完全可分）")
        rules = " ".join(result["rules"])
        assert "10.50" in rules, f"分裂阈值应为 10.50，实际规则: {rules}"
