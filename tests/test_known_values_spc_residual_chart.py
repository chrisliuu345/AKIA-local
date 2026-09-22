"""SPC 已知值 — 残差控制图（v4.2.0 P2-4）

命题: 自相关数据直接用 I-MR 会系统性误报；用 ARIMA 残差（白化）后误报回到名义水平。

覆盖:
1. AR(1)（φ=0.8）数据: 原始 I-MR 误报多、残差图显著减少；残差 lag-1 自相关接近 0
2. 白噪声数据: 两者量级相当
3. 结构契约: 诊断字段完整；ARIMA 失败时降级并给出原因
"""

import numpy as np
import pandas as pd
import pytest

from analysis.spc.residual_chart import analyze as residual_analyze
from tests.known_values import KnownValueCase, assert_close

_WHITEN_CASE = KnownValueCase(
    case_id="ar1-whitening-reduces-violations",
    source="合成 AR(1)（φ=0.8，固定种子）",
    reference="残差图越限点数 < 原始 I-MR 越限点数；残差 lag-1 自相关 |ρ| < 0.2",
    rel_tol=1e-9, abs_tol=0.2,
    notes="原始 lag-1 自相关应 > 0.5，作为白化前对照",
)


def _ar1(n: int = 300, phi: float = 0.8, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    noise = rng.normal(size=n + 200)
    series = np.zeros(n + 200)
    for t in range(1, n + 200):
        series[t] = phi * series[t - 1] + noise[t]
    return pd.Series(series[200:])


class TestResidualChart:
    def test_ar1_whitening_reduces_violations(self):
        series = _ar1()
        result = residual_analyze(series, order=(1, 0, 0))
        diagnostics = result["diagnostics"]

        assert result["fallback"] is False
        assert diagnostics["raw_lag1_autocorr"] > 0.5
        assert abs(diagnostics["residual_lag1_autocorr"]) < 0.2
        assert diagnostics["residual_violations"] < diagnostics["raw_violations"]
        assert diagnostics["improvement"]["violations_reduced"] > 0
        assert_close(diagnostics["residual_lag1_autocorr"], 0.0, _WHITEN_CASE,
                     context="残差 lag-1 自相关")

    def test_white_noise_behaves_like_raw(self):
        rng = np.random.default_rng(19)
        series = pd.Series(rng.normal(size=300))
        result = residual_analyze(series, order=(1, 0, 0))
        diagnostics = result["diagnostics"]
        assert abs(diagnostics["raw_lag1_autocorr"]) < 0.2
        assert diagnostics["residual_violations"] <= 20

    def test_auto_select_integration(self):
        series = _ar1(n=150, seed=11)
        result = residual_analyze(series, auto_select=True)
        assert result["fallback"] is False
        assert result["diagnostics"]["arima_order"] is not None
        assert len(result["residual_chart"]["i_chart"]["data"]) > 100

    def test_constant_series_falls_back(self):
        series = pd.Series(np.full(40, 2.5))
        result = residual_analyze(series, order=(1, 0, 1))
        assert result["fallback"] is True
        assert "常量" in result["fallback_reason"]
        assert result["residual_chart"]["chart_type"] == "I-MR"

    def test_fallback_when_arima_reports_error(self, monkeypatch):
        from analysis.spc import residual_chart

        monkeypatch.setattr(residual_chart.arima, "analyze",
                            lambda *a, **k: {"chart_type": "ARIMA", "error": "拟合失败: 模拟"})
        rng = np.random.default_rng(3)
        result = residual_analyze(pd.Series(rng.normal(size=60)), order=(1, 0, 0))
        assert result["fallback"] is True
        assert "模拟" in result["fallback_reason"]
        assert result["residual_chart"]["chart_type"] == "I-MR"
        assert "raw_lag1_autocorr" in result["diagnostics"]

    def test_short_series_raises(self):
        with pytest.raises(ValueError):
            residual_analyze(pd.Series([1.0, 2.0, 3.0]))
