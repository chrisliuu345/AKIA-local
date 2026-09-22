"""
MEWMA（多元指数加权移动平均）控制图 — Lowry et al. (1992)

参考:
- Lowry, Woodall, Champ & Rigdon (1992), "A Multivariate Exponentially Weighted
  Moving Average Control Chart", Technometrics 34(1), 46-53
- Montgomery《Introduction to Statistical Quality Control》ch.11（多元 EWMA）

模型（对角平滑矩阵 Λ = r·I）:

    Z_i = r·(x_i − μ₀) + (1 − r)·Z_{i−1},     Z_0 = 0
    T²_i = Z_iᵀ Σ_Z(i)⁻¹ Z_i,
    Σ_Z(i) = r/(2 − r)·[1 − (1 − r)^{2i}]·Σ

即 Z_i 为相对目标中心 μ₀ 的平滑偏差。``variance="exact"``（默认）逐点使用
精确协方差 Σ_Z(i)，各点 T² 同分布、期望为 p（Lowry 原文与 Minitab 采用的
形式）；``variance="steady_state"`` 使用与 i 无关的稳态 Σ_Z = r/(2−r)·Σ，
对应 Montgomery 教材中查表 h4 的工程近似（早期点 T² 偏小）。

r = 1 时两种形式都退化为 Hotelling 个体观测 T² 图，控制限与 `hotelling.py`
完全一致（见 tests/test_known_values_spc_mewma.py 的交叉验证）。

控制限:
- ``ucl_method="hotelling"``（默认，参数由样本估计）:
  UCL = p(m−1)(m+1) / (m(m−p)) · F(1−α; p, m−p)   — Montgomery 个体观测形式
- ``ucl_method="chi2"``（Σ 已知 / 大样本）: UCL = χ²(1−α; p)

参数口径（重要）: μ₀ / Σ 应来自 **Phase I 基线**，再用于 Phase II 监控 —— 蒙特
卡洛验证（r=0.1, p=2, m_phase1=1000）越限率 0.00267 ≈ α=0.0027，在控平均
T² ≈ p。若把同一批数据既当基线又当监控对象（Phase I 回顾式分析），T² 会系统性
偏小（实测约为理论值的 0.68 倍），此时应改用 Lowry 原文的 h4 表限，而非 F/χ²。

注意: 两种方差形式下 T²_i 均为标准化统计量，故控制限恒定、逐点可比。
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

_UCL_METHODS = ("hotelling", "chi2")
_VARIANCE_MODES = ("exact", "steady_state")


def analyze(
    data: pd.DataFrame,
    columns: list[str],
    lambda_: float = 0.1,
    alpha: float = 0.0027,
    ucl_method: str = "hotelling",
    variance: str = "exact",
    mean_vector: list[float] | None = None,
    cov_matrix: list[list[float]] | None = None,
    baseline_size: int | None = None,
) -> dict[str, Any]:
    """
    MEWMA 分析

    Args:
        data: 数据框（每个观测一行，多元变量各占一列）
        columns: 分析变量列表（至少 2 个）
        lambda_: 平滑参数 r ∈ (0, 1]，越小对小幅漂移越敏感（常用 0.05 ~ 0.2）
        alpha: 显著性水平（默认 0.0027 对应 3σ）
        ucl_method: "hotelling"（参数估计，默认）或 "chi2"（参数已知）
        variance: "exact"（逐点 Σ_Z(i)，默认）或 "steady_state"（稳态 Σ_Z）
        mean_vector: 已知目标均值 μ₀（默认取样本均值）
        cov_matrix: 已知协方差 Σ（默认取样本协方差）
        baseline_size: 估计 μ₀/Σ 所用的观测数（Phase I 容量），用于控制限的
            自由度。默认取被分析样本数（同源估计，Phase I 回顾式分析）

    Returns:
        分析结果字典
    """
    r = float(lambda_)
    if not 0.0 < r <= 1.0:
        raise ValueError(f"lambda_ 必须在 (0, 1] 内，当前 {lambda_}")
    if ucl_method not in _UCL_METHODS:
        raise ValueError(f"未知 ucl_method: {ucl_method}（可选 {_UCL_METHODS}）")
    if variance not in _VARIANCE_MODES:
        raise ValueError(f"未知 variance: {variance}（可选 {_VARIANCE_MODES}）")
    if len(columns) < 2:
        raise ValueError("MEWMA 需要至少 2 个变量")

    df = data[columns].dropna()
    if len(df) < len(columns) + 1:
        raise ValueError(f"数据量不足: {len(df)}，需要至少 {len(columns) + 1}")

    X = df.to_numpy(dtype=float)
    m, p = X.shape

    mu0 = (np.asarray(mean_vector, dtype=float) if mean_vector is not None
           else X.mean(axis=0))
    if mu0.shape != (p,):
        raise ValueError(f"mean_vector 长度应为 {p}，当前 {mu0.shape}")

    sigma = (np.asarray(cov_matrix, dtype=float) if cov_matrix is not None
             else np.cov(X, rowvar=False, ddof=1))
    sigma = np.atleast_2d(sigma).astype(float)
    if sigma.shape != (p, p):
        raise ValueError(f"cov_matrix 形状应为 ({p}, {p})，当前 {sigma.shape}")
    if np.linalg.matrix_rank(sigma) < p:
        sigma = sigma + np.eye(p) * 1e-10

    z_values = _mewma_statistic_series(X, mu0, r)

    sigma_z = r / (2.0 - r) * sigma
    sigma_inv = np.linalg.inv(sigma)
    quad = np.einsum("ij,jk,ik->i", z_values, sigma_inv, z_values)
    t2_values = quad * _variance_scale(m, r, variance)

    df_size = int(baseline_size) if baseline_size is not None else m
    if df_size <= p:
        raise ValueError(f"baseline_size={df_size} 需大于变量数 p={p}")

    ucl = _compute_ucl(p, df_size, alpha, ucl_method)
    violations = _collect_violations(t2_values, ucl)

    return {
        "chart_type": "MEWMA",
        "num_variables": p,
        "num_samples": m,
        "lambda": r,
        "mewma_chart": {
            "data": [round(float(v), 6) for v in t2_values],
            "cl": 0.0,
            "ucl": round(float(ucl), 6) if np.isfinite(ucl) else None,
            "violations": violations,
            "z_values": [[round(float(v), 6) for v in row] for row in z_values],
        },
        "summary": {
            "mean_vector": [round(float(v), 6) for v in mu0],
            "cov_matrix": [[round(float(v), 6) for v in row] for row in sigma],
            "sigma_z": [[round(float(v), 6) for v in row] for row in sigma_z],
            "ucl_method": ucl_method,
            "variance": variance,
            "baseline_size": df_size,
            "baseline_from_analysis_sample": baseline_size is None,
            "steady_state_factor": round(r / (2.0 - r), 6),
            "first_sample_factor": round(r * (2.0 - r), 6),
            "mean_t2": round(float(np.mean(t2_values)), 6),
        },
    }


def _mewma_statistic_series(X: np.ndarray, mu0: np.ndarray, r: float) -> np.ndarray:
    """按 Z_i = r(x_i − μ₀) + (1 − r)Z_{i−1} 递推（Z_0 = 0）。"""
    centered = X - mu0
    z_values = np.zeros_like(centered)
    prev = np.zeros(centered.shape[1], dtype=float)
    for i, row in enumerate(centered):
        prev = r * row + (1.0 - r) * prev
        z_values[i] = prev
    return z_values


def _variance_scale(m: int, r: float, variance: str) -> np.ndarray:
    """T² = quad / Var(Z_i)/Σ 的逐点缩放系数。

    quad = Z_iᵀ Σ⁻¹ Z_i；精确形式除以 r/(2−r)·[1−(1−r)^{2i}]，
    稳态形式除以 r/(2−r)（与 i 无关）。
    """
    steady = r / (2.0 - r)
    if variance == "steady_state":
        return np.full(m, 1.0 / steady)
    factors = 1.0 - (1.0 - r) ** (2.0 * np.arange(1, m + 1))
    return 1.0 / (steady * factors)


def _compute_ucl(p: int, m: int, alpha: float, ucl_method: str) -> float:
    """控制限：参数已知用 χ²，参数估计用 Montgomery 个体观测 F 形式。"""
    if ucl_method == "chi2":
        return float(stats.chi2.ppf(1 - alpha, p))
    df2 = m - p
    if df2 <= 0:
        return float("nan")
    f_crit = stats.f.ppf(1 - alpha, p, df2)
    return float(p * (m - 1) * (m + 1) / (m * (m - p)) * f_crit)


def _collect_violations(t2_values: np.ndarray, ucl: float) -> list[dict]:
    if not np.isfinite(ucl):
        return []
    violations = []
    for i, value in enumerate(t2_values):
        if value > ucl:
            violations.append({
                "point": int(i + 1),
                "rule": "T² UCL",
                "desc": f"MEWMA T²超出控制限 ({value:.3f} > {ucl:.3f})",
                "value": round(float(value), 6),
            })
    return violations
