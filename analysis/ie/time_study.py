"""
工时研究分析引擎 — 时间观测数据的自动分析
一键计算: 平均时间/正常时间/标准工时/异常值剔除/时间分布/能力分析
"""

from typing import Dict, List, Any, Tuple, Optional
import numpy as np
import pandas as pd
from scipy import stats
from core.data_objects import TimeObservation


def _effective_time(obs: TimeObservation) -> float:
    """观测时间优先；旧数据未填观测时间时回退 cycle（历史字段曾承载计时值）。"""
    if obs.observation_time and obs.observation_time > 0:
        return float(obs.observation_time)
    return float(obs.cycle)


def _effective_times(group: pd.DataFrame) -> pd.Series:
    """按行取有效计时列：observation_time > 0 优先，否则回退 cycle。"""
    obs = (pd.to_numeric(group["observation_time"], errors="coerce")
           if "observation_time" in group.columns else None)
    cyc = (pd.to_numeric(group["cycle"], errors="coerce")
           if "cycle" in group.columns else None)
    if obs is None:
        times = cyc if cyc is not None else pd.Series(np.zeros(len(group)))
    elif cyc is None:
        times = obs
    else:
        times = obs.where(obs.fillna(0) > 0, cyc)
    return times.fillna(0.0).astype(float)


class TimeStudyEngine:
    """秒表时间研究分析流水线"""

    @staticmethod
    def remove_outliers(times: pd.Series, method: str = "iqr") -> Tuple[pd.Series, List[int]]:
        if len(times) < 5:
            return times, []
        if method == "zscore":
            z = np.abs(stats.zscore(times.values, nan_policy="omit"))
            mask = z <= 3
        else:
            q1, q3 = times.quantile(0.25), times.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            mask = (times >= lower) & (times <= upper)
        outliers = list(times.index[~mask])
        return times[mask].reset_index(drop=True), outliers

    @staticmethod
    def basic_stats(times: pd.Series) -> Dict[str, Any]:
        n = len(times)
        if n == 0:
            return {"n": 0, "mean": 0, "median": 0, "std": 0, "min": 0,
                    "max": 0, "range": 0, "cv": 0, "sem": 0}
        return {
            "n": n,
            "mean": float(times.mean()),
            "median": float(times.median()),
            "std": float(times.std(ddof=1)) if n > 1 else 0.0,
            "min": float(times.min()),
            "max": float(times.max()),
            "range": float(times.max() - times.min()),
            "cv": float(times.std(ddof=1) / times.mean()) if n > 1 and times.mean() != 0 else 0.0,
            "sem": float(times.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0,
        }

    @staticmethod
    def calculate_normal_time(avg_time: float, rating: float) -> float:
        return avg_time * rating

    @staticmethod
    def calculate_standard_time(normal_time: float, allowance_pct: float) -> float:
        return normal_time * (1 + allowance_pct / 100.0)

    @staticmethod
    def time_distribution(times: pd.Series, bins: int = None) -> Dict[str, Any]:
        n = len(times)
        if n < 3:
            return {"n": n, "bins": [], "counts": [], "normality_test": None}
        if bins is None:
            bins = max(5, min(20, int(np.sqrt(n))))
        hist, edges = np.histogram(times, bins=bins)

        std_val = float(times.std(ddof=1)) if n > 1 else 0.0
        if n <= 5000 and std_val > 0:
            stat, p = stats.shapiro(times.values)
            normality = {"test": "Shapiro-Wilk", "statistic": float(stat), "p_value": float(p)}
        elif n > 5000 and std_val > 0:
            stat, p = stats.kstest(times.values, "norm", args=(times.mean(), std_val))
            normality = {"test": "Kolmogorov-Smirnov", "statistic": float(stat), "p_value": float(p)}
        else:
            normality = {"test": "N/A", "statistic": 0.0, "p_value": 1.0, "note": "数据为常数(std=0)"}

        return {
            "n": n,
            "bins": edges.tolist(),
            "counts": hist.tolist(),
            "normality_test": normality,
        }

    @staticmethod
    def capability_analysis(times: pd.Series, takt_time: Optional[float] = None,
                            target_time: Optional[float] = None) -> Dict[str, Any]:
        n = len(times)
        if n < 3 or takt_time is None:
            return {"n": n, "available": False}

        mean = float(times.mean())
        std = float(times.std(ddof=1)) if n > 1 else 0.0
        if std == 0:
            cp = cpu = cpk = cpl = cpm = 999.0
        else:
            cp = (takt_time - 0) / (6 * std) if takt_time > 0 else 0
            cpl = (mean - 0) / (3 * std) if mean > 0 else 0
            cpu = (takt_time - mean) / (3 * std) if takt_time > mean else 0
            cpk = min(cpl, cpu)
            if target_time is not None:
                bias = (mean - target_time) ** 2
                cpm = cp / np.sqrt(1 + bias / std**2) if std > 0 else 0
            else:
                cpm = None

        sigma_level = min(cpu * 3, 8.0)
        can_meet = cpu >= 1.0

        return {
            "n": n,
            "available": True,
            "cp": round(cp, 4),
            "cpk": round(cpk, 4),
            "cpu": round(cpu, 4),
            "cpl": round(cpl, 4),
            "cpm": round(cpm, 4) if cpm else None,
            "sigma_level": round(sigma_level, 2),
            "can_meet_takt": can_meet,
            "takt_time": takt_time,
            "mean": mean,
            "std": std,
            "margin": round(takt_time - mean, 3),
            "margin_pct": round((takt_time - mean) / takt_time * 100, 1) if takt_time > 0 else 0,
        }

    @staticmethod
    def analyze(observations: List[TimeObservation], rating: float = 1.0,
                allowance_pct: float = 12.0, takt_time: Optional[float] = None,
                confidence_level: float = 0.95) -> Dict[str, Any]:
        """一键分析流水线"""
        if not observations:
            return {"valid": False, "error": "无观测数据"}

        df = pd.DataFrame([o.to_dict() for o in observations])
        groups = df.groupby(["process_id", "operator"], dropna=False)
        results = []

        for (pid, op), group in groups:
            times = _effective_times(group)
            times_clean, outliers = TimeStudyEngine.remove_outliers(times)
            stats_result = TimeStudyEngine.basic_stats(times_clean)
            avg_time = stats_result["mean"]
            normal_time = TimeStudyEngine.calculate_normal_time(avg_time, rating)
            standard_time = TimeStudyEngine.calculate_standard_time(normal_time, allowance_pct)
            dist = TimeStudyEngine.time_distribution(times_clean)
            cap = TimeStudyEngine.capability_analysis(times_clean, takt_time, target_time=avg_time)

            results.append({
                "process_id": pid,
                "operator": op,
                "cycles": len(times),
                "outliers_removed": len(outliers),
                "outlier_indices": outliers,
                "stats": stats_result,
                "avg_time": round(avg_time, 3),
                "normal_time": round(normal_time, 3),
                "standard_time": round(standard_time, 3),
                "rating": rating,
                "allowance_pct": allowance_pct,
                "distribution": dist,
                "capability": cap,
            })

        all_clean_times = pd.Series([_effective_time(o) for o in observations])
        overall_times, overall_outliers = TimeStudyEngine.remove_outliers(all_clean_times)
        overall_stats = TimeStudyEngine.basic_stats(overall_times)

        return {
            "valid": True,
            "analysis_type": "TimeStudy",
            "params": {
                "rating": rating,
                "allowance_pct": allowance_pct,
                "takt_time": takt_time,
                "confidence_level": confidence_level,
            },
            "results": results,
            "summary": {
                "total_groups": len(results),
                "total_observations": len(observations),
                "total_outliers_removed": sum(r["outliers_removed"] for r in results),
                "overall_stats": overall_stats,
                "overall_outliers": len(overall_outliers),
            },
        }
