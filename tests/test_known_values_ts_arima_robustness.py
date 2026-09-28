"""ARIMA 自动选阶稳健性（v4.2.0 P2-7）

覆盖边界与退化场景，确保"不崩溃 + 结构化结果 + 搜索空间合理":
1. 缺测序列（索引空洞）—— 旧实现 dropna 后保留空洞索引，get_forecast 抛
   "No supported index is available" 直接崩溃（本文件为回归守卫）
2. 常量序列 —— 不拟合无意义模型，返回结构化 error
3. 极短序列 —— 搜索空间按样本量收窄，不再试探高阶模型
4. 随机游走 —— 差分阶数 d ≥ 1
5. 季节序列 —— 结果有限、残差诊断可用
6. 候选集按 AIC 升序（选阶依据可解释）
"""

import numpy as np
import pandas as pd

from analysis.time_series import arima
from tests.known_values import KnownValueCase, assert_close

_SHORT_CASE = KnownValueCase(
    case_id="arima-short-series-order-bound",
    source="本仓库稳健性约定（v4.2.0 P2-7）",
    reference="n=14 时 p、q ≤ ⌊n/5⌋=2，d ≤ ⌊(n−1)/10⌋=1",
    rel_tol=1e-9, abs_tol=1e-9,
    notes="参数个数必须少于观测数，避免高阶假收敛",
)


def _analyze(series: pd.Series, **kwargs) -> dict:
    defaults = {"max_p": 2, "max_d": 2, "max_q": 2, "forecast_steps": 3}
    defaults.update(kwargs)
    return arima.analyze(series, **defaults)


class TestMissingValuesRegression:
    def test_series_with_gaps_does_not_crash(self):
        rng = np.random.default_rng(3)
        values = rng.normal(size=120)
        values[rng.random(120) < 0.05] = np.nan
        result = _analyze(pd.Series(values))
        assert "error" not in result, result.get("error")
        assert all(np.isfinite(result["forecast"]))
        assert result["summary"]["sample_size"] == int(np.isfinite(values).sum())

    def test_gapped_index_is_normalised(self):
        series = pd.Series([np.nan, 1.0, 2.0, np.nan, 3.0, 4.5, 5.0, np.nan,
                            7.0, 8.5, 9.0, 11.0, 12.5, 13.0])
        result = _analyze(series, max_p=1, max_d=1, max_q=1)
        assert "error" not in result, result.get("error")
        assert all(np.isfinite(result["forecast"]))


class TestDegenerateSeries:
    def test_constant_series_reports_structured_error(self):
        result = _analyze(pd.Series(np.full(60, 5.0)))
        assert "常量" in result["error"]
        assert result["chart_type"] == "ARIMA"

    def test_short_series_reports_insufficient_data(self):
        result = _analyze(pd.Series([1.0, 2.0, 3.0]))
        assert "不足" in result["error"]

    def test_too_short_for_any_model(self):
        rng = np.random.default_rng(4)
        result = _analyze(pd.Series(rng.normal(size=11)), max_p=3, max_d=1, max_q=3)
        assert "error" not in result or "失败" in result["error"]
        if "error" not in result:
            assert all(np.isfinite(result["forecast"]))


class TestSearchSpace:
    def test_short_series_bounds_search_space(self):
        rng = np.random.default_rng(5)
        series = pd.Series(rng.normal(size=14))
        order, candidates = arima.auto_select(series, max_p=5, max_d=2, max_q=5)
        assert order is not None
        p, d, q = order
        bound_p = min(5, 14 // 5)
        bound_q = min(5, 14 // 5)
        bound_d = min(2, (14 - 1) // 10)
        # 搜索空间上界被收窄：候选集的极大阶数不得超过按样本量推导的上界
        assert_close(max(c["order"][0] for c in candidates), bound_p,
                     _SHORT_CASE, context="p 上界")
        assert_close(max(c["order"][2] for c in candidates), bound_q,
                     _SHORT_CASE, context="q 上界")
        assert max(c["order"][1] for c in candidates) <= bound_d
        assert p <= bound_p and q <= bound_q and d <= bound_d

    def test_candidates_sorted_by_aic(self):
        rng = np.random.default_rng(6)
        series = pd.Series(rng.normal(size=100))
        order, candidates = arima.auto_select(series, max_p=2, max_d=1, max_q=2)
        aics = [c["aic"] for c in candidates]
        assert aics == sorted(aics)
        assert tuple(candidates[0]["order"]) == order


class TestStochasticStructure:
    def test_random_walk_uses_differencing(self):
        rng = np.random.default_rng(7)
        walk = pd.Series(np.cumsum(rng.normal(size=120)))
        result = _analyze(walk)
        assert "error" not in result, result.get("error")
        assert result["summary"]["order"][1] >= 1
        assert all(np.isfinite(result["forecast"]))

    def test_seasonal_series_produces_finite_diagnostics(self):
        rng = np.random.default_rng(8)
        idx = np.arange(144)
        series = pd.Series(10 + 3 * np.sin(idx * 2 * np.pi / 12)
                           + rng.normal(size=144))
        result = _analyze(series, forecast_steps=12)
        assert "error" not in result, result.get("error")
        assert len(result["forecast"]) == 12
        assert all(np.isfinite(result["confidence_lower"]))
        assert all(np.isfinite(result["confidence_upper"]))
        assert np.isfinite(result["summary"]["durbin_watson"])
        assert 0.0 <= result["summary"]["ljung_box_p_value"] <= 1.0

    def test_forecast_bounds_ordered(self):
        rng = np.random.default_rng(9)
        result = _analyze(pd.Series(rng.normal(size=80)), forecast_steps=5)
        assert "error" not in result, result.get("error")
        for low, high in zip(result["confidence_lower"],
                             result["confidence_upper"], strict=True):
            assert low <= high
