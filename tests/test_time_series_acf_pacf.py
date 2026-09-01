"""时间序列 ACF/PACF 分析测试"""

import numpy as np
import pandas as pd
import pytest


class TestCheckStationarity:

    def test_stationary_series(self):
        from analysis.time_series.acf_pacf import check_stationarity
        np.random.seed(42)
        data = pd.Series(np.random.randn(200))
        result = check_stationarity(data)
        assert result["is_stationary"] is True
        assert result["p_value"] < 0.05

    def test_non_stationary_series(self):
        from analysis.time_series.acf_pacf import check_stationarity
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(200)))
        result = check_stationarity(data)
        assert result["is_stationary"] is False

    def test_too_few_points(self):
        from analysis.time_series.acf_pacf import check_stationarity
        data = pd.Series([1.0, 2.0, 3.0])
        result = check_stationarity(data)
        assert result["error"] is not None


class TestComputeACF:

    def test_basic_acf(self):
        from analysis.time_series.acf_pacf import compute_acf
        np.random.seed(42)
        data = pd.Series(np.random.randn(100))
        result = compute_acf(data, lags=20)
        assert "acf_values" in result
        assert len(result["acf_values"]) > 0
        assert result["acf_values"][0] == pytest.approx(1.0, abs=0.01)

    def test_acf_confidence_band(self):
        from analysis.time_series.acf_pacf import compute_acf
        np.random.seed(42)
        data = pd.Series(np.random.randn(100))
        result = compute_acf(data, lags=10)
        assert "confidence_band" in result
        # confidence band from lag 1 onward should be positive
        assert result["confidence_band"] >= 0


class TestComputePACF:

    def test_basic_pacf(self):
        from analysis.time_series.acf_pacf import compute_pacf
        np.random.seed(42)
        data = pd.Series(np.random.randn(100))
        result = compute_pacf(data, lags=20)
        assert "pacf_values" in result
        assert len(result["pacf_values"]) > 0


class TestAnalyze:

    def test_full_analysis(self):
        from analysis.time_series.acf_pacf import analyze
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = analyze(data, lags=15)
        assert result["analysis_type"] == "time_series.acf_pacf"
        assert result["summary"]["sample_size"] == 100
        assert "is_stationary" in result["summary"]
        assert "durbin_watson" in result["summary"]
        assert "acf" in result
        assert "pacf" in result

    def test_too_few_points(self):
        from analysis.time_series.acf_pacf import analyze
        data = pd.Series([1.0, 2.0])
        result = analyze(data)
        assert "error" in result

    def test_with_nan(self):
        from analysis.time_series.acf_pacf import analyze
        np.random.seed(42)
        data = pd.Series(np.random.randn(100))
        data.iloc[5] = np.nan
        result = analyze(data, lags=10)
        assert "error" not in result
