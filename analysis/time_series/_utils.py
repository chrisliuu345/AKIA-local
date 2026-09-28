"""时间序列分析 — 内部工具函数"""


import pandas as pd

from analysis._sanitize import sanitize_series


def clean_series(data: pd.Series) -> pd.Series:
    """时间序列入口净化 —— 统一走 ``analysis._sanitize.sanitize_series``。

    为什么必须净化（2026-09-28 质量审查）：
      1. ``dropna()`` 只处理 NaN，±inf 会穿透并进入 statsmodels，导致拟合产生全 NaN
         残差，最终在 Ljung-Box 处抛 ``IndexError: index 0 is out of bounds``；
      2. 去缺失后索引有空洞时，statsmodels 无法构建预测索引
         （``ValueError: No supported index is available``）——必须 ``reset_index``。
    """
    return sanitize_series(data)


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
