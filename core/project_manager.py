"""
.qap 项目文件管理 — zip 打包: 数据 + 分析结果 + 图表 + 元信息
"""

import json
import os
import io
import zipfile
from datetime import datetime
from typing import Any
from PySide6.QtCore import QSettings

import pandas as pd

from core.improvement_case import CASE_SCHEMA_VERSION
from core.legacy import legacy_home_dir, migrate_legacy_dir

# 2.0：新增 sampling.json / gauge_studies.json / benefits.json / skills.json（v4.4.0 B0）；
# 1.6~1.9 只读兼容（无对应段时按空处理）
VERSION = "2.0"
RECENT_MAX = 8


def _payload_segment(value: Any, name: str) -> dict[str, Any] | None:
    """可选段载荷归一化：None → None；带 to_dict() 的对象直接用；dict 原样。"""
    if value is None:
        return None
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    elif isinstance(value, dict):
        payload = value
    else:
        raise TypeError(f"{name} 需为 dict 或带 to_dict() 的对象")
    return _sanitize_for_json(payload)


def _count_items(payload: dict[str, Any] | None, key: str) -> int:
    """段载荷中的条目计数（非列表或缺失按 0）。"""
    if not isinstance(payload, dict):
        return 0
    items = payload.get(key) or []
    return len(items) if isinstance(items, list) else 0


class ProjectManager:
    """AKIA 项目文件 (.qap) 管理器"""

    @staticmethod
    def save_project(path: str, raw_data: dict[str, pd.DataFrame],
                     analyses: dict[int, dict[str, Any]],
                     chart_bytes: dict[str, bytes],
                     annotations: str = "",
                     project_context: dict[str, Any] | None = None,
                     cases: list[dict[str, Any]] | None = None,
                     standards: Any = None,
                     evidence_events: Any = None,
                     measurements: Any = None,
                     sampling: Any = None,
                     gauge_studies: Any = None,
                     benefits: Any = None,
                     skills: Any = None) -> str:
        """保存项目为 .qap 文件。

        raw_data: {sheet_name: DataFrame}
        analyses: {tab_idx: {analysis_type, params, result}}
        chart_bytes: {label: PNG bytes}
        project_context: {project_name, characteristics, fmea_items, ...} (可选)
        cases: 改善案例 dict 列表 (可选；写入 cases.json)
        standards: StandardRegistry | dict (可选；写入 standards.json)
        evidence_events: EvidenceLedger | list[dict] (可选；写入 evidence/events.jsonl)
        measurements: MeasurementStore | list[MeasurementEvent | dict] (可选；
                      写入 measurements.jsonl)
        sampling: 抽样域载荷 dict | 带 to_dict() 的对象（可选；写入 sampling.json）
        gauge_studies: 量具在线研究载荷（可选；写入 gauge_studies.json）
        benefits: 收益账本载荷（可选；写入 benefits.json）
        skills: 技能矩阵载荷（可选；写入 skills.json）
        """
        if not path.endswith(".qap"):
            path += ".qap"

        if standards is None:
            standards_payload = None
        elif hasattr(standards, "to_dict"):
            standards_payload = standards.to_dict()
        elif isinstance(standards, dict):
            standards_payload = standards
        else:
            raise TypeError("standards 需为 StandardRegistry 或 dict")

        if evidence_events is None:
            evidence_payload: list[dict[str, Any]] | None = None
        elif hasattr(evidence_events, "events"):
            evidence_payload = [event.to_dict() for event in evidence_events.events]
        elif isinstance(evidence_events, list):
            evidence_payload = list(evidence_events)
        else:
            raise TypeError("evidence_events 需为 EvidenceLedger 或 list")

        if measurements is None:
            measurement_payload: list[dict[str, Any]] | None = None
        elif hasattr(measurements, "events"):
            measurement_payload = [event.to_dict() for event in measurements.events]
        elif isinstance(measurements, list):
            measurement_payload = list(measurements)
        else:
            raise TypeError("measurements 需为 MeasurementStore 或 list")

        sampling_payload = _payload_segment(sampling, "sampling")
        gauge_payload = _payload_segment(gauge_studies, "gauge_studies")
        benefits_payload = _payload_segment(benefits, "benefits")
        skills_payload = _payload_segment(skills, "skills")

        manifest = {
            "version": VERSION,
            "created": datetime.now().isoformat(),
            "sheet_count": len(raw_data),
            "analysis_count": len(analyses),
            "credential_count": sum(1 for a in analyses.values()
                                    if isinstance(a, dict) and a.get("credential")),
            "tab_indices": list(analyses.keys()),
            "has_context": project_context is not None,
            "case_count": len(cases or []),
            "has_cases": bool(cases),
            "standard_count": len((standards_payload or {}).get("records", [])),
            "has_standards": standards_payload is not None,
            "evidence_event_count": len(evidence_payload or []),
            "has_evidence": bool(evidence_payload),
            "measurement_count": len(measurement_payload or []),
            "has_measurements": bool(measurement_payload),
            "has_sampling": sampling_payload is not None,
            "sampling_lot_count": _count_items(sampling_payload, "lots"),
            "has_gauge_studies": gauge_payload is not None,
            "gauge_study_count": _count_items(gauge_payload, "studies"),
            "has_benefits": benefits_payload is not None,
            "benefit_count": _count_items(benefits_payload, "records"),
            "has_skills": skills_payload is not None,
            "skill_entry_count": _count_items(skills_payload, "entries"),
        }

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            for sname, df in raw_data.items():
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                zf.writestr(f"data/{_safe_name(sname)}.csv", buf.getvalue())

            analyses_serializable = {}
            for idx, a in analyses.items():
                entry = {
                    "analysis_type": a.get("analysis_type", ""),
                    "params": a.get("params", {}),
                    "result": _sanitize_for_json(a.get("result", {})),
                }
                if a.get("credential"):
                    entry["credential"] = _sanitize_for_json(a["credential"])
                analyses_serializable[str(idx)] = entry
            zf.writestr("analyses.json",
                        json.dumps(analyses_serializable, indent=2, ensure_ascii=False, default=str))

            if project_context:
                zf.writestr("context.json",
                            json.dumps(_sanitize_for_json(project_context), indent=2, ensure_ascii=False, default=str))

            if cases is not None:
                zf.writestr("cases.json", json.dumps({
                    "schema_version": CASE_SCHEMA_VERSION,
                    "cases": _sanitize_for_json(cases),
                }, indent=2, ensure_ascii=False, default=str))

            if standards_payload is not None:
                zf.writestr("standards.json",
                            json.dumps(_sanitize_for_json(standards_payload),
                                       indent=2, ensure_ascii=False, default=str))

            if evidence_payload:
                lines = "".join(
                    json.dumps(_sanitize_for_json(event), ensure_ascii=False,
                               separators=(",", ":"), default=str) + "\n"
                    for event in evidence_payload)
                zf.writestr("evidence/events.jsonl", lines)

            if measurement_payload:
                lines = "".join(
                    json.dumps(_sanitize_for_json(event), ensure_ascii=False,
                               separators=(",", ":"), default=str) + "\n"
                    for event in measurement_payload)
                zf.writestr("measurements.jsonl", lines)

            for segment, payload in (("sampling.json", sampling_payload),
                                     ("gauge_studies.json", gauge_payload),
                                     ("benefits.json", benefits_payload),
                                     ("skills.json", skills_payload)):
                if payload is not None:
                    zf.writestr(segment, json.dumps(
                        payload, indent=2, ensure_ascii=False, default=str))

            for label, png_data in chart_bytes.items():
                zf.writestr(f"charts/{_safe_name(label)}.png", png_data)

            if annotations:
                zf.writestr("annotations.txt", annotations)

        ProjectManager.add_recent(path, os.path.basename(path))
        return path

    @staticmethod
    def load_project(path: str) -> dict[str, Any]:
        """从 .qap 加载项目，返回完整上下文字典。

        Returns: {
            "manifest": dict,
            "raw_data": {sheet_name: DataFrame},
            "analyses": {tab_idx: {...}},
            "chart_bytes": {label: PNG bytes},
            "annotations": str,
            "project_context": dict | None,
            "cases": [case dict, ...],   # CaseWorkflow 包装或裸 ImprovementCase（v1/v0）
            "standards": dict | None,    # 标准版本注册表；旧文件为 None
            "evidence_events": [event dict, ...],  # 证据账本；旧文件为 []
            "evidence_recovered": bool,  # 是否恢复过崩溃遗留的半行
            "evidence_errors": [str, ...],
            "measurements": [event dict, ...],  # 测量事件；旧文件为 []
            "measurement_recovered": bool,
            "measurement_errors": [str, ...],
            "sampling": dict | None,       # 抽样域（方案/批/转移状态）；旧文件为 None
            "gauge_studies": dict | None,  # 量具在线研究；旧文件为 None
            "benefits": dict | None,       # 收益账本；旧文件为 None
            "skills": dict | None,         # 技能矩阵；旧文件为 None
        }
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"项目文件不存在: {path}")

        raw_data: dict[str, pd.DataFrame] = {}
        analyses: dict[int, dict] = {}
        chart_bytes: dict[str, bytes] = {}
        manifest: dict = {}
        annotations = ""
        project_context = None
        cases: list[dict] = []
        standards = None
        evidence_events: list[dict] = []
        evidence_recovered = False
        evidence_errors: list[str] = []
        measurements: list[dict] = []
        measurement_recovered = False
        measurement_errors: list[str] = []
        sampling = None
        gauge_studies = None
        benefits = None
        skills = None

        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name == "manifest.json":
                    manifest = json.loads(zf.read(name).decode("utf-8"))
                elif name.startswith("data/") and name.endswith(".csv"):
                    sname = name[5:-4]
                    df = pd.read_csv(io.BytesIO(zf.read(name)))
                    raw_data[sname] = df
                elif name == "analyses.json":
                    raw = json.loads(zf.read(name).decode("utf-8"))
                    for k, v in raw.items():
                        analyses[int(k)] = v
                elif name == "context.json":
                    project_context = json.loads(zf.read(name).decode("utf-8"))
                elif name == "cases.json":
                    payload = json.loads(zf.read(name).decode("utf-8"))
                    if isinstance(payload, dict):
                        cases = payload.get("cases") or []
                    elif isinstance(payload, list):
                        cases = payload
                elif name == "standards.json":
                    standards = json.loads(zf.read(name).decode("utf-8"))
                elif name == "evidence/events.jsonl":
                    from core.evidence_ledger import EvidenceLedger

                    ledger = EvidenceLedger.from_bytes(zf.read(name))
                    evidence_events = [event.to_dict() for event in ledger.events]
                    evidence_recovered = ledger.recovered_truncation
                    evidence_errors = list(ledger.load_errors)
                elif name == "measurements.jsonl":
                    from core.measurement_store import MeasurementStore

                    store = MeasurementStore.from_bytes(zf.read(name))
                    measurements = store.to_dicts()
                    measurement_recovered = store.recovered_truncation
                    measurement_errors = list(store.load_errors)
                elif name == "sampling.json":
                    sampling = json.loads(zf.read(name).decode("utf-8"))
                elif name == "gauge_studies.json":
                    gauge_studies = json.loads(zf.read(name).decode("utf-8"))
                elif name == "benefits.json":
                    benefits = json.loads(zf.read(name).decode("utf-8"))
                elif name == "skills.json":
                    skills = json.loads(zf.read(name).decode("utf-8"))
                elif name.startswith("charts/") and name.endswith(".png"):
                    label = name[7:-4]
                    chart_bytes[label] = zf.read(name)
                elif name == "annotations.txt":
                    annotations = zf.read(name).decode("utf-8")

        ProjectManager.add_recent(path, os.path.basename(path))
        return {
            "manifest": manifest,
            "raw_data": raw_data,
            "analyses": analyses,
            "chart_bytes": chart_bytes,
            "annotations": annotations,
            "project_context": project_context,
            "cases": cases,
            "standards": standards,
            "evidence_events": evidence_events,
            "evidence_recovered": evidence_recovered,
            "evidence_errors": evidence_errors,
            "measurements": measurements,
            "measurement_recovered": measurement_recovered,
            "measurement_errors": measurement_errors,
            "sampling": sampling,
            "gauge_studies": gauge_studies,
            "benefits": benefits,
            "skills": skills,
        }

    @staticmethod
    def get_project_info(path: str) -> dict[str, Any]:
        """仅读取 manifest，不解压全部内容"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"项目文件不存在: {path}")
        with zipfile.ZipFile(path, "r") as zf:
            if "manifest.json" in zf.namelist():
                return json.loads(zf.read("manifest.json").decode("utf-8"))
        return {}

    @staticmethod
    def recent_projects() -> list[dict[str, str]]:
        settings = QSettings("AKIA", "RecentProjects")
        raw = settings.value("list", "[]")
        try:
            return json.loads(raw)
        except Exception:
            return []

    @staticmethod
    def add_recent(path: str, name: str):
        recent = ProjectManager.recent_projects()
        recent = [r for r in recent if r.get("path") != path]
        recent.insert(0, {"path": path, "name": name, "opened": datetime.now().isoformat()})
        recent = recent[:RECENT_MAX]
        settings = QSettings("AKIA", "RecentProjects")
        settings.setValue("list", json.dumps(recent, ensure_ascii=False))


def _safe_name(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace(":", "_")


def _sanitize_for_json(obj: Any) -> Any:
    """递归清理 numpy/pandas 类型使其可 JSON 序列化"""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if pd.isna(obj) if isinstance(obj, (float,)) else False:
        return None
    return obj


_DEFAULT_SHARED_DIR = os.path.join(os.path.expanduser("~"), ".akia_shared")
SHARED_DIR = _DEFAULT_SHARED_DIR
PUBLIC_DEPT = "公共"


def _ensure_shared_dir() -> None:
    """共享目录首次使用时迁移旧版数据（保留旧目录）。"""
    if SHARED_DIR != _DEFAULT_SHARED_DIR:   # 测试/自定义目录不做旧数据搬迁
        return
    migrate_legacy_dir(legacy_home_dir("shared"), SHARED_DIR)


class SharedProjectManager:
    """团队共享 .qap 项目管理"""

    @staticmethod
    def save_shared(path: str, raw_data: dict[str, pd.DataFrame],
                    analyses: dict[int, dict], chart_bytes: dict[str, bytes],
                    department: str, annotations: str = "",
                    project_context: dict[str, Any] | None = None,
                    cases: list[dict[str, Any]] | None = None,
                    standards: Any = None,
                    measurements: Any = None,
                    evidence_events: Any = None,
                    sampling: Any = None,
                    gauge_studies: Any = None,
                    benefits: Any = None,
                    skills: Any = None) -> str:
        """保存项目到共享目录"""
        _ensure_shared_dir()
        dept_norm = (department or PUBLIC_DEPT).replace("\\", "/")
        safe_dept = os.path.basename(dept_norm)
        dept_dir = os.path.join(SHARED_DIR, safe_dept)
        real_dept_dir = os.path.realpath(dept_dir)
        real_shared_dir = os.path.realpath(SHARED_DIR)
        if not real_dept_dir.startswith(real_shared_dir + os.sep):
            raise ValueError(f"非法的部门目录: {department}")
        os.makedirs(dept_dir, exist_ok=True)
        basename = os.path.basename(path)
        if not basename.endswith(".qap"):
            basename += ".qap"
        full_path = os.path.join(dept_dir, basename)
        return ProjectManager.save_project(
            full_path, raw_data, analyses, chart_bytes, annotations,
            project_context, cases=cases, standards=standards,
            measurements=measurements, evidence_events=evidence_events,
            sampling=sampling, gauge_studies=gauge_studies,
            benefits=benefits, skills=skills)

    @staticmethod
    def list_shared(department: str = "", role: str = "") -> list[dict[str, str]]:
        """列出共享项目。admin 看到全部；其他人看到本部门+公共。"""
        _ensure_shared_dir()
        projects = []
        if not os.path.exists(SHARED_DIR):
            return projects
        for dept_name in os.listdir(SHARED_DIR):
            dept_path = os.path.join(SHARED_DIR, dept_name)
            if not os.path.isdir(dept_path):
                continue
            if role != "admin":
                if department and dept_name not in (department, PUBLIC_DEPT):
                    continue
                if not department and dept_name != PUBLIC_DEPT:
                    continue
            for fname in os.listdir(dept_path):
                if fname.endswith(".qap"):
                    full = os.path.join(dept_path, fname)
                    info = ProjectManager.get_project_info(full)
                    projects.append({
                        "path": full, "name": fname, "department": dept_name,
                        "created": info.get("created", ""), "version": info.get("version", ""),
                    })
        projects.sort(key=lambda x: x.get("created", ""), reverse=True)
        return projects

    @staticmethod
    def load_shared(path: str) -> dict[str, Any]:
        """加载共享项目（与 load_project 相同）"""
        return ProjectManager.load_project(path)
