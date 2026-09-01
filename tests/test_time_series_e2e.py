"""时间序列 E2E 测试 — 数据导入→ACF/PACF→建模→预测→可视化"""

import numpy as np
import pandas as pd
import pytest


class TestTimeSeriesE2E:

    def test_full_workflow(self):
        """完整工作流：生成数据 → ACF/PACF → 季节分解 → ARIMA → 预测"""
        from analysis.time_series import acf_pacf, seasonal_decomposition, arima, forecasting

        np.random.seed(42)
        n = 120
        t = np.arange(n)
        data = pd.Series(
            10 + 0.1 * t + 3 * np.sin(2 * np.pi * t / 12) + np.random.randn(n) * 0.3,
            name="销售额",
        )

        # Step 1: ACF/PACF 分析
        acf_result = acf_pacf.analyze(data, lags=20)
        assert acf_result["analysis_type"] == "time_series.acf_pacf"
        assert acf_result["summary"]["sample_size"] == n
        assert "is_stationary" in acf_result["summary"]

        # Step 2: 季节分解
        decomp_result = seasonal_decomposition.analyze(data, period=12)
        assert decomp_result["analysis_type"] == "time_series.seasonal_decomposition"
        assert decomp_result["summary"]["period"] == 12
        assert len(decomp_result["trend"]) == n

        # Step 3: ARIMA 建模（自动选阶）
        arima_result = arima.analyze(
            data, auto_select=True, max_p=2, max_d=1, max_q=2, forecast_steps=12,
        )
        assert arima_result["analysis_type"] == "time_series.arima"
        assert len(arima_result["forecast"]) == 12

        # Step 4: 模型对比
        compare_result = forecasting.compare_models(
            data, models=["arima", "double_exp"], forecast_steps=12,
        )
        assert compare_result["analysis_type"] == "time_series.model_comparison"
        assert len(compare_result["comparisons"]) >= 1
        assert "best_model" in compare_result["summary"]

    def test_with_excel_data(self):
        """模拟 Excel 导入数据的 E2E 测试"""
        from analysis.time_series import acf_pacf, arima

        np.random.seed(42)
        df = pd.DataFrame({
            "日期": pd.date_range("2024-01-01", periods=100, freq="D"),
            "测量值": np.cumsum(np.random.randn(100)) + 50,
        })

        value_col = "测量值"
        data = df[value_col].dropna()

        acf_result = acf_pacf.analyze(data, lags=15)
        assert acf_result["summary"]["sample_size"] == 100

        arima_result = arima.analyze(data, order=(1, 1, 1), auto_select=False, forecast_steps=10)
        assert len(arima_result["forecast"]) == 10

    def test_chart_generation(self):
        """测试图表生成不报错"""
        from analysis.time_series import acf_pacf
        from analysis.charts.chart_generator import generate_chart

        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = acf_pacf.analyze(data, lags=15)

        fig = generate_chart("ACF/PACF图", {
            "acf": result["acf"],
            "pacf": result["pacf"],
        })
        assert fig is not None

    def test_forecast_chart_generation(self):
        """测试预测图表生成"""
        from analysis.time_series import arima
        from analysis.charts.chart_generator import generate_chart

        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(80)))
        result = arima.analyze(data, order=(1, 1, 0), auto_select=False, forecast_steps=10)

        fig = generate_chart("预测图", {
            "historical": result["fitted_values"],
            "forecast": result["forecast"],
            "confidence_lower": result["confidence_lower"],
            "confidence_upper": result["confidence_upper"],
        })
        assert fig is not None


class TestForecasting:

    def test_predict_arima(self):
        from analysis.time_series.forecasting import predict
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(80)))
        result = predict(data, model="arima", forecast_steps=10)
        assert result["analysis_type"] == "time_series.forecast"
        assert len(result["forecast"]) == 10

    def test_predict_holt_winters(self):
        from analysis.time_series.forecasting import predict
        data = pd.Series(10 + 0.1 * np.arange(60) + 3 * np.sin(2 * np.pi * np.arange(60) / 12) + np.random.randn(60) * 0.3)
        result = predict(data, model="holt_winters", forecast_steps=6, seasonal_periods=12)
        assert result["analysis_type"] == "time_series.forecast"
        assert len(result["forecast"]) == 6

    def test_compare_models_3_default(self):
        from analysis.time_series.forecasting import compare_models
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = compare_models(data, forecast_steps=10)
        assert result["analysis_type"] == "time_series.model_comparison"
        assert len(result["comparisons"]) >= 1
        assert "best_model" in result["summary"]

    def test_compare_models_multiplicative(self):
        from analysis.time_series.forecasting import compare_models
        data = pd.Series(20 + 0.1 * np.arange(60) + 3 * np.sin(2 * np.pi * np.arange(60) / 12) + np.random.randn(60) * 0.3)
        result = compare_models(data, models=["holt_winters"], forecast_steps=6,
                                seasonal_periods=12, seasonal="multiplicative")
        assert result["comparisons"][0]["model"] == "Holt-Winters(Multiplicative)"

    def test_arima_residual_diagnostics(self):
        from analysis.time_series.arima import analyze
        np.random.seed(42)
        data = pd.Series(np.cumsum(np.random.randn(100)))
        result = analyze(data, order=(1, 1, 1), auto_select=False, forecast_steps=5)
        resid = result.get("residual_diagnostics", {})
        assert "acf_values" in resid
        assert "pacf_values" in resid
        assert "qq_theoretical" in resid
        assert "qq_sample" in resid
        assert len(resid["acf_values"]) > 0
        assert len(resid["qq_theoretical"]) == len(resid["qq_sample"])

    def test_qq_chart_generation(self):
        from analysis.charts.chart_generator import generate_chart
        fig = generate_chart("Q-Q图", {
            "qq_theoretical": [float(i) for i in range(-3, 4)],
            "qq_sample": [float(i) for i in range(-3, 4)],
        })
        assert fig is not None

    def test_resid_acf_pacf_chart_generation(self):
        from analysis.charts.chart_generator import generate_chart
        fig = generate_chart("残差ACF/PACF图", {
            "resid_acf": [0.1, -0.05, 0.02],
            "resid_pacf": [0.1, -0.05, 0.02],
        })
        assert fig is not None
