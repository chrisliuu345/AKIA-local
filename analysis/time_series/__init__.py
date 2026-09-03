"""时间序列分析 — ACF/PACF / 平稳性检验 / 季节性分解 / 指数平滑 / ARIMA / 预测"""

_SUBMODULES = {
    "acf_pacf": ".acf_pacf",
    "seasonal_decomposition": ".seasonal_decomposition",
    "exponential_smoothing": ".exponential_smoothing",
    "arima": ".arima",
    "forecasting": ".forecasting",
}

__all__ = ["acf_pacf", "seasonal_decomposition", "exponential_smoothing", "arima", "forecasting"]


def __getattr__(name):
    import importlib
    if name in _SUBMODULES:
        mod = importlib.import_module(_SUBMODULES[name], __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
