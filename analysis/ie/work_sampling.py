"""
工作抽样分析引擎 — 工时利用率、状态占比、置信区间
"""

from collections import OrderedDict
from typing import Any
import numpy as np


BUILTIN_STATUSES = OrderedDict([
    ("working",    {"label": "工作",   "color": "#4CAF50", "productive": True}),
    ("waiting",    {"label": "等待",   "color": "#FF9800", "productive": False}),
    ("transport",  {"label": "搬运",   "color": "#2196F3", "productive": True}),
    ("inspection", {"label": "检验",   "color": "#9C27B0", "productive": True}),
    ("meeting",    {"label": "开会",   "color": "#607D8B", "productive": True}),
    ("away",       {"label": "离岗",   "color": "#F44336", "productive": False}),
])


def _z_value(confidence: float) -> float:
    """W84: 使用 scipy 正态分位数函数，支持任意置信度"""
    from scipy import stats
    return float(stats.norm.ppf((1 + confidence) / 2))


class WorkSamplingEngine:
    """工作抽样分析"""

    @staticmethod
    def get_default_statuses() -> OrderedDict:
        return OrderedDict(BUILTIN_STATUSES)

    @staticmethod
    def calculate_ratios(observations: list[str],
                         statuses: OrderedDict | None = None) -> dict[str, dict[str, Any]]:
        if statuses is None:
            statuses = BUILTIN_STATUSES
        total = len(observations)
        if total == 0:
            return {"_total": 0, "ratios": {}}

        label_to_key = {}
        for key, info in statuses.items():
            label_to_key[info["label"]] = key

        counts = {}
        for obs in observations:
            key = label_to_key.get(obs)
            if key:
                counts[key] = counts.get(key, 0) + 1
            else:
                counts.setdefault("_other", 0)
                counts["_other"] += 1

        ratios = {}
        for key, info in statuses.items():
            cnt = counts.get(key, 0)
            ratios[key] = {
                "label": info["label"],
                "color": info["color"],
                "productive": info["productive"],
                "count": cnt,
                "pct": round(cnt / total * 100, 2),
            }
        if "_other" in counts:
            ratios["_other"] = {
                "label": "其他",
                "color": "#9E9E9E",
                "productive": False,
                "count": counts["_other"],
                "pct": round(counts["_other"] / total * 100, 2),
            }

        return {"_total": total, "ratios": ratios}

    @staticmethod
    def confidence_intervals(ratios_data: dict[str, Any],
                             confidence: float = 0.95) -> dict[str, dict[str, Any]]:
        total = ratios_data.get("_total", 0)
        if total == 0:
            return {}

        z = _z_value(confidence)
        result = {}
        for key, info in ratios_data.get("ratios", {}).items():
            p = info["pct"] / 100.0
            se = np.sqrt(p * (1 - p) / total) if total > 0 else 0
            ci_low = max(0, p - z * se)
            ci_high = min(1, p + z * se)
            result[key] = {
                "label": info["label"],
                "p": round(p, 4),
                "pct": info["pct"],
                "ci_low": round(ci_low, 4),
                "ci_high": round(ci_high, 4),
                "ci_low_pct": round(ci_low * 100, 2),
                "ci_high_pct": round(ci_high * 100, 2),
                "se": round(se, 4),
            }

        return result

    @staticmethod
    def calculate_utilization(ratios_data: dict[str, Any]) -> dict[str, Any]:
        ratios = ratios_data.get("ratios", {})
        total = ratios_data.get("_total", 0)
        productive_count = sum(info["count"] for info in ratios.values()
                               if info.get("productive", False))
        productive_pct = round(productive_count / total * 100, 2) if total > 0 else 0.0
        non_productive_pct = round(100.0 - productive_pct, 2)

        return {
            "productive_count": productive_count,
            "productive_pct": productive_pct,
            "non_productive_pct": non_productive_pct,
            "total": total,
        }

    @staticmethod
    def sample_size_required(expected_pct: float, margin_error: float = 5.0,
                             confidence: float = 0.95) -> int:
        z = _z_value(confidence)
        p = expected_pct / 100.0
        e = margin_error / 100.0
        n = (z**2 * p * (1 - p)) / (e**2) if e > 0 else 0
        return max(1, int(np.ceil(n)))

    @staticmethod
    def analyze(observations: list[str], confidence: float = 0.95,
                custom_statuses: OrderedDict | None = None,
                show_sample_size_estimate: bool = True) -> dict[str, Any]:
        statuses = custom_statuses if custom_statuses else BUILTIN_STATUSES
        ratios = WorkSamplingEngine.calculate_ratios(observations, statuses)
        ci = WorkSamplingEngine.confidence_intervals(ratios, confidence)
        utilization = WorkSamplingEngine.calculate_utilization(ratios)

        result = {
            "valid": True,
            "analysis_type": "WorkSampling",
            "params": {
                "confidence": confidence,
                "total_observations": ratios.get("_total", 0),
            },
            "ratios": ratios,
            "confidence_intervals": ci,
            "utilization": utilization,
            "chart_data": {
                "labels": [info["label"] for info in ratios.get("ratios", {}).values()],
                "values": [info["pct"] for info in ratios.get("ratios", {}).values()],
                "colors": [info["color"] for info in ratios.get("ratios", {}).values()],
            },
        }

        if show_sample_size_estimate and ratios.get("_total", 0) > 0:
            utilization["productive_pct"] / 100
            n_required = WorkSamplingEngine.sample_size_required(
                utilization["productive_pct"], 5.0, confidence
            )
            result["sample_size"] = {
                "current": ratios["_total"],
                "required_for_5pct_margin": n_required,
                "is_sufficient": ratios["_total"] >= n_required,
            }

        return result
