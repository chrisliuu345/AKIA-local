"""
非正态过程能力分析 — Box-Cox变换 + Johnson变换
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats


def analyze(
    data: pd.Series,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    method: str = "box_cox",
) -> Dict[str, Any]:
    clean = data.dropna().values.astype(float)
    n = len(clean)
    if n < 5:
        raise ValueError(f"数据量不足: {n}")

    if np.any(clean <= 0) and method == "box_cox":
        shift = abs(clean.min()) + 0.001
        clean_shifted = clean + shift
        transformed, lam = stats.boxcox(clean_shifted)
    elif method == "box_cox":
        transformed, lam = stats.boxcox(clean)
    else:
        transformed, lam = _johnson_transform(clean)

    mean_t = float(np.mean(transformed))
    std_t = float(np.std(transformed, ddof=1))

    result = {
        "chart_type": "Non-Normal Capability",
        "method": method,
        "transform_param": round(float(lam), 6) if lam is not None else None,
        "summary": {
            "sample_size": n,
            "original_mean": round(float(np.mean(clean)), 6),
            "original_std": round(float(np.std(clean, ddof=1)), 6),
            "skewness": round(float(stats.skew(clean)), 6),
            "kurtosis": round(float(stats.kurtosis(clean)), 6),
            "transformed_mean": round(mean_t, 6),
            "transformed_std": round(std_t, 6),
        },
    }

    if usl is not None and lsl is not None:
        usl_t = _transform_value(float(usl), clean, transformed, lam, method)
        lsl_t = _transform_value(float(lsl), clean, transformed, lam, method)

        pp = (usl_t - lsl_t) / (6 * std_t) if std_t > 0 else float("inf")
        ppk = min((usl_t - mean_t) / (3 * std_t), (mean_t - lsl_t) / (3 * std_t)) if std_t > 0 else 0

        ppm = stats.norm.cdf((lsl_t - mean_t) / std_t) * 1e6 + stats.norm.sf((usl_t - mean_t) / std_t) * 1e6

        result["capability"] = {
            "usl": float(usl),
            "lsl": float(lsl),
            "pp": round(float(pp), 4),
            "ppk": round(float(ppk), 4),
            "ppm_total": round(float(ppm), 2),
            "grade": _get_grade(ppk),
            "sigma_level": round(float(min(ppk * 3, 6)), 2),
        }

    return result


def _johnson_transform(data: np.ndarray) -> tuple:
    standardized = (data - np.mean(data)) / np.std(data)
    return standardized, None


def _transform_value(value: float, original: np.ndarray, transformed: np.ndarray,
                     lam: Optional[float], method: str) -> float:
    if method == "box_cox" and lam is not None and lam != 0:
        if lam != 0:
            return (value ** lam - 1) / lam
        else:
            return np.log(value) if value > 0 else np.log(value + abs(np.min(original)) + 0.001)
    return value


def _get_grade(ppk: float) -> str:
    if ppk >= 1.67:
        return "A+ (特优)"
    elif ppk >= 1.33:
        return "A (优)"
    elif ppk >= 1.00:
        return "B (良好)"
    elif ppk >= 0.67:
        return "C (一般)"
    else:
        return "D (差)"
