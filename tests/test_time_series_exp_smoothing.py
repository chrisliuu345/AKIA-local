"""时间序列季节性分解 + 指数平滑测试"""

import numpy as np
import pandas as pd


def _seasonal_data(n=120, period=12):
    t = np.arange(n)
    return pd.Series(10 + 0.1 * t + 3 * np.sin(2 * np.pi * t / period) + np.random.randn(n) * 0.3)


class TestSeasonalDecomposition:

    def test_basic_decomposition(self):
        from analysis.time_series.seasonal_decomposition import analyze
        data = _seasonal_data()
        result = analyze(data, period=12)
        assert result["analysis_type"] == "time_series.seasonal_decomposition"
        assert result["summary"]["period"] == 12
        assert len(result["trend"]) == 120
        assert len(result["seasonal"]) == 120
        assert len(result["residual"]) == 120

    def test_stl_method(self):
        from analysis.time_series.seasonal_decomposition import analyze
        data = _seasonal_data()
        result = analyze(data, period=12, method="stl")
        assert result["summary"]["method"] == "stl"
        assert result["summary"]["trend_strength"] > 0.5

    def test_multiplicative_model(self):
        from analysis.time_series.seasonal_decomposition import analyze
        data = _seasonal_data() + 20  # 全部为正
        result = analyze(data, period=12, model="multiplicative")
        assert result["summary"]["model"] == "multiplicative"

    def test_too_few_points(self):
        from analysis.time_series.seasonal_decomposition import analyze
        data = pd.Series([1.0, 2.0])
        result = analyze(data)
        assert "error" in result

    def test_auto_detect_period(self):
        from analysis.time_series.seasonal_decomposition import analyze
        data = _seasonal_data(n=200, period=12)
        result = analyze(data, period=None)
        assert "error" not in result
        assert result["summary"]["period"] >= 2


class TestExponentialSmoothing:

    def test_holt_winters(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = _seasonal_data()
        result = analyze(data, method="holt_winters", seasonal="additive",
                         seasonal_periods=12, forecast_steps=12)
        assert result["analysis_type"] == "time_series.exponential_smoothing"
        assert result["summary"]["method"] == "holt_winters"
        assert len(result["forecast"]) == 12
        assert result["summary"]["aic"] is not None

    def test_double_exp(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = pd.Series(np.cumsum(np.random.randn(100)) + 10)
        result = analyze(data, method="double", forecast_steps=6)
        assert result["summary"]["method"] == "double"
        assert len(result["forecast"]) == 6

    def test_single_exp(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = pd.Series(np.random.randn(50) + 10)
        result = analyze(data, method="single", forecast_steps=5)
        assert result["summary"]["method"] == "single"
        assert len(result["forecast"]) == 5

    def test_too_few_points(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = pd.Series([1.0, 2.0])
        result = analyze(data)
        assert "error" in result

    def test_confidence_intervals(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = _seasonal_data()
        result = analyze(data, method="holt_winters", seasonal="additive",
                         seasonal_periods=12, forecast_steps=12)
        assert len(result["confidence_lower"]) == 12
        assert len(result["confidence_upper"]) == 12
        for i in range(12):
            assert result["confidence_lower"][i] <= result["forecast"][i] <= result["confidence_upper"][i]


class TestHoltWintersMultiplicative:

    def test_multiplicative_seasonal(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = _seasonal_data() + 20  # 全部为正
        result = analyze(data, method="holt_winters", seasonal="multiplicative",
                         seasonal_periods=12, forecast_steps=12)
        assert result["summary"]["seasonal"] == "multiplicative"
        assert len(result["forecast"]) == 12

    def test_multiplicative_requires_positive(self):
        from analysis.time_series.exponential_smoothing import analyze
        data = pd.Series([-5, -3, -1, 1, 3, 5, -5, -3, -1, 1, 3, 5, -5, -3, -1, 1, 3, 5])
        result = analyze(data, method="holt_winters", seasonal="multiplicative",
                         seasonal_periods=6, forecast_steps=6)
        assert "error" in result


class TestDetectPeriod:

    def test_detect_period_basic(self):
        from analysis.time_series._utils import detect_period
        data = _seasonal_data(n=200, period=12)
        result = detect_period(data)
        assert result == 12

    def test_detect_period_short_series(self):
        from analysis.time_series._utils import detect_period
        data = pd.Series([1.0, 2.0, 3.0])
        result = detect_period(data)
        assert result is None

    def test_detect_period_constant(self):
        from analysis.time_series._utils import detect_period
        data = pd.Series([5.0] * 50)
        result = detect_period(data)
        assert result is None
