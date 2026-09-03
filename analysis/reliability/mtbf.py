"""MTBF / MTTR / 可用度分析

输入: 故障间隔时间 + 修复时间 (可分组: 按设备/产线/班组)

输出:
  - MTBF (Mean Time Between Failures)
  - MTTR (Mean Time To Repair)
  - 可用度 A = MTBF / (MTBF + MTTR)
  - 故障率 λ = 1 / MTBF
  - 趋势分析 (Laplace 趋势检验)
  - 分组汇总表
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import math
import numpy as np
from scipy import stats as sp_stats


@dataclass
class MTBFResult:
    label: str
    n_failures: int
    total_uptime: float
    total_downtime: float
    mtbf: float
    mttr: float
    availability: float
    failure_rate: float
    laplace_stat: Optional[float]
    trend: str
    mtbf_ci_low: float
    mtbf_ci_high: float


class MTBFAnalyzer:
    """MTBF/MTTR 分析器 — 支持多分组"""

    MIN_EVENTS = 2

    def analyze(self, time_between_failures: list,
                repair_times: Optional[list] = None,
                labels: Optional[list] = None,
                group_by: Optional[list] = None,
                confidence_level: float = 0.90) -> Dict[str, Any]:
        """主入口

        参数:
            time_between_failures: 故障间隔时间 (小时)
            repair_times: 修复时间 (小时)，默认全部为 0
            labels: 事件标签 (如 "2024-01-01", "设备A-故障1")
            group_by: 分组列 (如 "产线1", "产线2", ...)
            confidence_level: MTBF 置信区间水平

        返回:
            {"overall": MTBFResult, "groups": [MTBFResult], "warnings": [...], "error": str|None}
        """
        out: Dict[str, Any] = {
            "overall": None, "groups": [], "warnings": [], "error": None,
        }

        tbf = np.asarray(time_between_failures, dtype=float)
        valid = np.isfinite(tbf) & (tbf >= 0)
        if valid.sum() < self.MIN_EVENTS:
            out["error"] = f"有效故障间隔数据不足（{valid.sum()} 条，至少 {self.MIN_EVENTS} 条）"
            return out

        tbf = tbf[valid]
        if repair_times is not None:
            rt = np.asarray(repair_times, dtype=float)[valid]
            rt = np.maximum(rt, 0.0)
        else:
            rt = np.zeros(len(tbf))

        labels_v = labels if labels else [f"事件{i + 1}" for i in range(len(tbf))]

        out["overall"] = self._compute_group("全部", tbf, rt, confidence_level)

        if group_by and len(group_by) == len(time_between_failures):
            gb = np.asarray(group_by)[valid]
            for gname in sorted(set(gb)):
                mask = gb == gname
                if mask.sum() >= self.MIN_EVENTS:
                    g_result = self._compute_group(
                        str(gname), tbf[mask], rt[mask], confidence_level)
                    out["groups"].append(g_result)
                else:
                    out["warnings"].append(
                        f"分组 '{gname}' 数据不足 ({mask.sum()} 条)，已跳过")

        return out

    def _compute_group(self, label: str, tbf: np.ndarray,
                       rt: np.ndarray, cl: float) -> MTBFResult:
        """计算单组 MTBF/MTTR 指标"""
        n = len(tbf)
        total_uptime = float(np.sum(tbf))
        total_downtime = float(np.sum(rt))

        mtbf = total_uptime / n if n > 0 else 0.0
        mttr = total_downtime / n if n > 0 else 0.0
        avail = mtbf / (mtbf + mttr) if (mtbf + mttr) > 0 else 0.0
        failure_rate = 1.0 / mtbf if mtbf > 0 else 0.0

        alpha = 1 - cl
        chi2_low = sp_stats.chi2.ppf(alpha / 2, 2 * n)
        chi2_high = sp_stats.chi2.ppf(1 - alpha / 2, 2 * n)
        ci_low = 2 * total_uptime / chi2_high if chi2_high > 0 else 0.0
        ci_high = 2 * total_uptime / chi2_low if chi2_low > 0 else float("inf")

        laplace, trend = self._laplace_test(tbf)

        return MTBFResult(
            label=label, n_failures=n,
            total_uptime=round(total_uptime, 2),
            total_downtime=round(total_downtime, 2),
            mtbf=round(mtbf, 2),
            mttr=round(mttr, 2),
            availability=round(avail, 4),
            failure_rate=round(failure_rate, 6),
            laplace_stat=round(laplace, 4) if laplace is not None else None,
            trend=trend,
            mtbf_ci_low=round(ci_low, 2),
            mtbf_ci_high=round(ci_high, 2),
        )

    @staticmethod
    def _laplace_test(tbf: np.ndarray) -> Tuple[Optional[float], str]:
        """Laplace 趋势检验: H0=齐次泊松过程 (无趋势)"""
        n = len(tbf)
        if n < 3:
            return None, "stable"

        cum_t = np.cumsum(tbf)
        T = cum_t[-1]
        sum_ti = np.sum(cum_t[:-1])

        stat = ((sum_ti - (n - 1) * T / 2)
                / (T * np.sqrt((n - 1) / 12)))
        stat = float(stat)

        if abs(stat) < 1.96:
            trend = "stable"
        elif stat > 0:
            trend = "degrading"
        else:
            trend = "improving"

        return round(stat, 4), trend


def crow_amsaa(
    failure_times: list,
    total_time: Optional[float] = None,
    confidence_level: float = 0.90,
) -> Dict[str, Any]:
    """
    Crow-AMSAA (Power Law) 增长模型

    用于可靠性增长试验，估计强度函数 λ(t) = β·t^(β-1)/α

    Args:
        failure_times: 失效时间列表（累积时间）
        total_time: 总试验时间（默认取最后一个失效时间）
        confidence_level: 置信水平

    Returns:
        Crow-AMSAA 分析结果
    """
    times = np.sort(np.asarray(failure_times, dtype=float))
    times = times[times > 0]
    n = len(times)

    if n < 3:
        return {
            "analysis_type": "reliability.mtbf.crow_amsaa",
            "error": f"失效事件不足: {n}（至少需要 3 个）",
        }

    if total_time is not None and total_time <= 0:
        return {
            "analysis_type": "reliability.mtbf.crow_amsaa",
            "error": "total_time必须为正",
        }

    T = total_time if total_time and total_time > times[-1] else float(times[-1])

    from scipy.optimize import minimize_scalar

    def neg_loglik(beta):
        if beta <= 0.01:
            return 1e12
        alpha = T ** beta / n
        if alpha <= 0:
            return 1e12
        ll = n * (math.log(beta) - math.log(alpha)) + (beta - 1) * np.sum(np.log(times)) - T ** beta / alpha
        return -ll

    result = minimize_scalar(neg_loglik, bounds=(0.1, 5.0), method="bounded")
    beta = result.x
    alpha = T ** beta / n

    mtbf_at_T = alpha / (beta * T ** (beta - 1)) if beta > 0 else float("inf")

    mtbf_initial = alpha / beta if beta > 0 else float("inf")

    growth_rate = 1 - beta

    if beta < 0.95:
        trend = "improving"
    elif beta > 1.05:
        trend = "degrading"
    else:
        trend = "stable"

    z = sp_stats.norm.ppf((1 + confidence_level) / 2)
    se_beta = 1.0 / (math.sqrt(n) * abs(math.log(beta) + 1)) if beta > 0 else 1.0
    beta_ci_low = max(0.01, beta - z * se_beta)
    beta_ci_high = beta + z * se_beta

    return {
        "analysis_type": "reliability.mtbf.crow_amsaa",
        "summary": {
            "n_failures": int(n),
            "total_time": round(T, 4),
            "beta": round(beta, 4),
            "alpha": round(alpha, 4),
            "mtbf_at_T": round(mtbf_at_T, 4),
            "mtbf_initial": round(mtbf_initial, 4),
            "growth_rate": round(growth_rate, 4),
            "trend": trend,
            "beta_ci_low": round(beta_ci_low, 4),
            "beta_ci_high": round(beta_ci_high, 4),
            "confidence_level": confidence_level,
        },
    }
