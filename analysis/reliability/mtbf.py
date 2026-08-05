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
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
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
    failure_rate: float          # λ (每小时失效数)
    # 趋势
    laplace_stat: Optional[float]  # Laplace 趋势检验统计量
    trend: str                     # "improving" | "degrading" | "stable"
    # 置信区间 (指数分布假设)
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

        # ── 整体 ──
        out["overall"] = self._compute_group("全部", tbf, rt, confidence_level)

        # ── 分组 ──
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

        # 指数分布置信区间
        alpha = 1 - cl
        chi2_low = sp_stats.chi2.ppf(alpha / 2, 2 * n)
        chi2_high = sp_stats.chi2.ppf(1 - alpha / 2, 2 * n)
        ci_low = 2 * total_uptime / chi2_high if chi2_high > 0 else 0.0
        ci_high = 2 * total_uptime / chi2_low if chi2_low > 0 else float("inf")

        # Laplace 趋势检验
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
        mean_ratio = sum_ti / ((n - 1) * T / 2) if T > 0 else 1.0

        stat = ((sum_ti - (n - 1) * T / 2)
                / (T * np.sqrt((n - 1) / 12)))
        stat = float(stat)

        # 双侧 5% 临界值 ≈ 1.96
        if abs(stat) < 1.96:
            trend = "stable"
        elif stat > 0:
            trend = "degrading"  # 故障间隔变长 = 恶化
        else:
            trend = "improving"  # 故障间隔变短 = 改善

        return round(stat, 4), trend
