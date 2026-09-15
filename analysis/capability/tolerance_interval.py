"""公差区间 — 正态/非参数"""

import numpy as np
from scipy import stats
from typing import Any


def tolerance_interval_normal(
    data: np.ndarray,
    confidence: float = 0.95,
    proportion: float = 0.99,
    method: str = "two-sided",
) -> dict[str, Any]:
    """正态公差区间

    基于正态分布假设，估计包含指定比例总体的区间。

    Args:
        data: 数据数组
        confidence: 置信水平（默认0.95）
        proportion: 总体比例（默认0.99，即99%的总体）
        method: "two-sided"（双侧）或 "one-sided"（单侧）

    Returns:
        Dict包含公差区间和统计量
    """
    data = np.asarray(data, dtype=float)
    clean = data[np.isfinite(data)]
    n = len(clean)

    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    if not 0 < confidence < 1:
        raise ValueError("confidence必须在0-1之间")

    if not 0 < proportion < 1:
        raise ValueError("proportion必须在0-1之间")

    x_bar = np.mean(clean)
    s = np.std(clean, ddof=1)

    if s == 0:
        return {
            "method": "Normal Tolerance Interval",
            "interval_method": method,
            "confidence": confidence,
            "proportion": proportion,
            "center": round(float(x_bar), 6),
            "lower": round(float(x_bar), 6),
            "upper": round(float(x_bar), 6),
            "width": 0.0,
            "sample_size": n,
            "sample_mean": round(float(x_bar), 6),
            "sample_std": 0.0,
            "k_factor": 0.0,
            "error": "标准差为0，公差区间退化为点",
        }

    alpha = 1 - confidence
    p = proportion

    if method == "two-sided":
        n - 1

        stats.norm.ppf((1 + p) / 2)
        stats.norm.ppf(1 - alpha / 2)

        k = _k_factor_two_sided(n, p, alpha)
    else:
        k = _k_factor_one_sided(n, p, alpha)

    lower = x_bar - k * s
    upper = x_bar + k * s

    return {
        "method": "Normal Tolerance Interval",
        "interval_method": method,
        "confidence": confidence,
        "proportion": proportion,
        "center": round(float(x_bar), 6),
        "lower": round(float(lower), 6),
        "upper": round(float(upper), 6),
        "width": round(float(upper - lower), 6),
        "sample_size": n,
        "sample_mean": round(float(x_bar), 6),
        "sample_std": round(float(s), 6),
        "k_factor": round(float(k), 6),
    }


def tolerance_interval_nonparam(
    data: np.ndarray,
    confidence: float = 0.95,
    proportion: float = 0.99,
    method: str = "two-sided",
) -> dict[str, Any]:
    """非参数公差区间

    不依赖分布假设，基于顺序统计量的非参数方法。

    Args:
        data: 数据数组
        confidence: 置信水平（默认0.95）
        proportion: 总体比例（默认0.99，即99%的总体）
        method: "two-sided"（双侧）或 "one-sided"（单侧）

    Returns:
        Dict包含公差区间和统计量
    """
    data = np.asarray(data, dtype=float)
    clean = data[np.isfinite(data)]
    n = len(clean)

    if n < 2:
        raise ValueError(f"数据量不足: {n}")

    if not 0 < confidence < 1:
        raise ValueError("confidence必须在0-1之间")

    if not 0 < proportion < 1:
        raise ValueError("proportion必须在0-1之间")

    sorted_data = np.sort(clean)

    alpha = 1 - confidence
    p = proportion

    if method == "two-sided":
        r, s = _find_order_statistics_two_sided(n, p, alpha)

        lower = sorted_data[r - 1]
        upper = sorted_data[s - 1]
    else:
        r = _find_order_statistics_one_sided(n, p, alpha)
        if r == 0:
            lower = sorted_data[0]
            upper = np.inf
        else:
            lower = sorted_data[r - 1]
            upper = sorted_data[-1]

    return {
        "method": "Nonparametric Tolerance Interval",
        "interval_method": method,
        "confidence": confidence,
        "proportion": proportion,
        "lower": round(float(lower), 6),
        "upper": round(float(upper), 6),
        "width": round(float(upper - lower), 6) if np.isfinite(upper - lower) else None,
        "sample_size": n,
        "order_lower": r if method == "two-sided" else (r if r > 0 else None),
        "order_upper": s if method == "two-sided" else None,
        "sample_median": round(float(np.median(clean)), 6),
    }


def _k_factor_two_sided(n: int, p: float, alpha: float) -> float:
    """计算双侧公差区间的k因子

    使用Johnson (1963) 的近似方法。
    """
    df = n - 1
    z_p = stats.norm.ppf((1 + p) / 2)
    z_alpha = stats.norm.ppf(1 - alpha / 2)

    chi2 = stats.chi2.ppf(1 - alpha, df)
    k = np.sqrt((1 + 1/n) * z_alpha**2 / chi2 * df) * z_p / z_alpha

    ncp = z_p * np.sqrt(n)
    k_approx = stats.nct.ppf(1 - alpha/2, df, ncp) / np.sqrt(n)

    return (k + k_approx) / 2


def _k_factor_one_sided(n: int, p: float, alpha: float) -> float:
    """计算单侧公差区间的k因子"""
    df = n - 1
    z_p = stats.norm.ppf(p)
    z_alpha = stats.norm.ppf(1 - alpha)

    chi2 = stats.chi2.ppf(1 - alpha, df)
    k = np.sqrt((1 + 1/n) * z_alpha**2 / chi2 * df) * z_p / z_alpha

    ncp = z_p * np.sqrt(n)
    k_approx = stats.nct.ppf(1 - alpha, df, ncp) / np.sqrt(n)

    return (k + k_approx) / 2


def _find_order_statistics_two_sided(n: int, p: float, alpha: float) -> tuple[int, int]:
    """找到双侧公差区间的顺序统计量位置

    寻找r和s使得：
    P(X_(r) ≤ 至少p比例的总体 ≤ X_(s)) ≥ 1-α

    使用累积二项分布CDF优化，复杂度从O(n³)降至O(n²)。
    """

    best_r, best_s = 1, n
    min_width = n

    for r in range(1, n):
        for s in range(r + 1, n + 1):
            prob = stats.binom.cdf(s - 1, n, p) - stats.binom.cdf(r - 1, n, p)

            if prob >= 1 - alpha and (s - r) < min_width:
                best_r, best_s = r, s
                min_width = s - r

    return best_r, best_s


def _find_order_statistics_one_sided(n: int, p: float, alpha: float) -> int:
    """找到单侧公差区间的顺序统计量位置

    寻找r使得：
    P(至少p比例的总体 ≥ X_(r)) ≥ 1-α

    使用累积二项分布CDF优化，复杂度从O(n²)降至O(n)。
    """

    for r in range(1, n + 1):
        prob = 1 - stats.binom.cdf(r - 1, n, p)

        if prob >= 1 - alpha:
            return r

    return 1
