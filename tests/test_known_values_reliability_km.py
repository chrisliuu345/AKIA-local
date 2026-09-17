"""可靠性已知值 — Kaplan-Meier 与 Crow-AMSAA（v4.2.0 P1）。

来源:
- Kaplan & Meier (1958) 乘积极限估计量定义（手算小样本）
- Crow-AMSAA 失效截尾 MLE：β = n / Σ ln(T/t_i)（MIL-HDBK-189 / IEC 61164）
"""

import math

import pandas as pd

from analysis.reliability.mtbf import crow_amsaa
from analysis.reliability.survival import kaplan_meier
from tests.known_values import KnownValueCase, assert_close

_KM_CASE = KnownValueCase.with_preset(
    "km-1958-product-limit", "Kaplan & Meier (1958)",
    preset="rounded_6dp",
    reference="t=[1,2,3] 全部失效：S(1)=2/3, S(2)=1/3, S(3)=0",
)

_CROW_CASE = KnownValueCase.with_preset(
    "mil-hdbk-189-failure-truncated", "MIL-HDBK-189 / IEC 61164",
    preset="rounded_4dp",
    reference="t=[1,2,4,8], T=8：β=2/(3ln2), α=e²/4, MTBF(T)=3ln2",
    notes="失效截尾 MLE 闭式解；引擎为等价数值优化",
)


class TestKaplanMeierKnownValues:
    def test_product_limit_estimator(self):
        result = kaplan_meier(pd.Series([1, 2, 3]), pd.Series([1, 1, 1]))

        assert_close(result["survival_function"][0], 1.0, _KM_CASE, context="S(0)")
        assert_close(result["survival_function"][1], 2.0 / 3.0, _KM_CASE, context="S(1)")
        assert_close(result["survival_function"][2], 1.0 / 3.0, _KM_CASE, context="S(2)")
        assert_close(result["survival_function"][3], 0.0, _KM_CASE, context="S(3)")
        assert_close(result["summary"]["median_survival"], 2.0, _KM_CASE,
                     context="中位生存 = 首次 S≤0.5 的时间")


class TestCrowAmsaaKnownValues:
    def test_failure_truncated_mle(self):
        result = crow_amsaa([1, 2, 4, 8])
        summary = result["summary"]
        beta = 2.0 / (3.0 * math.log(2.0))
        alpha = math.exp(2.0) / 4.0
        mtbf_at_t = 3.0 * math.log(2.0)

        assert_close(summary["beta"], beta, _CROW_CASE, context="β = n/Σln(T/t_i)")
        assert_close(summary["alpha"], alpha, _CROW_CASE, context="α = T^β/n")
        assert_close(summary["mtbf_at_T"], mtbf_at_t, _CROW_CASE,
                     context="MTBF(T) = α/(β·T^(β−1))")
        assert_close(summary["growth_rate"], 1.0 - beta, _CROW_CASE,
                     context="growth = 1 − β")
