"""
广义方差（|S|）控制图 — 多元过程变异性监控

参考:
- Montgomery《Introduction to Statistical Quality Control》ch.11,
  "The Generalized Variance Chart"（b1 / b2 常数）
- Anderson (1958), An Introduction to Multivariate Statistical Analysis

统计量: 每个子组计算样本协方差阵 S_i，取行列式 |S_i| 作为"广义方差"。
控制限（子组大小 n、变量数 p、合并协方差阵 S̄）:

    b1 = Π_{j=1..p}(n − j) / (n − 1)^p
    b2 = Π(n − j) · [ Π(n − j + 2) − Π(n − j) ] / (n − 1)^{2p}
    CL  = b1·|S̄|
    UCL = |S̄|·(b1 + 3√b2)
    LCL = max(0, |S̄|·(b1 − 3√b2))

b1/b2 来自 |S| 的均值/方差渐近近似，要求 n 明显大于 p（p = 1 时该近似不如
S 图的 B3/B4 常数精确，单变量场景请用 XBar-S 图）。
"""

from typing import Any

import numpy as np
import pandas as pd


def analyze(
    data: pd.DataFrame,
    columns: list[str],
    subgroup_col: str | None = None,
    subgroup_size: int | None = None,
    alpha: float = 0.0027,
) -> dict[str, Any]:
    """
    广义方差图分析

    Args:
        data: 数据框
        columns: 分析变量列表（至少 2 个；单变量请用 XBar-S）
        subgroup_col: 子组 ID 列名
        subgroup_size: 等长子组大小（与 subgroup_col 二选一）
        alpha: 显著性水平（默认 0.0027 对应 3σ，即 b1 ± 3√b2）

    Returns:
        分析结果字典
    """
    if len(columns) < 2:
        raise ValueError("广义方差图需要至少 2 个变量（单变量请用 XBar-S）")
    if (subgroup_col is None) == (subgroup_size is None):
        raise ValueError("subgroup_col 与 subgroup_size 必须且只能提供其一")

    df = data[columns].dropna()
    p = len(columns)
    subgroups, labels = _split_subgroups(data, df, subgroup_col, subgroup_size)
    if len(subgroups) < 2:
        raise ValueError(f"子组数不足: {len(subgroups)}，需要至少 2 个")
    if any(len(g) < 2 for g in subgroups):
        raise ValueError("每个子组至少需要 2 个观测")
    if any(len(g) <= p for g in subgroups):
        raise ValueError(f"每个子组观测数需大于变量数 {p}")

    n_sizes = [len(g) for g in subgroups]
    equal_n = len(set(n_sizes)) == 1
    n = n_sizes[0] if equal_n else int(round(float(np.mean(n_sizes))))

    dets = np.array([float(np.linalg.det(np.cov(g, rowvar=False, ddof=1)))
                     for g in subgroups])
    if not np.all(np.isfinite(dets)):
        raise ValueError("存在奇异协方差子组（观测数过少或变量线性相关）")

    dof = np.array([size - 1 for size in n_sizes], dtype=float)
    pooled = sum(w * np.cov(g, rowvar=False, ddof=1)
                 for w, g in zip(dof, subgroups, strict=True)) / dof.sum()
    pooled_det = abs(float(np.linalg.det(pooled)))

    b1, b2 = generalized_variance_constants(n, p)
    k = _k_from_alpha(alpha)
    cl = b1 * pooled_det
    ucl = pooled_det * (b1 + k * np.sqrt(b2))
    lcl = max(0.0, pooled_det * (b1 - k * np.sqrt(b2)))

    violations = _collect_violations(dets, ucl, lcl, labels)

    return {
        "chart_type": "广义方差 |S|",
        "num_variables": p,
        "num_subgroups": len(subgroups),
        "subgroup_size": n,
        "equal_subgroup_size": equal_n,
        "genvar_chart": {
            "data": [round(float(v), 10) for v in dets],
            "labels": labels,
            "cl": round(float(cl), 10),
            "ucl": round(float(ucl), 10),
            "lcl": round(float(lcl), 10),
            "violations": violations,
        },
        "summary": {
            "pooled_det": round(pooled_det, 10),
            "b1": round(float(b1), 10),
            "b2": round(float(b2), 10),
            "k_sigma": k,
            "subgroup_sizes": n_sizes,
            "note": ("子组大小不等，b1/b2 按平均子组大小近似"
                     if not equal_n else ""),
        },
    }


def generalized_variance_constants(n: int, p: int) -> tuple[float, float]:
    """b1 = E|S|/|Σ|、b2 = Var|S|/|Σ|² 的渐近常数（Montgomery ch.11）。"""
    if n <= p + 1:
        raise ValueError(f"子组大小 n={n} 需大于变量数 p+1={p + 1}")
    prod_nm = float(np.prod([n - j for j in range(1, p + 1)]))
    prod_nm2 = float(np.prod([n - j + 2 for j in range(1, p + 1)]))
    denom = float((n - 1) ** (2 * p))
    b1 = prod_nm / float((n - 1) ** p)
    b2 = prod_nm * (prod_nm2 - prod_nm) / denom
    return b1, b2


def _k_from_alpha(alpha: float) -> float:
    """控制限倍数：默认 3σ 等价 0.0027；其余 alpha 按正态分位数换算。"""
    if np.isclose(alpha, 0.0027):
        return 3.0
    from scipy import stats
    return float(stats.norm.ppf(1 - alpha / 2))


def _split_subgroups(
    data: pd.DataFrame,
    df: pd.DataFrame,
    subgroup_col: str | None,
    subgroup_size: int | None,
) -> tuple[list[np.ndarray], list[str]]:
    """切分子组；subgroup_col 按首次出现顺序，subgroup_size 按行序等长切块。"""
    if subgroup_col is not None:
        if subgroup_col not in data.columns:
            raise ValueError(f"子组列不存在: {subgroup_col}")
        aligned = data.loc[df.index]
        subgroups: list[np.ndarray] = []
        labels: list[str] = []
        for name, group in aligned.groupby(subgroup_col, sort=False):
            subgroups.append(group[list(df.columns)].to_numpy(dtype=float))
            labels.append(str(name))
        return subgroups, labels

    if int(subgroup_size) < 2:
        raise ValueError(f"subgroup_size 需 ≥ 2，当前 {subgroup_size}")
    size = int(subgroup_size)
    values = df.to_numpy(dtype=float)
    subgroups = [values[i:i + size] for i in range(0, len(values) - size + 1, size)]
    labels = [f"子组{i + 1}" for i in range(len(subgroups))]
    return subgroups, labels


def _collect_violations(
    dets: np.ndarray,
    ucl: float,
    lcl: float,
    labels: list[str],
) -> list[dict]:
    violations = []
    for i, value in enumerate(dets):
        if value > ucl:
            violations.append({
                "point": int(i + 1),
                "label": labels[i],
                "rule": "above_ucl",
                "desc": f"广义方差高于 UCL ({value:.4g} > {ucl:.4g})",
                "value": round(float(value), 10),
            })
        elif value < lcl:
            violations.append({
                "point": int(i + 1),
                "label": labels[i],
                "rule": "below_lcl",
                "desc": f"广义方差低于 LCL ({value:.4g} < {lcl:.4g})",
                "value": round(float(value), 10),
            })
    return violations
