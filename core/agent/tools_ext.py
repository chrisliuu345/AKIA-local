"""QAM Harness 扩展工具（v3.8.0 P2.5 / 评审建议 O1）。

补齐 Agent 对 36 个分析 Tab 的覆盖：SPC 的 Laney·Hotelling、能力的 Sixpack·
组间组内·Johnson·容差区间、MSA 的属性一致性·Type1·线性·偏倚·EMP、假设检验的
双因素 ANOVA·卡方·比例·TOST·非参数、DOE 全系（含设计生成与功效）、回归、
可靠性（Weibull·KM·Cox·Crow-AMSAA·保修·RBD）、时间序列（ARIMA·指数平滑·
季节分解·ACF/PACF）、IE（工时·线平衡·VSM·工作抽样·SMED·TPM）与 AI 根因分析。

约定与 tools.py 一致：直接调用既有分析引擎，返回结构化 data + 中文 text。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.agent.tool_helpers import (
    _as_list, _call_with_supported, _dataclass_dict, _df, _first_spec,
    _limit_text, _match_columns, _num_series, _pick,
)
from core.agent.tools import AgentContext, ToolRegistry, ToolResult, _fmt, _to_float


# ---------------------------------------------------------------- 注册入口


def register_extended_tools(reg: ToolRegistry, ctx: AgentContext) -> ToolRegistry:
    """把扩展工具注册进既有注册表（由 build_default_registry 调用）。"""
    _register_quality_tools(reg, ctx)
    _register_doe_tools(reg, ctx)
    _register_reliability_tools(reg, ctx)
    _register_timeseries_tools(reg, ctx)
    _register_ie_tools(reg, ctx)
    _register_ai_tools(reg, ctx)
    return reg


# ---------------------------------------------------------------- 质量分析


def _register_quality_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_laney_chart", "Laney 控制图（P′/U′）",
              "运行 Laney P′/U′ 控制图（大样本下修正过度离散），返回控制限与判异点",
              {"defects_column": "不合格品数/缺陷数列", "sizes_column": "子组样本量/单位数列",
               "chart_type": "P 或 U（默认 P）", "sheet": "表名(可选)"},
              category="质量分析", returns="cl/ucl/lcl/violations/sigma_z")
    def _laney(context: AgentContext, defects_column: str | None = None,
               sizes_column: str | None = None, chart_type: str = "P", sheet: str | None = None):
        name, frame = _df(context, sheet)
        cols = _match_columns(frame, [defects_column or "", sizes_column or ""])
        defects = _num_series(frame, cols[0]).values
        sizes = _num_series(frame, cols[1])
        sizes = sizes.reindex(range(len(frame))).dropna()
        n = min(len(defects), len(sizes))
        if n < 2:
            raise ValueError("Laney 图需要至少 2 个子组")
        from analysis.spc import laney
        ctype = "Laney U'" if str(chart_type).strip().upper().startswith("U") else "Laney P'"
        result = laney.analyze(defects[:n], sizes.values[:n], chart_type=ctype)
        data = {"sheet": name, "defects": cols[0], "sizes": cols[1],
                "chart_type": ctype, "cl": _pick(result, "center_line", "cl"),
                "ucl": _pick(result, "ucl"), "lcl": _pick(result, "lcl"),
                "sigma_z": _pick(result, "sigma_z", "sigma"),
                "violations": int(_pick(result, "n_violations", default=0) or 0)}
        text = (f"{ctype} — 表「{name}」{cols[0]}/{cols[1]}: "
                f"CL={_fmt(data['cl'])} UCL={_limit_text(data['ucl'])} "
                f"LCL={_limit_text(data['lcl'])}，判异 {data['violations']} 点"
                + (f"，σ_Z={_fmt(data['sigma_z'])}（>1 表示过度离散）"
                   if data["sigma_z"] else ""))
        return ToolResult("run_laney_chart", data=data, text=text)

    @reg.tool("run_hotelling_t2", "Hotelling T² 多变量控制图",
              "对多个相关测量列做 T² 多变量控制图（Phase 1/2），返回 T² 控制限与越限样本",
              {"columns": "测量列(逗号分隔，至少 2 列)", "subgroup_column": "子组列(可选)",
               "phase": "phase1/phase2", "sheet": "表名(可选)"},
              category="质量分析", returns="t2_ucl/violations/hotelling_test")
    def _hotelling(context: AgentContext, columns=None, subgroup_column: str | None = None,
                   phase: str = "phase1", sheet: str | None = None):
        name, frame = _df(context, sheet)
        wanted = _as_list(columns) or context.numeric_columns(name)[:3]
        if len(wanted) < 2:
            raise ValueError("Hotelling T² 需要至少 2 个测量列")
        cols = _match_columns(frame, wanted)
        subgroup = None
        if subgroup_column:
            subgroup = _match_columns(frame, [subgroup_column])[0]
        from analysis.spc import hotelling
        result = hotelling.analyze(frame, cols, subgroup_col=subgroup,
                                   phase=str(phase or "phase1"))
        chart = result.get("t2_chart", {})
        violations = chart.get("violations", []) or result.get("violations", []) or []
        ucl_values = chart.get("ucl")
        flat = (list(ucl_values) if isinstance(ucl_values, (list, tuple, np.ndarray))
                else [ucl_values])
        try:
            ucl_usable = all(np.isfinite(float(v)) and float(v) > 0 for v in flat)
        except (TypeError, ValueError):
            ucl_usable = False
        data = {"sheet": name, "columns": cols, "phase": result.get("phase", phase),
                "t2_ucl": _pick(chart, "ucl"), "violations": len(violations),
                "ucl_usable": ucl_usable,
                "hotelling_test": result.get("hotelling_test"),
                "summary": result.get("summary")}
        text = (f"Hotelling T²（{data['phase']}）— 表「{name}」变量 {', '.join(cols)}: "
                f"T² UCL={_limit_text(data['t2_ucl'])}，越限 {len(violations)} 点")
        if not ucl_usable:
            text += ("\n⚠ 当前样本量下 T² 控制限不可用（越限数不可信）；"
                     "请增加观测数或提供 subgroup_column（按批次/班次/产线分组）后重跑")
        return ToolResult("run_hotelling_t2", data=data, text=text)

    @reg.tool("run_capability_sixpack", "能力六合一（Capability Sixpack）",
              "一次输出控制图/直方图/概率图/能力统计/稳定性/正态性（六合一）",
              {"column": "测量列", "usl": "规格上限", "lsl": "规格下限",
               "target": "目标值(可选)", "subgroup_size": "子组大小(默认1)",
               "sheet": "表名(可选)"},
              category="质量分析", returns="cp/cpk/ppk/percent_defective/稳定性")
    def _sixpack(context: AgentContext, column: str | None = None, usl=None, lsl=None,
                 target=None, subgroup_size: int = 1, sheet: str | None = None):
        name, frame = _df(context, sheet)
        col = _match_columns(frame, [column] if column else
                             [context.pick_column(name) or ""])[0]
        usl_v, lsl_v = _first_spec(frame, usl, lsl)
        from analysis.capability import sixpack
        result = sixpack.analyze(_num_series(frame, col), usl_v, lsl_v,
                                 _to_float(target), int(subgroup_size or 1))
        stats = result.get("statistics", {})
        data = {"sheet": name, "column": col, "usl": usl_v, "lsl": lsl_v,
                "cp": _pick(stats, "cp"), "cpk": _pick(stats, "cpk"),
                "pp": _pick(stats, "pp"), "ppk": _pick(stats, "ppk"),
                "percent_defective": result.get("percent_defective"),
                "summary": result.get("summary")}
        text = (f"能力六合一 — 列「{col}」: Cp={_fmt(data['cp'])} Cpk={_fmt(data['cpk'])} "
                f"Pp={_fmt(data['pp'])} Ppk={_fmt(data['ppk'])}，"
                f"预计不良 {_fmt(data['percent_defective'], 3)}%")
        return ToolResult("run_capability_sixpack", data=data, text=text)

    @reg.tool("run_capability_advanced", "能力分析（进阶方法）",
              "组间组内能力 / Johnson 变换 / 容差区间",
              {"method": "between_within/johnson/tolerance_interval", "column": "测量列",
               "subgroup_column": "子组列(组间组内必填)", "usl": "规格上限(可选)",
               "lsl": "规格下限(可选)", "confidence": "置信水平(默认0.95)",
               "proportion": "容差区间覆盖比例(默认0.99)", "sheet": "表名(可选)"},
              category="质量分析")
    def _cap_advanced(context: AgentContext, method: str = "between_within",
                      column: str | None = None, subgroup_column: str | None = None,
                      usl=None, lsl=None, confidence: float = 0.95,
                      proportion: float = 0.99, sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(method or "between_within").lower()
        col = _match_columns(frame, [column] if column else
                             [context.pick_column(name) or ""])[0]
        series = _num_series(frame, col)
        usl_v, lsl_v = _first_spec(frame, usl, lsl)
        if kind.startswith("johnson"):
            from analysis.capability import johnson_transform
            result = johnson_transform.johnson_transform(series.values, method="auto")
            out = result.get("result", result)
            data = {"sheet": name, "column": col, "method": "johnson",
                    "johnson_type": _pick(out, "johnson_type", "type"),
                    "params": _pick(out, "params")}
            text = (f"Johnson 变换 — 列「{col}」: 建议类型 {data['johnson_type']}"
                    f"（参数 {data['params']}）")
            return ToolResult("run_capability_advanced", data=data, text=text)
        if kind.startswith("tolerance"):
            from analysis.capability import tolerance_interval
            result = tolerance_interval.tolerance_interval_normal(
                series.values, float(confidence), float(proportion))
            out = result.get("result", result)
            lower = _pick(out, "lower", "lower_limit")
            upper = _pick(out, "upper", "upper_limit")
            data = {"sheet": name, "column": col, "method": "tolerance_interval",
                    "confidence": confidence, "proportion": proportion,
                    "lower": lower, "upper": upper, "detail": out}
            text = (f"容差区间（置信 {confidence:g} / 覆盖 {proportion:g}）— 列「{col}」: "
                    f"[{_fmt(lower)}, {_fmt(upper)}]")
            return ToolResult("run_capability_advanced", data=data, text=text)
        if not subgroup_column:
            raise ValueError("组间组内能力分析需要 subgroup_column（子组/批次列）")
        sub = _match_columns(frame, [subgroup_column])[0]
        from analysis.capability import between_within_cap
        result = between_within_cap.analyze(frame, col, sub, usl_v, lsl_v)
        stats = result.get("capability", result.get("statistics", result))
        summary = result.get("summary", {})
        data = {"sheet": name, "column": col, "subgroup": sub,
                "method": "between_within", "usl": usl_v, "lsl": lsl_v,
                "cp": _pick(stats, "cp"), "cpk": _pick(stats, "cpk"),
                "grade": _pick(stats, "grade"),
                "std_within": _pick(summary, "within_std", "std_within"),
                "std_overall": _pick(summary, "overall_std", "std_overall"),
                "std_between": _pick(summary, "between_std")}
        ratio = None
        if data["std_within"] and data["std_overall"]:
            ratio = float(data["std_overall"]) / float(data["std_within"])
        text = (f"组间组内能力 — 列「{col}」按「{sub}」: Cp={_fmt(data['cp'])} "
                f"Cpk={_fmt(data['cpk'])}（{data['grade'] or '—'}），"
                f"整体/组内标准差比={_fmt(ratio, 3)}"
                + ("（>1.1 说明批间波动显著）" if ratio and ratio > 1.1 else ""))
        return ToolResult("run_capability_advanced", data=data, text=text)

    @reg.tool("run_msa_advanced", "MSA 进阶研究",
              "属性一致性 / Type 1 量具研究 / 线性 / 偏倚 / EMP 方法",
              {"method": "attribute_agreement/type1/linearity/bias/emp",
               "measurement_column": "测量列", "part_column": "零件列",
               "operator_column": "操作员列", "reference_column": "参考值列",
               "result_column": "判定结果列", "standard_column": "标准判定列",
               "reference": "参考值(偏倚/Type1)", "usl": "规格上限(可选)",
               "lsl": "规格下限(可选)", "sheet": "表名(可选)"},
              category="质量分析")
    def _msa_advanced(context: AgentContext, method: str = "type1",
                      measurement_column: str | None = None, part_column: str | None = None,
                      operator_column: str | None = None, reference_column: str | None = None,
                      result_column: str | None = None, standard_column: str | None = None,
                      reference=None, usl=None, lsl=None, sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(method or "type1").lower()
        if kind.startswith("attr"):
            cols = _match_columns(frame, [result_column or "结果", standard_column or "标准",
                                          operator_column or "操作员"])
            from analysis.msa import attribute_agree
            result = attribute_agree.analyze(frame, cols[0], cols[1], cols[2])
            data = {"sheet": name, "method": "attribute_agreement", "columns": cols,
                    "kappa": _pick(result, "kappa", "fleiss_kappa"),
                    "agreement_rate": _pick(result, "agreement_rate",
                                            "percent_agreement", "agreement"),
                    "interpretation": _pick(result, "kappa_interpretation"),
                    "acceptable": _pick(result, "is_acceptable"),
                    "detail": result}
            text = (f"属性一致性 — 判定列「{cols[0]}」 vs 标准「{cols[1]}」"
                    f"（操作员 {cols[2]}）: Kappa={_fmt(data['kappa'])}，"
                    f"一致率={_fmt(data['agreement_rate'], 1)}%"
                    + (f"，{data['interpretation']}" if data["interpretation"] else ""))
            return ToolResult("run_msa_advanced", data=data, text=text)
        if kind.startswith("emp"):
            cols = _match_columns(frame, [measurement_column or "测量值",
                                          part_column or "零件", operator_column or "操作员"])
            from analysis.msa import emp
            result = emp.analyze_crossed(frame, cols[0], cols[1], cols[2])
            data = {"sheet": name, "method": "emp", "columns": cols,
                    "ndc": _pick(result, "ndc"),
                    "grade": _pick(result, "discrimination_grade"),
                    "acceptance": _pick(result, "acceptance"),
                    "detail": result}
            text = (f"EMP 方法 — {cols[0]} × {cols[1]} × {cols[2]}: "
                    f"ndc={_fmt(data['ndc'], 0)}，判别能力 "
                    f"{data['grade'] or _fmt(data['acceptance'])}")
            return ToolResult("run_msa_advanced", data=data, text=text)
        if kind.startswith("line"):
            cols = _match_columns(frame, [measurement_column or "测量值",
                                          reference_column or "参考值"])
            from analysis.msa import linearity_bias
            result = linearity_bias.analyze_linearity(frame, cols[0], cols[1])
            data = {"sheet": name, "method": "linearity", "columns": cols,
                    "slope": _pick(result, "slope"), "p_value": _pick(result, "p_value"),
                    "detail": result}
            text = (f"线性 — {cols[0]} vs {cols[1]}: 斜率={_fmt(data['slope'])}，"
                    f"p={_fmt(data['p_value'], 4)}")
            return ToolResult("run_msa_advanced", data=data, text=text)
        if kind.startswith("bias"):
            col = _match_columns(frame, [measurement_column or "测量值"])[0]
            ref = _to_float(reference)
            if ref is None:
                raise ValueError("偏倚研究需要 reference（参考值）")
            from analysis.msa import linearity_bias
            result = linearity_bias.analyze_bias(_num_series(frame, col), ref)
            data = {"sheet": name, "method": "bias", "column": col, "reference": ref,
                    "bias": _pick(result, "bias"), "p_value": _pick(result, "p_value"),
                    "detail": result}
            text = (f"偏倚 — 列「{col}」 vs 参考值 {_fmt(ref)}: 偏倚={_fmt(data['bias'])}，"
                    f"p={_fmt(data['p_value'], 4)}")
            return ToolResult("run_msa_advanced", data=data, text=text)
        col = _match_columns(frame, [measurement_column or "测量值"])[0]
        ref = _to_float(reference)
        if ref is None:
            raise ValueError("Type 1 量具研究需要 reference（参考值）")
        from analysis.msa import type1_study
        result = type1_study.analyze(_num_series(frame, col), ref,
                                     _to_float(usl), _to_float(lsl))
        summary = result.get("summary", {})
        bias_test = result.get("bias_test", {}) or {}
        mean = _pick(summary, "mean")
        data = {"sheet": name, "method": "type1", "column": col, "reference": ref,
                "repeatability": _pick(summary, "std", "repeatability"),
                "mean": mean,
                "bias": (float(mean) - float(ref)) if mean is not None else None,
                "bias_p_value": _pick(bias_test, "p_value", "p"),
                "bias_conclusion": _pick(bias_test, "conclusion", "is_significant"),
                "detail": result}
        text = (f"Type 1 量具研究 — 列「{col}」: 重复性(σ)={_fmt(data['repeatability'])}，"
                f"平均={_fmt(data['mean'])} vs 参考 {_fmt(ref)} → 偏倚="
                f"{_fmt(data['bias'])}"
                + (f"，偏倚 p={_fmt(data['bias_p_value'], 4)}"
                   if data["bias_p_value"] is not None else ""))
        return ToolResult("run_msa_advanced", data=data, text=text)

    @reg.tool("run_hypothesis_advanced", "假设检验（进阶）",
              "双因素 ANOVA / 卡方独立性 / 两比例检验 / TOST 等价 / Mann-Whitney / Kruskal-Wallis",
              {"method": "anova_twoway/chi_square/proportion/tost/mann_whitney/kruskal",
               "column": "数值列", "second_column": "第二数值列(两组比较)",
               "group_column": "分组列(A/B 组)", "factor_a": "因素A列(双因素)",
               "factor_b": "因素B列(双因素)", "categorical_column": "分类列(卡方)",
               "successes1": "组1成功数(两比例)", "n1": "组1样本量",
               "successes2": "组2成功数", "n2": "组2样本量",
               "target_mean": "目标均值(TOST)", "margin": "等价界限(TOST)",
               "alpha": "显著性水平(默认0.05)", "sheet": "表名(可选)"},
              category="质量分析")
    def _hyp_advanced(context: AgentContext, method: str = "anova_twoway",
                      column: str | None = None, second_column: str | None = None,
                      group_column: str | None = None, factor_a: str | None = None,
                      factor_b: str | None = None, categorical_column: str | None = None,
                      successes1=None, n1=None, successes2=None, n2=None,
                      target_mean=None, margin=None, alpha: float = 0.05,
                      sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(method or "").lower()
        kw = {"alpha": float(alpha or 0.05)}
        if kind.startswith("anova_two"):
            cols = _match_columns(frame, [column or "响应", factor_a or "因素A",
                                          factor_b or "因素B"])
            from analysis.hypothesis import anova
            result = anova.two_way(frame, cols[0], cols[1], cols[2])
            table = result.get("anova_table", {}) or {}
            data = {"sheet": name, "method": "anova_twoway", "columns": cols,
                    "significant_factors": _pick(result, "significant_factors"),
                    "p_values": _pick(table, "p_value", "p") if isinstance(table, dict) else None,
                    "detail": result}
            sig = data["significant_factors"]
            if isinstance(sig, dict):
                sig = [k for k, v in sig.items() if v] or ["无（均不显著）"]
            text = (f"双因素 ANOVA — {cols[0]} ~ {cols[1]} × {cols[2]}: "
                    f"显著因素 {', '.join(str(s) for s in sig) if isinstance(sig, list) else sig}")
            if isinstance(table, dict):
                for source, p in zip(table.get("source", []),
                                     table.get("p_value", table.get("p", [])),
                                     strict=False):
                    if source and p is not None:
                        text += f"\n  {source}: p={_fmt(p, 4)}"
            return ToolResult("run_hypothesis_advanced", data=data, text=text)
        if kind.startswith("chi"):
            cols = _match_columns(frame, [column or "列1", categorical_column or "列2"])
            from analysis.hypothesis import proportion
            result = proportion.chi_square_independence(frame, cols[0], cols[1])
            data = {"sheet": name, "method": "chi_square", "columns": cols,
                    "chi2": _pick(result, "chi2_statistic", "chi2", "statistic"),
                    "p_value": _pick(result, "p_value"),
                    "dof": _pick(result, "dof", "degrees_of_freedom"),
                    "cramers_v": _pick(result, "cramers_v"),
                    "conclusion": ("差异显著" if result.get("is_significant")
                                   else "差异不显著")}
            text = (f"卡方独立性检验 — {cols[0]} × {cols[1]}: χ²={_fmt(data['chi2'])}，"
                    f"p={_fmt(data['p_value'], 4)}，{data['conclusion']}"
                    + (f"（Cramér's V={_fmt(data['cramers_v'], 3)}）"
                       if data["cramers_v"] is not None else ""))
            return ToolResult("run_hypothesis_advanced", data=data, text=text)
        if kind.startswith("prop"):
            from analysis.hypothesis import proportion
            result = proportion.two_proportion_test(
                int(successes1 or 0), int(n1 or 0), int(successes2 or 0), int(n2 or 0))
            data = {"method": "proportion", "p_value": _pick(result, "p_value"),
                    "z": _pick(result, "z_statistic", "z"),
                    "detail": result}
            text = (f"两比例检验 — p1={_fmt(int(successes1 or 0) / max(int(n1 or 1), 1))} "
                    f"vs p2={_fmt(int(successes2 or 0) / max(int(n2 or 1), 1))}: "
                    f"p={_fmt(data['p_value'], 4)}")
            return ToolResult("run_hypothesis_advanced", data=data, text=text)
        if kind.startswith("tost"):
            col = _match_columns(frame, [column or context.pick_column(name) or ""])[0]
            if target_mean is None or margin is None:
                raise ValueError("TOST 需要 target_mean 与 margin（等价界限）")
            from analysis.hypothesis import equivalence
            result = equivalence.one_sample_tost(
                _num_series(frame, col), float(target_mean), float(margin),
                kw["alpha"])
            data = {"sheet": name, "method": "tost", "column": col,
                    "p_value": _pick(result, "p_value"), "equivalent": _pick(
                        result, "equivalent", "is_equivalent"),
                    "detail": result}
            text = (f"TOST 等价检验 — 列「{col}」 vs 目标 {_fmt(target_mean)}"
                    f"（±{_fmt(margin)}）: p={_fmt(data['p_value'], 4)}，"
                    f"{'等效' if data['equivalent'] else '不等效'}")
            return ToolResult("run_hypothesis_advanced", data=data, text=text)
        # 非参数：两组比较 / 多组比较
        if kind.startswith("kruskal"):
            if not group_column:
                raise ValueError("Kruskal-Wallis 需要 group_column（分组列）")
            cols = _match_columns(frame, [column or context.pick_column(name) or "",
                                          group_column])
            groups = [pd.to_numeric(g[cols[0]], errors="coerce").dropna().values
                      for _k, g in frame.groupby(cols[1])]
            groups = [g for g in groups if len(g) >= 2]
            if len(groups) < 2:
                raise ValueError("至少需要 2 个有效分组")
            from analysis.hypothesis import nonparametric
            result = nonparametric.kruskal_wallis(*groups)
            data = {"sheet": name, "method": "kruskal", "columns": cols,
                    "statistic": _pick(result, "h_statistic", "statistic", "h"),
                    "p_value": _pick(result, "p_value"), "detail": result}
            text = (f"Kruskal-Wallis — 「{cols[0]}」按「{cols[1]}」: "
                    f"H={_fmt(data['statistic'])}，p={_fmt(data['p_value'], 4)}")
            return ToolResult("run_hypothesis_advanced", data=data, text=text)
        cols = _match_columns(frame, [column or "样本1", second_column or "样本2"])
        from analysis.hypothesis import nonparametric
        a = _num_series(frame, cols[0]).values
        b = _num_series(frame, cols[1]).values
        result = nonparametric.mann_whitney(a, b)
        data = {"sheet": name, "method": "mann_whitney", "columns": cols,
                "statistic": _pick(result, "u_statistic", "statistic", "u"),
                "p_value": _pick(result, "p_value"), "detail": result}
        text = (f"Mann-Whitney U — {cols[0]} vs {cols[1]}: "
                f"U={_fmt(data['statistic'])}，p={_fmt(data['p_value'], 4)}")
        return ToolResult("run_hypothesis_advanced", data=data, text=text)


# ---------------------------------------------------------------- DOE / 回归


_DOE_ANALYZERS = {
    "factorial": ("analysis.doe.factorial", "analyze_factorial"),
    "fractional": ("analysis.doe.fractional", "analyze"),
    "response_surface": ("analysis.doe.response_surface", "analyze_response_surface"),
    "box_behnken": ("analysis.doe.box_behnken", "analyze_box_behnken"),
    "plackett_burman": ("analysis.doe.plackett_burman", "analyze"),
    "dsd": ("analysis.doe.definitive_screening", "analyze"),
    "taguchi": ("analysis.doe.taguchi", "analyze"),
    "mixture": ("analysis.doe.mixture", "analyze"),
}


def _register_doe_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_doe_analysis", "DOE 试验分析",
              "对已录入的试验结果做方差分析/效应与显著性判定（因子设计/部分因子/"
              "响应曲面/Box-Behnken/PB/DSD/田口/混料）",
              {"design": "factorial/fractional/response_surface/box_behnken/"
                         "plackett_burman/dsd/taguchi/mixture",
               "response_column": "响应列", "factor_columns": "因子列(逗号分隔，需数值编码如 -1/+1)",
               "alpha": "显著性水平(默认0.05)", "model": "混料模型(linear/quadratic)",
               "sn_type": "田口信噪比(larger_is_better/smaller_is_better/"
                          "nominal_is_best)", "sheet": "表名(可选)"},
              category="DOE", returns="r_squared/显著效应/p_value")
    def _doe(context: AgentContext, design: str = "factorial",
             response_column: str | None = None, factor_columns=None, alpha: float = 0.05,
             model: str = "quadratic", sn_type: str = "larger_is_better",
             sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(design or "factorial").lower()
        if kind not in _DOE_ANALYZERS:
            raise ValueError(f"不支持的试验设计 {design}"
                             f"（可选 {', '.join(_DOE_ANALYZERS)}）")
        wanted = _as_list(factor_columns)
        if not wanted:
            wanted = [c for c in context.numeric_columns(name) if c != response_column][:4]
        resp = _match_columns(frame, [response_column or context.pick_column(name) or ""])[0]
        factors = [c for c in _match_columns(frame, wanted) if c != resp]
        if not factors:
            raise ValueError("DOE 分析需要至少 1 个因子列（factor_columns）")
        import importlib
        module_name, fn_name = _DOE_ANALYZERS[kind]
        fn = getattr(importlib.import_module(module_name), fn_name)
        kwargs = {"alpha": float(alpha or 0.05)}
        if kind == "mixture":
            result = _call_with_supported(fn, frame, resp, factors,
                                          model=model or "quadratic", **kwargs)
        elif kind == "taguchi":
            result = _call_with_supported(
                fn, frame, resp, factors,
                sn_type=sn_type or "larger_is_better", **kwargs)
        else:
            result = _call_with_supported(fn, frame, resp, factors, **kwargs)
        effects = (_pick(result, "effects") or _pick(result, "anova_table")
                   or _pick(result, "significant_effects"))
        anova_table = result.get("anova") if isinstance(result.get("anova"), dict) else {}
        p_list = [p for p in (anova_table.get("p_value") or []) if p is not None]
        data = {"sheet": name, "design": kind, "response": resp, "factors": factors,
                "r_squared": _pick(result, "model_r_squared", "r_squared", "r2"),
                "adj_r_squared": _pick(result, "r_squared_adjusted",
                                       "adj_r_squared", "adj_r2"),
                "model_p_value": (min(p_list) if p_list
                                  else _pick(result, "model_p_value", "p_value")),
                "effects": effects,
                "significant_effects": _pick(result, "significant_factors"),
                "detail": result}
        text = (f"{kind} 分析 — 响应「{resp}」因子 {', '.join(factors)}: "
                f"R²={_fmt(data['r_squared'], 4)}，模型 p={_fmt(data['model_p_value'], 4)}")
        lines = [text]
        sig = data["significant_effects"]
        if isinstance(sig, dict):
            sig = [k for k, v in sig.items() if v] or ["无（均不显著）"]
        if isinstance(sig, (list, tuple)) and sig:
            lines.append("显著效应: " + ", ".join(str(s) for s in sig[:8]))
        if isinstance(anova_table, dict):
            for source, p in zip(anova_table.get("source", []),
                                 anova_table.get("p_value", []), strict=False):
                if source and p is not None:
                    lines.append(f"  {source}: p={_fmt(p, 4)}")
        return ToolResult("run_doe_analysis", data=data, text="\n".join(lines))

    @reg.tool("generate_doe_design", "生成 DOE 试验计划",
              "生成试验设计矩阵（运行表），用于安排试验顺序与记录表单",
              {"design": "factorial/fractional/ccd/bbd/plackett_burman/dsd/"
                         "taguchi/simplex_lattice",
               "factors": "因子/成分名(逗号分隔)", "replicates": "重复次数(默认1)",
               "fraction": "部分因子分数(如 1/2)", "center_points": "中心点(默认3)",
               "degree": "混料单纯形格点阶数(默认2)", "n_runs": "PB 运行数(可选)"},
              category="DOE", returns="runs/design_table")
    def _gen_design(context: AgentContext, design: str = "factorial", factors=None,
                    replicates: int = 1, fraction: str = "1/2",
                    center_points: int = 3, degree: int = 2, n_runs=None):
        import importlib
        items = _as_list(factors)
        kind = str(design or "factorial").lower()
        if not items:
            raise ValueError("请提供 factors（因子名，逗号分隔）")
        if kind == "factorial":
            from analysis.doe import factorial
            table = factorial.generate_design(items, int(replicates or 1))
        elif kind == "fractional":
            from analysis.doe import fractional
            table = fractional.generate_design(items, fraction=fraction or "1/2")
        elif kind in ("ccd", "response_surface"):
            from analysis.doe import response_surface
            table = response_surface.generate_ccd(items, center_points=int(center_points or 3))
        elif kind in ("bbd", "box_behnken"):
            from analysis.doe import box_behnken
            table = box_behnken.generate_bbd(items, center_points=int(center_points or 3))
        elif kind == "plackett_burman":
            from analysis.doe import plackett_burman
            table = plackett_burman.generate_design(items, n_runs=n_runs)
        elif kind == "dsd":
            from analysis.doe import definitive_screening
            table = definitive_screening.generate_design(items)
        elif kind == "taguchi":
            from analysis.doe import taguchi
            table = taguchi.generate_design(items)
        elif kind in ("simplex_lattice", "mixture"):
            from analysis.doe import mixture
            table = mixture.simplex_lattice(items, degree=int(degree or 2))
        else:
            raise ValueError(f"不支持的设计类型 {design}")
        del importlib
        head = table.head(5).to_dict("records")
        data = {"design": kind, "factors": items, "runs": int(len(table)),
                "columns": [str(c) for c in table.columns], "head": head}
        lines = [f"{kind} 设计已生成: {len(table)} 次运行 × {len(table.columns)} 列",
                 "列: " + ", ".join(str(c) for c in table.columns),
                 "前 5 行:"]
        for row in head:
            lines.append("  " + ", ".join(f"{k}={row[k]}" for k in row))
        return ToolResult("generate_doe_design", data=data, text="\n".join(lines))

    @reg.tool("run_power_analysis", "功效与样本量",
              "计算检验功效或所需样本量（单样本/双样本 t 检验）",
              {"method": "power/sample_size", "test": "one_sample/two_sample",
               "n": "样本量(power 用)", "delta": "需检出的差值", "sigma": "标准差",
               "alpha": "显著性水平(默认0.05)", "power": "目标功效(默认0.8)",
               "ratio": "两组样本量比(默认1)"},
              category="DOE", returns="power/sample_size")
    def _power(context: AgentContext, method: str = "power", test: str = "one_sample",
               n=None, delta=None, sigma=None, alpha: float = 0.05,
               power: float = 0.8, ratio: float = 1.0):
        delta_v, sigma_v = _to_float(delta), _to_float(sigma)
        if delta_v is None or sigma_v in (None, 0):
            raise ValueError("需要 delta（差值）与 sigma（标准差）")
        from analysis.doe import power_analysis as pa
        two = str(test or "one_sample").lower().startswith("two")
        value = None
        if str(method).startswith("sample"):
            fn = pa.sample_size_two_sample_t if two else pa.sample_size_one_sample_t
            value = fn(delta_v, sigma_v, power=float(power), alpha=float(alpha),
                       **({"ratio": float(ratio)} if two else {}))
            metric = "sample_size"
        else:
            if n is None:
                raise ValueError("计算功效需要 n（样本量）")
            fn = pa.power_two_sample_t if two else pa.power_one_sample_t
            value = fn(int(n), delta_v, sigma_v, alpha=float(alpha),
                       **({"ratio": float(ratio)} if two else {}))
            metric = "power"
        data = {"method": method, "test": test, "metric": metric, "value": value,
                "delta": delta_v, "sigma": sigma_v, "alpha": alpha}
        text = (f"{'双样本' if two else '单样本'} t 检验 — "
                f"δ={_fmt(delta_v)} σ={_fmt(sigma_v)} α={alpha:g}: "
                f"{'所需样本量' if metric == 'sample_size' else '检验功效'}="
                f"{_fmt(value, 3)}")
        return ToolResult("run_power_analysis", data=data, text=text)

    @reg.tool("run_regression", "回归分析",
              "线性/多元回归（系数、R²、显著性、共线性提示）",
              {"response_column": "响应列", "factor_columns": "自变量列(逗号分隔)",
               "sheet": "表名(可选)"}, category="回归",
              returns="r_squared/coefficients/p_value")
    def _regression(context: AgentContext, response_column: str | None = None,
                    factor_columns=None, sheet: str | None = None):
        name, frame = _df(context, sheet)
        resp = _match_columns(
            frame, [response_column or context.pick_column(name) or ""])[0]
        wanted = _as_list(factor_columns)
        if not wanted:
            wanted = [c for c in context.numeric_columns(name) if c != resp][:4]
        factors = [c for c in _match_columns(frame, wanted) if c != resp]
        if not factors:
            raise ValueError("回归分析需要至少 1 个自变量列")
        from analysis.regression import linear_regression
        result = linear_regression.analyze(frame, resp, factors)
        model = result.get("model", result)
        coefficients = result.get("coefficients", [])
        anova_table = result.get("anova") if isinstance(result.get("anova"), dict) else {}
        data = {"sheet": name, "response": resp, "factors": factors,
                "r_squared": _pick(result, "r_squared", default=_pick(model, "r_squared", "r2")),
                "adj_r_squared": _pick(result, "r_squared_adjusted", "adj_r_squared",
                                       "adj_r2"),
                "p_value": _to_float(_pick(anova_table, "f_p_value", "p_value", "p",
                                           "model_p_value")),
                "residual_std": _pick(result, "residual_std"),
                "coefficients": coefficients,
                "warnings": result.get("warnings", [])}
        lines = [(f"回归分析 — {resp} ~ {' + '.join(factors)}: "
                 f"R²={_fmt(data['r_squared'], 4)}，"
                 f"调整 R²={_fmt(data['adj_r_squared'], 4)}，"
                 f"p={_fmt(data['p_value'], 4)}")]
        for coef in (coefficients or [])[:5]:
            if isinstance(coef, dict):
                lines.append(f"  {coef.get('term', coef.get('name', '?'))}: "
                             f"系数={_fmt(coef.get('coef', coef.get('estimate')))} "
                             f"p={_fmt(coef.get('p_value'), 4)}")
        return ToolResult("run_regression", data=data, text="\n".join(lines))


# ---------------------------------------------------------------- 可靠性


def _register_reliability_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_reliability", "可靠性分析",
              "Weibull 寿命 / Kaplan-Meier 生存曲线 / Cox 回归 / Crow-AMSAA 可靠性增长 / "
              "保修成本 / RBD 系统可靠度",
              {"method": "weibull/kaplan_meier/cox/crow_amsaa/warranty/rbd",
               "time_column": "失效时间/寿命列", "event_column": "事件列(1=失效,0=删失)",
               "covariates": "协变量列(逗号分隔，Cox 用)", "warranty_period": "保修期",
               "cost_per_failure": "单次失效成本", "total_units": "总出货数量",
               "three_parameter": "Weibull 三参数(true/false)",
               "mtbf_column": "RBD 组件 MTBF 列", "mission_time": "任务时间(默认1)",
               "structure": "RBD 结构(series/parallel)", "sheet": "表名(可选)"},
              category="可靠性")
    def _reliability(context: AgentContext, method: str = "weibull",
                     time_column: str | None = None, event_column: str | None = None,
                     covariates=None, warranty_period=None, cost_per_failure=None,
                     total_units=None, three_parameter: bool = False,
                     mtbf_column: str | None = None, mission_time: float = 1.0,
                     structure: str = "series", sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(method or "weibull").lower()
        if kind.startswith("weibull"):
            col = _match_columns(frame, [time_column or "失效时间"])[0]
            times = [float(v) for v in _num_series(frame, col).tolist()]
            from analysis.reliability.weibull import WeibullAnalyzer
            raw = WeibullAnalyzer().analyze(times, three_parameter=bool(three_parameter))
            result = _dataclass_dict(raw.get("result", raw))
            data = {"sheet": name, "method": "weibull", "column": col,
                    "beta": _pick(result, "beta", "shape"),
                    "eta": _pick(result, "eta", "scale"),
                    "b10_life": _pick(result, "b10", "b10_life"),
                    "mtbf": _pick(result, "mtbf", "mean_life"),
                    "detail": result}
            text = (f"Weibull 寿命分析 — 列「{col}」(n={len(times)}): "
                    f"β={_fmt(data['beta'])} η={_fmt(data['eta'])}，"
                    f"B10={_fmt(data['b10_life'])} MTBF={_fmt(data['mtbf'])}")
            return ToolResult("run_reliability", data=data, text=text)
        if kind.startswith(("kaplan", "km")):
            cols = _match_columns(frame, [time_column or "时间", event_column or "事件"])
            from analysis.reliability.survival import kaplan_meier
            result = kaplan_meier(_num_series(frame, cols[0]),
                                  pd.to_numeric(frame[cols[1]], errors="coerce").fillna(0))
            summary = result.get("summary", {})
            data = {"sheet": name, "method": "kaplan_meier", "columns": cols,
                    "median_life": _pick(summary, "median_life", "median_survival"),
                    "summary": summary}
            text = (f"Kaplan-Meier — 「{cols[0]}」/「{cols[1]}」: "
                    f"中位寿命={_fmt(data['median_life'])}，"
                    f"{_fmt(summary) if isinstance(summary, str) else ''}")
            return ToolResult("run_reliability", data=data, text=text)
        if kind.startswith("cox"):
            cols = _match_columns(frame, [time_column or "时间", event_column or "事件"])
            cov = _as_list(covariates) or [
                c for c in context.numeric_columns(name) if c not in cols][:3]
            cov_cols = [c for c in _match_columns(frame, cov) if c not in cols]
            from analysis.reliability.survival import cox_regression
            result = cox_regression(frame, cols[0], cols[1], cov_cols)
            summary = result.get("summary", {})
            data = {"sheet": name, "method": "cox", "duration": cols[0],
                    "event": cols[1], "covariates": cov_cols,
                    "concordance": _pick(summary, "concordance_index",
                                         "concordance", "c_index"),
                    "n_events": _pick(summary, "n_events"),
                    "lr_p_value": _pick(summary, "log_likelihood_ratio_test_p"),
                    "detail": result}
            text = (f"Cox 回归 — 时间「{cols[0]}」事件「{cols[1]}」协变量 "
                    f"{', '.join(cov_cols) or '无'}: 一致性指数="
                    f"{_fmt(data['concordance'], 3)}"
                    + (f"，LR 检验 p={_fmt(data['lr_p_value'], 4)}"
                       if data["lr_p_value"] is not None else ""))
            return ToolResult("run_reliability", data=data, text=text)
        if kind.startswith("crow"):
            col = _match_columns(frame, [time_column or "失效时间"])[0]
            times = [float(v) for v in _num_series(frame, col).tolist()]
            from analysis.reliability.mtbf import crow_amsaa
            result = crow_amsaa(times)
            summary = result.get("summary", {})
            data = {"sheet": name, "method": "crow_amsaa", "column": col,
                    "beta": _pick(summary, "beta"),
                    "growth_rate": _pick(summary, "growth_rate"),
                    "mtbf": _pick(summary, "mtbf_at_T", "mtbf"),
                    "trend": _pick(summary, "trend"),
                    "detail": result}
            text = (f"Crow-AMSAA 可靠性增长 — 列「{col}」: β={_fmt(data['beta'])}"
                    f"（trend={data['trend'] or '—'}），当前 MTBF={_fmt(data['mtbf'])}，"
                    f"增长率 {_fmt(data['growth_rate'])}")
            return ToolResult("run_reliability", data=data, text=text)
        if kind.startswith("warrant"):
            col = _match_columns(frame, [time_column or "失效时间"])[0]
            period = _to_float(warranty_period)
            cost = _to_float(cost_per_failure)
            units = _to_float(total_units)
            if None in (period, cost, units):
                raise ValueError("保修分析需要 warranty_period / cost_per_failure / total_units")
            from analysis.reliability import warranty
            result = warranty.analyze(_num_series(frame, col), period, cost, int(units))
            summary = result.get("summary", {})
            data = {"sheet": name, "method": "warranty", "column": col,
                    "expected_failures": _pick(summary, "expected_failures", "failures",
                                               "predicted_failures"),
                    "warranty_cost": _pick(summary, "total_cost", "cost", "warranty_cost",
                                           "expected_cost"),
                    "summary": summary,
                    "detail": result}
            text = (f"保修分析 — 列「{col}」保修期 {_fmt(period)}（出货 {int(units)} 台，"
                    f"单次成本 {_fmt(cost)}）: 预计失效 "
                    f"{_fmt(data['expected_failures'], 1)} 台，成本 "
                    f"{_fmt(data['warranty_cost'], 2)}")
            if data["expected_failures"] is None:
                text += f"\n（引擎摘要: {summary}）"
            return ToolResult("run_reliability", data=data, text=text)
        col = _match_columns(frame, [mtbf_column or "MTBF"])[0]
        mission = float(mission_time or 1.0)
        # RBD 引擎按组件可靠度计算；由 MTBF 按指数分布折算 R = exp(-t/MTBF)
        mtbf_values = _num_series(frame, col).tolist()
        components = [{"name": f"C{i+1}", "mtbf": float(v),
                       "reliability": float(np.exp(-mission / float(v)))}
                      for i, v in enumerate(mtbf_values) if float(v) > 0]
        if not components:
            raise ValueError("RBD 需要正的 MTBF 数值")
        from analysis.reliability.rbd import calculate_system_reliability
        result = calculate_system_reliability(
            components, structure=str(structure or "series"), mission_time=mission)
        summary = result.get("summary", {})
        data = {"sheet": name, "method": "rbd", "column": col,
                "structure": structure, "components": len(components),
                "system_reliability": _pick(summary, "system_reliability", "reliability",
                                            "mission_reliability"),
                "system_unreliability": _pick(summary, "system_unreliability"),
                "weakest_component": _pick(result, "weakest_component"),
                "detail": result}
        weakest = data["weakest_component"] or {}
        text = (f"RBD 系统可靠度（{structure}，{len(components)} 个组件，"
                f"任务时间 {_fmt(mission)}）: R={_fmt(data['system_reliability'], 4)}，"
                f"失效概率 {_fmt(data['system_unreliability'], 4)}"
                + (f"，最薄弱环节 {weakest.get('name')}"
                   f"（R={_fmt(weakest.get('reliability'), 3)}）" if weakest else "")
                + "（组件可靠度按指数分布由 MTBF 折算）")
        return ToolResult("run_reliability", data=data, text=text)


# ---------------------------------------------------------------- 时间序列


def _register_timeseries_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_time_series", "时间序列分析",
              "ARIMA 预测 / 指数平滑(Holt-Winters) / 季节分解 / ACF·PACF 与平稳性检验",
              {"method": "arima/exp_smoothing/decomposition/acf_pacf", "column": "数据列",
               "horizon": "预测步数(默认12)", "period": "季节周期(可选)",
               "model": "分解模型(additive/multiplicative)",
               "es_method": "指数平滑方法(holt_winters/holt/simple)",
               "lags": "ACF/PACF 滞后阶数(默认40)", "sheet": "表名(可选)"},
              category="时间序列")
    def _timeseries(context: AgentContext, method: str = "arima", column: str | None = None,
                    horizon: int = 12, period=None, model: str = "additive",
                    es_method: str = "holt_winters", lags: int = 40,
                    sheet: str | None = None):
        name, frame = _df(context, sheet)
        col = _match_columns(frame, [column or context.pick_column(name) or ""])[0]
        series = _num_series(frame, col)
        kind = str(method or "arima").lower()
        if kind.startswith("arima"):
            from analysis.time_series import arima
            result = arima.analyze(series, forecast_steps=int(horizon or 12))
            forecast = result.get("forecast", [])
            data = {"sheet": name, "method": "arima", "column": col,
                    "order": _pick(result, "order"), "aic": _pick(result, "aic"),
                    "forecast": forecast[:8], "detail_keys": list(result)[:8]}
            text = (f"ARIMA — 列「{col}」: 阶数 {_pick(result, 'order')}，"
                    f"AIC={_fmt(_pick(result, 'aic'))}，未来 {len(forecast)} 步预测"
                    + (f"，首值 {_fmt(forecast[0])}" if forecast else ""))
            return ToolResult("run_time_series", data=data, text=text)
        if kind.startswith("exp"):
            from analysis.time_series import exponential_smoothing
            result = exponential_smoothing.analyze(
                series, method=es_method or "holt_winters",
                seasonal=model or "additive", seasonal_periods=period,
                forecast_steps=int(horizon or 12))
            forecast = result.get("forecast", [])
            data = {"sheet": name, "method": "exp_smoothing", "column": col,
                    "forecast": forecast[:8], "metrics": _pick(result, "metrics", "fit")}
            text = (f"指数平滑（{es_method}）— 列「{col}」: 未来 {len(forecast)} 步预测"
                    + (f"，首值 {_fmt(forecast[0])}" if forecast else "")
                    + (f"，拟合 {_fmt(_pick(result, 'metrics'))}"
                       if _pick(result, "metrics") else ""))
            return ToolResult("run_time_series", data=data, text=text)
        if kind.startswith("decomp"):
            from analysis.time_series import seasonal_decomposition
            result = seasonal_decomposition.analyze(
                series, model=model or "additive",
                period=int(period) if period else None)
            strength = _pick(result, "seasonal_strength", "strength")
            data = {"sheet": name, "method": "decomposition", "column": col,
                    "period": _pick(result, "period"), "model": model,
                    "seasonal_strength": strength, "detail_keys": list(result)[:8]}
            text = (f"季节分解（{model}）— 列「{col}」: 周期 "
                    f"{_fmt(_pick(result, 'period'), 0)}，季节强度={_fmt(strength, 3)}")
            return ToolResult("run_time_series", data=data, text=text)
        from analysis.time_series import acf_pacf
        result = acf_pacf.analyze(series, lags=int(lags or 40))
        summary = result.get("summary", {})
        data = {"sheet": name, "method": "acf_pacf", "column": col,
                "stationary": _pick(summary, "is_stationary"),
                "adf_p_value": _pick(summary, "adf_p_value"),
                "ljung_box_p_value": _pick(summary, "ljung_box_p_value"),
                "summary": summary}
        stationary = data["stationary"]
        text = (f"ACF/PACF — 列「{col}」(lags={lags}): "
                f"{'序列平稳' if stationary else '序列非平稳'}"
                f"（ADF p={_fmt(data['adf_p_value'], 4)}，"
                f"Ljung-Box p={_fmt(data['ljung_box_p_value'], 4)}）")
        return ToolResult("run_time_series", data=data, text=text)


# ---------------------------------------------------------------- IE 工具


def _register_ie_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_ie_analysis", "IE 工业工程分析",
              "标准工时 / 线平衡 / VSM 价值流 / 工作抽样 / SMED 快速换模 / TPM 六大损失",
              {"method": "time_study/line_balance/vsm/work_sampling/smed/tpm",
               "time_column": "观测时间列(工时)", "rating": "评比系数(默认1.0)",
               "allowance_pct": "宽放率%(默认15)", "takt": "节拍(线平衡/VSM,可选)",
               "daily_demand": "日需求(VSM)", "status_column": "状态列(工作抽样)",
               "task_column": "作业名(SMED)", "task_type_column": "内外作业列(SMED)",
               "improved_column": "改善后时间列(SMED)", "sheet": "表名(可选)"},
              category="IE 与成本")
    def _ie(context: AgentContext, method: str = "time_study", time_column: str | None = None,
             rating: float = 1.0, allowance_pct: float = 15.0, takt=None,
             daily_demand=None, status_column: str | None = None, task_column: str | None = None,
             task_type_column: str | None = None, improved_column: str | None = None,
             sheet: str | None = None):
        name, frame = _df(context, sheet)
        kind = str(method or "time_study").lower()
        if kind.startswith("time"):
            col = _match_columns(frame, [time_column or "观测时间"])[0]
            from analysis.ie.time_study import TimeStudyEngine
            engine = TimeStudyEngine()
            series = _num_series(frame, col)
            stats = engine.basic_stats(series)
            avg = _pick(stats, "mean", "avg", "average") or float(series.mean())
            normal = engine.calculate_normal_time(float(avg), float(rating or 1.0))
            standard = engine.calculate_standard_time(normal, float(allowance_pct or 15))
            data = {"sheet": name, "method": "time_study", "column": col,
                    "stats": stats, "normal_time": normal, "standard_time": standard,
                    "rating": rating, "allowance_pct": allowance_pct}
            text = (f"标准工时 — 列「{col}」(n={len(series)}): 平均 {_fmt(avg)}s，"
                    f"评比 {_fmt(rating, 2)} → 正常时间 {_fmt(normal)}s，"
                    f"宽放 {_fmt(allowance_pct, 0)}% → 标准时间 {_fmt(standard)}s")
            return ToolResult("run_ie_analysis", data=data, text=text)
        if kind.startswith("line"):
            from core.ie_parser import IEDataParser
            processes = IEDataParser().parse(frame, "Process")
            if not processes:
                raise ValueError("线平衡需要工序数据（工序名称/周期时间列）")
            from analysis.ie.line_balance import LineBalanceEngine
            result = LineBalanceEngine().analyze(
                processes, takt=_to_float(takt))
            current = result.get("current", {})
            data = {"sheet": name, "method": "line_balance",
                    "takt": result.get("takt"),
                    "balance_rate": _pick(current, "balance_rate", "efficiency"),
                    "bottleneck": _pick(current, "bottleneck"),
                    "stations": len(result.get("stations", []) or []),
                    "warnings": result.get("warnings", []),
                    "detail": result}
            text = (f"线平衡 — {data['stations']} 个工位: 平衡率 "
                    f"{_fmt(data['balance_rate'], 4)}"
                    + (f"，瓶颈 {data['bottleneck']}" if data["bottleneck"] else ""))
            return ToolResult("run_ie_analysis", data=data, text=text)
        if kind.startswith("vsm"):
            demand = _to_float(daily_demand)
            if demand is None:
                raise ValueError("VSM 需要 daily_demand（日需求）")
            from core.ie_parser import IEDataParser
            processes = IEDataParser().parse(frame, "Process")
            from analysis.ie.vsm import VSMEngine
            result = VSMEngine().analyze(processes, [], demand)
            summary = result.get("summary", {})
            data = {"sheet": name, "method": "vsm", "daily_demand": demand,
                    "lead_time_days": _pick(summary, "lead_time_days", "lead_time"),
                    "va_ratio": _pick(summary, "va_ratio", "value_added_ratio"),
                    "takt_sec": _pick(summary, "takt_sec"),
                    "total_va_sec": _pick(summary, "total_va_sec"),
                    "over_takt": _pick(summary, "over_takt"),
                    "steps": len(result.get("steps", []) or []),
                    "summary": summary,
                    "detail": result}
            text = (f"VSM — {data['steps']} 个步骤，日需求 {_fmt(demand)}，"
                    f"节拍 {_fmt(data['takt_sec'])}s: 生产周期 "
                    f"{_fmt(data['lead_time_days'], 4)} 天，增值时间合计 "
                    f"{_fmt(data['total_va_sec'])}s，增值比 {_fmt(data['va_ratio'], 3)}"
                    + (f"（{data['va_ratio'] * 100:.1f}%）"
                       if isinstance(data["va_ratio"], (int, float)) else "")
                    + (f"，超节拍工序 {len(data['over_takt'])} 个"
                       if data["over_takt"] else ""))
            return ToolResult("run_ie_analysis", data=data, text=text)
        if kind.startswith("work"):
            col = _match_columns(frame, [status_column or "状态"])[0]
            observations = frame[col].dropna().astype(str).tolist()
            from analysis.ie.work_sampling import WorkSamplingEngine
            engine = WorkSamplingEngine()
            ratios = engine.calculate_ratios(observations)
            ci = engine.confidence_intervals(ratios)
            util = engine.calculate_utilization(ratios)
            detail = ratios.get("ratios", {}) if isinstance(ratios, dict) else {}
            data = {"sheet": name, "method": "work_sampling", "column": col,
                    "observations": len(observations), "ratios": ratios,
                    "confidence_intervals": ci, "utilization": util}
            top = sorted(
                ((k, v) for k, v in detail.items()
                 if isinstance(v, dict) and v.get("count")),
                key=lambda kv: kv[1].get("pct", 0), reverse=True)[:3]
            text = (f"工作抽样 — 列「{col}」(n={len(observations)}): "
                    + "；".join(f"{v.get('label', k)} {_fmt(v.get('pct'), 1)}%"
                                for k, v in top)
                    + f"，有效作业率 {_fmt(_pick(util, 'productive_pct'), 1)}%")
            return ToolResult("run_ie_analysis", data=data, text=text)
        if kind.startswith("smed"):
            task_col = _match_columns(frame, [task_column or "作业"])[0]
            type_col = _match_columns(frame, [task_type_column or "类型"])[0]
            time_col = _match_columns(
                frame, [time_column or context.pick_column(name) or ""])[0]
            improved_col = None
            if improved_column:
                improved_col = _match_columns(frame, [improved_column])[0]
            from analysis.ie.smed import SMEDEngine
            engine = SMEDEngine()
            unrecognized = 0

            def _norm_type(value) -> str:
                """内外作业归一化 — 引擎只认 'internal'/'external'，其余按内部处理。"""
                text = str(value).strip().lower()
                if "外" in text or "external" in text:
                    return "external"
                return "internal"

            for _, row in frame.iterrows():
                raw_type = str(row[type_col])
                task_type = _norm_type(raw_type)
                if not (raw_type.strip().lower().startswith(("内", "外"))
                        or "internal" in raw_type.lower()
                        or "external" in raw_type.lower()):
                    unrecognized += 1
                engine.add_task(str(row[task_col]), task_type,
                                float(pd.to_numeric(row[time_col], errors="coerce") or 0))
                if improved_col is not None and engine.tasks:
                    value = pd.to_numeric(row[improved_col], errors="coerce")
                    if pd.notna(value):
                        engine.tasks[-1].improved_time = float(value)
            data = {"sheet": name, "method": "smed", "columns": [task_col, type_col, time_col],
                    "result": engine.to_dict(), "unrecognized_type_rows": unrecognized}
            detail = data["result"]
            before, after = detail.get("total_before"), detail.get("total_after")
            improve = ((before - after) / before * 100) if before else 0
            text = (f"SMED 快速换模 — {len(engine.tasks)} 项作业: 换模时间 "
                    f"{_fmt(before)} → {_fmt(after)} 秒（改善 {_fmt(improve, 1)}%）")
            if unrecognized:
                text += (f"\n⚠ 有 {unrecognized} 行作业类型未被识别为内/外作业，"
                         "已按「内部作业」计入；建议在表中使用 内部/外部 或 internal/external")
            return ToolResult("run_ie_analysis", data=data, text=text)
        # TPM：把每条记录折算为 OEE 资源后复用 OEE 引擎，保证口径一致
        from core.data_objects import Resource
        resources = []
        for idx, row_data in frame.iterrows():
            def _get(*names, default=0.0, _row=row_data):
                for cand in names:
                    if cand in frame.columns:
                        value = pd.to_numeric(_row[cand], errors="coerce")
                        if pd.notna(value):
                            return float(value)
                return default

            resources.append(Resource(
                resource_id=f"R{idx + 1}",
                available_time=_get("可用时间", "operating_time", "运行时间", default=0.0),
                downtime=_get("故障时间", "breakdown_time") + _get("换型时间", "setup_time")
                + _get("等待时间", "idle_time"),
                total_qty=_get("总产量", "total_output"),
                good_qty=_get("良品数", "good_output")))
        if not any(r.available_time > 0 for r in resources):
            raise ValueError("TPM 需要可用时间/运行时间列（>0）")
        from analysis.ie.oee import OEEEngine
        result = OEEEngine().analyze(resources, "all")
        overall = result.get("overall", {})
        data = {"sheet": name, "method": "tpm", "records": len(resources),
                "overall": overall, "losses": overall.get("losses"),
                "warnings": result.get("warnings", [])}
        text = (f"TPM 六大损失 — {len(resources)} 条记录: OEE={_fmt(overall.get('oee'))} "
                f"(A={_fmt(overall.get('availability'))} "
                f"P={_fmt(overall.get('performance')) if overall.get('performance') is not None else '未提供节拍'} "
                f"Q={_fmt(overall.get('quality'))})，损失分解 "
                f"{overall.get('losses')}")
        return ToolResult("run_ie_analysis", data=data, text=text)


# ---------------------------------------------------------------- AI 根因


def _register_ai_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    @reg.tool("run_root_cause", "根因分析（AI）",
              "随机森林 + 特征重要性 + 相关性 + 异常关联，输出主要变异来源与解释",
              {"target_column": "目标列(如测量值)", "top_k": "输出条数(默认8)",
               "subgroup_size": "子组大小(默认1)", "sheet": "表名(可选)"},
              category="质量分析", returns="causes[column/score/explanation]")
    def _root_cause(context: AgentContext, target_column: str | None = None,
                    top_k: int = 8, subgroup_size: int = 1, sheet: str | None = None):
        name, frame = _df(context, sheet)
        target = _match_columns(
            frame, [target_column or context.pick_column(name) or ""])[0]
        from analysis.ai.root_cause import RootCauseAnalyzer
        result = RootCauseAnalyzer().analyze(
            frame, target, subgroup_size=int(subgroup_size or 1),
            top_k=int(top_k or 8))
        causes = []
        for cause in result.get("causes", []) or []:
            payload = _dataclass_dict(cause)
            causes.append({
                "column": payload.get("column"),
                "score": payload.get("score"),
                "importance": payload.get("importance"),
                "correlation": payload.get("correlation"),
                "explanation": payload.get("explanation"),
            })
        data = {"sheet": name, "target": target, "method": result.get("method"),
                "violation_rows": result.get("n_violation_rows"), "causes": causes}
        lines = [(f"根因分析 — 目标列「{target}」（{result.get('method')}）: "
                 f"变异关联行 {result.get('n_violation_rows', 0)}")]
        for item in causes[:5]:
            lines.append(f"  {item['column']}: 评分 {_fmt(item['score'], 3)}"
                         f"（重要性 {_fmt(item['importance'], 3)}）— {item['explanation']}")
        if not causes:
            lines.append("  未发现可用变量（检查数据列与目标列变异）")
        return ToolResult("run_root_cause", data=data, text="\n".join(lines))
