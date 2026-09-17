"""Weibull 2P-MLE 已知值（v4.2.0 P1 批次 2）。

来源: NIST/SEMATECH e-Handbook 8.1.5.1 MLE 方程
  Σ tᵢ^β ln tᵢ / Σ tᵢ^β − 1/β = (1/n)Σ ln tᵢ,  η = (Σ tᵢ^β / n)^(1/β)
数据 t=[1,2,3,4,5]：独立 brentq 求解（tol=1e-12）→ β=2.2938067, η=3.3942907。
引擎为数值优化，容差按实测收敛精度 1e-5 记录（notes 说明）。
"""

import math

from analysis.reliability.weibull import WeibullAnalyzer
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase(
    case_id="nist-weibull-2p-mle-12345",
    source="NIST/SEMATECH 8.1.5.1（MLE 方程独立求解）",
    reference="t=[1,2,3,4,5]：β=2.2938067, η=3.3942907",
    rel_tol=1e-6,
    abs_tol=2e-5,
    notes="β 与独立 brentq 解一致到 1e-6；η 受引擎数值优化收敛容差影响（实测 ~1e-5）",
)


class TestWeibullKnownValues:
    def test_2p_mle_matches_equation_solution(self):
        out = WeibullAnalyzer().analyze([1, 2, 3, 4, 5])
        assert out["error"] is None
        result = out["result"]
        assert result is not None
        assert result.method == "2P-MLE"

        assert_close(result.beta, 2.2938067, _CASE, context="形状参数 β")
        assert_close(result.eta, 3.3942907, _CASE, context="尺度参数 η")

    def test_b10_derived_from_exponential_formula(self):
        out = WeibullAnalyzer().analyze([1, 2, 3, 4, 5])
        result = out["result"]
        beta, eta = 2.2938067, 3.3942907
        expected_b10 = eta * math.pow(math.log(1 / 0.9), 1 / beta)
        assert_close(result.b10_life, expected_b10, _CASE,
                     context="B10 = η·(ln(1/0.9))^{1/β}")
