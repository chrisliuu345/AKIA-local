"""AKIA 本地数据资产 `.qda` v1 — 可校验、可迁移的统一 ZIP 契约。

与完整工作会话不同，数据资产聚焦可长期迁移的数据与领域记录。特性、批次、
标准工时统一写入 ``assets.json``，后续版本继续扩展该段而不另起文件格式。
本模块无 Qt，读取全程使用共享归档资源边界。
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import APP_VERSION
from core.archive_safety import open_safe_zip, read_member
from core.improvement_case import CASE_SCHEMA_VERSION
from core.project_manager import _payload_segment, _sanitize_for_json
from core.time_utils import now_iso

DATA_ASSET_SCHEMA_VERSION = "1.0"
DATA_ASSET_KIND = "akia-local-data-asset"
DATA_ASSET_EXTENSION = ".qda"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(_sanitize_for_json(payload), ensure_ascii=False,
                      separators=(",", ":"), default=str).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl_bytes(items: list[Any]) -> bytes:
    return b"".join(_json_bytes(item) + b"\n" for item in items)


def _object_payload(value: Any, name: str) -> Any:
    if value is None or isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [item.to_dict() if hasattr(item, "to_dict") else item
                for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if name in ("evidence_events", "measurements") and hasattr(value, "events"):
        return [event.to_dict() for event in value.events]
    if name == "measurements" and hasattr(value, "to_dicts"):
        return value.to_dicts()
    raise TypeError(f"{name} 需为 dict/list 或支持序列化的领域对象")


def export_data_asset(dest: str | Path, *, raw_data: dict[str, pd.DataFrame] | None = None,
                      analyses: dict[int, dict[str, Any]] | None = None,
                      chart_bytes: dict[str, bytes] | None = None,
                      annotations: str = "", project_context: Any = None,
                      cases: list[dict[str, Any]] | None = None, standards: Any = None,
                      evidence_events: Any = None, measurements: Any = None,
                      sampling: Any = None, gauge_studies: Any = None,
                      benefits: Any = None, skills: Any = None,
                      app_version: str = APP_VERSION) -> dict[str, Any]:
    """导出数据资产并立即执行完整读取校验。"""
    target = Path(dest)
    if target.suffix.lower() != DATA_ASSET_EXTENSION:
        target = Path(f"{target}{DATA_ASSET_EXTENSION}")
    frames = dict(raw_data or {})
    invalid = [name for name, frame in frames.items() if not isinstance(frame, pd.DataFrame)]
    if invalid:
        raise TypeError(f"以下工作表不是 DataFrame: {invalid}")

    context = _object_payload(project_context, "project_context") or {}
    standards_payload = _object_payload(standards, "standards")
    if standards_payload is None:
        standards_payload = context.get("standards") if isinstance(context, dict) else None
    sampling_payload = _payload_segment(sampling, "sampling")
    evidence_payload = _object_payload(evidence_events, "evidence_events") or []
    measurement_payload = _object_payload(measurements, "measurements") or []

    entries: dict[str, bytes] = {}
    sheets = []
    for index, (name, frame) in enumerate(frames.items(), 1):
        member = f"data/sheet_{index}.csv"
        buffer = io.StringIO()
        frame.to_csv(buffer, index=False)
        entries[member] = buffer.getvalue().encode("utf-8")
        sheets.append({"name": str(name), "file": member})

    charts = []
    for index, (label, data) in enumerate((chart_bytes or {}).items(), 1):
        member = f"charts/chart_{index}.png"
        entries[member] = bytes(data)
        charts.append({"name": str(label), "file": member})

    optional_json = {
        "analyses.json": {str(key): value for key, value in (analyses or {}).items()},
        "context.json": context,
        "cases.json": {"schema_version": CASE_SCHEMA_VERSION,
                       "cases": list(cases or [])},
        "standards.json": standards_payload,
        "sampling.json": sampling_payload,
        "gauge_studies.json": _payload_segment(gauge_studies, "gauge_studies"),
        "benefits.json": _payload_segment(benefits, "benefits"),
        "skills.json": _payload_segment(skills, "skills"),
    }
    for name, payload in optional_json.items():
        if payload is not None:
            entries[name] = _json_bytes(payload)
    if evidence_payload:
        entries["evidence/events.jsonl"] = _jsonl_bytes(evidence_payload)
    if measurement_payload:
        entries["measurements.jsonl"] = _jsonl_bytes(measurement_payload)
    if annotations:
        entries["annotations.txt"] = str(annotations).encode("utf-8")

    standard_records = (standards_payload or {}).get("records", [])
    characteristics = context.get("characteristics", []) if isinstance(context, dict) else []
    lots = (sampling_payload or {}).get("lots", [])
    assets = {
        "schema_version": DATA_ASSET_SCHEMA_VERSION,
        "characteristics": characteristics,
        "lots": lots,
        "standard_times": [record for record in standard_records
                           if record.get("object_type") == "standard_time"],
        # 后续领域记录在同一契约内增加命名段，保持旧读取器可忽略扩展。
        "extensions": {},
    }
    entries["assets.json"] = _json_bytes(assets)

    manifest = {
        "schema_version": DATA_ASSET_SCHEMA_VERSION,
        "kind": DATA_ASSET_KIND,
        "created_at": now_iso(),
        "app_version": app_version,
        "sheet_count": len(sheets),
        "analysis_count": len(analyses or {}),
        "case_count": len(cases or []),
        "evidence_event_count": len(evidence_payload),
        "measurement_count": len(measurement_payload),
        "asset_counts": {
            "characteristics": len(characteristics),
            "lots": len(lots),
            "standard_times": len(assets["standard_times"]),
        },
        "sheets": sheets,
        "charts": charts,
        "files": {name: {"sha256": _sha256(data), "size": len(data)}
                  for name, data in entries.items()},
    }
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", _json_bytes(manifest))
    return {"path": str(target), "manifest": manifest,
            "verify": verify_data_asset(target)}


def _load_json(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


def verify_data_asset(path: str | Path) -> dict[str, Any]:
    """独立校验格式、文件集合和逐项哈希，不恢复任何业务对象。"""
    try:
        with open_safe_zip(path) as (archive, inspection):
            names = set(inspection.names())
            if "manifest.json" not in names:
                raise ValueError("数据资产缺少 manifest.json")
            manifest = _load_json(read_member(
                archive, inspection, "manifest.json", max_bytes=2 * 1024 ** 2))
            if not isinstance(manifest, dict):
                raise ValueError("数据资产 manifest 必须为对象")
            if manifest.get("kind") != DATA_ASSET_KIND:
                raise ValueError("不是 AKIA 本地数据资产")
            if str(manifest.get("schema_version", "")).split(".", 1)[0] != "1":
                raise ValueError(f"不支持的数据资产 schema: {manifest.get('schema_version')}")
            files = manifest.get("files")
            if not isinstance(files, dict):
                raise ValueError("manifest.files 必须为对象")
            expected = set(files)
            if expected != names - {"manifest.json"}:
                raise ValueError("数据资产文件集合与 manifest 不一致")
            for name, metadata in files.items():
                if not isinstance(metadata, dict):
                    raise ValueError(f"数据资产文件元数据无效: {name}")
                data = read_member(archive, inspection, name)
                if len(data) != metadata.get("size") or _sha256(data) != metadata.get("sha256"):
                    raise ValueError(f"数据资产文件校验失败: {name}")
            return {"ok": True, "manifest": manifest, "problems": []}
    except (OSError, ValueError, TypeError, zipfile.BadZipFile) as exc:
        return {"ok": False, "manifest": {}, "problems": [str(exc)]}


def load_data_asset(path: str | Path) -> dict[str, Any]:
    """校验并恢复为与 ``ProjectManager.load_project`` 对齐的项目载荷。"""
    source = Path(path)
    verification = verify_data_asset(source)
    if not verification.get("ok"):
        raise ValueError("读取数据资产失败: " + "; ".join(verification["problems"]))
    manifest = verification["manifest"]
    raw_data: dict[str, pd.DataFrame] = {}
    analyses: dict[int, dict] = {}
    chart_bytes: dict[str, bytes] = {}
    payload: dict[str, Any] = {
        "manifest": manifest,
        "raw_data": raw_data,
        "analyses": analyses,
        "chart_bytes": chart_bytes,
        "annotations": "",
        "project_context": None,
        "cases": [],
        "standards": None,
        "evidence_events": [],
        "evidence_recovered": False,
        "evidence_errors": [],
        "measurements": [],
        "measurement_recovered": False,
        "measurement_errors": [],
        "sampling": None,
        "gauge_studies": None,
        "benefits": None,
        "skills": None,
        "assets": {},
    }
    json_fields = {
        "analyses.json": "analyses",
        "context.json": "project_context",
        "cases.json": "cases",
        "standards.json": "standards",
        "sampling.json": "sampling",
        "gauge_studies.json": "gauge_studies",
        "benefits.json": "benefits",
        "skills.json": "skills",
        "assets.json": "assets",
    }
    with open_safe_zip(source) as (archive, inspection):
        cached = {name: read_member(archive, inspection, name)
                  for name in inspection.names()}
    for item in manifest.get("sheets", []):
        raw_data[str(item["name"])] = pd.read_csv(io.BytesIO(cached[item["file"]]))
    for item in manifest.get("charts", []):
        chart_bytes[str(item["name"])] = cached[item["file"]]
    for name, field in json_fields.items():
        if name not in cached:
            continue
        value = _load_json(cached[name])
        if field == "analyses":
            analyses.update({int(key): item for key, item in value.items()})
        elif field == "cases" and isinstance(value, dict):
            payload[field] = value.get("cases") or []
        else:
            payload[field] = value
    if "evidence/events.jsonl" in cached:
        from core.evidence_ledger import EvidenceLedger
        ledger = EvidenceLedger.from_bytes(cached["evidence/events.jsonl"])
        payload["evidence_events"] = [event.to_dict() for event in ledger.events]
        payload["evidence_recovered"] = ledger.recovered_truncation
        payload["evidence_errors"] = list(ledger.load_errors)
    if "measurements.jsonl" in cached:
        from core.measurement_store import MeasurementStore
        store = MeasurementStore.from_bytes(cached["measurements.jsonl"])
        payload["measurements"] = store.to_dicts()
        payload["measurement_recovered"] = store.recovered_truncation
        payload["measurement_errors"] = list(store.load_errors)
    if "annotations.txt" in cached:
        payload["annotations"] = cached["annotations.txt"].decode("utf-8")
    return payload


def migrate_project_to_asset(project_path: str | Path, dest: str | Path) -> dict[str, Any]:
    """把现有 `.qap` 全量迁移为 `.qda`，不修改最近项目记录。"""
    from core.project_manager import ProjectManager
    project = ProjectManager.load_project(str(project_path), record_recent=False)
    return export_data_asset(
        dest, raw_data=project["raw_data"], analyses=project["analyses"],
        chart_bytes=project["chart_bytes"], annotations=project["annotations"],
        project_context=project["project_context"], cases=project["cases"],
        standards=project["standards"], evidence_events=project["evidence_events"],
        measurements=project["measurements"], sampling=project["sampling"],
        gauge_studies=project["gauge_studies"], benefits=project["benefits"],
        skills=project["skills"])


__all__ = [
    "DATA_ASSET_EXTENSION", "DATA_ASSET_KIND", "DATA_ASSET_SCHEMA_VERSION",
    "export_data_asset", "load_data_asset", "migrate_project_to_asset",
    "verify_data_asset",
]
