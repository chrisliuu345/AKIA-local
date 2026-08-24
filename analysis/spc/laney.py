"""Laney P'/U' 控制图 — 修正过度离散/欠离散计数数据"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from scipy import stats


def analyze(
    defects,
    sample_sizes,
    chart_type: str = "Laney P'",
    alpha: float = 0.0027,
) -> Dict[str, Any]:
    """Laney P'/U' 控制图统一入口

    Args:
        defects: 缺陷数数据（数组或Series）
        sample_sizes: 子组大小数据（数组或Series）
        chart_type: 图表类型 "Laney P'" 或 "Laney U'"
        alpha: 显著性水平（默认0.0027，对应3σ控制限）

    Returns:
        Dict包含控制限和统计量
    """
    defects_arr = np.asarray(defects, dtype=float)
    sample_sizes_arr = np.asarray(sample_sizes, dtype=float)

    if chart_type == "Laney P'":
        return laney_p_prime(defects_arr, sample_sizes_arr, alpha)
    elif chart_type == "Laney U'":
        return laney_u_prime(defects_arr, sample_sizes_arr, alpha)
    else:
        raise ValueError(f"无效的图表类型: {chart_type}，支持 'Laney P'' 或 'Laney U''")


def laney_p_prime(
    defects: np.ndarray,
    sample_sizes: np.ndarray,
    alpha: float = 0.0027,
) -> Dict[str, Any]:
    """Laney P' 图 — 修正过度离散的计数数据（比例）

    适用于子组内变异无法解释过度离散的场景，如：
    - 子组大小差异大
    - 过度离散（σ² >> μ）
    - 欠离散（σ² << μ）

    Args:
        defects: 缺陷数数组
        sample_sizes: 子组大小数组
        alpha: 显著性水平（默认0.0027，对应3σ控制限）

    Returns:
        Dict包含控制限和统计量
    """
    defects = np.asarray(defects, dtype=float)
    sample_sizes = np.asarray(sample_sizes, dtype=float)

    # 校验
    if len(defects) != len(sample_sizes):
        raise ValueError("defects与sample_sizes长度不一致")
    if np.any(sample_sizes <= 0):
        raise ValueError("sample_sizes必须大于0")
    if np.any(defects < 0):
        raise ValueError("defects不能为负数")

    n = len(defects)
    if n < 2:
        raise ValueError(f"数据量不足: {n} (至少需要2个子组)")

    # 计算比例
    p = defects / sample_sizes

    # 总体比例
    p_bar = np.sum(defects) / np.sum(sample_sizes)

    # 计算z分数 (标准化残差)
    p_hat = np.where(p_bar * (1 - p_bar) > 0,
                     p_bar * (1 - p_bar) / sample_sizes,
                     1e-10)
    z = (p - p_bar) / np.sqrt(p_hat)

    # 计算移动波动率 σ_z
    # σ_z = mean(|z_i - z_{i-1}|) / sqrt(2)
    sigma_z = np.mean(np.abs(np.diff(z))) / np.sqrt(2)

    # 确保sigma_z至少为1（避免欠离散时控制限过窄）
    sigma_z = max(sigma_z, 1.0)

    # 从alpha计算k因子（标准正态分布的临界值）
    k_factor = stats.norm.ppf(1 - alpha / 2)

    # 计算控制限
    # UCL/LCL = p_bar ± k * sigma_z * sqrt(p_bar * (1-p_bar) / n_i)
    se = np.sqrt(p_bar * (1 - p_bar) / sample_sizes)
    ucl = p_bar + k_factor * sigma_z * se
    lcl = p_bar - k_factor * sigma_z * se
    lcl = np.maximum(lcl, 0)  # LCL不能为负

    # 中心线
    cl = p_bar

    # 检测违规点
    violations = (p > ucl) | (p < lcl)

    return {
        "chart_type": "Laney P'",
        "center_line": round(float(cl), 6),
        "ucl": [round(float(v), 6) for v in ucl],
        "lcl": [round(float(v), 6) for v in lcl],
        "proportions": [round(float(v), 6) for v in p],
        "sample_sizes": sample_sizes.tolist(),
        "defects": defects.tolist(),
        "sigma_z": round(float(sigma_z), 4),
        "k_factor": round(float(k_factor), 4),
        "n_subgroups": n,
        "n_violations": int(np.sum(violations)),
        "violation_indices": np.where(violations)[0].tolist(),
        "p_bar": round(float(p_bar), 6),
    }


def laney_u_prime(
    defects: np.ndarray,
    sample_sizes: np.ndarray,
    alpha: float = 0.0027,
) -> Dict[str, Any]:
    """Laney U' 图 — 修正过度离散的计数数据（单位缺陷数）

    适用于子组内变异无法解释过度离散的场景，如：
    - 子组大小差异大
    - 过度离散（σ² >> μ）
    - 欠离散（σ² << μ）

    Args:
        defects: 缺陷数数组
        sample_sizes: 子组大小/检验单位数数组
        alpha: 显著性水平（默认0.0027，对应3σ控制限）

    Returns:
        Dict包含控制限和统计量
    """
    defects = np.asarray(defects, dtype=float)
    sample_sizes = np.asarray(sample_sizes, dtype=float)

    # 校验
    if len(defects) != len(sample_sizes):
        raise ValueError("defects与sample_sizes长度不一致")
    if np.any(sample_sizes <= 0):
        raise ValueError("sample_sizes必须大于0")
    if np.any(defects < 0):
        raise ValueError("defects不能为负数")

    n = len(defects)
    if n < 2:
        raise ValueError(f"数据量不足: {n} (至少需要2个子组)")

    # 计算单位缺陷数
    u = defects / sample_sizes

    # 总体单位缺陷数
    u_bar = np.sum(defects) / np.sum(sample_sizes)

    # 计算z分数 (标准化残差)
    u_hat = np.where(u_bar > 0,
                     u_bar / sample_sizes,
                     1e-10)
    z = (u - u_bar) / np.sqrt(u_hat)

    # 计算移动波动率 σ_z
    sigma_z = np.mean(np.abs(np.diff(z))) / np.sqrt(2)

    # 确保sigma_z至少为1
    sigma_z = max(sigma_z, 1.0)

    # 从alpha计算k因子
    k_factor = stats.norm.ppf(1 - alpha / 2)

    # 计算控制限
    # UCL/LCL = u_bar ± k * sigma_z * sqrt(u_bar / n_i)
    se = np.sqrt(u_bar / sample_sizes)
    ucl = u_bar + k_factor * sigma_z * se
    lcl = u_bar - k_factor * sigma_z * se
    lcl = np.maximum(lcl, 0)

    # 中心线
    cl = u_bar

    # 检测违规点
    violations = (u > ucl) | (u < lcl)

    return {
        "chart_type": "Laney U'",
        "center_line": round(float(cl), 6),
        "ucl": [round(float(v), 6) for v in ucl],
        "lcl": [round(float(v), 6) for v in lcl],
        "unit_defects": [round(float(v), 6) for v in u],
        "sample_sizes": sample_sizes.tolist(),
        "defects": defects.tolist(),
        "sigma_z": round(float(sigma_z), 4),
        "k_factor": round(float(k_factor), 4),
        "n_subgroups": n,
        "n_violations": int(np.sum(violations)),
        "violation_indices": np.where(violations)[0].tolist(),
        "u_bar": round(float(u_bar), 6),
    }
