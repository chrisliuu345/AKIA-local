"""证据包导出与独立校验（v4.3.0 B4-3）。

证据包 = 案例 + 账本 + 凭证 + 标准 + 测量摘要（+ 可选报告）；
默认**不含原始数据**。`verify_evidence_pack` 可在不加载主程序的情况下独立校验：
逐文件哈希 + 账本哈希链 + 未登记文件检查。

本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any

from config.settings import APP_VERSION
from core.time_utils import now_iso

EVIDENCE_PACK_SCHEMA_VERSION = "1"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                      default=str).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_"
                   for ch in str(name or "sheet"))[:80] or "sheet"


def export_evidence_pack(dest: str, *, case: dict[str, Any] | None = None,
                         case_markdown: str = "",
                         analyses: dict[int, dict[str, Any]] | None = None,
                         ledger=None, standards: dict[str, Any] | None = None,
                         measurements=None, report_paths: list[str] | None = None,
                         raw_data: dict[str, Any] | None = None,
                         include_raw_data: bool = False,
                         app_version: str = APP_VERSION) -> dict[str, Any]:
    """导出 `.zip` 证据包并立即校验；返回 {path, manifest, verify}。"""
    target = str(dest or "")
    if not target:
        raise ValueError("证据包导出路径不能为空")
    if not target.endswith(".zip"):
        target += ".zip"

    entries: dict[str, bytes] = {}
    raw_case = case or {}
    if not isinstance(raw_case, dict):
        raw_case = {}
    nested_case = raw_case.get("case")
    nested_case = nested_case if isinstance(nested_case, dict) else None
    case_id = str((nested_case or {}).get("id") or raw_case.get("id") or "")
    entries["case.json"] = _json_bytes(raw_case)
    if case_markdown:
        entries["case.md"] = str(case_markdown).encode("utf-8")
    entries["events.jsonl"] = (ledger.to_jsonl() if ledger is not None else "").encode("utf-8")

    credentials = []
    for key, analysis in (analyses or {}).items():
        if not isinstance(analysis, dict) or not analysis.get("credential"):
            continue
        credentials.append({
            "tab": int(key) if str(key).lstrip("-").isdigit() else str(key),
            "analysis_type": analysis.get("analysis_type", ""),
            "credential": analysis.get("credential"),
            "rerun_diff": analysis.get("rerun_diff"),
        })
    entries["credentials.json"] = _json_bytes(
        {"schema_version": "1", "analyses": credentials})

    if standards:
        entries["standards.json"] = _json_bytes(standards)
    if measurements:
        items = [m.to_dict() if hasattr(m, "to_dict") else m for m in measurements]
        entries["measurements.jsonl"] = b"".join(_json_bytes(item) + b"\n"
                                                 for item in items)
    for report in report_paths or []:
        report_path = Path(report)
        if report_path.is_file():
            entries[f"reports/{_safe_name(report_path.name)}"] = report_path.read_bytes()
    if include_raw_data and raw_data:
        for sheet, frame in raw_data.items():
            buffer = io.StringIO()
            frame.to_csv(buffer, index=False)
            entries[f"raw/{_safe_name(sheet)}.csv"] = buffer.getvalue().encode("utf-8")

    chain = ledger.verify() if ledger is not None else None
    manifest = {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "created_at": now_iso(),
        "app_version": app_version,
        "case_id": case_id,
        "includes_raw_data": bool(include_raw_data and raw_data),
        "event_count": len(ledger) if ledger is not None else 0,
        "credential_count": len(credentials),
        "ledger_chain": chain,
        "files": {
            name: {"sha256": _sha256_bytes(data), "size": len(data)}
            for name, data in entries.items()
        },
    }

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", _json_bytes(manifest))

    return {"path": target, "manifest": manifest,
            "verify": verify_evidence_pack(target)}


def verify_evidence_pack(path: str) -> dict[str, Any]:
    """独立校验证据包：manifest 完整性 + 逐文件哈希 + 账本链。"""
    problems: list[str] = []
    manifest: dict[str, Any] = {}
    chain: dict[str, Any] = {"ok": None, "reason": "无账本"}
    if not os.path.exists(path):
        return {"ok": False, "problems": ["证据包不存在"], "manifest": {},
                "ledger_chain": chain}
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names:
                return {"ok": False, "problems": ["缺少 manifest.json"],
                        "manifest": {}, "ledger_chain": chain}
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            files = manifest.get("files") or {}
            for name, meta in files.items():
                if name not in names:
                    problems.append(f"缺少文件: {name}")
                    continue
                data = archive.read(name)
                if _sha256_bytes(data) != meta.get("sha256"):
                    problems.append(f"哈希不匹配: {name}")
                elif len(data) != meta.get("size"):
                    problems.append(f"大小不匹配: {name}")
            extra = sorted(names - set(files) - {"manifest.json"})
            if extra:
                problems.append("未登记文件: " + ", ".join(extra[:5]))
            if "events.jsonl" in names:
                from core.evidence_ledger import EvidenceLedger

                ledger = EvidenceLedger.from_bytes(archive.read("events.jsonl"))
                chain = ledger.verify()
                if not chain.get("ok"):
                    problems.append("账本校验失败: " + str(chain.get("reason", "")))
    except (OSError, zipfile.BadZipFile, ValueError, TypeError,
            AttributeError) as exc:  # manifest 结构异常也按"无法读取"返回
        return {"ok": False, "problems": [f"证据包无法读取: {exc}"],
                "manifest": manifest, "ledger_chain": chain}
    return {"ok": not problems, "problems": problems,
            "manifest": manifest, "ledger_chain": chain}


def read_evidence_pack(path: str) -> dict[str, Any]:
    """读取证据包内容（不落盘解压），供证据视图/审计工具使用。"""
    with zipfile.ZipFile(path, "r") as archive:
        payload: dict[str, Any] = {"manifest": {}}
        for name in archive.namelist():
            data = archive.read(name)
            if name.endswith(".json"):
                payload[name] = json.loads(data.decode("utf-8"))
            elif name.endswith((".jsonl", ".md", ".csv")):
                payload[name] = data.decode("utf-8", errors="replace")
            else:
                payload[name] = data
    payload["manifest"] = payload.get("manifest.json", {})
    return payload
