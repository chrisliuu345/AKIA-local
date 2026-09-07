"""
Capability Sixpack — 六合图

生成 Minitab 级别的 Capability Sixpack 六图联动:
1. 控制图 (Individual/MR 或 Xbar-R)
2. 能力直方图
3. 概率图 (正态性检验)
4. 统计量表
5. 不合格品率
6. 能力图 (Cp/Cpk/Pp/Ppk)

参考: Minitab Quality Tools > Capability Analysis > Sixpack
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats


def analyze(
    data: pd.Series,
    usl: Optional[float] = None,
    lsl: Optional[float] = None,
    target: Optional[float] = None,
    subgroup_size: int = 1,
) -> Dict[str, Any]:
    """
    Capability Sixpack 分析

    Args:
        data: 测量数据
        usl: 上规格限
        lsl: 下规格限
        target: 目标值
        subgroup_size: 子组大小 (1=Individual, >1=Xbar-R)

    Returns:
        包含六图数据的字典
    """
    clean = data.dropna().values.astype(float)
    n = len(clean)

    if n < 5:
        raise ValueError(f"数据量不足: 需要至少 5 个观测值，当前 {n}")

    mean = float(np.mean(clean))
    std_overall = float(np.std(clean, ddof=1))

    if subgroup_size > 1 and n >= subgroup_size:
        std_within = _estimate_within_sigma(clean, subgroup_size)
    else:
        std_within = std_overall

    control_chart = _control_chart_data(clean, subgroup_size)
    histogram = _histogram_data(clean, usl, lsl, mean, std_within)
    probability_plot = _probability_plot_data(clean, mean, std_overall)
    statistics = _statistics_data(clean, mean, std_overall, std_within, usl, lsl, target, subgroup_size)
    percent_defective = _percent_defective_data(clean, usl, lsl, mean, std_within)
    capability_plot = _capability_plot_data(clean, usl, lsl, mean, std_within, std_overall)

    return {
        "chart_type": "Capability Sixpack",
        "summary": {
            "sample_size": n,
            "mean": round(mean, 6),
            "std_overall": round(std_overall, 6),
            "std_within": round(std_within, 6),
            "subgroup_size": subgroup_size,
        },
        "control_chart": control_chart,
        "histogram": histogram,
        "probability_plot": probability_plot,
        "statistics": statistics,
        "percent_defective": percent_defective,
        "capability_plot": capability_plot,
    }


def _estimate_within_sigma(data: np.ndarray, subgroup_size: int) -> float:
    """估计组内标准差 (基于 MR 或 R-bar)"""
    if subgroup_size == 1:
        mr = np.abs(np.diff(data))
        mr_bar = np.mean(mr) if len(mr) > 0 else 0
        d2 = 1.128
        return mr_bar / d2 if d2 > 0 else 0
    else:
        n_subgroups = len(data) // subgroup_size
        if n_subgroups < 1:
            return float(np.std(data, ddof=1))
        subgroups = data[:n_subgroups * subgroup_size].reshape(n_subgroups, subgroup_size)
        ranges = np.max(subgroups, axis=1) - np.min(subgroups, axis=1)
        r_bar = np.mean(ranges)
        d2 = _get_d2(subgroup_size)
        return r_bar / d2 if d2 > 0 else 0


def _get_d2(n: int) -> float:
    """获取 d2 常数"""
    d2_table = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
    return d2_table.get(n, 1.128)


def _control_chart_data(data: np.ndarray, subgroup_size: int) -> Dict[str, Any]:
    """控制图数据 (I-MR 或 Xbar-R)"""
    n = len(data)

    if subgroup_size == 1:
        mr = np.abs(np.diff(data))
        mr_bar = float(np.mean(mr)) if len(mr) > 0 else 0
        d2 = 1.128
        sigma = mr_bar / d2 if d2 > 0 else 0
        mean = float(np.mean(data))

        i_ucl = mean + 3 * sigma
        i_lcl = mean - 3 * sigma

        mr_ucl = 3.267 * mr_bar
        mr_lcl = 0

        return {
            "type": "I-MR",
            "individual": {
                "data": [round(float(x), 4) for x in data],
                "center": round(mean, 4),
                "ucl": round(i_ucl, 4),
                "lcl": round(i_lcl, 4),
            },
            "moving_range": {
                "data": [round(float(x), 4) for x in mr],
                "center": round(mr_bar, 4),
                "ucl": round(mr_ucl, 4),
                "lcl": round(mr_lcl, 4),
            },
        }
    else:
        n_subgroups = n // subgroup_size
        subgroups = data[:n_subgroups * subgroup_size].reshape(n_subgroups, subgroup_size)
        x_bar = np.mean(subgroups, axis=1)
        ranges = np.max(subgroups, axis=1) - np.min(subgroups, axis=1)

        x_bar_mean = float(np.mean(x_bar))
        r_bar = float(np.mean(ranges))

        d2 = _get_d2(subgroup_size)
        a2 = _get_a2(subgroup_size)

        sigma = r_bar / d2 if d2 > 0 else 0
        x_ucl = x_bar_mean + a2 * r_bar
        x_lcl = x_bar_mean - a2 * r_bar

        d4 = _get_d4(subgroup_size)
        r_ucl = d4 * r_bar

        return {
            "type": "Xbar-R",
            "xbar": {
                "data": [round(float(x), 4) for x in x_bar],
                "center": round(x_bar_mean, 4),
                "ucl": round(x_ucl, 4),
                "lcl": round(x_lcl, 4),
            },
            "range": {
                "data": [round(float(x), 4) for x in ranges],
                "center": round(r_bar, 4),
                "ucl": round(r_ucl, 4),
                "lcl": 0,
            },
        }


def _get_a2(n: int) -> float:
    """获取 A2 常数"""
    a2_table = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
    return a2_table.get(n, 0.577)


def _get_d4(n: int) -> float:
    """获取 D4 常数"""
    d4_table = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
    return d4_table.get(n, 2.114)


def _histogram_data(
    data: np.ndarray,
    usl: Optional[float],
    lsl: Optional[float],
    mean: float,
    std: float,
) -> Dict[str, Any]:
    """直方图数据 + 正态拟合曲线"""
    n_bins = min(50, max(10, int(np.sqrt(len(data)))))
    counts, bin_edges = np.histogram(data, bins=n_bins)

    if usl is not None and lsl is not None:
        x_range = np.linspace(lsl - 3 * std, usl + 3 * std, 200)
    else:
        x_range = np.linspace(mean - 4 * std, mean + 4 * std, 200)

    normal_pdf = stats.norm.pdf(x_range, mean, std)
    bin_width = bin_edges[1] - bin_edges[0]
    normal_scaled = normal_pdf * len(data) * bin_width

    return {
        "counts": counts.tolist(),
        "bin_edges": [round(float(x), 4) for x in bin_edges],
        "x_range": [round(float(x), 4) for x in x_range],
        "normal_curve": [round(float(x), 4) for x in normal_scaled],
        "usl": usl,
        "lsl": lsl,
        "target": (usl + lsl) / 2 if usl is not None and lsl is not None else None,
    }


def _probability_plot_data(
    data: np.ndarray,
    mean: float,
    std: float,
) -> Dict[str, Any]:
    """概率图数据 (正态性检验)"""
    sorted_data = np.sort(data)
    n = len(sorted_data)
    theoretical = stats.norm.ppf(np.arange(1, n + 1) / (n + 1), mean, std)

    ks_stat, ks_p = stats.kstest(data, lambda x: stats.norm.cdf(x, loc=mean, scale=std))

    return {
        "observed": [round(float(x), 4) for x in sorted_data],
        "theoretical": [round(float(x), 4) for x in theoretical],
        "ks_statistic": round(float(ks_stat), 6),
        "ks_p_value": round(float(ks_p), 6),
        "is_normal": ks_p > 0.05,
        "mean": round(mean, 4),
        "std": round(std, 4),
    }


def _statistics_data(
    data: np.ndarray,
    mean: float,
    std_overall: float,
    std_within: float,
    usl: Optional[float],
    lsl: Optional[float],
    target: Optional[float],
    subgroup_size: int,
) -> Dict[str, Any]:
    """统计量数据"""
    n = len(data)
    result = {
        "sample_size": n,
        "mean": round(mean, 6),
        "std_overall": round(std_overall, 6),
        "std_within": round(std_within, 6),
    }

    if usl is not None and lsl is not None and std_within > 0:
        cp = (usl - lsl) / (6 * std_within)
        cpk = min((usl - mean) / (3 * std_within), (mean - lsl) / (3 * std_within))
        pp = (usl - lsl) / (6 * std_overall) if std_overall > 0 else 0
        ppk = min((usl - mean) / (3 * std_overall), (mean - lsl) / (3 * std_overall)) if std_overall > 0 else 0

        cpm = None
        if target is not None:
            sigma_t = _estimate_sigma_t(data, target)
            cpm = (usl - lsl) / (6 * sigma_t) if sigma_t > 0 else float('inf')

        result.update({
            "cp": round(float(cp), 4),
            "cpk": round(float(cpk), 4),
            "pp": round(float(pp), 4),
            "ppk": round(float(ppk), 4),
            "cpm": round(float(cpm), 4) if cpm is not None else None,
        })

        result["grade"] = _capability_grade(cpk)

    return result


def _estimate_sigma_t(data: np.ndarray, target: float) -> float:
    """估计 Cpm 的 sigma_t"""
    return float(np.sqrt(np.mean((data - target) ** 2)))


def _capability_grade(cpk: float) -> str:
    """能力等级判定"""
    if cpk >= 1.67:
        return "A+ (优秀)"
    elif cpk >= 1.33:
        return "A (良好)"
    elif cpk >= 1.00:
        return "B (可接受)"
    elif cpk >= 0.67:
        return "C (边缘)"
    else:
        return "D (差)"


def _percent_defective_data(
    data: np.ndarray,
    usl: Optional[float],
    lsl: Optional[float],
    mean: float,
    std: float,
) -> Dict[str, Any]:
    """不合格品率数据"""
    len(data)

    if usl is None and lsl is None:
        return {"ppm_total": 0, "pct_total": 0}

    ppm_above = 0
    ppm_below = 0

    if usl is not None:
        z_upper = (usl - mean) / std if std > 0 else 0
        ppm_above = (1 - stats.norm.cdf(z_upper)) * 1_000_000

    if lsl is not None:
        z_lower = (mean - lsl) / std if std > 0 else 0
        ppm_below = (1 - stats.norm.cdf(z_lower)) * 1_000_000

    ppm_total = ppm_above + ppm_below
    pct_total = ppm_total / 10_000

    return {
        "ppm_above": round(float(ppm_above), 0),
        "ppm_below": round(float(ppm_below), 0),
        "ppm_total": round(float(ppm_total), 0),
        "pct_above": round(float(ppm_above / 10_000), 4),
        "pct_below": round(float(ppm_below / 10_000), 4),
        "pct_total": round(float(pct_total), 4),
    }


def _capability_plot_data(
    data: np.ndarray,
    usl: Optional[float],
    lsl: Optional[float],
    mean: float,
    std_within: float,
    std_overall: float,
) -> Dict[str, Any]:
    """能力图数据 (Cp/Cpk/Pp/Ppk 对比)"""
    if usl is None or lsl is None or std_within == 0:
        return {"indices": [], "values": []}

    cp = (usl - lsl) / (6 * std_within)
    cpk = min((usl - mean) / (3 * std_within), (mean - lsl) / (3 * std_within))
    pp = (usl - lsl) / (6 * std_overall) if std_overall > 0 else 0
    ppk = min((usl - mean) / (3 * std_overall), (mean - lsl) / (3 * std_overall)) if std_overall > 0 else 0

    indices = ["Cp", "Cpk", "Pp", "Ppk"]
    values = [round(float(cp), 4), round(float(cpk), 4), round(float(pp), 4), round(float(ppk), 4)]

    return {
        "indices": indices,
        "values": values,
        "target_line": 1.33,
    }
