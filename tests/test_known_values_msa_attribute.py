"""MSA 属性一致性已知值 — Cohen's Kappa（v4.2.0 P1）。

来源: Cohen, J. (1960) "A Coefficient of Agreement for Nominal Scales"；
手算案例 po=6/10=0.6, pe=0.52 → κ=(0.6−0.52)/(1−0.52)=1/6。
"""

import pandas as pd

from analysis.msa.attribute_agree import analyze as attribute_analyze
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase.with_preset(
    "cohen-1960-kappa-handcalc", "Cohen (1960)",
    preset="rounded_4dp",
    reference="10 次评定：po=0.60, pe=0.52 → κ=1/6≈0.1667",
)

_PERFECT_CASE = KnownValueCase.with_preset(
    "cohen-1960-perfect-agreement", "Cohen (1960)",
    preset="rounded_4dp",
    reference="完全一致：po=pe=1 → κ=1（边界已知值）",
)


def _dataset(truth, rater) -> pd.DataFrame:
    return pd.DataFrame({"truth": truth, "rater": rater})


class TestAttributeAgreementKnownValues:
    def test_kappa_hand_calculation(self):
        truth = ["OK", "OK", "NG", "NG", "OK", "OK", "OK", "NG", "NG", "OK"]
        rater = ["OK", "NG", "NG", "OK", "OK", "OK", "NG", "NG", "OK", "OK"]
        result = attribute_analyze(_dataset(truth, rater), "rater", "truth")

        assert result["method"] == "cohen"
        assert_close(result["agreement_count"], 6.0, _CASE, context="一致次数")
        assert_close(result["agreement_rate"], 60.0, _CASE, context="一致率 %")
        assert_close(result["kappa"], 1.0 / 6.0, _CASE, context="κ = 1/6")

    def test_perfect_agreement_boundary(self):
        labels = ["OK"] * 10
        result = attribute_analyze(_dataset(labels, labels), "rater", "truth")

        assert_close(result["agreement_rate"], 100.0, _PERFECT_CASE, context="一致率")
        assert_close(result["kappa"], 1.0, _PERFECT_CASE, context="κ = 1")
