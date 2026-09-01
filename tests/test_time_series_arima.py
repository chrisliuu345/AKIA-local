"""ARIMA 建模测试"""

import numpy as np
import pandas as pd
import pytest


class TestARIMA:

    def test_manual_order(self):
        from analysis.time_series.arima import analyze
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = analyze(data, order=(1, 1, 1), auto_select=False, forecast_steps=10)
        assert result["analysis_type"] == "time_series.arima"
        assert result["summary"]["order"] == [1, 1, 1]
        assert len(result["forecast"]) == 10
        assert result["summary"]["aic"] is not None

    def test_auto_select(self):
        from analysis.time_series.arima import analyze
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = analyze(data, auto_select=True, max_p=2, max_d=1, max_q=2, forecast_steps=5)
        assert "error" not in result
        order = result["summary"]["order"]
        assert len(order) == 3
        assert len(result["candidates"]) > 0

    def test_too_few_points(self):
        from analysis.time_series.arima import analyze
        data = pd.Series([1.0, 2.0, 3.0])
        result = analyze(data)
        assert "error" in result

    def test_diagnostics(self):
        from analysis.time_series.arima import analyze
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = analyze(data, order=(1, 1, 0), auto_select=False, forecast_steps=5)
        assert "ljung_box_p_value" in result["summary"]
        assert "durbin_watson" in result["summary"]
        assert result["summary"]["durbin_watson"] > 0


class TestAutoSelect:

    def test_returns_order(self):
        from analysis.time_series.arima import auto_select
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(80)))
        order, candidates = auto_select(data, max_p=2, max_d=1, max_q=2)
        assert order is not None
        assert len(candidates) > 0
        assert candidates[0]["aic"] <= candidates[-1]["aic"]  # sorted by AIC

    def test_candidates_sorted(self):
        from analysis.time_series.arima import auto_select
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(80)))
        _, candidates = auto_select(data, max_p=2, max_d=1, max_q=2)
        aics = [c["aic"] for c in candidates]
        assert aics == sorted(aics)
