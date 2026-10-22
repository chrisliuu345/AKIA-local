"""脱敏分享包 v1 — 合成数据 + 统计等价声明 + 泄漏扫描（v4.3.0 B4-4）。

原则：
- 只输出**参数化合成数据**（数值列按均值/标准差生成，分类列按频率重标为
  Cat_1..n），绝不复用原始值；
- 列名/表名在包内统一为 C1.. / sheet_1..，不携带原始标识；
- 案例只保留 ID / 状态 / 阶段，不含标题、负责人、产品、问题描述与关闭原因；
- 导出后自动执行泄漏扫描（原始高精度值、表列名、路径/人名等禁用词）。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import zipfile
from typing import Any

import numpy as np
import pandas as pd

from config.settings import APP_VERSION
from core.archive_safety import ArchiveSecurityError, open_safe_zip, read_member
from core.time_utils import now_iso

SHARE_PACK_SCHEMA_VERSION = "1"
DEFAULT_TOLERANCES = {"mean_rel": 0.05, "std_rel": 0.05, "quantile_rel": 0.10}

#: 泄漏扫描上界（v4.3.1）：避免 O(候选数 × 文件大小) 的逐候选项搜索在
#: 大表导出时拖死 UI。数值候选走单遍 token 提取（全量扫描、语义等价于数字
#: 边界匹配）；文本候选在小文件上保留完整子串匹配，大文件退化为 token
#: 精确匹配（CSV 字段级）。
MAX_VALUE_CANDIDATES_PER_COLUMN = 20000
MAX_SUBSTRING_TEXT_CANDIDATES = 2000
MAX_SUBSTRING_TEXT_BYTES = 1_000_000

_NUMERIC_TOKEN_RE = re.compile(r"[+-]?\d[\d.]*")
_TEXT_TOKEN_RE = re.compile(r"[^\s,;:=\"']+")


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                      default=str).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stats(series: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"n": 0.0, "mean": 0.0, "std": 0.0,
                "p05": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "n": int(clean.count()),
        "mean": float(clean.mean()),
        "std": float(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "p05": float(clean.quantile(0.05)),
        "p50": float(clean.quantile(0.50)),
        "p95": float(clean.quantile(0.95)),
    }


def synthesize_frame(df: pd.DataFrame, *, seed: int = 42,
                     tolerances: dict[str, float] | None = None
                     ) -> tuple[pd.DataFrame, dict[str, Any]]:
    """生成与原始表统计等价的合成表；返回 (合成表, 等价声明)。"""
    tol = dict(DEFAULT_TOLERANCES)
    tol.update(tolerances or {})
    rng = np.random.default_rng(int(seed))
    columns: dict[str, Any] = {}
    synthetic: dict[str, Any] = {}
    for index, column in enumerate(df.columns):
        series = df[column]
        name = f"C{index + 1}"
        if pd.api.types.is_numeric_dtype(series) and series.notna().any():
            clean = pd.to_numeric(series, errors="coerce")
            stats_original = _stats(clean)
            mean, std = stats_original["mean"], stats_original["std"]
            mask = clean.isna().to_numpy()
            values = (rng.normal(mean, std, len(clean)) if std > 0
                      else np.full(len(clean), mean))
            values[mask] = np.nan
            synthetic[name] = values
            stats_synthetic = _stats(pd.Series(values))
            count = max(int(stats_original["n"]), 2)
            mean_tol = max(tol["mean_rel"] * abs(mean), 3 * std / math.sqrt(count))
            std_tol = max(tol["std_rel"] * std, 3 * std / math.sqrt(2 * (count - 1)))
            span = max(stats_original["p95"] - stats_original["p05"], std, 1e-12)
            quantile_tol = max(tol["quantile_rel"] * span,
                               3 * std / math.sqrt(count))
            equivalent = (
                abs(stats_synthetic["mean"] - mean) <= mean_tol
                and abs(stats_synthetic["std"] - std) <= std_tol
                and max(abs(stats_synthetic[key] - stats_original[key])
                        for key in ("p05", "p50", "p95")) <= quantile_tol
            )
            columns[name] = {
                "kind": "numeric", "n": stats_original["n"],
                "original": stats_original, "synthetic": stats_synthetic,
                "tolerances": {"mean": mean_tol, "std": std_tol,
                               "quantile": quantile_tol},
                "equivalent": bool(equivalent),
            }
        else:
            texts = series.astype(str).fillna("")
            counts = texts.value_counts()
            ordered = list(counts.index)
            labels = {value: f"Cat_{i + 1}" for i, value in enumerate(ordered)}
            synthetic[name] = [labels[value] for value in texts.tolist()]
            columns[name] = {
                "kind": "categorical", "n": int(len(texts)),
                "categories": int(len(counts)),
                "top_frequency": int(counts.iloc[0]) if len(counts) else 0,
                "equivalent": True,
            }
    statement = {
        "schema_version": SHARE_PACK_SCHEMA_VERSION,
        "method": "parametric-synthetic-v1",
        "tolerances": tol,
        "columns": columns,
        "all_equivalent": all(item.get("equivalent") for item in columns.values()),
    }
    return pd.DataFrame(synthetic), statement


def _leak_candidates(raw_data: dict[str, pd.DataFrame]
                     ) -> tuple[list[str], dict[str, Any]]:
    """挑出高区分度的原始文本（高精度数值 / 表名 / 列名），用于泄漏扫描。

    单列候选值数量按首次出现顺序截断（``MAX_VALUE_CANDIDATES_PER_COLUMN``），
    避免百万行大表把候选集合撑到无界；返回 (候选列表, 统计信息)。
    """
    candidates: set[str] = set()
    capped_columns = 0
    for sheet, frame in (raw_data or {}).items():
        if not isinstance(frame, pd.DataFrame):
            continue
        if len(str(sheet)) >= 2:
            candidates.add(str(sheet))
        for column in frame.columns:
            if len(str(column)) >= 2:
                candidates.add(str(column))
            series = frame[column]
            if not pd.api.types.is_numeric_dtype(series):
                values = series.astype(str).unique()
                if len(values) > MAX_VALUE_CANDIDATES_PER_COLUMN:
                    capped_columns += 1
                for value in values[:MAX_VALUE_CANDIDATES_PER_COLUMN]:
                    text = str(value)
                    if len(text) >= 3 and text.lower() not in ("nan", "none"):
                        candidates.add(text)
                continue
            values = pd.to_numeric(series, errors="coerce").dropna().unique()
            if len(values) > MAX_VALUE_CANDIDATES_PER_COLUMN:
                capped_columns += 1
            for value in values[:MAX_VALUE_CANDIDATES_PER_COLUMN]:
                number = float(value)
                if not math.isfinite(number) or abs(number) < 1e-9:
                    continue
                for text in (repr(number), f"{number:.10g}"):
                    digits = sum(ch.isdigit() for ch in text)
                    if len(text) >= 10 and digits >= 8:
                        candidates.add(text)
    meta = {
        "candidates_total": len(candidates),
        "value_cap_per_column": MAX_VALUE_CANDIDATES_PER_COLUMN,
        "capped_columns": capped_columns,
    }
    return sorted(candidates), meta


def _is_numeric_candidate(text: str) -> bool:
    """与 ``_contains`` 的数值分支同一分类：数字或负号开头的候选走数字匹配。"""
    return bool(text) and (text[0].isdigit() or text[0] == "-")


def _contains(text: str, needle: str) -> bool:
    """数值候选按数字边界匹配，避免 10.0000 命中 10.0000123 的前缀。"""
    if not needle:
        return False
    if needle[0].isdigit() or needle[0] == "-":
        pattern = r"(?<![\d.])" + re.escape(needle) + r"(?![\d.])"
        return re.search(pattern, text) is not None
    return needle in text


def scan_share_pack(path: str, *, raw_data: dict[str, pd.DataFrame] | None = None,
                    forbidden: list[str] | None = None) -> dict[str, Any]:
    """扫描分享包是否含原始高区分度值、表列名或禁用词（路径/人名等）。

    匹配策略（性能与检出强度平衡，结果附 ``candidates_*`` / ``capped`` 元数据）：

    - 禁用词：逐词全量匹配（数值词按数字边界）；
    - 原始数值：单遍提取包内数字 token 与候选集合比对，全量扫描；
    - 原始文本：全量 token 精确匹配 + 小文件（≤1MB）内前
      ``MAX_SUBSTRING_TEXT_CANDIDATES`` 个候选的完整子串匹配。
    """
    findings: list[dict[str, str]] = []
    try:
        with open_safe_zip(path) as (archive, inspection):
            texts = []
            for name in inspection.names():
                try:
                    data = read_member(archive, inspection, name)
                    texts.append((name, data.decode("utf-8")))
                except UnicodeDecodeError:
                    continue
    except (OSError, zipfile.BadZipFile, ArchiveSecurityError) as exc:
        return {"ok": False, "findings": [{"kind": "read-error", "value": str(exc)}]}

    forbidden_values = [str(item) for item in (forbidden or []) if str(item or "").strip()]
    candidates, meta = _leak_candidates(raw_data or {})
    numeric = {item for item in candidates if _is_numeric_candidate(item)}
    text_candidates = [item for item in candidates if not _is_numeric_candidate(item)]
    text_set = set(text_candidates)
    substring_pool = text_candidates[:MAX_SUBSTRING_TEXT_CANDIDATES]
    substring_limited = len(text_candidates) > MAX_SUBSTRING_TEXT_CANDIDATES

    def _record(kind: str, value: str, filename: str) -> None:
        findings.append({"kind": kind, "value": value, "file": filename})

    for name, text in texts:
        for needle in forbidden_values:
            if _contains(text, needle):
                _record("forbidden", needle, name)
        if numeric:
            for match in _NUMERIC_TOKEN_RE.finditer(text):
                token = match.group(0)
                if token in numeric:
                    _record("original", token, name)
                elif token.lstrip("+-") in numeric:
                    _record("original", token.lstrip("+-"), name)
        if substring_pool and len(text) <= MAX_SUBSTRING_TEXT_BYTES:
            for candidate in substring_pool:
                if _contains(text, candidate):
                    _record("original", candidate, name)
        if text_set:
            for match in _TEXT_TOKEN_RE.finditer(text):
                token = match.group(0)
                if token in text_set:
                    _record("original", token, name)
    deduped = []
    seen = set()
    for item in findings:
        key = (item["kind"], item["value"], item["file"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    large_files = (sum(1 for _name, text in texts
                       if len(text) > MAX_SUBSTRING_TEXT_BYTES)
                   if substring_pool else 0)
    return {"ok": not deduped, "findings": deduped[:20],
            "candidates_total": meta["candidates_total"],
            "candidates_numeric": len(numeric),
            "candidates_text": len(text_candidates),
            "large_files_token_only": large_files,
            "capped": (bool(meta["capped_columns"]) or substring_limited
                       or large_files > 0)}


def build_share_pack(dest: str, *, raw_data: dict[str, pd.DataFrame],
                     case: dict[str, Any] | None = None, ledger=None,
                     forbidden: list[str] | None = None, seed: int = 42,
                     app_version: str = APP_VERSION) -> dict[str, Any]:
    """生成脱敏分享包（合成数据 + 等价声明 + 事件摘要）并自动泄漏扫描。"""
    target = str(dest or "")
    if not target:
        raise ValueError("分享包导出路径不能为空")
    if not target.endswith(".zip"):
        target += ".zip"

    entries: dict[str, bytes] = {}
    sheets_statement: dict[str, Any] = {}
    for index, (_sheet, frame) in enumerate((raw_data or {}).items()):
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        synthetic, statement = synthesize_frame(frame, seed=seed + index,
                                                tolerances=DEFAULT_TOLERANCES)
        sheet_name = f"sheet_{index + 1}"
        buffer = io.StringIO()
        synthetic.to_csv(buffer, index=False)
        entries[f"synthetic/{sheet_name}.csv"] = buffer.getvalue().encode("utf-8")
        sheets_statement[sheet_name] = statement

    nested_case = (case or {}).get("case") if isinstance(case, dict) else None
    raw_case = nested_case or (case or {})
    case_summary = {
        "case_id": str(raw_case.get("id") or ""),
        "status": str(raw_case.get("status") or ""),
        "stage_count": len(raw_case.get("steps") or []),
        "phases": [step.get("phase") for step in (raw_case.get("steps") or [])
                   if isinstance(step, dict)],
    }
    entries["case_summary.json"] = _json_bytes(case_summary)
    entries["equivalence.json"] = _json_bytes({
        "schema_version": SHARE_PACK_SCHEMA_VERSION,
        "created_at": now_iso(), "app_version": app_version,
        "sheets": sheets_statement,
    })
    entries["events_summary.json"] = _json_bytes(
        ledger.export_manifest() if ledger is not None else {
            "schema_version": "1", "event_count": 0, "chain_ok": True})
    entries["README.md"] = (
        "# AKIA 脱敏分享包\n\n"
        "本包只包含**参数化合成数据**与统计等价声明，不含原始数据、路径或人员信息。\n\n"
        "- 数值列：按原始均值/标准差生成正态样本（随机种子固定，可复现）；\n"
        "- 分类列：按原始频率重标为 Cat_1..n；\n"
        "- 列名统一为 C1..Cn，表名统一为 sheet_1..k；\n"
        "- `equivalence.json` 给出每列原始/合成统计量与判定容差；\n"
        "- `events_summary.json` 只含账本事件计数与链状态，不含事件内容。\n"
    ).encode()

    manifest = {
        "schema_version": SHARE_PACK_SCHEMA_VERSION,
        "created_at": now_iso(),
        "app_version": app_version,
        "files": {name: {"sha256": _sha256_bytes(data), "size": len(data)}
                  for name, data in entries.items()},
    }
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", _json_bytes(manifest))

    scan = scan_share_pack(target, raw_data=raw_data, forbidden=forbidden)
    return {"path": target, "manifest": manifest,
            "sheets": sheets_statement, "scan": scan}


__all__ = [
    "SHARE_PACK_SCHEMA_VERSION",
    "DEFAULT_TOLERANCES",
    "build_share_pack",
    "scan_share_pack",
    "synthesize_frame",
]
