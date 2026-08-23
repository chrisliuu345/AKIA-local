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

    # 提取数据
    df = data[columns].dropna()
    if len(df) < len(columns) + 1:
        raise ValueError(f"数据量不足: {len(df)}，需要至少 {len(columns) + 1}")

    X = df.values.astype(float)
    n, p = X.shape

    # 计算均值向量和协方差矩阵
    mean_vec = np.mean(X, axis=0)
    cov_matrix = np.cov(X, rowvar=False)

    # 处理奇异协方差矩阵
    if np.linalg.matrix_rank(cov_matrix) < p:
        # 添加小扰动使矩阵可逆
        cov_matrix += np.eye(p) * 1e-10

    cov_inv = np.linalg.inv(cov_matrix)

    # 计算 T² 统计量
    if subgroup_col is not None and subgroup_col in data.columns:
        # 子组数据
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
        sample_sizes = [len(data[data[subgroup_col] == g].dropna()) for g in groups]
    else:
        # 个体数据
        t2_values = np.array([_compute_t2(x, mean_vec, cov_inv, 1) for x in X])
        sample_sizes = [1] * n

    # 计算控制限
    ucl = _compute_ucl(p, n, alpha, sample_sizes)
    cl = _compute_cl(p, n, sample_sizes)

    # 检测违规点
    violations = []
    for i, t2 in enumerate(t2_values):
        if t2 > ucl[i] if isinstance(ucl, np.ndarray) else t2 > ucl:
            violations.append({
                "point": int(i + 1),
                "rule": "T² UCL",
                "desc": f"T²超出控制限 ({t2:.3f} > {ucl[i] if isinstance(ucl, np.ndarray) else ucl:.3f})",
                "value": round(float(t2), 6),
            })

    # 计算 Q 残差（用于检测异常方向）
    q_values = []
    for i, x in enumerate(X):
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


def _compute_ucl(p: int, n: int, alpha: float, sample_sizes: Optional[List[int]] = None) -> float:
    """计算 UCL"""
    # 使用 F 分布
    f_crit = stats.f.ppf(1 - alpha, p, n - p)
    if sample_sizes and len(sample_sizes) > 1:
        # 子组数据：每个子组的 UCL 不同
        ucl_values = []
        for ni in sample_sizes:
            ucl = (p * (ni - 1) * (n - 1)) / (n * (n - p)) * f_crit
            ucl_values.append(ucl)
        return np.array(ucl_values)
    else:
        return (p * (n - 1) * (n - p)) / (n * (n - p)) * f_crit


def _compute_cl(p: int, n: int, sample_sizes: Optional[List[int]] = None) -> float:
    """计算中心线（期望值）"""
    # E[T²] ≈ p * (n-1) / (n-p) * (n+1)/n
    return p * (n - 1) / (n - p) * (n + 1) / n


def _multivariate_normality_test(
    X: np.ndarray,
    mean: np.ndarray,
    cov: np.ndarray,
) -> Dict[str, Any]:
    """多元正态性检验（基于 Mardia 偏度/峰度）"""
    n, p = X.shape

    # Mardia 偏度
    centered = X - mean
    cov_inv = np.linalg.inv(cov + np.eye(p) * 1e-10)

    # 计算偏度统计量
    g1 = 0
    for i in range(n):
        for j in range(n):
            xi = centered[i]
            xj = centered[j]
            g1 += (xi.T @ cov_inv @ xj) ** 3
    g1 = g1 / (n ** 2)

    # 计算峰度统计量
    g2 = 0
    for i in range(n):
        xi = centered[i]
        g2 += (xi.T @ cov_inv @ xi) ** 2
    g2 = g2 / n

    # 近似检验
    skew_stat = n * g1 / 6
    kurt_stat = (g2 - p * (p + 2)) * np.sqrt(n / (8 * p * (p + 2)))

    return {
        "skewness_statistic": round(float(skew_stat), 4),
        "kurtosis_statistic": round(float(kurt_stat), 4),
        "interpretation": "近似多元正态" if abs(skew_stat) < 3.84 and abs(kurt_stat) < 1.96 else "可能偏离多元正态",
    }
