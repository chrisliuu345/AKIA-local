"""
Edgeworth 近似能力指数 — 非参数能力评估

基于 Edgeworth 展开近似非正态分布的能力指数，
不需要假设特定分布或进行数据变换。

参考: Bowman KO, Shenton LR (1999) "Edgeworth approximations"
      Minitab Nonparametric Capability Analysis
"""

from typing import Any
import numpy as np
from scipy import stats


def analyze(
    data: np.ndarray,
    usl: float | None = None,
    lsl: float | None = None,
    target: float | None = None,
) -> dict[str, Any]:
    """
    Edgeworth 近似能力分析

    Args:
        data: 测量数据
        usl: 上规格限
        lsl: 下规格限
        target: 目标值

    Returns:
        Edgeworth 近似能力指数
    """
    clean = data[~np.isnan(data)].astype(float)
    n = len(clean)

    if n < 20:
        raise ValueError(f"数据量不足: 需要至少 20 个观测值，当前 {n}")

    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1))
    skewness = float(stats.skew(clean))
    kurtosis = float(stats.kurtosis(clean))

    if usl is None or lsl is None:
        return {
            "chart_type": "Edgeworth Approximation",
            "sample_size": n,
            "mean": round(mean, 6),
            "std": round(std, 6),
            "skewness": round(skewness, 6),
            "kurtosis": round(kurtosis, 6),
            "error": "未提供规格限，无法计算能力指数",
        }

    z_upper = (usl - mean) / std if std > 0 else 0
    z_lower = (mean - lsl) / std if std > 0 else 0

    pp_upper = _edgeworth_pp(z_upper, skewness, kurtosis)
    pp_lower = _edgeworth_pp(-z_lower, skewness, kurtosis)
    pp_total = pp_upper + pp_lower

    pct_above = pp_upper * 100
    pct_below = pp_lower * 100
    pct_total = pct_above + pct_below

    ppm_above = pp_upper * 1_000_000
    ppm_below = pp_lower * 1_000_000
    ppm_total = ppm_above + ppm_below

    cp_edgeworth = _edgeworth_cap_index(usl, lsl, mean, std, skewness, kurtosis, side="upper")
    cpk_edgeworth = min(
        _edgeworth_cap_index(usl, lsl, mean, std, skewness, kurtosis, side="upper"),
        _edgeworth_cap_index(usl, lsl, mean, std, skewness, kurtosis, side="lower"),
    )

    return {
        "chart_type": "Edgeworth Approximation",
        "sample_size": n,
        "mean": round(mean, 6),
        "std": round(std, 6),
        "skewness": round(skewness, 6),
        "kurtosis": round(kurtosis, 6),
        "usl": usl,
        "lsl": lsl,
        "z_upper": round(float(z_upper), 4),
        "z_lower": round(float(z_lower), 4),
        "pp_above": round(float(pp_upper), 6),
        "pp_below": round(float(pp_lower), 6),
        "pp_total": round(float(pp_total), 6),
        "pct_above": round(float(pct_above), 4),
        "pct_below": round(float(pct_below), 4),
        "pct_total": round(float(pct_total), 4),
        "ppm_above": round(float(ppm_above), 0),
        "ppm_below": round(float(ppm_below), 0),
        "ppm_total": round(float(ppm_total), 0),
        "cp_edgeworth": round(float(cp_edgeworth), 4),
        "cpk_edgeworth": round(float(cpk_edgeworth), 4),
        "interpretation": _edgeworth_interpretation(cpk_edgeworth),
    }


def _edgeworth_pp(z: float, skewness: float, kurtosis: float) -> float:
    """
    Edgeworth 展开近似尾部概率

    P(Z > z) ≈ Φ(-z) - φ(z) * [skewness * (z² - 1) / 6
                                + kurtosis * (z³ - 3z) / 24
                                + skewness² * (2z³ - 5z) / 36]
    """
    phi_z = stats.norm.pdf(z)
    Phi_z = stats.norm.cdf(z)

    correction = (
        skewness * (z ** 2 - 1) / 6
        + kurtosis * (z ** 3 - 3 * z) / 24
        + skewness ** 2 * (2 * z ** 3 - 5 * z) / 36
    )

    pp = (1 - Phi_z) - phi_z * correction

    return max(0, min(1, pp))


def _edgeworth_cap_index(
    usl: float,
    lsl: float,
    mean: float,
    std: float,
    skewness: float,
    kurtosis: float,
    side: str = "upper",
) -> float:
    """Edgeworth 近似能力指数"""
    if std == 0:
        return float('inf')

    if side == "upper":
        z = (usl - mean) / std
        pp = _edgeworth_pp(z, skewness, kurtosis)
        return -np.log10(pp) / 3 if pp > 0 else float('inf')
    else:
        z = -(lsl - mean) / std
        pp = _edgeworth_pp(z, skewness, kurtosis)
        return -np.log10(pp) / 3 if pp > 0 else float('inf')


def _edgeworth_interpretation(cpk: float) -> str:
    """Edgeworth 能力指数解释"""
    if cpk >= 2.0:
        return "优秀 — 过程能力远超要求"
    elif cpk >= 1.67:
        return "优秀 — 过程能力充足"
    elif cpk >= 1.33:
        return "良好 — 过程能力满足要求"
    elif cpk >= 1.0:
        return "可接受 — 过程能力基本满足"
    elif cpk >= 0.67:
        return "边缘 — 过程能力不足，需要改进"
    else:
        return "差 — 过程能力严重不足"
