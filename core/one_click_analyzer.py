"""一键智能分析引擎 — 数据画像 → 推荐分析 → 批量执行 → AI 撰写结论 → 整合报告"""

from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from core.data_profiler import DataProfiler
from core.log_util import get_logger

_log = get_logger(__name__)


class OneClickAnalyzer:
    """一键分析: 自动画像 + 推荐 + 执行 + 合成"""

    def __init__(self, llm_client=None):
        self.profiler = DataProfiler()
        self.llm = llm_client
        self._progress_cb: Optional[Callable[[str, int], None]] = None

    def set_progress_callback(self, cb: Callable[[str, int], None]):
        """设置进度回调: cb(message, percent)"""
        self._progress_cb = cb

    def _emit(self, msg: str, pct: int):
        if self._progress_cb:
            self._progress_cb(msg, pct)
        _log.info(msg)

    # ── 阶段1: 画像 + 推荐 ──
    def profile_and_recommend(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """数据画像并生成推荐分析列表"""
        self._emit("分析数据画像...", 5)
        profile = self.profiler.profile(raw_data)

        recommendations = []
        sheets = profile.get("sheets", {})

        # 收集所有列信息
        all_numeric = []
        all_datetime = []
        all_text = []
        for sn, info in sheets.items():
            for col in info.get("columns", []):
                cat = col.get("category", "text")
                if cat == "measurement":
                    col_info = dict(col)
                    col_info["sheet"] = sn
                    all_numeric.append(col_info)
                elif cat == "datetime":
                    col_info = dict(col)
                    col_info["sheet"] = sn
                    all_datetime.append(col_info)
                else:
                    col_info = dict(col)
                    col_info["sheet"] = sn
                    all_text.append(col_info)

        # ── 推荐逻辑 ──
        self._emit("生成分析推荐...", 15)

        # SPC: 有数值列+时间列
        if all_numeric and all_datetime:
            recommendations.append({
                "type": "spc", "label": "SPC 控制图",
                "priority": "high", "reason": f"检测到{len(all_numeric)}个数值列+时间序列，建议建立过程控制",
            })
        elif all_numeric:
            recommendations.append({
                "type": "spc", "label": "SPC 控制图",
                "priority": "medium", "reason": f"有{len(all_numeric)}个数值列, 可进行过程能力评估",
            })

        # 过程能力
        if all_numeric:
            recommendations.append({
                "type": "capability", "label": "过程能力分析",
                "priority": "high" if len(all_numeric) >= 2 else "medium",
                "reason": f"{len(all_numeric)}个数值列适合 Cp/Cpk 评估",
            })

        # MSA: 多个同类型测量列
        if len(all_numeric) >= 3:
            recommendations.append({
                "type": "msa", "label": "测量系统分析 (MSA)",
                "priority": "medium", "reason": "多列数值型数据，建议评估测量系统变差",
            })

        # 假设检验: 有分组信息
        if all_text or all_numeric:
            recommendations.append({
                "type": "hypothesis", "label": "假设检验",
                "priority": "medium", "reason": "可进行组间差异显著性分析",
            })

        # DOE: 多个因子列
        if len(all_numeric) >= 4:
            recommendations.append({
                "type": "doe", "label": "实验设计 (DOE)",
                "priority": "low", "reason": f"{len(all_numeric)}个因子可进行因子效应分析",
            })

        # 回归
        if len(all_numeric) >= 2:
            recommendations.append({
                "type": "regression", "label": "回归分析",
                "priority": "medium", "reason": "可建立变量间定量关系模型",
            })

        # 图表
        if all_numeric:
            recommendations.append({
                "type": "chart", "label": "图表可视化",
                "priority": "high", "reason": "自动生成直方图/箱线图/散点图矩阵",
            })

        return {
            "profile": profile,
            "recommendations": recommendations,
            "stats": {
                "total_sheets": len(sheets),
                "total_columns": sum(len(s.get("columns", [])) for s in sheets.values()),
                "numeric_columns": len(all_numeric),
                "datetime_columns": len(all_datetime),
            },
        }

    # ── 阶段2: 批量执行分析 ──
    def execute_analyses(self, raw_data: Dict[str, pd.DataFrame],
                         profile_result: Dict[str, Any],
                         selected: List[str]) -> List[Dict[str, Any]]:
        """执行选定的分析, 返回结果列表"""
        results = []
        total = len(selected)
        base_pct = 30
        pct_range = 55  # 30→85%

        # 从画像结果中提取测量类列名（替代 select_dtypes，因数据以 str 加载）
        first_sheet = list(raw_data.values())[0] if raw_data else pd.DataFrame()
        num_cols = []
        sheets = profile_result.get("profile", {}).get("sheets", {})
        for sn, info in sheets.items():
            for col in info.get("columns", []):
                if col.get("category") == "measurement":
                    num_cols.append(col.get("name", ""))
        num_cols = num_cols[:8]  # 最多8个

        for i, analysis_type in enumerate(selected):
            self._emit(f"执行: {analysis_type}...", base_pct + int(pct_range * i / max(total, 1)))

            try:
                result = self._run_single_analysis(analysis_type, raw_data, first_sheet, num_cols, profile_result)
                if result:
                    results.append(result)
            except Exception as e:
                _log.warning(f"分析 {analysis_type} 失败: {e}")
                results.append({
                    "analysis_type": analysis_type,
                    "success": False,
                    "error": str(e),
                })

        self._emit("分析执行完成", 85)
        return results

    def _run_single_analysis(self, atype: str, raw_data: Dict, df: pd.DataFrame,
                             num_cols: List[str], profile: Dict) -> Optional[Dict]:
        """执行单个分析（轻量版本 — 返回摘要即可）"""
        if df.empty:
            return None

        try:
            if atype == "spc" and num_cols:
                col = num_cols[0]
                from analysis.spc.xbar_r import analyze as xbar_analyze
                sub_size = min(5, max(2, len(df) // 20))
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                result = xbar_analyze(series, subgroup_size=sub_size)
                xbar = result.get("xbar_chart", {})
                r_chart = result.get("r_chart", {})
                v_count = len(xbar.get("violations", [])) + len(r_chart.get("violations", []))
                return {
                    "analysis_type": "spc", "success": True, "column": col,
                    "summary": {
                        "cl": xbar.get("cl"), "ucl": xbar.get("ucl"),
                        "lcl": xbar.get("lcl"), "violations": v_count,
                    },
                }

            if atype == "capability" and num_cols:
                col = num_cols[0]
                from analysis.capability.normal_cap import analyze as cap_analyze
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                result = cap_analyze(series, usl=None, lsl=None, subgroup_size=min(5, len(series)))
                return {
                    "analysis_type": "capability", "success": True, "column": col,
                    "summary": {
                        "cp": result.get("cp"), "cpk": result.get("cpk"),
                        "pp": result.get("pp"), "ppk": result.get("ppk"),
                        "grade": result.get("grade", ""),
                    },
                }

            if atype == "msa" and len(num_cols) >= 2:
                from analysis.msa.gage_rr import analyze_crossed
                col = num_cols[0]
                # 构造至少2个操作员的MSA数据
                msa_df = df[[col]].copy()
                msa_df["part"] = (df.index % max(5, min(10, len(df) // 5))).astype(str)
                msa_df["operator"] = ["OP1" if i % 2 == 0 else "OP2" for i in range(len(msa_df))]
                result = analyze_crossed(msa_df, col, "part", "operator")
                pcts = result.get("percentages", {})
                # W10 fix: 统一为0-1标度（与kpi_extractor一致）
                grr_raw = pcts.get("grr_pct_tv")
                grr_normalized = grr_raw / 100.0 if grr_raw is not None else None
                return {
                    "analysis_type": "msa", "success": True,
                    "summary": {
                        "grr_pct": grr_normalized,
                        "ndc": result.get("ndc"),
                        "acceptable": result.get("acceptance"),
                    },
                }

            if atype == "hypothesis" and len(num_cols) >= 2:
                from scipy import stats
                s1 = pd.to_numeric(df[num_cols[0]], errors="coerce").dropna()
                s2 = pd.to_numeric(df[num_cols[1]], errors="coerce").dropna() if len(num_cols) >= 2 else None
                if s2 is not None and len(s2) > 0:
                    stat, p = stats.ttest_ind(s1, s2, equal_var=False)
                else:
                    stat, p = stats.shapiro(s1)
                return {
                    "analysis_type": "hypothesis", "success": True,
                    "summary": {"test": "t检验" if s2 is not None else "Shapiro-Wilk",
                               "statistic": float(stat), "p_value": float(p)},
                }

            if atype == "regression" and len(num_cols) >= 2:
                from analysis.regression.linear_regression import analyze as reg_analyze
                y_col, x_cols = num_cols[0], num_cols[1:min(3, len(num_cols))]
                result = reg_analyze(df, y_col, x_cols)
                return {
                    "analysis_type": "regression", "success": True,
                    "summary": {
                        "r_squared": result.get("r_squared"),
                        "adj_r_squared": result.get("adj_r_squared"),
                    },
                }

            if atype == "chart":
                return {
                    "analysis_type": "chart", "success": True,
                    "summary": {"chart_types": ["histogram", "boxplot", "correlation_heatmap"],
                               "columns": num_cols[:5]},
                }

            if atype == "doe":
                return {
                    "analysis_type": "doe", "success": True,
                    "summary": {"recommendation": f"建议对{num_cols[:4]}进行因子筛选实验"},
                }
        except Exception as e:
            _log.warning(f"分析 {atype} 失败: {e}")
            return {"analysis_type": atype, "success": False, "error": str(e)}

        return None

    # ── 阶段3: AI 合成 ──
    def synthesize(self, results: List[Dict], profile: Dict) -> str:
        """调用 LLM 生成分析结论（或使用知识库降级）"""
        summary_parts = []
        for r in results:
            s = r.get("summary", {})
            if r.get("success") and s:
                summary_parts.append(f"{r['analysis_type']}: {s}")
            elif not r.get("success"):
                summary_parts.append(f"{r['analysis_type']}: 失败({r.get('error','?')})")

        stats = profile.get("global_summary", {})

        prompt = (
            f"你是专业质量分析工程师。基于以下数据分析结果撰写一份简洁的分析报告（300-500字）。\n\n"
            f"数据概况: {stats.get('total_sheets',0)}个表, "
            f"{stats.get('total_rows',0)}行数据\n\n"
            "分析结果摘要:\n" + "\n".join(summary_parts) + "\n\n"
            "请按以下结构输出:\n"
            "1. 数据概况 (1-2句)\n"
            "2. 关键发现 (3-5个要点)\n"
            "3. 风险提示 (如有SPC违规或CPK偏低)\n"
            "4. 行动建议 (具体可执行的改善步骤)\n"
        )

        if self.llm and self.llm.available:
            try:
                full = "".join(list(self.llm.generate(prompt)))
                return full
            except Exception:
                pass

        # 降级: 知识库 + 规则生成
        return self._fallback_synthesis(results, stats)

    def _fallback_synthesis(self, results: List[Dict], stats: Dict) -> str:
        """无 LLM 时基于规则的报告生成"""
        lines = [
            "## 一键分析报告 (规则引擎)",
            "",
            f"**数据概况**: {stats.get('total_sheets', '?')} 个工作表, "
            f"{stats.get('total_rows', '?')} 行记录",
            "",
            "### 分析结果",
        ]

        for r in results:
            s = r.get("summary", {})
            label = r.get("analysis_type", "?")
            if r.get("success") and s:
                if label == "spc":
                    v = s.get("violations", 0)
                    lines.append(f"- **SPC 控制图**: {'发现' + str(v) + '个违规点,建议排查异常原因' if v > 0 else '未发现特殊原因变异,过程受控'}")
                elif label == "capability":
                    cpk = s.get("cpk")
                    if cpk:
                        level = "充足(Cpk≥1.33)" if cpk >= 1.33 else ("尚可(Cpk≥1.0)" if cpk >= 1.0 else "不足(Cpk<1.0)")
                        lines.append(f"- **过程能力**: Cpk={cpk:.2f}, 等级: {level}")
                elif label == "msa":
                    grr = s.get("grr_pct")
                    if grr is not None:
                        # W10 fix: 统一0-1标度（kpi_extractor归一化为0-1）
                        ok = "可接受(<10%)" if grr < 0.1 else ("条件接受(10-30%)" if grr < 0.3 else "不可接受(>30%)")
                        lines.append(f"- **MSA 量具 R&R**: GRR={grr*100:.1f}%, {ok}")
                elif label == "regression":
                    r2 = s.get("r_squared")
                    if r2:
                        lines.append(f"- **回归分析**: R²={r2:.3f}, {'强相关' if r2 > 0.7 else ('中等相关' if r2 > 0.3 else '弱相关')}")
                else:
                    lines.append(f"- **{label}**: 已完成分析")
            elif not r.get("success"):
                lines.append(f"- **{label}**: ⚠ 执行失败 — {r.get('error', '未知错误')}")

        lines.append("")
        lines.append("### 一般建议")
        lines.append("1. 确认测量系统(MSA)合格后再进行过程能力分析")
        lines.append("2. SPC违规点需逐一排查5M1E因素")
        lines.append("3. 建议定期(每季度)复核标准工时和产能数据")

        return "\n".join(lines)

    # ── 一键执行(全流程) ──
    def run(self, raw_data: Dict[str, pd.DataFrame],
            selected: Optional[List[str]] = None) -> Dict[str, Any]:
        """一键执行全流程: 画像 → 推荐 → 执行 → 合成"""
        self._emit("开始一键分析...", 0)

        # Phase 1
        plan = self.profile_and_recommend(raw_data)
        if selected is None:
            # 默认选择 high priority 的推荐
            selected = [r["type"] for r in plan["recommendations"] if r.get("priority") == "high"]
            if not selected:
                selected = [r["type"] for r in plan["recommendations"][:4]]

        self._emit(f"选定 {len(selected)} 项分析: {', '.join(selected)}", 25)

        # Phase 2
        results = self.execute_analyses(raw_data, plan, selected)

        # Phase 3
        self._emit("AI 撰写分析结论...", 90)
        conclusion = self.synthesize(results, plan.get("profile", {}))

        self._emit("报告生成完成", 100)

        return {
            "plan": plan,
            "results": results,
            "conclusion": conclusion,
            "success_count": sum(1 for r in results if r.get("success")),
            "total_count": len(results),
        }
