"""
Johnson 变换 — SU/SB/SL/LN 四类变换

参考: Johnson (1949) "Systems of Frequency Curves"
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from scipy import stats
from scipy.optimize import minimize


# Johnson 变换类型
JOHNSON_TYPES = ["SU", "SB", "SL", "LN"]


def johnson_transform(
    data: np.ndarray,
    method: str = "auto",
) -> Dict[str, Any]:
    """
    Johnson 变换

    Args:
        data: 输入数据（1D 数组）
        method: 变换类型 ("SU", "SB", "SL", "LN", "auto")

    Returns:
        变换结果字典
    """
    data = np.asarray(data, dtype=float)
    data = data[np.isfinite(data)]

    if len(data) < 5:
        raise ValueError(f"数据量不足: {len(data)}，至少需要 5 个观测值")

    if np.std(data) == 0:
        return {
            "type": "constant",
            "transformed": data,
            "params": {},
            "error": "数据为常数，无法进行 Johnson 变换",
        }

    if method == "auto":
        # 自动选择最佳变换类型
        result = _auto_select_transform(data)
    elif method in JOHNSON_TYPES:
        result = _fit_johnson(data, method)
    else:
        raise ValueError(f"不支持的变换类型: {method}")

    return result


def inverse_transform(
    transformed: np.ndarray,
    params: Dict[str, float],
    johnson_type: str,
) -> np.ndarray:
    """
    Johnson 逆变换

    Args:
        transformed: 变换后的数据
        params: 变换参数
        johnson_type: Johnson 变换类型

    Returns:
        逆变换后的数据
    """
    transformed = np.asarray(transformed, dtype=float)

    if johnson_type == "SU":
        return _inverse_su(transformed, params)
    elif johnson_type == "SB":
        return _inverse_sb(transformed, params)
    elif johnson_type == "SL":
        return _inverse_sl(transformed, params)
    elif johnson_type == "LN":
        return _inverse_ln(transformed, params)
    else:
        raise ValueError(f"不支持的 Johnson 类型: {johnson_type}")


def transform_value(
    value: float,
    params: Dict[str, float],
    johnson_type: str,
) -> float:
    """
    单值 Johnson 变换

    Args:
        value: 原始值
        params: 变换参数
        johnson_type: Johnson 变换类型

    Returns:
        变换后的值
    """
    gamma = params.get("gamma", 0)
    delta = params.get("delta", 1)
    xi = params.get("xi", 0)
    lam = params.get("lambda", 1)

    x = value

    if johnson_type == "SU":
        # SU: y = gamma + delta * arcsinh((x - xi) / lambda)
        z = (x - xi) / lam
        return gamma + delta * np.arcsinh(z)

    elif johnson_type == "SB":
        # SB: y = gamma + delta * log((x - xi) / (xi + lambda - x))
        if lam <= 0:
            return float("inf")
        z = (x - xi) / lam
        if z <= 0 or z >= 1:
            return float("inf") if z <= 0 else float("-inf")
        return gamma + delta * np.log(z / (1 - z))

    elif johnson_type == "SL":
        # SL: y = gamma + delta * log(x - xi)
        z = x - xi
        if z <= 0:
            return float("-inf")
        return gamma + delta * np.log(z)

    elif johnson_type == "LN":
        # LN: y = gamma + delta * log(x - xi)
        z = x - xi
        if z <= 0:
            return float("-inf")
        return gamma + delta * np.log(z)

    else:
        raise ValueError(f"不支持的 Johnson 类型: {johnson_type}")


# ── 内部函数：变换拟合 ──────────────────────────────

def _auto_select_transform(data: np.ndarray) -> Dict[str, Any]:
    """自动选择最佳 Johnson 变换类型"""
    best_result = None
    best_score = float("inf")

    for jtype in JOHNSON_TYPES:
        try:
            result = _fit_johnson(data, jtype)
            if "error" not in result:
                # 使用 AD 统计量作为选择标准
                transformed = result["transformed"]
                _, ad_p = stats.normaltest(transformed)
                # p 值越大表示越接近正态
                score = -ad_p  # 最小化负 p 值（即最大化 p 值）
                if score < best_score:
                    best_score = score
                    best_result = result
        except Exception:
            continue

    if best_result is None:
        # 如果所有变换都失败，使用 z-score 标准化
        std = np.std(data, ddof=1)
        if std <= 0:
            std = 1.0
        transformed = (data - np.mean(data)) / std
        best_result = {
            "type": "zscore",
            "transformed": transformed,
            "params": {"mean": np.mean(data), "std": std},
            "normality_p_value": 0.0,
        }

    return best_result


def _fit_johnson(data: np.ndarray, jtype: str) -> Dict[str, Any]:
    """拟合指定类型的 Johnson 变换"""
    # 标准化数据到 [0, 1] 范围用于参数估计
    x_min, x_max = data.min(), data.max()
    x_range = x_max - x_min
    if x_range <= 0:
        x_range = 1.0
    x_std = (data - x_min) / x_range

    # 使用矩估计初始参数
    try:
        params = _estimate_params_moment(data, jtype)
    except Exception:
        params = {"gamma": 0, "delta": 1, "xi": x_min, "lambda": x_range}

    # 应用变换
    transformed = np.array([transform_value(x, params, jtype) for x in data])

    # 检查变换结果
    finite_mask = np.isfinite(transformed)
    if finite_mask.sum() < len(data) * 0.9:
        return {
            "type": jtype,
            "transformed": transformed,
            "params": params,
            "error": f"变换后有限值比例过低 ({finite_mask.sum()}/{len(data)})",
        }

    # 计算正态性检验
    finite_transformed = transformed[finite_mask]
    if len(finite_transformed) >= 8:
        _, p_value = stats.normaltest(finite_transformed)
    else:
        p_value = 0.0

    return {
        "type": jtype,
        "transformed": transformed,
        "params": params,
        "normality_p_value": round(float(p_value), 6),
    }


def _estimate_params_moment(data: np.ndarray, jtype: str) -> Dict[str, float]:
    """使用矩估计法估计 Johnson 参数"""
    n = len(data)
    mean = np.mean(data)
    std = np.std(data, ddof=1)
    skew = stats.skew(data)
    kurt = stats.kurtosis(data)

    # 基于偏度和峰度的简单矩估计
    # 实际应用中应使用更精确的方法（如 L-moments）

    if jtype == "SU":
        # SU 分布：偏度可以是任意值
        delta = max(1.0, np.sqrt(np.log(1 + (std/mean)**2))) if mean != 0 else 1.0
        gamma = skew * delta / 3 if abs(skew) < 10 else 0
        xi = mean - std * 0.5
        lam = max(std, 0.1)
        return {"gamma": gamma, "delta": delta, "xi": xi, "lambda": lam}

    elif jtype == "SB":
        # SB 分布：有界分布
        xi = data.min() - abs(std) * 0.1
        lam = (data.max() - data.min()) * 1.2
        delta = max(1.0, 2.0 / (1 + abs(skew)))
        gamma = 0.0
        return {"gamma": gamma, "delta": delta, "xi": xi, "lambda": lam}

    elif jtype == "SL":
        # SL 分布：左尾无界
        xi = data.min() - abs(std) * 0.1
        delta = max(1.0, np.sqrt(np.log(1 + (std/mean)**2))) if mean != 0 else 1.0
        gamma = -skew * delta / 3 if abs(skew) < 10 else 0
        lam = max(std, 0.1)
        return {"gamma": gamma, "delta": delta, "xi": xi, "lambda": lam}

    elif jtype == "LN":
        # LN 类型：对数正态
        xi = 0.0
        lam = 1.0
        # 使用对数变换参数
        log_data = np.log(data[data > 0])
        if len(log_data) > 0:
            delta = 1.0 / np.std(log_data, ddof=1) if np.std(log_data, ddof=1) > 0 else 1.0
            gamma = -np.mean(log_data) * delta
        else:
            delta = 1.0
            gamma = 0.0
        return {"gamma": gamma, "delta": delta, "xi": xi, "lambda": lam}

    else:
        raise ValueError(f"不支持的 Johnson 类型: {jtype}")


# ── 内部函数：逆变换 ──────────────────────────────

def _inverse_su(transformed: np.ndarray, params: Dict[str, float]) -> np.ndarray:
    """SU 逆变换"""
    gamma = params.get("gamma", 0)
    delta = params.get("delta", 1)
    xi = params.get("xi", 0)
    lam = params.get("lambda", 1)

    y = (transformed - gamma) / delta
    z = np.sinh(y)
    return xi + lam * z


def _inverse_sb(transformed: np.ndarray, params: Dict[str, float]) -> np.ndarray:
    """SB 逆变换"""
    gamma = params.get("gamma", 0)
    delta = params.get("delta", 1)
    xi = params.get("xi", 0)
    lam = params.get("lambda", 1)

    y = (transformed - gamma) / delta
    exp_y = np.exp(y)
    return xi + lam * exp_y / (1 + exp_y)


def _inverse_sl(transformed: np.ndarray, params: Dict[str, float]) -> np.ndarray:
    """SL 逆变换"""
    gamma = params.get("gamma", 0)
    delta = params.get("delta", 1)
    xi = params.get("xi", 0)
    lam = params.get("lambda", 1)

    y = (transformed - gamma) / delta
    return xi + lam * np.exp(y)


def _inverse_ln(transformed: np.ndarray, params: Dict[str, float]) -> np.ndarray:
    """LN 逆变换"""
    gamma = params.get("gamma", 0)
    delta = params.get("delta", 1)
    xi = params.get("xi", 0)
    lam = params.get("lambda", 1)

    y = (transformed - gamma) / delta
    return xi + lam * np.exp(y)
