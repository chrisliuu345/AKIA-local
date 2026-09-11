"""指标工程化解读 — QAM Harness 离线兜底能力（纯函数，无 Qt/无 IO）。

用于两类场景:
  1. 离线模式（无 LLM）也能对 Cp/Cpk/OEE/GRR 等给出可执行的工程解读；
  2. 在线模式下作为"事实层"，避免模型对判定阈值自由发挥。
判定阈值与 config.settings / 分析引擎保持一致。
"""
from __future__ import annotations

from typing import Any

SUPPORTED = ("cp", "cpk", "pp", "ppk", "ppm", "dppm", "sigma_level",
             "grr", "ndc", "oee", "availability", "performance", "quality",
             "p_value", "rpn", "balance_rate", "defect_rate")

_ALIASES = {
    "cpk": "cpk", "cp": "cp", "pp": "pp", "ppk": "ppk",
    "ppm": "ppm", "dppm": "ppm", "不良率": "ppm",
    "sigma": "sigma_level", "sigma_level": "sigma_level", "σ水平": "sigma_level",
    "grr": "grr", "%grr": "grr", "量具": "grr",
    "ndc": "ndc", "可分辨类别数": "ndc",
    "oee": "oee", "设备综合效率": "oee",
    "a": "availability", "availability": "availability", "可用率": "availability",
    "p": "performance", "performance": "performance", "性能": "performance",
    "q": "quality", "quality": "quality", "良品率": "quality",
    "p值": "p_value", "p_value": "p_value", "pvalue": "p_value",
    "rpn": "rpn", "风险优先数": "rpn",
    "平衡率": "balance_rate", "balance_rate": "balance_rate",
    "defect_rate": "defect_rate", "不良比例": "defect_rate",
}


def _f(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(num) >= 1000:
        return f"{num:,.0f}"
    return f"{round(num, digits):g}"


def _result(metric: str, value, level: str, text: str, advice: str = "") -> dict:
    return {"metric": metric, "value": value, "level": level,
            "text": text, "advice": advice}


def explain_metric(metric: str, value: float | None = None) -> dict | None:
    """返回 {metric, value, level, text, advice}；未知指标返回 None。"""
    key = _ALIASES.get(str(metric or "").strip().lower())
    if key is None:
        return None
    fn = globals().get(f"_explain_{key}")
    if fn is None:
        return None
    return fn(value)


def _explain_cpk(value):
    if value is None:
        return _result("cpk", None, "未知",
                       "Cpk 衡量过程在规格中心附近的实际能力（含均值偏移）。",
                       "给出 Cpk 数值后可判定等级：≥1.67 优秀 / ≥1.33 良好 / "
                       "≥1.00 勉强 / <1.00 不足。")
    if value >= 1.67:
        level, advice = "优秀", "可维持现状，重点是保持（SPC 监控 + 减少漂移）。"
    elif value >= 1.33:
        level, advice = "良好", "满足多数客户要求，可继续降低变异以留出安全余量。"
    elif value >= 1.00:
        level, advice = ("勉强", "存在超差风险：优先减小普通原因变异并评估均值对中。")
    else:
        level, advice = ("不足", "必然产生超差：立即做均值对中 + 降低变异（MSA 先确认测量系统）。")
    return _result("cpk", value, level,
                   f"Cpk={_f(value)} → {level}。", advice)


def _explain_cp(value):
    if value is None:
        return _result("cp", None, "未知", "Cp 只反映变异（不含均值偏移）。",
                       "Cp 与 Cpk 差距大说明均值偏离规格中心。")
    level = "优秀" if value >= 1.67 else ("良好" if value >= 1.33 else
                                      ("勉强" if value >= 1.0 else "不足"))
    return _result("cp", value, level, f"Cp={_f(value)}（潜在能力）→ {level}。",
                   "若 Cp 明显大于 Cpk，问题主要是对中而非变异。")


def _explain_pp(value):
    if value is None:
        return _result("pp", None, "未知", "Pp 用整体标准差衡量长期能力。",
                       "Pp/Ppk 与 Cp/Cpk 差距大说明过程存在时间漂移。")
    level = "优秀" if value >= 1.67 else ("良好" if value >= 1.33 else
                                      ("勉强" if value >= 1.0 else "不足"))
    return _result("pp", value, level, f"Pp={_f(value)}（长期表现）→ {level}。",
                   "与 Cp 对比可判断过程稳定性。")


def _explain_ppk(value):
    if value is None:
        return _result("ppk", None, "未知", "Ppk 用整体标准差衡量长期实际能力。",
                       "客户通常以 Ppk≥1.33 作为接收门槛。")
    level = "优秀" if value >= 1.67 else ("良好" if value >= 1.33 else
                                      ("勉强" if value >= 1.0 else "不足"))
    return _result("ppk", value, level, f"Ppk={_f(value)} → {level}。",
                   "Ppk 低于 Cpk 越多，说明过程随时间漂移越明显。")


def _explain_ppm(value):
    if value is None:
        return _result("ppm", None, "未知",
                       "PPM 为百万件不良数，可与 σ 水平换算。",
                       "常见目标: ≤233 PPM（4σ 级）, ≤3.4 PPM（6σ 级）。")
    if value <= 3.4:
        level = "6σ 级"
    elif value <= 233:
        level = "5σ 级"
    elif value <= 6210:
        level = "4σ 级"
    else:
        level = "低于 4σ"
    return _result("ppm", value, level, f"预计不良 {_f(value, 1)} PPM → {level}。",
                   "按 PPM × 产量可估算废品损失（可让成本工具给出金额）。")


def _explain_sigma_level(value):
    if value is None:
        return _result("sigma_level", None, "未知",
                       "σ 水平反映缺陷机会中的不良比例（含 1.5σ 长期偏移）。",
                       "6σ 对应 3.4 PPM，4σ 对应 6210 PPM。")
    level = ("6σ 级" if value >= 6 else "5σ 级" if value >= 5 else
             "4σ 级" if value >= 4 else "低于 4σ")
    return _result("sigma_level", value, level, f"σ 水平 {_f(value, 2)} → {level}。",
                   "σ 水平提升主要靠减小变异，而非单纯加严检验。")


def _explain_grr(value):
    if value is None:
        return _result("grr", None, "未知",
                       "%GRR 表示测量系统变异占过程/公差变异的比例。",
                       "判定: <10% 可接受，10–30% 有条件接受，>30% 不可接受。")
    if value < 10:
        level, advice = "可接受", "测量系统可用于当前过程控制与能力分析。"
    elif value < 30:
        level, advice = ("有条件接受", "视应用场合与客户要求；优先改善夹具/重复性。")
    else:
        level, advice = ("不可接受", "先修测量系统再谈过程改进（否则数据不可信）。")
    return _result("grr", value, level, f"%GRR={_f(value, 2)}% → {level}。", advice)


def _explain_ndc(value):
    if value is None:
        return _result("ndc", None, "未知", "ndc 为可分辨类别数（≥5 才有能力分辨过程）。",
                       "ndc<5 往往与 %GRR 偏高同源。")
    level = "合格" if value >= 5 else "不足"
    return _result("ndc", value, level, f"ndc={_f(value, 0)} → {level}。",
                   "提升办法: 增加零件间差异跨度、改善量具重复性。")


def _explain_oee(value):
    if value is None:
        return _result("oee", None, "未知", "OEE = A × P × Q。",
                       "分级: ≥85% 世界级，≥65% 达标，<40% 需系统性改善。")
    if value >= 0.85:
        level, advice = "世界级", "保持并关注长期稳定性与换型损失。"
    elif value >= 0.65:
        level, advice = ("达标", "按六大损失排序改善，优先停机与速度损失。")
    elif value >= 0.40:
        level, advice = ("待改善", "先解决可用率（故障/换型），再谈性能与质量。")
    else:
        level, advice = ("低效", "属于系统性瓶颈，建议 SMED + TPM 专项。")
    shown = value * 100 if value <= 1 else value
    return _result("oee", value, level, f"OEE={_f(shown, 2)}% → {level}。", advice)


def _explain_availability(value):
    return _explain_part(value, "availability", "可用率 A（时间开动率）",
                         "瓶颈通常是故障与换型，可用 SMED/TPM 改善。")


def _explain_performance(value):
    return _explain_part(value, "performance", "性能 P（速度/小停损失）",
                         "P>1 通常意味着节拍配置偏大，应校准理想节拍。")


def _explain_quality(value):
    return _explain_part(value, "quality", "质量 Q（良品率）",
                         "结合 PPM 与成本工具定位主要不良模式。")


def _explain_part(value, key: str, title: str, advice: str) -> dict:
    if value is None:
        return _result(key, None, "未知", f"{title} 是 OEE 的三要素之一。", advice)
    shown = value * 100 if value <= 1 else value
    level = "高" if shown >= 90 else ("中" if shown >= 75 else "低")
    return _result(key, value, level, f"{title}={_f(shown, 2)}% → {level}。", advice)


def _explain_p_value(value):
    if value is None:
        return _result("p_value", None, "未知", "p 值是在原假设成立时观测到当前结果的概率。",
                       "通常 α=0.05：p<0.05 拒绝原假设（差异显著）。")
    significant = value < 0.05
    level = "显著" if significant else "不显著"
    return _result("p_value", value, level,
                   f"p={_f(value, 4)} → {level}（α=0.05）。",
                   "统计显著不等于工程重要：请结合效应量与置信区间判断。" if significant
                   else "不显著不代表无差异，可能是样本量不足或变异过大。")


def _explain_rpn(value):
    if value is None:
        return _result("rpn", None, "未知", "RPN = 严重度 S × 频度 O × 探测度 D。",
                       "常见分档: ≥200 关键，≥100 高，≥50 中。")
    if value >= 200:
        level, advice = "关键", "必须制定纠正措施并重新评估（优先降低 S 或 O）。"
    elif value >= 100:
        level, advice = ("高", "建议纳入改善计划并跟踪至关闭。")
    elif value >= 50:
        level, advice = ("中", "可结合 S 单独判断（S≥9 即使 RPN 不高也需关注）。")
    else:
        level, advice = ("低", "维持现有控制。")
    return _result("rpn", value, level, f"RPN={_f(value, 0)} → {level}。", advice)


def _explain_balance_rate(value):
    if value is None:
        return _result("balance_rate", None, "未知",
                       "线平衡率 = 各工位作业时间之和 / (瓶颈时间 × 工位数)。",
                       "通常 ≥85% 为良好，<70% 存在明显等待浪费。")
    shown = value * 100 if value <= 1 else value
    level = "良好" if shown >= 85 else ("可改善" if shown >= 70 else "低")
    return _result("balance_rate", value, level,
                   f"平衡率={_f(shown, 1)}% → {level}。",
                   "用 ECRS（取消/合并/重排/简化）拆分瓶颈工位作业。")


def _explain_defect_rate(value):
    if value is None:
        return _result("defect_rate", None, "未知", "不良率 = 不良数 / 总数。",
                       "与成本工具结合可换算为金额损失。")
    shown = value * 100 if value <= 1 else value
    level = "良好" if shown < 1 else ("需改善" if shown < 5 else "差")
    return _result("defect_rate", value, level,
                   f"不良率={_f(shown, 2)}% → {level}。",
                   "先用 Pareto 找主要不良模式，再上 8D/FMEA 闭环。")
