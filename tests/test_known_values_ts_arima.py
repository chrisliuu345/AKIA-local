"""ARIMA 已知值 — 随机游走点预测（v4.2.0 P1 批次 2）。

来源: Hyndman & Athanasopoulos, Forecasting: Principles and Practice (FPP3),
ARIMA(0,1,0) 即随机游走：任意步长点预测 = 最后观测值。
"""

import pandas as pd

from analysis.time_series.arima import analyze as arima_analyze
from tests.known_values import KnownValueCase, assert_allclose, assert_close

_CASE = KnownValueCase.with_preset(
    "fpp3-random-walk-forecast", "FPP3（ARIMA(0,1,0) = 随机游走）",
    preset="closed_form",
    reference="数据 10..19：3 步点预测恒为最后观测值 19",
)


class TestArimaKnownValues:
    def test_random_walk_forecast_is_last_value(self):
        data = pd.Series([float(v) for v in range(10, 20)])
        result = arima_analyze(data, order=(0, 1, 0), auto_select=False,
                               forecast_steps=3)

        assert result.get("error") is None
        assert result["summary"]["order"] == [0, 1, 0]
        assert_allclose(result["forecast"], [19.0, 19.0, 19.0], _CASE,
                        context="ARIMA(0,1,0) 点预测")
        assert_close(result["summary"]["sample_size"], 10.0, _CASE, context="样本量")
