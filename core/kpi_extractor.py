"""统一 KPI 提取器 — 从分析结果中按正确嵌套路径提取关键指标

修复 Dashboard 卡片 3 项坏指标 (OEE/%GRR/SPC违规 键路径写错导致从未显示),
同时作为 v2.4 F3 公式编辑器的变量命名空间基础。

采用结构探测而非 analysis_type 名称匹配 — 各引擎结果有独特的顶层键,
名称随语言/图表类型变化而结构稳定。

标度约定: 所有百分比类指标统一归一化为 0-1 分数 (与 OEE 引擎一致),
供显示层 format_pct 和公式引擎共同使用。
"""

from typing import Any


def _scalar(v) -> bool:
    """是否为可用数值标量 (排除 bool/list/dict)"""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _extract_capability(r: dict) -> dict:
    cap = r.get("capability", {})
    if not isinstance(cap, dict):
        return {}
    return {
        "cp": cap.get("cp"),
        "cpk": cap.get("cpk"),
        "pp": cap.get("pp"),
        "ppk": cap.get("ppk"),
        "grade": cap.get("grade"),
        "sigma_level": cap.get("sigma_level"),
        "ppm_total": cap.get("ppm_total"),
    }


def _extract_spc(r: dict) -> dict:
    """SPC 违规点 — XBar-R/S/I-MR/CUSUM/EWMA 在 {chart_type}_chart.violations,
    P/NP/C/U 图在顶层 violations"""
    total = 0
    for key, value in r.items():
        if key.endswith("_chart") and isinstance(value, dict):
            viols = value.get("violations")
            if isinstance(viols, (list, tuple, dict)):
                total += len(viols)
    top = r.get("violations")
    if isinstance(top, (list, tuple, dict)):
        total += len(top)
    return {"violations": total}


def _extract_oee(r: dict) -> dict:
    """OEE 引擎 — 汇总在 overall 下; TPM 引擎 — 顶层 avg_oee"""
    if isinstance(r.get("overall"), dict):
        src = r["overall"]
        return {
            "oee": src.get("oee"),
            "availability": src.get("availability"),
            "performance": src.get("performance"),
            "quality": src.get("quality"),
            "grade": src.get("grade"),
        }
    if "avg_oee" in r:
        return {"oee": r.get("avg_oee")}
    return {}


def _extract_msa(r: dict) -> dict:
    """MSA — 引擎输出 grr_pct_tv 为 0-100 百分数, 此处归一化为 0-1 分数"""
    pct = r.get("percentages", {})
    if not isinstance(pct, dict):
        return {}
    grr = pct.get("grr_pct_tv")
    if _scalar(grr):
        grr = grr / 100.0
    acceptance = r.get("acceptance", {})
    msg = acceptance.get("message", "") if isinstance(acceptance, dict) else ""
    return {
        "grr_pct": grr,
        "ndc": r.get("ndc"),
        "acceptance": msg,
    }


def _extract_hypothesis(r: dict) -> dict:
    """假设检验 — 双因素 ANOVA 的 p_value/is_significant 是 list, 跳过非标量"""
    if not _scalar(r.get("p_value")):
        return {}
    return {
        "p_value": r.get("p_value"),
        "is_significant": r.get("is_significant") if _scalar(r.get("is_significant")) else None,
    }


def _extract_regression(r: dict) -> dict:
    """回归 — 真实引擎输出顶层 r_squared; 兼容 model.r_squared 形状"""
    rs = r.get("r_squared")
    if not _scalar(rs):
        model = r.get("model", {})
        if isinstance(model, dict):
            rs = model.get("r_squared")
    if not _scalar(rs):
        return {}
    return {"r_squared": rs}


def _extract_reliability(r: dict) -> dict:
    """可靠性引擎用 mtbf/mttr, TPM 引擎用 avg_mtbf/avg_mttr"""
    mtbf = r.get("mtbf", r.get("avg_mtbf"))
    mttr = r.get("mttr", r.get("avg_mttr"))
    if not _scalar(mtbf) and not _scalar(mttr):
        return {}
    return {
        "mtbf": mtbf,
        "mttr": mttr,
        "availability": r.get("availability") if _scalar(r.get("availability")) else None,
    }


def _extract_weibull(r: dict) -> dict:
    """Weibull 寿命分析 — beta/eta 特征键"""
    if not _scalar(r.get("beta")) or not _scalar(r.get("eta")):
        return {}
    return {
        "b10_life": r.get("b10_life"),
        "characteristic_life": r.get("characteristic_life"),
        "mean_life": r.get("mean_life") if _scalar(r.get("mean_life")) else None,
    }


def _extract_tolerance(r: dict) -> dict:
    """公差区间 — 正态/非参数 均有 lower/upper/width"""
    if not _scalar(r.get("lower")) or not _scalar(r.get("upper")):
        return {}
    return {
        "tolerance_lower": r.get("lower"),
        "tolerance_upper": r.get("upper"),
        "tolerance_width": r.get("width"),
        "confidence": r.get("confidence"),
        "proportion": r.get("proportion"),
    }


def _extract_smed(r: dict) -> dict:
    """SMED 快速换模 — improvement_pct/total_before/total_after"""
    if not _scalar(r.get("improvement_pct")):
        return {}
    return {
        "improvement_pct": r.get("improvement_pct"),
        "total_before": r.get("total_before"),
        "total_after": r.get("total_after"),
    }


def _extract_work_sampling(r: dict) -> dict:
    """Work Sampling — utilization.productive_pct → worker_utilization"""
    util = r.get("utilization")
    if not isinstance(util, dict):
        return {}
    pct = util.get("productive_pct")
    if not _scalar(pct):
        return {}
    return {"worker_utilization": pct / 100.0 if pct > 1 else pct}


def _extract_multi_plant(r: dict) -> dict:
    """多工厂对比 — best_cpk/worst_cpk/total_violations"""
    if not _scalar(r.get("best_cpk")) and not _scalar(r.get("worst_cpk")):
        return {}
    return {
        "best_cpk": r.get("best_cpk"),
        "worst_cpk": r.get("worst_cpk"),
        "total_violations": r.get("total_violations"),
    }


def _extract_doe(r: dict) -> dict:
    """DOE — model_r_squared / r_squared 兼容"""
    rs = r.get("r_squared") or r.get("model_r_squared")
    if not _scalar(rs):
        return {}
    return {"r_squared": rs}


def _extract_time_study(r: dict) -> dict:
    """时间研究 — standard_time 在 results[] 列表内"""
    results = r.get("results")
    if not isinstance(results, list) or not results:
        return {}
    first = results[0]
    st = first.get("standard_time") if isinstance(first, dict) else None
    ct = first.get("avg_time") if isinstance(first, dict) else None
    out = {}
    if _scalar(st):
        out["standard_time"] = st
    if _scalar(ct):
        out["cycle_time"] = ct
    return out


def _extract_normality(r: dict) -> dict:
    """正态性检验 — tests 子字典中的 p_value"""
    tests = r.get("tests")
    if not isinstance(tests, dict):
        return {}
    for test_name in ("shapiro_wilk", "dagostino_pearson", "kolmogorov_smirnov"):
        sub = tests.get(test_name)
        if isinstance(sub, dict) and _scalar(sub.get("p_value")):
            return {
                "p_value": sub["p_value"],
                "is_significant": 1 if sub["p_value"] < 0.05 else 0,
            }
    return {}


def _extract_ie_default(r: dict) -> dict:
    """线平衡/VSM/工时研究等 — summary/current 嵌套下的通用指标 (仅标量)"""
    metrics = {}
    sources = [r.get("summary", {}), r.get("current", {}), r]
    for src in sources:
        if not isinstance(src, dict):
            continue
        for k in ("balance_rate", "efficiency", "cycle_time", "takt_time",
                  "standard_time", "lead_time", "lead_time_days", "va_ratio",
                  "bottleneck_count", "worker_utilization", "utilization"):
            if _scalar(src.get(k)) and k not in metrics:
                metrics[k] = src[k]
    return metrics


def extract_metrics(analyses: dict[int, dict]) -> dict[str, dict[str, Any]]:
    """从 MainWindow.analyses 提取每项分析的关键指标

    analyses: {tab_index: {"analysis_type": str, "params": {}, "result": {}}}
    返回: {analysis_type: {metric_name: value}} — 每个 Tab 仅保留最新结果
    """
    out: dict[str, dict[str, Any]] = {}
    for idx in sorted(analyses.keys()):
        entry = analyses[idx]
        if not isinstance(entry, dict):
            continue
        atype = entry.get("analysis_type", f"analysis_{idx}")
        r = entry.get("result", entry if "result" not in entry else {})
        if not isinstance(r, dict):
            continue

        metrics: dict[str, Any] = {}
        if "capability" in r:
            metrics.update(_extract_capability(r))
        if any(k.endswith("_chart") and isinstance(v, dict) for k, v in r.items()) \
                or isinstance(r.get("violations"), (list, tuple, dict)):
            metrics.update(_extract_spc(r))
        if isinstance(r.get("overall"), dict) or "avg_oee" in r:
            metrics.update(_extract_oee(r))
        if isinstance(r.get("percentages"), dict):
            metrics.update(_extract_msa(r))
        if "p_value" in r:
            metrics.update(_extract_hypothesis(r))
        if "r_squared" in r or isinstance(r.get("model"), dict):
            metrics.update(_extract_regression(r))
        if any(k in r for k in ("mtbf", "mttr", "avg_mtbf", "avg_mttr")):
            metrics.update(_extract_reliability(r))
        if "beta" in r and "eta" in r:
            metrics.update(_extract_weibull(r))
        if "lower" in r and "upper" in r and "width" in r:
            metrics.update(_extract_tolerance(r))
        if "improvement_pct" in r:
            metrics.update(_extract_smed(r))
        if isinstance(r.get("utilization"), dict):
            metrics.update(_extract_work_sampling(r))
        if "best_cpk" in r or "worst_cpk" in r:
            metrics.update(_extract_multi_plant(r))
        if "model_r_squared" in r:
            metrics.update(_extract_doe(r))
        if isinstance(r.get("results"), list):
            metrics.update(_extract_time_study(r))
        if isinstance(r.get("tests"), dict):
            metrics.update(_extract_normality(r))
        metrics.update({k: v for k, v in _extract_ie_default(r).items()
                        if k not in metrics})

        if metrics:
            out[atype] = metrics
    return out


def build_variable_namespace(analyses: dict[int, dict]) -> dict[str, float]:
    """为公式引擎构建扁平变量命名空间 — {metric_name: value}

    同名指标取最近一次分析的值; 仅保留数值变量。
    """
    ns: dict[str, float] = {}
    for metrics in extract_metrics(analyses).values():
        for name, value in metrics.items():
            if _scalar(value):
                ns[name] = value
    return ns
