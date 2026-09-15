"""
可靠性框图 (RBD) — 串联/并联/混合系统可靠度计算

支持:
  series     — 串联系统 (任一失效则系统失效)
  parallel   — 并联系统 (全部失效则系统失效)
  mixed      — 混合系统 (串联+并联组合)
  k_out_of_n — k/n 表决系统 (至少 k 个正常则系统正常)
"""

import numpy as np
from typing import Any


def _compute_system_r(
    reliabilities: list[float], structure: str,
    parallel_groups: list[list[int]] | None, k: int,
) -> float:
    """内部辅助: 计算系统可靠度"""
    if structure == "series":
        return _series(reliabilities)
    elif structure == "parallel":
        return _parallel(reliabilities)
    elif structure == "mixed":
        return _mixed(reliabilities, parallel_groups)
    elif structure == "k_out_of_n":
        return _k_out_of_n(reliabilities, k)
    return 0.0


def calculate_system_reliability(
    components: list[dict[str, Any]],
    structure: str = "series",
    parallel_groups: list[list[int]] | None = None,
    k_out_of_n: dict[str, int] | None = None,
    mission_time: float = 1.0,
) -> dict[str, Any]:
    """
    可靠性框图计算

    Args:
        components: 组件列表，每个组件为 {"name": str, "reliability": float}
                    reliability 为在 mission_time 时的可靠度 R(t)
        structure: "series" | "parallel" | "mixed" | "k_out_of_n"
        parallel_groups: 混合结构时的并联组索引列表，如 [[0,1],[2]] 表示组件0和1并联，再与组件2串联
        k_out_of_n: k/n 表决系统，{"k": int, "n": int}
        mission_time: 任务时间（用于一致性标注）

    Returns:
        系统可靠度计算结果
    """
    if not components:
        return {"analysis_type": "reliability.rbd", "error": "组件列表为空"}

    n = len(components)
    for i, c in enumerate(components):
        if "reliability" not in c:
            return {"analysis_type": "reliability.rbd", "error": f"组件 {i} 缺少 reliability 字段"}
        r = c["reliability"]
        if not (0 <= r <= 1):
            return {"analysis_type": "reliability.rbd", "error": f"组件 {i} 的可靠性 {r} 不在 [0,1] 范围"}

    reliabilities = [c["reliability"] for c in components]
    names = [c.get("name", f"Component_{i}") for i, c in enumerate(components)]

    if structure == "mixed" and parallel_groups is None:
        return {"analysis_type": "reliability.rbd", "error": "混合结构需要 parallel_groups 参数"}
    if structure == "k_out_of_n" and k_out_of_n is None:
        return {"analysis_type": "reliability.rbd", "error": "k/n 表决系统需要 k_out_of_n 参数"}

    k_val = k_out_of_n.get("k", 1) if k_out_of_n else 1

    sys_r = _compute_system_r(reliabilities, structure, parallel_groups, k_val)

    contributions = []
    for i, r_i in enumerate(reliabilities):
        if structure == "series":
            sensitivity = sys_r / r_i if r_i > 1e-12 else 0.0
        elif structure == "parallel":
            sensitivity = (1 - sys_r) / (1 - r_i) if r_i < 1 - 1e-12 else 0.0
        else:
            perturbed = reliabilities.copy()
            perturbed[i] = min(1.0, r_i + 0.01)
            r_perturbed = _compute_system_r(perturbed, structure, parallel_groups, k_val)
            sensitivity = (r_perturbed - sys_r) / 0.01 if abs(r_i - 1.0) > 1e-9 else 0.0
        contributions.append({
            "name": names[i],
            "reliability": round(r_i, 6),
            "sensitivity": round(float(sensitivity), 6),
        })

    contributions.sort(key=lambda x: x["sensitivity"], reverse=True)

    weakest = contributions[0] if contributions else None

    return {
        "analysis_type": "reliability.rbd",
        "summary": {
            "structure": structure,
            "n_components": n,
            "system_reliability": round(float(sys_r), 6),
            "system_unreliability": round(float(1 - sys_r), 6),
            "mission_time": mission_time,
        },
        "components": contributions,
        "weakest_component": weakest,
    }


def _series(reliabilities: list[float]) -> float:
    """串联系统: R = ∏Ri"""
    r = 1.0
    for ri in reliabilities:
        r *= ri
    return r


def _parallel(reliabilities: list[float]) -> float:
    """并联系统: R = 1 - ∏(1-Ri)"""
    r = 1.0
    for ri in reliabilities:
        r *= (1 - ri)
    return 1 - r


def _mixed(reliabilities: list[float], groups: list[list[int]]) -> float:
    """混合系统: 每组并联，组间串联"""
    r = 1.0
    for group in groups:
        group_r = _parallel([reliabilities[i] for i in group])
        r *= group_r
    return r


def _k_out_of_n(reliabilities: list[float], k: int) -> float:
    """k/n 表决系统: 至少 k 个正常
    使用动态规划计算精确概率
    """
    n = len(reliabilities)
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0

    dp = [0.0] * (n + 1)
    dp[0] = 1.0

    for ri in reliabilities:
        for j in range(n, 0, -1):
            dp[j] = dp[j] * (1 - ri) + dp[j - 1] * ri
        dp[0] = dp[0] * (1 - ri)

    return sum(dp[k:])


def system_mtbf(
    components: list[dict[str, Any]],
    structure: str = "series",
    parallel_groups: list[list[int]] | None = None,
) -> dict[str, Any]:
    """
    系统 MTBF 计算（基于指数分布假设）

    Args:
        components: 组件列表，每个组件为 {"name": str, "mtbf": float} (MTBF 值)
        structure: "series" | "parallel"
        parallel_groups: 混合结构时的并联组索引列表

    Returns:
        系统 MTBF 计算结果
    """
    if not components:
        return {"analysis_type": "reliability.rbd_mtbf", "error": "组件列表为空"}

    for i, c in enumerate(components):
        if "mtbf" not in c:
            return {"analysis_type": "reliability.rbd_mtbf", "error": f"组件 {i} 缺少 mtbf 字段"}
        if c["mtbf"] <= 0:
            return {"analysis_type": "reliability.rbd_mtbf", "error": f"组件 {i} 的 MTBF 必须为正"}

    lambdas = [1.0 / c["mtbf"] for c in components]
    names = [c.get("name", f"Component_{i}") for i, c in enumerate(components)]

    if structure == "series":
        total_lambda = sum(lambdas)
        sys_mtbf = 1.0 / total_lambda if total_lambda > 0 else float("inf")
    elif structure == "parallel":
        sys_mtbf = _parallel_mtbf(lambdas)
    elif structure == "mixed" and parallel_groups:
        equiv_lambdas = []
        for group in parallel_groups:
            group_lambdas = [lambdas[i] for i in group]
            equiv_lambda = _parallel_lambda(group_lambdas)
            equiv_lambdas.append(equiv_lambda)
        total_lambda = sum(equiv_lambdas)
        sys_mtbf = 1.0 / total_lambda if total_lambda > 0 else float("inf")
    else:
        return {"analysis_type": "reliability.rbd_mtbf", "error": f"不支持的结构: {structure}"}

    return {
        "analysis_type": "reliability.rbd_mtbf",
        "summary": {
            "structure": structure,
            "system_mtbf": round(float(sys_mtbf), 4),
            "system_failure_rate": round(float(1.0 / sys_mtbf), 8) if sys_mtbf > 0 else 0,
        },
        "components": [
            {"name": names[i], "mtbf": round(c["mtbf"], 4), "failure_rate": round(lambdas[i], 8)}
            for i, c in enumerate(components)
        ],
    }


def _parallel_mtbf(lambdas: list[float]) -> float:
    """并联系统 MTBF (数值积分)"""
    t_max = max(5.0 / min(lambdas), 100)
    n_points = 1000
    dt = t_max / n_points
    t = np.linspace(0, t_max, n_points + 1)

    R = np.ones(n_points + 1)
    for lam in lambdas:
        R *= (1 - np.exp(-lam * t))
    R = 1 - R

    integral = dt / 3 * (R[0] + R[-1] + 4 * np.sum(R[1:-1:2]) + 2 * np.sum(R[2:-1:2]))
    return float(integral)


def _parallel_lambda(lambdas: list[float]) -> float:
    """并联组等效失效率"""
    mtbf = _parallel_mtbf(lambdas)
    return 1.0 / mtbf if mtbf > 0 else float("inf")
