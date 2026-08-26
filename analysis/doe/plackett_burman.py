"""
Plackett-Burman 筛选设计 — Hadamard 矩阵构造 + 效应分析

参考文献:
    Plackett R L, Burman J P (1946). The Design of Optimal Multifactorial
    Experiments. Biometrika, 33(4), 305-325.

支持的试验次数: N=4, 8, 12, 16 (最大 k=15 因子)
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


# ── Plackett-Burman 第一行模式 (Plackett & Burman 1946, Table) ──
# N=4,8,12: 循环移位法（Cyclic shift）
# N=16: Sylvester 构造（Kronecker 积），取前 15 列
_BASE_ROWS: Dict[int, List[int]] = {
    4:  [-1, 1, -1],
    8:  [1, 1, 1, -1, 1, -1, -1],
    12: [1, 1, -1, 1, 1, 1, -1, -1, -1, 1, -1],
}
# N=16 不使用循环移位，改用 Sylvester 构造


def _hadamard_from_base(base_row: List[int]) -> np.ndarray:
    """从第一行构造 Hadamard 矩阵（循环移位法）

    Parameters
    ----------
    base_row : list of int
        长度 N-1 的第一行元素（±1）

    Returns
    -------
    np.ndarray : shape (N, N-1)，每列为一个因子的编码水平
    """
    n = len(base_row) + 1  # 总试验次数
    h = np.zeros((n, n - 1), dtype=int)
    # 第一行
    h[0, :] = base_row
    # 向量化循环移位生成后续行
    indices = np.arange(n - 1)
    shifts = np.arange(1, n - 1)[:, np.newaxis]
    h[1:-1, :] = np.asarray(base_row)[(indices - shifts) % (n - 1)]
    # 最后一行全 -1（Plackett-Burman 规则）
    h[n - 1, :] = -1
    return h


_H2 = np.array([[1, 1], [1, -1]], dtype=int)


def _sylvester_hadamard(k: int) -> np.ndarray:
    """Sylvester 构造法生成 2^k 阶 Hadamard 矩阵

    Parameters
    ----------
    k : int
        使得 N = 2^k

    Returns
    -------
    np.ndarray : shape (2^k, 2^k)
    """
    h = _H2.copy()
    for _ in range(k - 1):
        h = np.kron(h, _H2)
    return h


# ── 公开 API ──

def generate_design(
    factors: List[str],
    n_runs: Optional[int] = None,
    center_points: int = 0,
    block: Optional[str] = None,
) -> pd.DataFrame:
    """生成 Plackett-Burman 筛选设计

    Parameters
    ----------
    factors : list of str
        因子名称列表，长度 ≤ N-1（N 为试验次数）
    n_runs : int, optional
        试验次数（必须为 4 的倍数，支持 4,8,12,16）。
        若不指定，自动选择 >= len(factors)+1 的最小值。
    center_points : int
        中心点数量（默认 0）
    block : str, optional
        区组列名（若提供则添加 Block 列）

    Returns
    -------
    pd.DataFrame
        包含因子编码列（-1/+1）、RunOrder、StdOrder，
        可选 CenterPoints、Block 列

    Raises
    ------
    ValueError
        - 因子数超出选定 N 的最大容量
        - n_runs 不是 4 的倍数或不在 {4,8,12,16}
    """
    k = len(factors)
    if k < 2:
        raise ValueError("至少需要 2 个因子")

    # 支持的试验次数
    supported = [4, 8, 12, 16]

    # 自动选择试验次数
    if n_runs is None:
        for candidate in supported:
            if candidate - 1 >= k:
                n_runs = candidate
                break
        if n_runs is None:
            raise ValueError(f"因子数 {k} 超出 PB 设计最大容量 (k≤15)")
    else:
        if n_runs not in supported:
            raise ValueError(f"n_runs 必须为 4 的倍数且在 {supported}，收到 {n_runs}")

    if k > n_runs - 1:
        raise ValueError(
            f"因子数 {k} 超出 N={n_runs} PB 设计的最大容量 "
            f"(最多 {n_runs - 1} 个因子)"
        )

    # 构造 Hadamard 矩阵
    if n_runs == 16:
        # N=16: Sylvester 构造（Kronecker 积），取前 15 列
        h_full = _sylvester_hadamard(4)  # 16×16
        design = h_full[:, :k].copy()
    else:
        # N=4,8,12: 循环移位法
        base = _BASE_ROWS[n_runs]
        h = _hadamard_from_base(base)
        design = h[:, :k].copy()

    # 构造 DataFrame
    data = {factors[i]: design[:, i] for i in range(k)}
    df = pd.DataFrame(data)
    df["StdOrder"] = list(range(1, n_runs + 1))
    df["RunOrder"] = np.random.permutation(n_runs) + 1

    # 中心点
    if center_points > 0:
        center_df = pd.DataFrame({f: [0.0] * center_points for f in factors})
        center_df["StdOrder"] = [0] * center_points
        center_df["RunOrder"] = list(range(n_runs + 1, n_runs + 1 + center_points))
        df = pd.concat([df, center_df], ignore_index=True)

    # 区组
    if block:
        df[block] = ["Design"] * n_runs + (["Center"] * center_points if center_points > 0 else [])

    return df


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """分析 Plackett-Burman 筛选设计

    计算主效应、方差分析（ANOVA）、Pareto 数据。
    基于 Plackett-Burman (1946) 的简化 ANOVA（主效应模型）。

    Parameters
    ----------
    df : pd.DataFrame
        包含响应列和因子列的数据框
    response_col : str
        响应变量列名
    factor_cols : list of str
        因子列名列表
    alpha : float
        显著性水平（默认 0.05）

    Returns
    -------
    dict
        包含以下键：
        - chart_type: "Plackett-Burman Screening Design"
        - factors: 因子列表
        - observations: 观测数
        - grand_mean: 总均值
        - effects: 主效应估计 {factor: effect}
        - anova: ANOVA 表 dict
        - significant_factors: 显著因子列表
        - pareto_data: Pareto 图数据
        - model_r_squared: 模型 R²
    """
    data = df[[response_col] + factor_cols].dropna()
    response = data[response_col].values.astype(float)
    design = data[factor_cols].values.astype(float)
    n = len(response)
    k = len(factor_cols)

    # ── 主效应计算 ──
    grand_mean = float(np.mean(response))

    # Vectorized effect computation
    design_f = design
    high_mask = design_f > 0
    low_mask = design_f < 0
    n_high = high_mask.sum(axis=0)
    n_low = low_mask.sum(axis=0)
    sum_high = (response[:, np.newaxis] * high_mask).sum(axis=0)
    sum_low = (response[:, np.newaxis] * low_mask).sum(axis=0)
    valid = (n_high > 0) & (n_low > 0)
    effects_arr = np.where(valid, sum_high / n_high - sum_low / n_low, 0.0)

    # ── ANOVA ──
    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = n - 1

    # SS computation (vectorized)
    ss_arr = np.where(valid, n * (effects_arr / 2) ** 2, 0.0)
    ss_model = float(np.sum(ss_arr))
    ss_effects = {factor_cols[i]: round(float(ss_arr[i]), 6) for i in range(k)}

    ss_error = max(ss_total - ss_model, 0.0)
    df_error = max(df_total - k, 1)

    # F/p computation (vectorized)
    ms_arr = ss_arr.copy()
    if df_error > 0 and ss_error > 0:
        f_arr = ms_arr / (ss_error / df_error)
        p_arr = 1.0 - stats.f.cdf(np.maximum(f_arr, 0), 1, df_error)
    elif ss_error == 0 and df_error > 0:
        f_arr = np.full(k, float('inf'))
        p_arr = np.zeros(k)
    else:
        f_arr = np.zeros(k)
        p_arr = np.ones(k)

    effects = {factor_cols[i]: round(float(effects_arr[i]), 6) for i in range(k)}
    f_values = {factor_cols[i]: round(float(f_arr[i]), 4) if f_arr[i] != float('inf') else f_arr[i] for i in range(k)}
    p_values = {factor_cols[i]: round(float(p_arr[i]), 6) for i in range(k)}
    ms_effects = {factor_cols[i]: round(float(ms_arr[i]), 6) for i in range(k)}

    # 显著因子
    significant = [f for f in factor_cols if p_values.get(f, 1.0) < alpha]

    # Pareto 数据
    pareto_data = sorted(
        [{"factor": f, "effect": abs(effects[f]), "f_value": f_values[f], "p_value": p_values[f]}
         for f in factor_cols],
        key=lambda x: x["effect"],
        reverse=True,
    )

    # 模型 R²
    r_squared = 1.0 - (ss_error / ss_total) if ss_total > 0 else 0.0

    return {
        "chart_type": "Plackett-Burman Screening Design",
        "factors": factor_cols,
        "observations": n,
        "grand_mean": round(grand_mean, 6),
        "effects": effects,
        "anova": {
            "source": factor_cols + ["Error", "Total"],
            "ss": [ss_effects[f] for f in factor_cols] + [round(ss_error, 6), round(ss_total, 6)],
            "df": [1] * k + [df_error, df_total],
            "ms": [ms_effects[f] for f in factor_cols] + [round(ss_error / df_error, 6) if df_error > 0 else 0, 0],
            "f_value": [f_values[f] for f in factor_cols] + [None, None],
            "p_value": [p_values[f] for f in factor_cols] + [None, None],
        },
        "significant_factors": significant,
        "pareto_data": pareto_data,
        "model_r_squared": round(r_squared, 6),
    }
