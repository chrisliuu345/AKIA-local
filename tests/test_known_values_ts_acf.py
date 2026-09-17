"""时间序列已知值 — 样本 ACF（v4.2.0 P1）。

推导: 对 x_t = (-1)^t（n=8），偏倚估计量（statsmodels 默认，除以 n）满足
  ρ_k = (n−k)/n · (−1)^k
  → ρ_1 = −7/8, ρ_2 = 6/8
参考: statsmodels acf 文档（样本自相关定义）。
"""

import pandas as pd

from analysis.time_series.acf_pacf import compute_acf
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase.with_preset(
    "statsmodels-acf-alternating", "样本自相关定义（statsmodels acf）",
    preset="closed_form",
    reference="x = [1,-1,1,-1,1,-1,1,-1]，ρ_k = (n−k)/n·(−1)^k",
)


class TestAcfKnownValues:
    def test_alternating_series(self):
        result = compute_acf(pd.Series([1, -1, 1, -1, 1, -1, 1, -1]), lags=2)
        acf_values = result["acf_values"]

        assert_close(acf_values[0], 1.0, _CASE, context="lag 0")
        assert_close(acf_values[1], -7.0 / 8.0, _CASE, context="lag 1")
        assert_close(acf_values[2], 6.0 / 8.0, _CASE, context="lag 2")
        assert_close(result["nlags"], 2.0, _CASE, context="nlags 上限")
