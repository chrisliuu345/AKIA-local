"""
非正态过程能力分析 — Box-Cox变换 + Johnson变换

注意: Johnson 变换当前为 z-score 标准化(近似), 规格限按同一标准化参数变换。
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

    shift = 0.0
    lam: Optional[float] = None
    if method == "box_cox":
        if np.any(clean <= 0):
            shift = abs(clean.min()) + 0.001
            transformed, lam = stats.boxcox(clean + shift)
        else:
            transformed, lam = stats.boxcox(clean)
    else:
        transformed, lam = _johnson_transform(clean)

    mean_t = float(np.mean(transformed))
    std_t = float(np.std(transformed, ddof=1))
    mean_orig = float(np.mean(clean))
    std_orig = float(np.std(clean, ddof=1))

    result = {
        "chart_type": "Non-Normal Capability",
        "method": method,
        "transform_param": round(float(lam), 6) if lam is not None else None,
        "summary": {
            "sample_size": n,
            "original_mean": round(mean_orig, 6),
            "original_std": round(std_orig, 6),
            "skewness": round(float(stats.skew(clean)), 6),
            "kurtosis": round(float(stats.kurtosis(clean)), 6),
            "transformed_mean": round(mean_t, 6),
            "transformed_std": round(std_t, 6),
        },
    }

    has_usl = usl is not None
    has_lsl = lsl is not None
    if not (has_usl or has_lsl):
        return result

    usl_t = _transform_value(float(usl), method, lam, shift, mean_orig, std_orig) if has_usl else None
    lsl_t = _transform_value(float(lsl), method, lam, shift, mean_orig, std_orig) if has_lsl else None

    if has_usl and has_lsl:
        pp = (usl_t - lsl_t) / (6 * std_t) if std_t > 0 else float("inf")
        ppk = min((usl_t - mean_t) / (3 * std_t), (mean_t - lsl_t) / (3 * std_t)) if std_t > 0 else 0
        ppm = stats.norm.cdf((lsl_t - mean_t) / std_t) * 1e6 + stats.norm.sf((usl_t - mean_t) / std_t) * 1e6
    elif has_usl:
        pp = (usl_t - mean_t) / (3 * std_t) if std_t > 0 else float("inf")
        ppk = pp
        ppm = stats.norm.sf((usl_t - mean_t) / std_t) * 1e6
    else:
        pp = (mean_t - lsl_t) / (3 * std_t) if std_t > 0 else float("inf")
        ppk = pp
        ppm = stats.norm.cdf((lsl_t - mean_t) / std_t) * 1e6

    capability = {
        "pp": round(float(pp), 4),
        "ppk": round(float(ppk), 4),
        "ppm_total": round(float(ppm), 2),
        "grade": _get_grade(ppk),
        "sigma_level": round(float(min(ppk * 3, 6)), 2),
    }
    if has_usl:
        capability["usl"] = float(usl)
        capability["ppu"] = round(float(pp), 4)
    if has_lsl:
        capability["lsl"] = float(lsl)
        capability["ppl"] = round(float(pp), 4)
    result["capability"] = capability

    return result


def _johnson_transform(data: np.ndarray) -> tuple:
    """z-score 标准化(Johnson 变换的近似实现)"""
    std = np.std(data, ddof=1)
    if std <= 0:
        return np.zeros_like(data), None
    return (data - np.mean(data)) / std, None


def _transform_value(value: float, method: str, lam: Optional[float],
                     shift: float, mean: float, std: float) -> float:
    """把原始尺度下的规格限变换到变换后尺度, 与数据变换口径完全一致"""
    if method == "johnson":
        return (value - mean) / std if std > 0 else value
    x = value + shift
    if x <= 0:
        return -1e9
    if lam == 0:
        return float(np.log(x))
    return float((x ** lam - 1) / lam)


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
