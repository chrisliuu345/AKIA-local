"""QAM Harness 工具注册表 — 把本软件能力暴露给 Agent（v3.8.0 Phase 1）。

设计要点:
  - **真引擎**: 每个工具直接调用既有分析引擎（analysis/、core/streaming/），
    不重写统计逻辑，保证 Agent 结论与界面分析结果同源。
  - **软件适配**: 工具以 `AgentContext`（由 ui/agent_bridge.py 组装）为输入，
    覆盖数据画像 / SPC / 过程能力 / MSA / 假设检验 / OEE / 成本 / 告警 /
    五链上下文 / 产线配置 / 实时状态 / 已跑分析 / 知识库 / 指标解读 14 类能力。
  - **可测**: 纯逻辑无 Qt，工具可脱离界面直接调用（tests/test_agent_*.py）。
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable

import pandas as pd

# ---------------------------------------------------------------- 数据结构


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    parameters: dict = field(default_factory=dict)   # 参数名 → 说明
    category: str = "通用"
    returns: str = ""
    handler: Callable = None

    def signature(self) -> str:
        params = ", ".join(f"{k}: {v}" for k, v in self.parameters.items()) or "无参数"
        return f"{self.name}({params})"


@dataclass
class ToolResult:
    name: str
    ok: bool = True
    data: dict = field(default_factory=dict)
    text: str = ""
    error: str = ""
    duration_ms: float = 0.0

    def summary(self, max_chars: int = 900) -> str:
        body = (self.text or self.error or "").strip()
        if len(body) > max_chars:
            body = body[:max_chars] + "…"
        return body

    def as_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "data": self.data,
                "text": self.text, "error": self.error,
                "duration_ms": round(self.duration_ms, 1)}


class ToolRegistry:
    """工具注册表 — 名称唯一，支持装饰器式注册与统一异常兜底。"""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    # ---------- 注册 ----------
    def register(self, spec: ToolSpec) -> ToolSpec:
        if spec.handler is None:
            raise ValueError(f"工具 {spec.name} 缺少 handler")
        self._tools[spec.name] = spec
        return spec

    def tool(self, name: str, title: str, description: str,
             parameters: dict | None = None, category: str = "通用",
             returns: str = ""):
        def deco(fn):
            return self.register(ToolSpec(
                name=name, title=title, description=description,
                parameters=dict(parameters or {}), category=category,
                returns=returns, handler=fn))
        return deco

    # ---------- 查询 ----------
    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [self._tools[n] for n in self.names()]

    def by_category(self) -> dict[str, list[ToolSpec]]:
        out: dict[str, list[ToolSpec]] = {}
        for spec in self.specs():
            out.setdefault(spec.category, []).append(spec)
        return out

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def describe(self, max_chars: int = 4000) -> str:
        """生成给 LLM 的工具清单文本。"""
        lines: list[str] = []
        for category, specs in self.by_category().items():
            lines.append(f"【{category}】")
            for spec in specs:
                params = "; ".join(f"{k}={v}" for k, v in spec.parameters.items())
                lines.append(f"- {spec.name}: {spec.description}"
                             + (f"（参数: {params}）" if params else ""))
                if spec.returns:
                    lines.append(f"  返回: {spec.returns}")
        text = "\n".join(lines)
        return text if len(text) <= max_chars else text[:max_chars] + "…"

    # ---------- 调用 ----------
    def call(self, name: str, args: dict | None = None,
             context: AgentContext | None = None) -> ToolResult:
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(name=name, ok=False,
                              error=f"未知工具 {name}（可用: {', '.join(self.names())}）")
        args = dict(args or {})
        unknown = [k for k in args if k not in spec.parameters]
        for k in unknown:
            args.pop(k, None)
        started = time.time()
        try:
            result = spec.handler(context, **args)
            if isinstance(result, ToolResult):
                if not result.name:
                    result.name = name
            else:                                  # 允许 handler 直接返回 dict/str
                result = ToolResult(name=name, data={"value": result},
                                    text=str(result))
        except Exception as e:                     # 工具异常不影响 Agent 主循环
            return ToolResult(name=name, ok=False, error=f"{type(e).__name__}: {e}",
                              duration_ms=(time.time() - started) * 1000)
        result.duration_ms = (time.time() - started) * 1000
        return result


# ---------------------------------------------------------------- 上下文


def _is_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    if series.dtype == object:
        conv = pd.to_numeric(series, errors="coerce")
        valid = conv.notna().sum()
        return bool(valid >= 2 and valid / max(len(series), 1) >= 0.8)
    return False


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


@dataclass
class AgentContext:
    """Agent 可见的软件状态（UI 层组装；无 Qt 依赖）。"""

    data_frames: dict = field(default_factory=dict)      # sheet 名 → DataFrame
    analyses: dict = field(default_factory=dict)         # tab 索引/标签 → 结果
    profile: dict = field(default_factory=dict)          # 数据画像
    project_context: Any = None                          # 五链 ProjectContext
    plant: Any = None                                    # PlantConfig
    journal: Any = None                                  # AlertJournal
    downtime: Any = None                                 # DowntimeTracker
    knowledge: Any = None                                # KnowledgeBase
    live_oee_snapshot: dict | None = None                # LiveOEEComputer.snapshot()
    connector_health: Any = None                         # HealthRegistry
    currency: str = ""
    extra: dict = field(default_factory=dict)

    # ---------- 数据访问 ----------
    def sheet_names(self) -> list[str]:
        return [str(k) for k in self.data_frames]

    def frame(self, sheet: str | None = None) -> pd.DataFrame | None:
        if not self.data_frames:
            return None
        if sheet:
            if sheet in self.data_frames:
                return self.data_frames[sheet]
            lowered = {str(k).lower(): v for k, v in self.data_frames.items()}
            return lowered.get(str(sheet).lower())
        return next(iter(self.data_frames.values()))

    def sheet_of(self, sheet: str | None = None) -> str:
        if sheet and sheet in self.data_frames:
            return sheet
        if sheet:
            for key in self.data_frames:
                if str(key).lower() == str(sheet).lower():
                    return str(key)
        return self.sheet_names()[0] if self.data_frames else ""

    def numeric_columns(self, sheet: str | None = None) -> list[str]:
        df = self.frame(sheet)
        if df is None:
            return []
        return [str(c) for c in df.columns if _is_numeric(df[c])]

    def text_columns(self, sheet: str | None = None) -> list[str]:
        df = self.frame(sheet)
        if df is None:
            return []
        return [str(c) for c in df.columns if not _is_numeric(df[c])]

    def pick_column(self, sheet: str | None = None, preferred: str | None = None,
                    kind: str = "numeric") -> str | None:
        df = self.frame(sheet)
        if df is None:
            return None
        columns = [str(c) for c in df.columns]
        if preferred:
            for col in columns:
                if col == str(preferred):
                    return col
            for col in columns:                       # 模糊匹配（包含关系）
                if str(preferred).lower() in col.lower():
                    return col
        pool = self.numeric_columns(sheet) if kind == "numeric" else self.text_columns(sheet)
        return pool[0] if pool else None

    def summary(self) -> str:
        parts = [f"数据表 {len(self.data_frames)} 张"]
        if self.analyses:
            parts.append(f"已运行分析 {len(self.analyses)} 项")
        if self.project_context is not None:
            parts.append("五链上下文已接入")
        if self.plant is not None and getattr(self.plant, "lines", None):
            stations = sum(len(getattr(l, "stations", [])) for l in self.plant.lines)
            parts.append(f"产线 {len(self.plant.lines)} 条/{stations} 工位")
        if self.journal is not None:
            try:
                parts.append(f"告警 {self.journal.unacked_count()} 条未确认")
            except Exception:
                pass
        if self.live_oee_snapshot:
            parts.append("实时 OEE 已接入")
        return " · ".join(parts)


# ---------------------------------------------------------------- 工具实现


def _fmt(value: Any, digits: int = 4) -> str:
    num = _to_float(value)
    if num is None:
        return "—" if value is None else str(value)
    if abs(num) >= 1000:
        return f"{num:,.0f}"
    return f"{round(num, digits):g}"


def _series(ctx: AgentContext, sheet: str | None, column: str | None,
            kind: str = "numeric") -> tuple[str, str, pd.Series]:
    """取列并转数值；返回 (sheet, column, series)，缺参数时自动挑选。"""
    sheet_name = ctx.sheet_of(sheet)
    df = ctx.frame(sheet_name)
    if df is None:
        raise ValueError("尚未导入数据表")
    col = ctx.pick_column(sheet_name, column, kind=kind)
    if not col:
        raise ValueError(f"表 {sheet_name} 中没有可用的{'数值' if kind == 'numeric' else '文本'}列")
    series = df[col]
    if kind == "numeric":
        series = pd.to_numeric(series, errors="coerce").dropna()
    else:
        series = series.dropna().astype(str)
    if len(series) < 2:
        raise ValueError(f"列 {col} 有效数据不足（{len(series)} 行）")
    return sheet_name, col, series


def _multi_columns(frame: pd.DataFrame, columns) -> list[str]:
    """解析多元控制图的变量列（list 或逗号/顿号分隔字符串）。

    未指定时取前两个数值列；不足两个即报错（MEWMA / 广义方差图至少需 2 个变量）。
    """
    if isinstance(columns, (list, tuple)):
        names = [str(c).strip() for c in columns if str(c).strip()]
    elif columns:
        normalized = str(columns).replace("，", ",").replace("、", ",")
        names = [c.strip() for c in normalized.split(",") if c.strip()]
    else:
        names = []
    if not names:
        names = frame.select_dtypes(include="number").columns.tolist()[:2]
    missing = [c for c in names if c not in frame.columns]
    if missing:
        raise ValueError(f"列不存在: {missing}")
    if len(names) < 2:
        raise ValueError("多元控制图需要至少 2 个数值列（用 columns 指定，如 'x,y'）")
    return names


def _chart_limits(result: dict) -> dict:
    """从各控制图引擎返回值中提取 CL/UCL/LCL 与判异点（结构因图型而异）。"""
    out: dict = {}
    for key in ("i_chart", "xbar_chart", "p_chart", "np_chart", "c_chart",
                "u_chart", "cusum_chart", "ewma_chart", "mewma_chart",
                "genvar_chart"):
        chart = result.get(key)
        if isinstance(chart, dict) and "cl" in chart:
            out = {
                "chart": key.replace("_chart", ""),
                "cl": chart.get("cl"), "ucl": chart.get("ucl"),
                "lcl": chart.get("lcl"),
                "violations": chart.get("violations", []),
            }
            break
    if not out:
        nested = result.get("residual_chart")
        if isinstance(nested, dict):
            inner = _chart_limits(nested)
            if inner.get("cl") is not None:
                inner["chart"] = "residual"
                return inner
        out = {"chart": result.get("chart_type", "?"), "cl": result.get("cl"),
               "ucl": result.get("ucl"), "lcl": result.get("lcl"),
               "violations": result.get("violations", [])}
    return out


def _violation_lines(violations: list, limit: int = 5) -> list[str]:
    lines = []
    for v in (violations or [])[:limit]:
        point = v.get("point", "?")
        desc = v.get("desc") or v.get("rule") or ""
        value = v.get("value")
        lines.append(f"  第 {point} 点: {desc}"
                     + (f"（值 {_fmt(value)}）" if value is not None else ""))
    return lines


def build_default_registry(ctx: AgentContext) -> ToolRegistry:
    """构建覆盖本软件主要能力的工具集（新增工具在此登记即可被 Agent 调用）。"""
    reg = ToolRegistry()

    # ---------------- 数据 ----------------
    @reg.tool("list_data", "数据表清单",
              "列出已导入的数据表、行列数与列名（含数值/文本类型与缺失情况）",
              category="数据")
    def _list_data(context: AgentContext):
        if not context.data_frames:
            return ToolResult("list_data", ok=False, error="尚未导入任何数据")
        lines, payload = [], []
        for name, df in context.data_frames.items():
            num_cols = context.numeric_columns(name)
            missing = int(df.isna().sum().sum())
            payload.append({"sheet": str(name), "rows": int(len(df)),
                            "columns": [str(c) for c in df.columns],
                            "numeric_columns": num_cols})
            lines.append(f"表「{name}」: {len(df)} 行 × {len(df.columns)} 列，"
                         f"缺失 {missing} 个；数值列 {len(num_cols)} 个")
            lines.append("  列: " + ", ".join(str(c) for c in df.columns))
        return ToolResult("list_data", data={"sheets": payload},
                          text="\n".join(lines))

    @reg.tool("describe_column", "列统计描述",
              "对某一列做描述统计（均值/标准差/分位数/缺失/唯一值）",
              {"sheet": "表名(可选)", "column": "列名(可选,默认首个数值列)"},
              category="数据")
    def _describe_column(context: AgentContext, sheet: str | None = None,
                         column: str | None = None):
        sheet_name = context.sheet_of(sheet)
        df = context.frame(sheet_name)
        if df is None:
            return ToolResult("describe_column", ok=False, error="尚未导入数据表")
        col = context.pick_column(sheet_name, column)
        if not col:
            return ToolResult("describe_column", ok=False,
                              error=f"表 {sheet_name} 无可用数值列")
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            return ToolResult("describe_column", ok=False,
                              error=f"列 {col} 无有效数值")
        stats = {
            "sheet": sheet_name, "column": col, "count": int(series.count()),
            "mean": float(series.mean()), "std": float(series.std(ddof=1) or 0),
            "min": float(series.min()), "p25": float(series.quantile(0.25)),
            "median": float(series.median()), "p75": float(series.quantile(0.75)),
            "max": float(series.max()),
            "missing": int(df[col].isna().sum()),
        }
        text = (f"表「{sheet_name}」列「{col}」: n={stats['count']}，"
                f"均值 {_fmt(stats['mean'])}，标准差 {_fmt(stats['std'])}，"
                f"最小 {_fmt(stats['min'])}，中位 {_fmt(stats['median'])}，"
                f"最大 {_fmt(stats['max'])}，缺失 {stats['missing']}")
        return ToolResult("describe_column", data=stats, text=text)

    # ---------------- 质量分析 ----------------
    @reg.tool("run_spc", "运行控制图",
              "运行 SPC 控制图并返回控制限与判异点（Nelson 规则）；"
              "多元图（mewma/gen_var）用 columns 指定变量列，residual 为 ARIMA 白化残差图",
              {"chart_type": ("imr/xbar_r/xbar_s/p_chart/np_chart/c_chart/u_chart/"
                              "cusum/ewma/mewma/gen_var/residual"),
               "sheet": "表名(可选)", "column": "测量列/不合格品数列",
               "subgroup_size": "子组大小(默认5)", "usl": "规格上限(可选)",
               "lsl": "规格下限(可选)", "sample_size": "NP 图样本量(可选)",
               "sample_sizes_column": "P/U 图的样本量列(可选)",
               "columns": "多元图变量列，逗号分隔（mewma/gen_var 用，可选）",
               "lambda_": "MEWMA 平滑参数 r∈(0,1]，默认 0.1（可选）",
               "subgroup_col": "广义方差图子组列（可选，缺省按 subgroup_size 切块）"},
              category="质量分析", returns="chart_type/cl/ucl/lcl/violations")
    def _run_spc(context: AgentContext, chart_type: str = "imr", sheet: str | None = None,
                 column: str | None = None, subgroup_size: int = 5, usl=None, lsl=None,
                 sample_size=None, sample_sizes_column: str | None = None,
                 columns=None, lambda_: float = 0.1, subgroup_col: str | None = None):
        kind = "numeric"
        chart = str(chart_type or "imr").lower().strip()
        result: dict
        multi_chart = chart in ("mewma", "mewma_chart", "gen_var", "genvar",
                                "generalized_variance", "gv")
        if multi_chart:
            # 多元图按"列集合"分析，不要求单列参数
            sheet_name = context.sheet_of(sheet)
            col = ""
            series = None
        else:
            sheet_name, col, series = _series(context, sheet, column, kind)
        if chart in ("imr", "i-mr", "i_mr"):
            from analysis.spc import imr
            result = imr.analyze(series)
        elif chart in ("xbar_r", "xbar-r", "xbarr"):
            from analysis.spc import xbar_r
            result = xbar_r.analyze(series, int(subgroup_size or 5))
        elif chart in ("xbar_s", "xbar-s", "xbars"):
            from analysis.spc import xbar_s
            result = xbar_s.analyze(series, int(subgroup_size or 5))
        elif chart in ("cusum",):
            from analysis.spc import cusum
            result = cusum.analyze(series)
        elif chart in ("ewma",):
            from analysis.spc import ewma
            result = ewma.analyze(series)
        elif chart in ("mewma", "mewma_chart"):
            from analysis.spc.mewma import analyze as mewma_analyze

            frame = context.frame(sheet_name)
            cols = _multi_columns(frame, columns)
            data = frame[cols].dropna()
            if len(data) < len(cols) + 1:
                raise ValueError(f"MEWMA 需要至少 {len(cols) + 1} 行完整数据，当前 {len(data)}")
            result = mewma_analyze(data, cols, lambda_=float(lambda_ or 0.1))
        elif chart in ("gen_var", "genvar", "generalized_variance", "gv"):
            from analysis.spc.gen_var import analyze as genvar_analyze

            frame = context.frame(sheet_name)
            cols = _multi_columns(frame, columns)
            if subgroup_col and str(subgroup_col) in frame.columns:
                result = genvar_analyze(frame, cols, subgroup_col=str(subgroup_col))
            else:
                result = genvar_analyze(frame, cols,
                                        subgroup_size=int(subgroup_size or 5))
        elif chart in ("residual", "residual_chart", "arima_residual"):
            from analysis.spc.residual_chart import analyze as residual_analyze

            result = residual_analyze(series)
        elif chart in ("p_chart", "p", "p-chart"):
            from analysis.spc import p_chart
            df = context.frame(sheet_name)
            sizes = (pd.to_numeric(df[sample_sizes_column], errors="coerce")
                     if sample_sizes_column and sample_sizes_column in df.columns
                     else None)
            if sizes is None or sizes.isna().all():
                raise ValueError("P 图需要 sample_sizes_column（每子组样本量列）")
            result = p_chart.analyze(series, sizes.loc[series.index])
        elif chart in ("np_chart", "np", "np-chart"):
            from analysis.spc import np_chart
            if not sample_size:
                raise ValueError("NP 图需要 sample_size 参数（固定样本量）")
            result = np_chart.analyze(series, int(sample_size))
        elif chart in ("c_chart", "c", "c-chart"):
            from analysis.spc import c_chart
            result = c_chart.analyze(series)
        elif chart in ("u_chart", "u", "u-chart"):
            from analysis.spc import u_chart
            df = context.frame(sheet_name)
            sizes = (pd.to_numeric(df[sample_sizes_column], errors="coerce")
                     if sample_sizes_column and sample_sizes_column in df.columns
                     else None)
            if sizes is None or sizes.isna().all():
                raise ValueError("U 图需要 sample_sizes_column（单位数/样本量列）")
            result = u_chart.analyze(series, sizes.loc[series.index])
        else:
            raise ValueError(f"不支持的控制图类型 {chart_type}（可选 imr/xbar_r/"
                             "xbar_s/p_chart/np_chart/c_chart/u_chart/cusum/ewma/"
                             "mewma/gen_var/residual）")

        limits = _chart_limits(result)
        violations = limits.get("violations") or []
        oos = 0
        if series is not None:
            oos = int(((series > float(usl)).sum() if usl is not None else 0)
                      + ((series < float(lsl)).sum() if lsl is not None else 0))
        data = {"sheet": sheet_name, "column": col, "chart_type": chart,
                "cl": limits.get("cl"), "ucl": limits.get("ucl"),
                "lcl": limits.get("lcl"),
                "violations": len(violations), "out_of_spec": oos,
                "detail": limits}
        target = ("多元变量 " + "/".join(columns if isinstance(columns, list)
                                         else str(columns or "").split(","))
                  if multi_chart else f"列「{col}」")
        lines = [f"控制图 {result.get('chart_type', chart)} — 表「{sheet_name}」{target}",
                 (f"CL={_fmt(limits.get('cl'))} UCL={_fmt(limits.get('ucl'))} "
                 f"LCL={_fmt(limits.get('lcl'))}"),
                 f"判异点 {len(violations)} 个"
                 + (f"，超规格 {oos} 点" if (usl is not None or lsl is not None) else "")]
        lines += _violation_lines(violations)
        if not violations:
            lines.append("未检出判异点（过程受控）")
        return ToolResult("run_spc", data=data, text="\n".join(lines))

    @reg.tool("detect_changepoints", "变点检测",
              "PELT 变点检测（均值漂移 / 均值+方差同时变化），返回变点位置与分段统计",
              {"sheet": "表名(可选)", "column": "测量列(可选)",
               "model": "mean 或 meanvar（默认 mean）",
               "penalty": "罚项 β(可选，缺省 2.5σ̂²log n)",
               "min_size": "每段最少点数(默认2)"},
              category="质量分析", returns="changepoints/segments/penalty")
    def _detect_changepoints(context: AgentContext, sheet: str | None = None,
                             column: str | None = None, model: str = "mean",
                             penalty=None, min_size: int = 2):
        sheet_name, col, series = _series(context, sheet, column, "numeric")
        from analysis.spc.change_point import detect

        result = detect(
            series,
            model=str(model or "mean").strip().lower(),
            penalty=(None if penalty in (None, "", 0) else float(penalty)),
            min_size=int(min_size or 2))
        points = result["changepoints"]
        lines = [(f"变点检测（{result['model']}）— 表「{sheet_name}」列「{col}」，"
                  f"n={result['num_points']}，罚项 β={_fmt(result['penalty'])}"),
                 f"检出变点 {result['num_changes']} 个"
                 + (f"（新段起点索引，0 基）：{points}" if points else "")]
        for segment in result["segments"][:5]:
            lines.append(f"  段 {segment['start']}–{segment['end']}"
                         f"（n={segment['n']}）均值 {_fmt(segment['mean'])}"
                         f"，σ={_fmt(segment['std'])}")
        return ToolResult("detect_changepoints", data=result, text="\n".join(lines))

    @reg.tool("run_capability", "过程能力分析",
              "计算 Cp/Cpk/Pp/Ppk、PPM 与能力评级（支持非正态变换）",
              {"sheet": "表名(可选)", "column": "测量列(可选)",
               "usl": "规格上限", "lsl": "规格下限", "target": "目标值(可选)",
               "subgroup_size": "子组大小(默认5)", "method": "normal/non_normal"},
              category="质量分析", returns="cp/cpk/pp/ppk/ppm/grade")
    def _run_capability(context: AgentContext, sheet: str | None = None,
                        column: str | None = None, usl=None, lsl=None, target=None,
                        subgroup_size: int = 5, method: str = "normal"):
        sheet_name, col, series = _series(context, sheet, column)
        usl_v, lsl_v, target_v = _to_float(usl), _to_float(lsl), _to_float(target)
        if usl_v is None and lsl_v is None:
            df = context.frame(sheet_name)
            for cand in ("USL", "usl", "规格上限"):
                if cand in df.columns:
                    usl_v = _to_float(pd.to_numeric(df[cand], errors="coerce").dropna().iloc[0])
                    break
            for cand in ("LSL", "lsl", "规格下限"):
                if cand in df.columns:
                    lsl_v = _to_float(pd.to_numeric(df[cand], errors="coerce").dropna().iloc[0])
                    break
        if usl_v is None or lsl_v is None:
            raise ValueError("过程能力分析需要 USL 与 LSL（可传参或在数据表中提供列）")
        if str(method).lower().startswith("non"):
            from analysis.capability import non_normal_cap
            result = non_normal_cap.analyze(series, usl_v, lsl_v)
        else:
            from analysis.capability import normal_cap
            result = normal_cap.analyze(series, usl_v, lsl_v, target_v,
                                        int(subgroup_size or 5))
        cap = result.get("capability", result)
        data = {"sheet": sheet_name, "column": col, "usl": usl_v, "lsl": lsl_v,
                "cp": cap.get("cp"), "cpk": cap.get("cpk"),
                "pp": cap.get("pp"), "ppk": cap.get("ppk"),
                "ppm_total": cap.get("ppm_total") or cap.get("ppm"),
                "grade": cap.get("grade") or result.get("grade"),
                "sigma_level": cap.get("sigma_level")}
        text = (f"过程能力 — 表「{sheet_name}」列「{col}」"
                f"（USL={_fmt(usl_v)}, LSL={_fmt(lsl_v)}）: "
                f"Cp={_fmt(data['cp'])} Cpk={_fmt(data['cpk'])} "
                f"Pp={_fmt(data['pp'])} Ppk={_fmt(data['ppk'])}，"
                f"不良率 ≈ {_fmt(data['ppm_total'], 1)} PPM，"
                f"评级 {data['grade']}")
        return ToolResult("run_capability", data=data, text=text)

    @reg.tool("run_msa_grr", "Gage R&R 量具研究",
              "运行 Gage R&R（交叉/嵌套）并给出 %GRR、ndc 与判定",
              {"sheet": "表名(可选)", "measurement_column": "测量值列",
               "part_column": "零件列", "operator_column": "操作员列",
               "tolerance": "公差(可选)", "nested": "true 为嵌套设计"},
              category="质量分析", returns="grr_pct/ndc/acceptance")
    def _run_msa_grr(context: AgentContext, sheet: str | None = None,
                     measurement_column: str | None = None, part_column: str | None = None,
                     operator_column: str | None = None, tolerance=None,
                     nested: bool = False):
        sheet_name = context.sheet_of(sheet)
        df = context.frame(sheet_name)
        if df is None:
            raise ValueError("尚未导入数据表")
        meas = context.pick_column(sheet_name, measurement_column)
        parts = context.pick_column(sheet_name, part_column or "零件", kind="text")
        operators = context.pick_column(sheet_name, operator_column or "操作员", kind="text")
        if not (meas and parts and operators):
            raise ValueError("需要测量值列、零件列、操作员列（可传参指定，或列名含零件/操作员）")
        from analysis.msa import gage_rr
        tol_v = _to_float(tolerance)
        if nested:
            result = gage_rr.analyze_nested(df, meas, parts, operators, tol_v)
        else:
            result = gage_rr.analyze_crossed(df, meas, parts, operators, tol_v)
        pct = result.get("percentages", {})
        data = {"sheet": sheet_name, "measurement": meas, "part": parts,
                "operator": operators, "design": result.get("design"),
                "grr_pct": pct.get("grr_pct_tv"), "ndc": result.get("ndc"),
                "acceptance": result.get("acceptance"),
                "variance_components": result.get("variance_components")}
        text = (f"Gage R&R（{'嵌套' if nested else '交叉'}）— {meas} × {parts} × {operators}: "
                f"%GRR={_fmt(data['grr_pct'], 2)}%，ndc={data['ndc']}，"
                f"判定 {data['acceptance']}")
        return ToolResult("run_msa_grr", data=data, text=text)

    @reg.tool("run_hypothesis_test", "假设检验",
              "运行正态性 / 单样本 t / 双样本 t / 配对 t / 单因素 ANOVA 检验",
              {"test": "normality/t_1sample/t_2sample/t_paired/anova_oneway",
               "sheet": "表名(可选)", "column": "数据列", "group_column": "分组列(ANOVA)",
               "second_column": "第二列(双样本/配对)", "pop_mean": "原假设均值(t_1sample)",
               "confidence_level": "置信水平(默认0.95)"},
              category="质量分析", returns="p_value/is_significant/conclusion")
    def _run_hypothesis_test(context: AgentContext, test: str = "normality",
                             sheet: str | None = None, column: str | None = None,
                             group_column: str | None = None, second_column: str | None = None,
                             pop_mean=None, confidence_level: float = 0.95):
        kind = str(test or "normality").lower()
        if kind in ("anova_oneway", "anova", "anova_one_way"):
            from analysis.hypothesis import anova
            sheet_name = context.sheet_of(sheet)
            df = context.frame(sheet_name)
            grp = context.pick_column(sheet_name, group_column or "组", kind="text")
            val = context.pick_column(sheet_name, column)
            if not (grp and val):
                raise ValueError("ANOVA 需要分组列与数值列")
            levels = df[grp].dropna().unique()
            if len(levels) < 2:
                raise ValueError("ANOVA 至少需要 2 个有效分组")
            result = anova.one_way(df, val, grp)
            p_value = result.get("p_value")
            conclusion = ("差异显著" if result.get("is_significant")
                          else "差异不显著")
            data = {"sheet": sheet_name, "column": val, "test": "anova_oneway",
                    "factor": grp, "levels": result.get("levels"),
                    "p_value": p_value,
                    "is_significant": result.get("is_significant"),
                    "conclusion": conclusion}
            return ToolResult("run_hypothesis_test", data=data,
                              text=f"One-Way ANOVA — {val} ~ {grp}: "
                                   f"p={_fmt(p_value, 4)}，{conclusion}")
        else:
            sheet_name, col, series = _series(context, sheet, column)
            if kind in ("t_1sample", "one_sample", "t1"):
                from analysis.hypothesis import t_tests
                if pop_mean is None:
                    raise ValueError("单样本 t 检验需要 pop_mean（原假设均值）")
                result = t_tests.one_sample(series, float(pop_mean))
            elif kind in ("t_2sample", "two_sample", "t2"):
                from analysis.hypothesis import t_tests
                if not second_column:
                    raise ValueError("双样本 t 检验需要 second_column")
                df = context.frame(sheet_name)
                if second_column not in df.columns:
                    raise ValueError(f"列 {second_column} 不存在")
                series2 = pd.to_numeric(df[second_column], errors="coerce").dropna()
                result = t_tests.two_sample(series, series2)
            elif kind in ("t_paired", "paired"):
                from analysis.hypothesis import t_tests
                if not second_column:
                    raise ValueError("配对 t 检验需要 second_column")
                df = context.frame(sheet_name)
                if second_column not in df.columns:
                    raise ValueError(f"列 {second_column} 不存在")
                series2 = pd.to_numeric(df[second_column], errors="coerce")
                paired = pd.DataFrame({"a": series, "b": series2}).dropna()
                result = t_tests.paired(paired["a"], paired["b"])
            else:
                from analysis.hypothesis import normality
                result = normality.normality_test(series, float(confidence_level))
                conclusion = result.get("overall_conclusion", "")
                tests = result.get("tests", {}) or {}
                sw = tests.get("shapiro_wilk", {}) if isinstance(tests, dict) else {}
                p_value = sw.get("p_value") if isinstance(sw, dict) else None
                data = {"sheet": sheet_name, "column": col, "test": "normality",
                        "sample_size": result.get("sample_size"),
                        "p_value": p_value, "conclusion": conclusion}
                return ToolResult("run_hypothesis_test", data=data,
                                  text=f"正态性检验 — 列「{col}」: {conclusion}"
                                       f"（Shapiro-Wilk p={_fmt(p_value, 4)}）")
        p_value = result.get("p_value")
        conclusion = (result.get("conclusion")
                      or ("差异显著" if result.get("is_significant") else "差异不显著"))
        data = {"sheet": sheet_name, "column": col, "test": kind,
                "p_value": p_value, "is_significant": result.get("is_significant"),
                "conclusion": conclusion}
        return ToolResult("run_hypothesis_test", data=data,
                          text=f"{result.get('test_type', kind)} — 列「{col}」: "
                               f"p={_fmt(p_value, 4)}，{conclusion}")

    # ---------------- IE / 成本 ----------------
    @reg.tool("run_oee", "OEE 计算",
              "按资源/班组/班次计算 OEE（A×P×Q 与六大损失分解）",
              {"sheet": "表名(可选)", "group_by": "all/group/shift"},
              category="IE 与成本", returns="availability/performance/quality/oee/grade")
    def _run_oee(context: AgentContext, sheet: str | None = None, group_by: str = "all"):
        resources = context.extra.get("ie_resources")
        if not resources:
            from core.ie_parser import IEDataParser
            parser = IEDataParser()
            # 不依赖 Sheet 命名（真实数据表名各异）— 按列别名匹配度挑最佳表，
            # 再强制按 Resource 语义解析。
            best_name, best_score = None, 0
            for name in ([context.sheet_of(sheet)] if sheet
                         else list(context.data_frames)):
                df = context.frame(name)
                if df is None:
                    continue
                score = len(parser.map_columns([str(c) for c in df.columns], "Resource"))
                if score > best_score:
                    best_name, best_score = name, score
            if best_name is None or best_score < 2:
                raise ValueError("没有可用的 IE 资源数据（需要可用时间/停机/产量等列）")
            resources = parser.parse(context.frame(best_name), "Resource")
        if not resources:
            raise ValueError("没有可用的 IE 资源数据（需要可用时间/停机/产量等列）")
        from analysis.ie.oee import OEEEngine
        result = OEEEngine().analyze(list(resources), group_by or "all")
        if result.get("error"):
            raise ValueError(result["error"])
        overall = result.get("overall", {})
        data = {"group_by": group_by, "overall": overall,
                "buckets": result.get("buckets", []),
                "warnings": result.get("warnings", [])}
        lines = [(f"OEE（按 {group_by}）: {_fmt((overall or {}).get('oee'), 4)}"
                 f"（A={_fmt((overall or {}).get('availability'))}, "
                 f"P={_fmt((overall or {}).get('performance'))}, "
                 f"Q={_fmt((overall or {}).get('quality'))}），"
                 f"评级 {(overall or {}).get('grade', '—')}")]
        for bucket in result.get("buckets", [])[:6]:
            lines.append(f"  {bucket.get('label')}: OEE={_fmt(bucket.get('oee'))} "
                         f"可用={_fmt(bucket.get('availability'))} "
                         f"性能={_fmt(bucket.get('performance'))} "
                         f"质量={_fmt(bucket.get('quality'))}")
        return ToolResult("run_oee", data=data, text="\n".join(lines))

    @reg.tool("get_live_oee", "实时 OEE 看板",
              "读取当前实时 OEE（滑窗）指标：A/P/Q、不良数、停机时长与原因",
              category="实时工厂")
    def _get_live_oee(context: AgentContext):
        snapshot = context.live_oee_snapshot
        if not snapshot:
            return ToolResult("get_live_oee", ok=False,
                              error="实时 OEE 未接入（需先启动实时看板/采集）")
        lines = []
        for name, m in snapshot.items():
            lines.append(f"{name}: OEE={_fmt(m.get('oee'))} "
                         f"A={_fmt(m.get('availability'))} "
                         f"P={_fmt(m.get('performance'))} Q={_fmt(m.get('quality'))} "
                         f"样本={m.get('samples', 0)} 不良={m.get('defects', 0)}"
                         + (f" 停机={_fmt(m.get('downtime_s'), 1)}s"
                            if m.get("downtime_s") else "")
                         + (f"（{m.get('downtime_reason')}）"
                            if m.get("downtime_reason") else ""))
        return ToolResult("get_live_oee", data={"lines": snapshot},
                          text="实时 OEE:\n" + "\n".join(lines))

    @reg.tool("estimate_cost", "成本损失估算",
              "按产线配置估算超规格废品损失 + 停机成本（单位: 配置货币）",
              category="IE 与成本", returns="defects/scrap_loss/downtime_loss/total_loss")
    def _estimate_cost(context: AgentContext):
        if context.plant is None or not getattr(context.plant, "lines", None):
            return ToolResult("estimate_cost", ok=False,
                              error="未配置产线（data/plant.json 或「工具→产线配置」）")
        from core.streaming.cost import CostAnalyzer
        analyzer = CostAnalyzer(context.plant, currency=context.currency,
                                downtime=context.downtime)
        samples = context.extra.get("samples_by_device") or {}
        result = analyzer.estimate(samples, context.live_oee_snapshot)
        if not result:
            return ToolResult("estimate_cost", ok=False, error="产线配置为空")
        lines = []
        for name, c in result.items():
            lines.append(f"{name}: 损失合计 {_fmt(c.get('total_loss'), 2)}"
                         f"（超规格 {c.get('defects', 0)} 件 → 废品 {_fmt(c.get('scrap_loss'), 2)}；"
                         f"停机 {_fmt(c.get('downtime_min'), 1)} min → "
                         f"{_fmt(c.get('downtime_loss'), 2)}）")
        return ToolResult("estimate_cost", data={"lines": result},
                          text="成本损失:\n" + "\n".join(lines))

    # ---------------- 实时工厂 ----------------
    @reg.tool("get_alerts", "查询告警",
              "查询告警日志（等级/未确认/设备筛选），用于异常处置建议",
              {"limit": "条数(默认10)", "only_unacked": "仅未确认(默认true)",
               "min_severity": "info/warning/critical", "device": "设备名(可选)"},
              category="实时工厂")
    def _get_alerts(context: AgentContext, limit: int = 10,
                    only_unacked: bool = True, min_severity: str = "info",
                    device: str | None = None):
        if context.journal is None:
            return ToolResult("get_alerts", ok=False, error="告警日志未接入")
        entries = context.journal.entries(limit=int(limit or 10),
                                          severity=min_severity or None,
                                          unacked_only=bool(only_unacked),
                                          device=device or None)
        if not entries:
            return ToolResult("get_alerts", data={"entries": [], "count": 0},
                              text="没有符合条件的告警记录")
        lines = [f"告警 {len(entries)} 条（未确认 {context.journal.unacked_count()} 条总）:"]
        payload = []
        for e in entries:
            lines.append(f"  [{e.severity}] {e.device}/{e.channel} {e.desc} "
                         f"值={_fmt(e.value, 3)}"
                         + ("（已确认）" if e.ack else "（未确认）"))
            payload.append(e.to_dict() if hasattr(e, "to_dict") else {
                "id": getattr(e, "id", ""), "severity": e.severity,
                "device": e.device, "channel": e.channel, "desc": e.desc,
                "value": e.value, "ack": e.ack})
        return ToolResult("get_alerts", data={"entries": payload},
                          text="\n".join(lines))

    @reg.tool("get_connector_health", "连接器健康",
              "查看数据源连接状态、最近错误与下次重连时间",
              category="实时工厂")
    def _get_connector_health(context: AgentContext):
        if context.connector_health is None:
            return ToolResult("get_connector_health", ok=False,
                              error="连接器健康未接入（未启动采集）")
        snapshot = context.connector_health.snapshot()
        if not snapshot:
            return ToolResult("get_connector_health", data={},
                              text="尚未注册任何数据源")
        lines = []
        for name, st in snapshot.items():
            lines.append(f"{name}: {st.get('status_label', st.get('status'))}"
                         f" 连续失败 {st.get('consecutive_errors', 0)}"
                         + (f" 最近错误: {st.get('last_error')}"
                            if st.get("last_error") else ""))
        return ToolResult("get_connector_health", data={"sources": snapshot},
                          text="数据源状态:\n" + "\n".join(lines))

    # ---------------- 五链与配置 ----------------
    @reg.tool("get_project_context", "五链上下文",
              "汇总 FMEA / 控制计划 / PPAP / 8D 与质量特性（五链贯通状态）",
              category="五链与配置")
    def _get_project_context(context: AgentContext):
        pctx = context.project_context
        if pctx is None:
            return ToolResult("get_project_context", ok=False,
                              error="项目上下文未接入")
        fmea = list(getattr(pctx, "fmea_items", []) or [])
        cp_rows = list(getattr(pctx, "control_plan_rows", []) or [])
        ppap = getattr(pctx, "ppap_report", {}) or {}
        eight_d = list(getattr(pctx, "eight_d_reports", []) or [])
        chars = list(getattr(pctx, "characteristics", []) or [])
        high_risk = []
        try:
            high_risk = pctx.get_high_risk_fmea_items()
        except Exception:
            pass
        data = {
            "characteristics": len(chars),
            "fmea_items": len(fmea),
            "high_risk_fmea": len(high_risk),
            "control_plan_rows": len(cp_rows),
            "ppap_level": ppap.get("submission_level"),
            "ppap_completion": ppap.get("completion_pct"),
            "eight_d_reports": len(eight_d),
        }
        text = (f"五链状态: 质量特性 {len(chars)} 项 · FMEA {len(fmea)} 条"
                f"（高风险 {len(high_risk)} 条）· 控制计划 {len(cp_rows)} 行 · "
                f"PPAP 等级 {data['ppap_level'] or '—'}"
                f"（完成度 {data['ppap_completion'] if data['ppap_completion'] is not None else '—'}%）· "
                f"8D 报告 {len(eight_d)} 份")
        return ToolResult("get_project_context", data=data, text=text)

    @reg.tool("get_plant", "产线配置",
              "查看产线/工位/通道、规格限、节拍、班次与成本参数",
              category="五链与配置")
    def _get_plant(context: AgentContext):
        plant = context.plant
        if plant is None or not getattr(plant, "lines", None):
            return ToolResult("get_plant", ok=False, error="未配置产线（plant.json）")
        lines, payload = [], []
        for line in plant.lines:
            stations = []
            for st in line.stations:
                spec = []
                if st.usl is not None:
                    spec.append(f"USL={_fmt(st.usl)}")
                if st.lsl is not None:
                    spec.append(f"LSL={_fmt(st.lsl)}")
                stations.append({"name": st.name, "device": st.device,
                                 "channels": list(st.channels),
                                 "usl": st.usl, "lsl": st.lsl,
                                 "cycle_time": st.ideal_cycle_time_s})
                lines.append(f"  [{line.name}] {st.name} ({st.device}) "
                             f"通道 {', '.join(st.channels) or '—'} "
                             f"{' '.join(spec) or '未设规格'}")
            payload.append({"line": line.name, "stations": stations,
                            "cycle_time": line.ideal_cycle_time_s,
                            "shift": line.shift, "unit_cost": line.unit_cost,
                            "scrap_cost": line.scrap_cost,
                            "downtime_cost_per_min": line.downtime_cost_per_min})
        head = f"产线 {len(plant.lines)} 条:"
        return ToolResult("get_plant", data={"lines": payload},
                          text="\n".join([head] + lines))

    @reg.tool("list_analyses", "已运行分析",
              "列出主界面已完成的分析及其关键指标（无需重新计算）",
              {"limit": "条数(默认10)"}, category="数据")
    def _list_analyses(context: AgentContext, limit: int = 10):
        if not context.analyses:
            return ToolResult("list_analyses", ok=False,
                              error="主界面还没有已运行的分析结果")
        items = []
        for key, result in list(context.analyses.items())[-int(limit or 10):]:
            if not isinstance(result, dict):
                continue
            atype = result.get("analysis_type") or result.get("result", {}).get("chart_type", "")
            cap = (result.get("result") or {}).get("capability") or result.get("capability") or {}
            metrics = {k: v for k, v in {
                "cpk": cap.get("cpk"), "cp": cap.get("cp"),
                "p_value": (result.get("result") or {}).get("p_value"),
                "grade": cap.get("grade"),
            }.items() if v is not None}
            items.append({"tab": str(key), "analysis_type": atype, "metrics": metrics})
        lines = [f"{len(items)} 项已运行分析:"]
        for it in items:
            metrics = ", ".join(f"{k}={_fmt(v)}" for k, v in it["metrics"].items())
            lines.append(f"  [{it['tab']}] {it['analysis_type']}" + (f" — {metrics}" if metrics else ""))
        return ToolResult("list_analyses", data={"analyses": items},
                          text="\n".join(lines))

    # ---------------- 知识库与指标解读 ----------------
    @reg.tool("search_knowledge", "知识库检索",
              "在质量/IE/精益知识库中检索标准、判定准则与方法说明（RAG）",
              {"query": "检索关键词或问题", "top_k": "返回条数(默认3)"},
              category="知识库")
    def _search_knowledge(context: AgentContext, query: str = "",
                          top_k: int = 3):
        kb = context.knowledge
        if kb is None:
            try:
                from core.knowledge_base import get_knowledge_base
                kb = get_knowledge_base()
            except Exception:
                kb = None
        if kb is None or not getattr(kb, "available", False):
            return ToolResult("search_knowledge", ok=False, error="知识库不可用")
        hits = kb.search(query, top_k=int(top_k or 3))
        if not hits:
            return ToolResult("search_knowledge", data={"hits": []},
                              text=f"知识库未找到与「{query}」匹配的内容")
        lines, payload = [f"知识库命中 {len(hits)} 条:"], []
        for h in hits:
            content = getattr(h, "content", "")
            lines.append(f"  [{h.category_label()}] {h.title}: {content[:200]}")
            payload.append({"title": h.title, "category": h.category_label(),
                            "content": content, "score": getattr(h, "score", None)})
        return ToolResult("search_knowledge", data={"hits": payload},
                          text="\n".join(lines))

    @reg.tool("explain_metric", "指标解读",
              "对 Cp/Cpk/Pp/Ppk/PPM/GRR/NDC/OEE/σ水平/P值 等指标做工程化解读",
              {"metric": "指标名(如 cpk)", "value": "指标值(可选，缺省用当前分析结果)"},
              category="知识库")
    def _explain_metric(context: AgentContext, metric: str = "",
                        value=None):
        import core.agent.explain as explain_mod
        result = explain_mod.explain_metric(str(metric), _to_float(value))
        if not result:
            return ToolResult("explain_metric", ok=False,
                              error=f"暂不支持解读指标「{metric}」"
                                    f"（支持: {', '.join(explain_mod.SUPPORTED)}）")
        return ToolResult("explain_metric", data=result, text=result["text"])

    # ---------------- 扩展工具（SPC/能力/MSA/检验/DOE/回归/可靠性/时序/IE/根因）----------------
    from core.agent.tools_ext import register_extended_tools
    register_extended_tools(reg, ctx)

    # ---------------- 机器学习工具（v4.0.0：准备/训练/AutoML/评估/解释/预测）----------------
    from core.agent.tools_ml import register_ml_tools
    register_ml_tools(reg, ctx)

    # ---------------- 插件工具（外部插件通过 manifest 声明贡献点）----------------
    try:
        from core.plugin_manager import PluginManager
        manager = PluginManager()
        manager.discover()
        manager.register_agent_tools(reg, ctx)
    except Exception:
        import logging
        logging.getLogger("QA-Tool.Agent").debug("插件工具注册失败", exc_info=True)

    return reg
