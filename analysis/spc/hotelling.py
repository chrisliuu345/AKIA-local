"""
Hotelling T² 多元控制图 — 单样本/多变量监控

参考: Hotelling (1947) "Multivariate Quality Control"
"""

from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd
from scipy import stats


def analyze(
    data: pd.DataFrame,
    columns: List[str],
    subgroup_col: Optional[str] = None,
    phase: str = "phase1",
    alpha: float = 0.0027,
) -> Dict[str, Any]:
    """
    Hotelling T² 分析

    Args:
        data: 数据框
        columns: 分析变量列表（至少 2 个）
        subgroup_col: 子组 ID 列名（可选，用于子组数据）
        phase: "phase1"（历史数据）或 "phase2"（未来数据）
        alpha: 显著性水平（默认 0.0027 对应 3σ）

    Returns:
        分析结果字典
    """
    if len(columns) < 2:
        raise ValueError("Hotelling T² 需要至少 2 个变量")

    df = data[columns].dropna()
    if len(df) < len(columns) + 1:
        raise ValueError(f"数据量不足: {len(df)}，需要至少 {len(columns) + 1}")

    X = df.values.astype(float)
    n, p = X.shape

    mean_vec = np.mean(X, axis=0)
    cov_matrix = np.cov(X, rowvar=False)

    if np.linalg.matrix_rank(cov_matrix) < p:
        cov_matrix += np.eye(p) * 1e-10

    cov_inv = np.linalg.inv(cov_matrix)

    if subgroup_col is not None and subgroup_col in data.columns:
        groups = data[subgroup_col].unique()
        t2_values = []
        for grp in groups:
            mask = data[subgroup_col] == grp
            subgroup_data = data.loc[mask, columns].dropna()
            if len(subgroup_data) >= 1:
                x_bar = subgroup_data.mean().values
                t2 = _compute_t2(x_bar, mean_vec, cov_inv, len(subgroup_data))
                t2_values.append(t2)
            else:
                t2_values.append(0)
        t2_values = np.array(t2_values)
        sample_sizes = [len(data.loc[data[subgroup_col] == g, columns].dropna())
                        for g in groups]
    else:
        t2_values = np.array([_compute_t2(x, mean_vec, cov_inv, 1) for x in X])
        sample_sizes = [1] * n

    ucl = _compute_ucl(p, n, alpha, sample_sizes)
    cl = _compute_cl(p, n, sample_sizes)

    violations = []
    for i, t2 in enumerate(t2_values):
        limit = float(ucl[i]) if isinstance(ucl, np.ndarray) else float(ucl)
        if np.isfinite(limit) and t2 > limit:
            violations.append({
                "point": int(i + 1),
                "rule": "T² UCL",
                "desc": f"T²超出控制限 ({t2:.3f} > {limit:.3f})",
                "value": round(float(t2), 6),
            })

    q_values = []
    for _, x in enumerate(X):
        deviation = x - mean_vec
        q = deviation.T @ cov_inv @ deviation
        q_values.append(q)

    return {
        "chart_type": "Hotelling T²",
        "phase": phase,
        "num_variables": p,
        "num_samples": n,
        "t2_chart": {
            "data": t2_values.tolist(),
            "cl": round(float(cl), 6) if isinstance(cl, (int, float)) else [round(float(c), 6) for c in cl],
            "ucl": round(float(ucl), 6) if isinstance(ucl, (int, float)) else [round(float(u), 6) for u in ucl],
            "violations": violations,
        },
        "summary": {
            "mean_vector": [round(float(m), 6) for m in mean_vec],
            "cov_matrix": [[round(float(c), 6) for c in row] for row in cov_matrix],
            "correlation_matrix": [[round(float(c), 6) for c in row] for row in np.corrcoef(X.T)],
        },
        "hotelling_test": _multivariate_normality_test(X, mean_vec, cov_matrix),
    }


def _compute_t2(x: np.ndarray, mean: np.ndarray, cov_inv: np.ndarray, n: int) -> float:
    """计算单个 T² 统计量"""
    deviation = x - mean
    return float(n * deviation.T @ cov_inv @ deviation)


def _individual_ucl(m: int, p: int, alpha: float) -> float:
    """单体观测（子组大小=1）的 T² 控制限。

    Montgomery《Introduction to Statistical Quality Control》个体观测形式：

        UCL = p(m-1)(m+1) / (m(m-p)) · F(1-α; p, m-p)

    m 为观测数。旧实现把个体观测当作子组大小=1 的子组代入子组公式，
    (m-1) 项恒为 0 → UCL=0、全部点误报越限。
    """
    if m - p <= 0:
        return float("nan")
    f_crit = stats.f.ppf(1 - alpha, p, m - p)
    return float(p * (m - 1) * (m + 1) / (m * (m - p)) * f_crit)


def _compute_ucl(
    p: int,
    n: int,
    alpha: float,
    sample_sizes: Optional[List[int]] = None,
):
    """计算 UCL（逐点，返回标量或与样本数等长的数组）。

    - 子组大小均 ≤1（无子组列）：个体观测限 ``_individual_ucl``
    - 子组数据：Tracy-Young-Mason (1992) Phase I 子组公式
      ``p(m-1)(n_i-1)/(N-m-p+1) · F(1-α; p, N-m-p+1)``，
      m 为子组数、N 为总观测数。旧实现误用总观测数代入系数与自由度，
      控制限约为正确值的 1/6，导致大量误报。
    - 自由度退化（数据量不足）时回退个体观测限，仍不可用则返回 NaN
      （调用方据此提示"控制限不可用"）
    """
    sizes = [int(s) for s in sample_sizes] if sample_sizes else []
    if not sizes or all(s <= 1 for s in sizes):
        m = len(sizes) if sizes else n
        ucl = _individual_ucl(m, p, alpha)
        return np.array([ucl] * len(sizes)) if len(sizes) > 1 else ucl

    m = len(sizes)
    total = sum(sizes)
    df2 = total - m - p + 1
    if df2 <= 0:
        ucl_values = np.array([_individual_ucl(m, p, alpha)] * m)
    else:
        f_crit = stats.f.ppf(1 - alpha, p, df2)
        ucl_values = np.array(
            [p * (m - 1) * (ni - 1) / df2 * f_crit for ni in sizes])
    return ucl_values if m > 1 else float(ucl_values[0])


def _compute_cl(p: int, n: int, sample_sizes: Optional[List[int]] = None) -> float:
    """计算中心线（期望值）"""
    return p * (n - 1) / (n - p) * (n + 1) / n


def _multivariate_normality_test(
    X: np.ndarray,
    mean: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """多元正态性检验（基于 Mardia 偏度/峰度）"""
    n, p = X.shape

    centered = X - mean
    cov_inv = np.linalg.inv(cov + np.eye(p) * 1e-10)

    g1 = 0
    for i in range(n):
        for j in range(n):
            xi = centered[i]
            xj = centered[j]
            g1 += (xi.T @ cov_inv @ xj) ** 3
    g1 = g1 / (n ** 2)

    g2 = 0
    for i in range(n):
        xi = centered[i]
        g2 += (xi.T @ cov_inv @ xi) ** 2
    g2 = g2 / n

    skew_stat = n * g1 / 6
    kurt_stat = (g2 - p * (p + 2)) * np.sqrt(n / (8 * p * (p + 2)))

    return {
        "skewness_statistic": round(float(skew_stat), 4),
        "kurtosis_statistic": round(float(kurt_stat), 4),
        "interpretation": "近似多元正态" if abs(skew_stat) < 3.84 and abs(kurt_stat) < 1.96 else "可能偏离多元正态",
    }
