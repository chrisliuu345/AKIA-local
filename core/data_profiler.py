"""数据画像引擎 — 自动分析数据特征并推荐分析方法"""

from typing import Any
import warnings
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from core.log_util import get_logger

_log = get_logger(__name__)


class DataProfiler:
    """对工作簿数据进行全面画像分析，生成分析推荐"""

    def __init__(self, sample_size: int = 5000):
        self.sample_size = sample_size

    def profile(self, raw_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
        sheets = {}
        total_rows = 0
        total_issues = []

        for sn, df in raw_data.items():
            if df.empty:
                continue
            sample = df.head(self.sample_size) if len(df) > self.sample_size else df
            total_rows += len(df)
            cols = self._profile_columns(sample)
            recs = self._generate_recommendations(sample, sn, cols)
            issues = self._detect_issues(cols, sn, sample)
            total_issues.extend(issues)

            health = self._health_check(cols)
            sheets[sn] = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": cols,
                "recommendations": recs,
                "issues": issues,
                "health": health,
            }

        return {
            "sheets": sheets,
            "global_summary": {
                "total_sheets": len(sheets),
                "total_rows": total_rows,
                "total_issues": len(total_issues),
                "issues": total_issues[:10],
            },
        }

    def _profile_columns(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        result = []
        for col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            non_null = series.dropna()
            n = len(non_null)
            missing_pct = round((len(df) - n) / max(len(df), 1) * 100, 1)

            if missing_pct >= 100.0:
                continue

            info: dict[str, Any] = {
                "name": _clean_col_name(col),
                "dtype": str(df[col].dtype),
                "missing_pct": missing_pct,
                "category": "text",
                "unique_count": 0,
                "skewness": None,
                "kurtosis": None,
                "outlier_count": None,
                "normality_pvalue": None,
                "distribution": None,
                "mean": None,
                "std": None,
            }

            if "datetime" in str(df[col].dtype):
                info["category"] = "datetime"
                result.append(info)
                continue

            if n >= 1 and n >= len(df) * 0.1:
                info["category"] = "measurement"
                info["mean"] = round(float(non_null.mean()), 4)
                info["std"] = round(float(non_null.std()), 4)
                if n >= 8:
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            info["skewness"] = round(float(sp_stats.skew(non_null)), 3)
                            info["kurtosis"] = round(float(sp_stats.kurtosis(non_null)), 3)
                    except Exception as e:  # 偏度/峰度算不出（样本退化）→ 字段留空
                        _log.debug("偏度/峰度计算失败: %s", e)

                if len(non_null) >= 4:
                    iqr = float(np.percentile(non_null, 75) - np.percentile(non_null, 25))
                    lo = float(np.percentile(non_null, 25) - 1.5 * iqr)
                    hi = float(np.percentile(non_null, 75) + 1.5 * iqr)
                    info["outlier_count"] = int(((non_null < lo) | (non_null > hi)).sum())

                if n >= 8 and n <= 5000:
                    try:
                        _, p = sp_stats.shapiro(non_null.sample(min(n, 5000)) if n > 5000 else non_null)
                        info["normality_pvalue"] = round(float(p), 4)
                    except Exception as e:  # 正态性检验不可用 → 不做正态判定
                        _log.debug("Shapiro-Wilk 检验失败: %s", e)

                if info["normality_pvalue"] is not None:
                    if info["normality_pvalue"] >= 0.05:
                        info["distribution"] = "normal"
                    elif abs(info["skewness"] or 0) > 1:
                        info["distribution"] = "skewed"
                    else:
                        info["distribution"] = "non_normal"
                elif info["skewness"] is not None:
                    info["distribution"] = "normal" if abs(info["skewness"]) < 0.5 else "skewed"

                result.append(info)
                continue

            info["unique_count"] = int(df[col].nunique())
            if info["unique_count"] <= min(50, max(len(df) * 0.1, 2)):
                info["category"] = "identifier"
            else:
                info["category"] = "text"
            result.append(info)

        return result

    @staticmethod
    def _score_recommendation(cols: list[dict], rec: dict) -> tuple[str, float]:
        """计算推荐置信度: 返回 (等级, 百分比)

        等级: highly_recommended / recommended / optional
        """
        tab_idx = rec.get("tab_index", 0)
        numeric = [c for c in cols if c["category"] == "measurement"]
        identifiers = [c for c in cols if c["category"] == "identifier"]

        if tab_idx == 1:
            if len(numeric) >= 3:
                return ("highly_recommended", 0.95)
            if len(numeric) >= 1:
                return ("recommended", 0.80)
            return ("optional", 0.40)
        if tab_idx == 2:
            best = max(numeric, key=lambda c: c.get("normality_pvalue") or 0) if numeric else None
            has_spec = rec["params"].get("usl") is not None or rec["params"].get("lsl") is not None
            if best and has_spec:
                return ("highly_recommended", 0.90)
            if best:
                return ("recommended", 0.70)
            return ("optional", 0.30)
        if tab_idx == 3:
            if len(identifiers) >= 2 and len(numeric) >= 1:
                return ("recommended", 0.75)
            return ("optional", 0.35)
        if tab_idx == 4:
            if len(numeric) >= 2:
                return ("recommended", 0.70)
            return ("optional", 0.30)
        if tab_idx in (5, 6):
            if len(numeric) >= 3:
                return ("recommended", 0.65)
            return ("optional", 0.25)
        return ("optional", 0.50)

    @staticmethod
    def _health_check(cols: list[dict]) -> dict[str, Any]:
        """四项数据健康指标: 完整性 / 正态性 / 稳定性 / 分辨力"""
        numeric = [c for c in cols if c["category"] == "measurement"]
        if not numeric:
            return {"completeness": 0, "normality": 0, "stability": 0, "resolution": 0}

        completeness = 1.0 - np.mean([c["missing_pct"] / 100 for c in numeric])

        normal_count = sum(1 for c in numeric if c.get("distribution") == "normal")
        normality = normal_count / max(len(numeric), 1)

        cvs = []
        for c in numeric:
            mean_val = c.get("mean")
            std_val = c.get("std")
            if mean_val and std_val and mean_val != 0:
                cvs.append(min(abs(std_val / mean_val), 1.0))
        stability = 1.0 - np.mean(cvs) if cvs else 0.5

        outlier_ratios = []
        for c in numeric:
            actual = c.get("outlier_count")
            if actual is not None and c.get("missing_pct", 0) < 50:
                outlier_ratios.append(min(actual / 100, 1.0))
        resolution = 1.0 - np.mean(outlier_ratios) if outlier_ratios else 0.5

        return {
            "completeness": round(float(completeness), 3),
            "normality": round(float(normality), 3),
            "stability": round(float(stability), 3),
            "resolution": round(float(resolution), 3),
        }

    def _generate_recommendations(self, df: pd.DataFrame, sheet_name: str,
                                  cols: list[dict]) -> list[dict[str, Any]]:
        recs = []
        numeric = [c for c in cols if c["category"] == "measurement"]
        identifiers = [c for c in cols if c["category"] == "identifier"]
        col_names = [c["name"] for c in cols]

        usl_col = _find_spec_col(col_names, "USL")
        lsl_col = _find_spec_col(col_names, "LSL")

        if numeric:
            best = max(numeric, key=lambda c: c.get("normality_pvalue") or 0)
            rec = {
                "tab_index": 1,
                "tab_name": "SPC 控制图",
                "method": "XBar-R" if len(df) >= 10 else "I-MR",
                "reason": f"'{best['name']}' 列数值连续，建议子组控制图监控过程稳定性",
                "params": {"column": best["name"], "subgroup_size": 5},
                "icon": "SPC",
            }
            if usl_col:
                usl_vals = pd.to_numeric(df[usl_col], errors="coerce").dropna()
                rec["params"]["usl"] = float(usl_vals.iloc[0]) if len(usl_vals) else None
            if lsl_col:
                lsl_vals = pd.to_numeric(df[lsl_col], errors="coerce").dropna()
                rec["params"]["lsl"] = float(lsl_vals.iloc[0]) if len(lsl_vals) else None
            grade, conf = self._score_recommendation(cols, rec)
            rec["confidence"] = {"grade": grade, "percentage": conf}
            recs.append(rec)

            rec2 = {
                "tab_index": 2,
                "tab_name": "过程能力分析",
                "method": "正态过程能力" if best.get("distribution") == "normal" else "非正态 (Box-Cox)",
                "reason": f"'{best['name']}' 列{'正态分布' if best.get('distribution') == 'normal' else '非正态'}，建议评估过程能力",
                "params": {"column": best["name"], "usl": rec["params"].get("usl"), "lsl": rec["params"].get("lsl")},
                "icon": "CPK",
            }
            grade2, conf2 = self._score_recommendation(cols, rec2)
            rec2["confidence"] = {"grade": grade2, "percentage": conf2}
            recs.append(rec2)

        if len(identifiers) >= 2 and numeric:
            part_col = identifiers[0]["name"]
            op_col = identifiers[1]["name"] if len(identifiers) >= 2 else identifiers[0]["name"]
            rec3 = {
                "tab_index": 3,
                "tab_name": "MSA 分析",
                "method": "量具R&R (交叉)",
                "reason": f"检测到 '{part_col}'（疑似零件列）和 '{op_col}'（疑似操作员列），推荐 GRR 分析",
                "params": {"column": numeric[0]["name"], "part_col": part_col, "operator_col": op_col},
                "icon": "MSA",
            }
            grade3, conf3 = self._score_recommendation(cols, rec3)
            rec3["confidence"] = {"grade": grade3, "percentage": conf3}
            recs.append(rec3)

        if len(numeric) >= 2:
            rec4 = {
                "tab_index": 4,
                "tab_name": "假设检验",
                "method": "双样本 t检验",
                "reason": f"'{numeric[0]['name']}' 和 '{numeric[1]['name']}' 两列数值数据，推荐对比检验",
                "params": {"col1": numeric[0]["name"], "col2": numeric[1]["name"]},
                "icon": "TTEST",
            }
            grade4, conf4 = self._score_recommendation(cols, rec4)
            rec4["confidence"] = {"grade": grade4, "percentage": conf4}
            recs.append(rec4)

        if len(numeric) >= 3:
            rec5 = {
                "tab_index": 5,
                "tab_name": "DOE 实验设计",
                "method": "因子设计分析",
                "reason": f"多个数值列（{', '.join(c['name'] for c in numeric[:4])}），可能存在因子关系",
                "params": {"response": numeric[0]["name"]},
                "icon": "DOE",
            }
            grade5, conf5 = self._score_recommendation(cols, rec5)
            rec5["confidence"] = {"grade": grade5, "percentage": conf5}
            recs.append(rec5)

            rec6 = {
                "tab_index": 6,
                "tab_name": "回归分析",
                "method": "线性回归",
                "reason": "数值变量间可能存在相关关系，建议回归建模",
                "params": {"response": numeric[0]["name"], "factor1": numeric[1]["name"]},
                "icon": "REG",
            }
            grade6, conf6 = self._score_recommendation(cols, rec6)
            rec6["confidence"] = {"grade": grade6, "percentage": conf6}
            recs.append(rec6)

        text_cols = [c for c in cols if c["category"] in ("text", "identifier")]
        col_names_lower = [c["name"].lower() for c in cols]

        if identifiers and any(kw in " ".join(col_names_lower) for kw in ["cycle", "ct", "time", "工时"]):
            rec = {"tab_index": 7, "tab_name": "工时研究", "method": "标准工时", "icon": "IE7",
                   "reason": "检测到工序/时间相关列, 推荐进行工时研究和标准工时计算",
                   "params": {"column": numeric[0]["name"] if numeric else ""}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.72}
            recs.append(rec)

        if text_cols and numeric:
            rec = {"tab_index": 8, "tab_name": "工作抽样", "method": "比率分析", "icon": "IE8",
                   "reason": f"检测到分类列'{text_cols[0]['name']}'和数值列, 推荐工作抽样分析",
                   "params": {"column": text_cols[0]["name"]}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.68}
            recs.append(rec)

        if identifiers and len(numeric) >= 2:
            rec = {"tab_index": 9, "tab_name": "线平衡分析", "method": "LPT平衡", "icon": "IE9",
                   "reason": "多个标识列和数值列, 可能存在工序时间数据, 推荐线平衡分析",
                   "params": {"column": numeric[0]["name"]}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.65}
            recs.append(rec)

        if any(kw in " ".join(col_names_lower) for kw in ["avail", "downtime", "oee", "qty", "ideal"]):
            rec = {"tab_index": 10, "tab_name": "OEE 分析", "method": "设备综合效率", "icon": "IE10",
                   "reason": "检测到可用时间/停机/产量相关列, 推荐 OEE 设备综合效率分析",
                   "params": {"column": numeric[0]["name"] if numeric else ""}}
            rec["confidence"] = {"grade": "highly_recommended", "percentage": 0.88}
            recs.append(rec)

        if any(kw in " ".join(col_names_lower) for kw in ["va", "nva", "lead", "inventory", "库存"]):
            rec = {"tab_index": 11, "tab_name": "价值流 VSM", "method": "VA/NVA分析", "icon": "IE11",
                   "reason": "检测到价值/库存相关列, 推荐价值流图分析",
                   "params": {"column": numeric[0]["name"] if numeric else ""}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.60}
            recs.append(rec)

        if len(numeric) >= 2:
            rec = {"tab_index": 12, "tab_name": "通用图表", "method": "散点图/箱线图", "icon": "CHT",
                   "reason": f"{len(numeric)} 个数值列, 推荐使用通用图表生成器进行可视化探索",
                   "params": {"column": numeric[0]["name"]}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.78}
            recs.append(rec)

        if len(numeric) >= 3 and (usl_col or lsl_col):
            rec = {"tab_index": 18, "tab_name": "工序能力对比", "method": "多工序Cp/Cpk对比", "icon": "CPC",
                   "reason": "多数值列且检测到规格限, 推荐工序能力对比图",
                   "params": {"column": numeric[0]["name"]}}
            rec["confidence"] = {"grade": "highly_recommended", "percentage": 0.85}
            recs.append(rec)

        datetime_cols = [c for c in cols if c["category"] == "datetime"]
        if datetime_cols and len(numeric) >= 1:
            rec = {"tab_index": 19, "tab_name": "多系列趋势图", "method": "移动平均+异常检测", "icon": "TRD",
                   "reason": f"检测到日期列'{datetime_cols[0]['name']}', 推荐趋势图分析时序变化",
                   "params": {"column": numeric[0]["name"]}}
            rec["confidence"] = {"grade": "highly_recommended", "percentage": 0.82}
            recs.append(rec)

        if len(numeric) >= 4:
            rec = {"tab_index": 20, "tab_name": "统计摘要面板", "method": "五数汇总+分布", "icon": "SUM",
                   "reason": f"{len(numeric)} 个数值列, 推荐统计摘要面板快速掌握数据全貌",
                   "params": {"column": numeric[0]["name"]}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.75}
            recs.append(rec)

        if any(kw in " ".join(col_names_lower) for kw in ["失效", "故障", "寿命", "fail", "life", "time"]):
            rec = {"tab_index": 13, "tab_name": "可靠性分析", "method": "Weibull/MTBF", "icon": "REL",
                   "reason": "检测到失效/时间相关列, 推荐进行 Weibull 寿命分析或 MTBF 计算",
                   "params": {"column": numeric[0]["name"] if numeric else ""}}
            rec["confidence"] = {"grade": "highly_recommended", "percentage": 0.86}
            recs.append(rec)

        if len(cols) >= 8:
            rec = {"tab_index": 16, "tab_name": "FMEA 分析", "method": "RPN风险评估", "icon": "FMEA",
                   "reason": f"数据列较多 ({len(cols)}列), 推荐使用 FMEA 工作表进行系统风险评估",
                   "params": {}}
            rec["confidence"] = {"grade": "recommended", "percentage": 0.62}
            recs.append(rec)

        return recs

    def _detect_issues(self, cols: list[dict], sheet_name: str,
                   df: pd.DataFrame | None = None) -> list[str]:
        issues = []
        for c in cols:
            if c["missing_pct"] > 10:
                issues.append(f"{sheet_name}: '{c['name']}' 缺失率 {c['missing_pct']}% 偏高")
            if c.get("outlier_count", 0) and c["outlier_count"] > 10:
                issues.append(f"{sheet_name}: '{c['name']}' 检测到 {c['outlier_count']} 个 IQR 异常点")
        for c in cols:
            if c["category"] == "measurement" and c.get("std", 0) == 0:
                issues.append(f"{sheet_name}: '{c['name']}' 为常数列, 无分析价值")
        numeric = [c for c in cols if c["category"] == "measurement" and c.get("std", 0) > 0]
        if len(numeric) >= 2:
            correlated_pairs = []
            if df is not None:
                names = [c["name"] for c in numeric]
                try:
                    valid = [n for n in names if n in df.columns]
                    if len(valid) >= 2:
                        corr = df[valid].corr()
                        for i in range(len(valid)):
                            for j in range(i + 1, len(valid)):
                                try:
                                    v = corr.iloc[i, j]
                                except (IndexError, KeyError):
                                    continue
                                if v is not None and not pd.isna(v) and abs(float(v)) > 0.95:
                                    correlated_pairs.append((valid[i], valid[j]))
                except Exception as e:  # 相关系数矩阵不可用 → 跳过冗余列提示
                    _log.debug("列相关性分析失败: %s", e)
            if len(correlated_pairs) <= 3 and correlated_pairs:
                a, b = correlated_pairs[0]
                issues.append(f"{sheet_name}: '{a}' 与 '{b}' 高度相关 (r>{0.95}), 可能存在冗余列")
        return issues


def _find_spec_col(col_names: list[str], keyword: str) -> str | None:
    for c in col_names:
        if keyword.lower() in str(c).lower():
            return c
    return None


def _clean_col_name(col) -> str:
    """清理列名: Unnamed:N → 列N+1, 纯数字列名 → 列N+1, 否则去空格"""
    import re
    s = str(col).strip()
    if not s:
        return s
    m = re.match(r"unnamed[:\s_-]*(\d+)", s, re.IGNORECASE)
    if m:
        return f"列 {int(m.group(1)) + 1}"
    try:
        n = int(s)
        return f"列 {n + 1}"
    except ValueError:  # 列名不是纯数字：保持原名
        pass
    return s
