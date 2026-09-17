"""SPC 第二批已知值 — EWMA / CUSUM / Hotelling T²（v4.2.0 P1 批次 2）。

来源:
- Roberts (1959) EWMA；Montgomery SQC ch.9（EWMA 递推与稳态限）
- Montgomery SQC ch.9 tabular CUSUM（k=0.5σ, h=5σ）
- Hotelling (1947)；Montgomery ch.11 个体观测 T² 控制限
"""

import numpy as np
import pandas as pd
from scipy import stats

from analysis.spc.cusum import analyze as cusum_analyze
from analysis.spc.ewma import analyze as ewma_analyze
from analysis.spc.hotelling import analyze as hotelling_analyze
from tests.known_values import KnownValueCase, assert_allclose, assert_close

_EWMA_CASE = KnownValueCase.with_preset(
    "roberts-1959-ewma-recursion", "Roberts (1959) / Montgomery ch.9",
    preset="rounded_6dp",
    reference="数据 [0,1,2,3]，λ=0.5：EWMA=[1.5, 0.5, 1.25, 2.125]",
    notes="EWMA[0]=x̄；UCL_i=x̄+L·s·√(λ/(2−λ)·(1−(1−λ)^{2i}))；summary 输出 6 位小数",
)

_CUSUM_CASE = KnownValueCase.with_preset(
    "montgomery-tabular-cusum", "Montgomery ch.9",
    preset="rounded_6dp",
    reference="数据 [0,1,2,3]，目标 1.5，k=0.5，h=5：C⁺=[0,0,0,0.8545]",
    notes="C⁺_i=max(0, C⁺_{i−1}+(x_i−μ₀)−kσ)；σ 为样本标准差（ddof=1）；summary 输出 6 位小数",
)

_T2_CASE = KnownValueCase.with_preset(
    "hotelling1947-orthogonal-t2", "Hotelling (1947) / Montgomery ch.11",
    preset="rounded_6dp",
    reference="5 点协方差对角（2.5,2.5）：T²=[2,2,0,2,2]，CL=3.2",
    notes="T²=(x−x̄)ᵀS⁻¹(x−x̄)；UCL=p(m−1)(m+1)/(m(m−p))·F(1−α;p,m−p)",
)


class TestEwmaKnownValues:
    def test_recursion_and_limits(self):
        data = pd.Series([0.0, 1.0, 2.0, 3.0])
        result = ewma_analyze(data, lam=0.5, L=3.0)
        mean = 1.5
        sigma = float(np.std(data, ddof=1))

        assert_allclose(result["ewma_chart"]["data"],
                        [1.5, 0.5, 1.25, 2.125], _EWMA_CASE, context="EWMA 递推")
        assert_close(result["ewma_chart"]["cl"], mean, _EWMA_CASE, context="CL")
        for i in (1, 4):
            factor = np.sqrt((0.5 / 1.5) * (1 - 0.5 ** (2 * i)))
            assert_close(result["ewma_chart"]["ucl"][i - 1], mean + 3.0 * sigma * factor,
                         _EWMA_CASE, context=f"UCL_{i}")
        assert_close(result["summary"]["steady_state_ucl"],
                     mean + 3.0 * sigma * np.sqrt(1.0 / 3.0),
                     _EWMA_CASE, context="稳态 UCL")
        assert result["ewma_chart"]["violations"] == []


class TestCusumKnownValues:
    def test_recursion_and_decision_interval(self):
        data = pd.Series([0.0, 1.0, 2.0, 3.0])
        result = cusum_analyze(data, target=1.5, k=0.5, h=5.0)
        sigma = float(np.std(data, ddof=1))
        k_abs, h_abs = 0.5 * sigma, 5.0 * sigma

        assert_allclose(result["cusum_chart"]["cusum_plus"],
                        [0.0, 0.0, 0.0, 1.5 - k_abs], _CUSUM_CASE, context="C⁺")
        assert_allclose(result["cusum_chart"]["cusum_minus"],
                        [1.5 - k_abs, 2.0 - 2 * k_abs, 0.0, 0.0],
                        _CUSUM_CASE, context="C⁻")
        assert_close(result["summary"]["k_absolute"], k_abs, _CUSUM_CASE, context="kσ")
        assert_close(result["summary"]["h_absolute"], h_abs, _CUSUM_CASE, context="hσ")
        assert result["cusum_chart"]["violations"] == []


class TestHotellingKnownValues:
    DATA = pd.DataFrame({
        "x": [-2.0, -1.0, 0.0, 1.0, 2.0],
        "y": [1.0, -2.0, 0.0, 2.0, -1.0],
    })

    def test_t2_and_control_limits(self):
        result = hotelling_analyze(self.DATA, ["x", "y"])
        p, m, alpha = 2, 5, 0.0027
        f_crit = stats.f.ppf(1 - alpha, p, m - p)
        ucl = p * (m - 1) * (m + 1) / (m * (m - p)) * f_crit

        assert_allclose(result["t2_chart"]["data"], [2.0, 2.0, 0.0, 2.0, 2.0],
                        _T2_CASE, context="T²（正交协方差手算）")
        assert_close(result["t2_chart"]["cl"], 3.2, _T2_CASE, context="CL=3.2")
        assert_close(result["t2_chart"]["ucl"][0], ucl,
                     _T2_CASE, context="UCL（Hotelling 个体观测公式）")
