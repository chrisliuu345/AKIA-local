"""多工厂对比引擎 — 逐工厂文件计算汇总指标 (v2.4 E2)

- summarize_plant: 单文件 → {name, sheet, column, sample_size, mean, std,
  cpk, cpk_grade, violations, spc, error}
- build_comparison: 汇总多工厂结果 + 派生对比指标 (最优/最差 Cpk 等)
- Qt-free, 供 Tab 34 与测试直接调用
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from core.data_loader import DataLoader
from core.data_parser import DataParser
from core.file_watcher import _coerce_numeric, pick_numeric_column
from analysis.capability.normal_cap import analyze as cap_analyze
from analysis.spc.imr import analyze as imr_analyze


def _count_violations(spc: dict) -> int:
    """统计 SPC 结果中所有 _chart 键的 violations 数量"""
    total = 0
    for key, value in spc.items():
        if key.endswith("_chart") and isinstance(value, dict):
            viols = value.get("violations")
            if isinstance(viols, (list, tuple)):
                total += len(viols)
    return total


def summarize_plant(
    file_path: str,
    sheet_name: Optional[str] = None,
    column: Optional[str] = None,
) -> Dict[str, Any]:
    """读取单工厂文件, 输出汇总指标 dict。

    cpk 仅在文件含 USL/LSL 规格列时计算 (DataParser 自动识别)。
    """
    out: Dict[str, Any] = {
        "file_path": file_path,
        "name": os.path.basename(file_path),
        "sheet": None,
        "column": None,
        "sample_size": 0,
        "mean": None,
        "std": None,
        "cpk": None,
        "cpk_grade": None,
        "usl": None,
        "lsl": None,
        "violations": 0,
        "spc": None,
        "error": None,
    }
    try:
        if not os.path.exists(file_path):
            out["error"] = "文件不存在"
            return out

        loader = DataLoader()
        raw = loader.load(file_path)
        if not raw:
            out["error"] = "数据表为空"
            return out

        sheet = sheet_name or list(raw.keys())[0]
        df = raw[sheet]
        if df is None or df.empty:
            out["error"] = "数据表为空"
            return out
        out["sheet"] = sheet

        # 智能解析: 表头/列类型/规格限
        parser = DataParser()
        info = parser.analyze(df)
        measurement_cols = info.get("measurement_columns", [])
        specs = info.get("spec_limits", {})

        if column:
            col = column
        elif measurement_cols:
            col = measurement_cols[0]
        else:
            cdf = df.apply(_coerce_numeric)
            col = pick_numeric_column(cdf)
        out["column"] = col

        series = pd.to_numeric(df[col], errors="coerce").dropna().astype(float)
        n = len(series)
        if n < 2:
            out["error"] = "数据量不足"
            return out
        out["sample_size"] = n
        out["mean"] = round(float(series.mean()), 6)
        out["std"] = round(float(series.std(ddof=1)), 6)

        spec = specs.get(col, {})
        usl = spec.get("usl")
        lsl = spec.get("lsl")
        # 规格限也可能以独立 USL/LSL 列形式存在 (parser 按规格列名作键)。
        # 仅当某侧规格来源唯一时合并；多组规格列(如多个特性的 USL/LSL)无法
        # 判断归属时跳过 Cpk 计算, 不猜测取列。
        if usl is None:
            usl_values = {s.get("usl") for s in specs.values() if s.get("usl") is not None}
            if len(usl_values) == 1:
                usl = next(iter(usl_values))
            elif len(usl_values) > 1:
                out["spec_warning"] = "检测到多组规格限列，无法确定归属，跳过 Cpk 计算"
        if lsl is None:
            lsl_values = {s.get("lsl") for s in specs.values() if s.get("lsl") is not None}
            if len(lsl_values) == 1:
                lsl = next(iter(lsl_values))
            elif len(lsl_values) > 1:
                out["spec_warning"] = "检测到多组规格限列，无法确定归属，跳过 Cpk 计算"
        if usl is not None or lsl is not None:
            cap = cap_analyze(series, usl=usl, lsl=lsl)
            capability = cap.get("capability", {})
            out["usl"] = capability.get("usl")
            out["lsl"] = capability.get("lsl")
            out["cpk"] = capability.get("cpk")
            out["cpk_grade"] = capability.get("grade")

        spc = imr_analyze(series)
        out["spc"] = spc
        out["violations"] = _count_violations(spc)
    except FileNotFoundError:
        out["error"] = "文件不存在"
    except Exception as e:
        out["error"] = str(e)
    return out


def build_comparison(plants: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总多工厂结果 + 派生对比指标"""
    ok = [p for p in plants if not p.get("error")]
    cpk_values = [p["cpk"] for p in ok if p["cpk"] is not None]
    viol_values = [p["violations"] for p in ok if p.get("violations") is not None]
    return {
        "plants": plants,
        "plant_count": len(plants),
        "ok_count": len(ok),
        "best_cpk": max(cpk_values) if cpk_values else None,
        "worst_cpk": min(cpk_values) if cpk_values else None,
        "has_cpk": bool(cpk_values),
        "total_violations": sum(viol_values),
    }
