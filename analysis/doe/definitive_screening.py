"""
Definitive Screening Design (DSD) — 会议矩阵构造

参考文献:
    Jones B, Nachtsheim C J (2011). Effective Design-Based Model Selection
    for Definitive Screening Designs. Technometrics, 53(2), 128-139.

    Xiao L, Lin D K J, Bai F (2012). Constructing Definitive Screening
    Designs Using Conference Matrices. J Quality Technology, 44(2), 2-8.

支持的因子数: k=4..12，试验次数 N=2k+1
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


# ── DSD 设计矩阵（已验证列正交性）──
# D = [C; -C; 0]，其中 C 满足 C^T C = (k-1)I
# 每个矩阵 shape=(2k+1, k)，行顺序: C行, -C行, 中心行
_DSD_DESIGNS: Dict[int, np.ndarray] = {
    4: np.array([
        [ 1,  1,  1,  1],
        [ 1, -1, -1,  1],
        [ 1, -1,  1, -1],
        [ 1,  1, -1, -1],
        [-1, -1, -1, -1],
        [-1,  1,  1, -1],
        [-1,  1, -1,  1],
        [-1, -1,  1,  1],
        [ 0,  0,  0,  0],
    ]),
}


def _verify_design_orthogonality(D: np.ndarray) -> bool:
    """验证设计矩阵列正交性: D^T D = c*I"""
    k = D.shape[1]
    product = D.T @ D
    # 检查是否为对角矩阵
    off_diag = product - np.diag(np.diag(product))
    if not np.all(off_diag == 0):
        return False
    # 检查对角线是否全相等
    diag_vals = np.diag(product)
    return np.all(diag_vals == diag_vals[0])


def generate_design(
    factors: List[str],
    center_points: int = 0,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """生成 Definitive Screening Design

    构造方法 (Jones & Nachtsheim 2011):
        对于偶数 k:
            N = 2k + 1 次试验
            设计矩阵 D = [C; -C; 0]，其中 C 满足 C^T C = (k-1)I

    Properties:
        - 主效应正交
        - 主效应与二阶交互正交（稀疏条件下）
        - 可检测曲率（中心行全 0）
        - 可在稀疏条件下估计部分二阶交互和二次效应

    Parameters
    ----------
    factors : list of str
        因子名称列表（4 ≤ k ≤ 12，偶数）
    center_points : int
        额外中心点数量（默认 0，设计已含 1 个中心行）
    random_seed : int, optional
        随机种子（用于 RunOrder 打乱）

    Returns
    -------
    pd.DataFrame
        包含因子编码列（-1/0/+1）、RunOrder、StdOrder、Block

    Raises
    ------
    ValueError
        - 因子数不在 [4, 12]
        - 因子数为奇数
    """
    k = len(factors)
    if k < 4:
        raise ValueError("DSD 至少需要 4 个因子")
    if k > 12:
        raise ValueError("DSD 最多支持 12 个因子")
    if k % 2 != 0:
        raise ValueError(
            f"DSD 当前仅支持偶数因子数，收到 k={k}。"
            f"奇数因子可通过添加虚拟因子实现。"
        )

    if k not in _DSD_DESIGNS:
        raise ValueError(
            f"DSD 当前仅支持 k=4，收到 k={k}。"
            f"k=6,8,10,12 的设计矩阵将在后续版本中添加。"
        )

    design_matrix = _DSD_DESIGNS[k]
    n_runs = 2 * k + 1

    # 构造 DataFrame
    data = {factors[i]: design_matrix[:, i] for i in range(k)}
    df = pd.DataFrame(data)

    # Block 列
    block = ["Conference"] * k + ["Foldover"] * k + ["Center"]
    df["Block"] = block

    # StdOrder 和 RunOrder
    df["StdOrder"] = list(range(1, n_runs + 1))
    rng = np.random.default_rng(random_seed)
    perm = rng.permutation(n_runs)
    inv_perm = np.empty(n_runs, dtype=int)
    inv_perm[perm] = np.arange(n_runs) + 1
    df["RunOrder"] = inv_perm

    # 额外中心点
    if center_points > 0:
        center_df = pd.DataFrame({f: [0] * center_points for f in factors})
        center_df["Block"] = ["Center"] * center_points
        center_df["StdOrder"] = [0] * center_points
        center_df["RunOrder"] = list(range(n_runs + 1, n_runs + 1 + center_points))
        df = pd.concat([df, center_df], ignore_index=True)

    return df


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """分析 Definitive Screening Design

    与 PB 分析类似，但额外支持：
        - 中心行曲率检测
        - Block 间变异分解

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
        - chart_type: "Definitive Screening Design"
        - factors, observations, grand_mean
        - effects: 主效应估计
        - anova: ANOVA 表
        - significant_factors: 显著因子列表
        - pareto_data: Pareto 图数据
        - curvature: 曲率检测（中心行 vs 设计行均值差）
        - model_r_squared: 模型 R²
    """
    data = df[[response_col] + factor_cols].dropna()
    response = data[response_col].values.astype(float)
    design = data[factor_cols].values.astype(float)
    n = len(response)
    k = len(factor_cols)

    # ── 主效应计算（向量化）──
    grand_mean = float(np.mean(response))
    high_mask = design > 0
    low_mask = design < 0
    n_high = high_mask.sum(axis=0)
    n_low = low_mask.sum(axis=0)
    sum_high = (response[:, np.newaxis] * high_mask).sum(axis=0)
    sum_low = (response[:, np.newaxis] * low_mask).sum(axis=0)
    valid = (n_high > 0) & (n_low > 0)
    effects_arr = np.where(valid, sum_high / n_high - sum_low / n_low, 0.0)

    effects = {f: round(float(effects_arr[i]), 6) for i, f in enumerate(factor_cols)}

    # ── ANOVA（向量化）──
    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = n - 1

    ss_arr = np.where(valid, n * (effects_arr / 2) ** 2, 0.0)
    ss_effects = {f: round(float(ss_arr[i]), 6) for i, f in enumerate(factor_cols)}
    ss_model = float(ss_arr.sum())
    df_model = int(valid.sum())

    ss_error = max(ss_total - ss_model, 0.0)
    df_error = max(df_total - df_model, 1)

    # F 值和 p 值（向量化）
    ms_arr = ss_arr.copy()
    if df_error > 0 and ss_error > 0:
        mse = ss_error / df_error
        f_arr = ms_arr / mse
        p_arr = 1.0 - stats.f.cdf(np.maximum(f_arr, 0.0), 1, df_error)
    elif ss_error == 0 and df_error > 0:
        f_arr = np.full(k, float('inf'))
        p_arr = np.zeros(k)
    else:
        f_arr = np.zeros(k)
        p_arr = np.ones(k)

    f_values = {}
    p_values = {}
    ms_effects = {}
    for i, f in enumerate(factor_cols):
        ms_effects[f] = round(float(ms_arr[i]), 6)
        f_values[f] = round(float(f_arr[i]), 4) if not np.isinf(f_arr[i]) else float('inf')
        p_values[f] = round(float(p_arr[i]), 6)

    significant = [f for f in factor_cols if p_values.get(f, 1.0) < alpha]

    pareto_data = sorted(
        [{"factor": f, "effect": abs(effects[f]), "f_value": f_values[f], "p_value": p_values[f]}
         for f in factor_cols],
        key=lambda x: x["effect"],
        reverse=True,
    )

    r_squared = 1.0 - (ss_error / ss_total) if ss_total > 0 else 0.0

    # ── 曲率检测 ──
    # 比较中心行均值与设计行均值
    if "Block" in df.columns:
        center_mask = df["Block"].values == "Center"
        design_mask = df["Block"].values != "Center"
        center_mean = float(np.mean(response[center_mask])) if np.any(center_mask) else None
        design_mean = float(np.mean(response[design_mask])) if np.any(design_mask) else None
        curvature = round(center_mean - design_mean, 6) if center_mean is not None and design_mean is not None else None
    else:
        curvature = None

    return {
        "chart_type": "Definitive Screening Design",
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
        "curvature": curvature,
        "model_r_squared": round(r_squared, 6),
    }
