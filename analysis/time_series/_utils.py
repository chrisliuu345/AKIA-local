"""时间序列分析 — 内部工具函数"""


import pandas as pd


def detect_period(data: pd.Series) -> int | None:
    """通过 ACF 峰值检测季节周期"""
    try:
        from statsmodels.tsa.stattools import acf
        vals = data.values.astype(float)
        n = len(vals)
        max_lags = min(n // 2, 40)
        if max_lags < 2:
            return None
        acf_vals = acf(vals, nlags=max_lags, fft=True)
        if len(acf_vals) < 3:
            return None
        peaks = []
        for i in range(2, len(acf_vals) - 1):
            if acf_vals[i] > acf_vals[i - 1] and acf_vals[i] > acf_vals[i + 1]:
                peaks.append((i, acf_vals[i]))
        if not peaks:
            return None
        peaks.sort(key=lambda x: x[1], reverse=True)
        return peaks[0][0]
    except Exception:  # noqa: BLE001 - 预处理失败：返回 None 由调用方判定
        return None
