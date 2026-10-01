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

# 1.8：analyses 条目增加 credential（判定凭证）；1.6/1.7 只读兼容（无凭证字段）
VERSION = "1.8"
RECENT_MAX = 8


class ProjectManager:
    """AKIA 项目文件 (.qap) 管理器"""

    @staticmethod
    def save_project(path: str, raw_data: dict[str, pd.DataFrame],
                     analyses: dict[int, dict[str, Any]],
                     chart_bytes: dict[str, bytes],
                     annotations: str = "",
                     project_context: dict[str, Any] | None = None,
                     cases: list[dict[str, Any]] | None = None) -> str:
        """保存项目为 .qap 文件。

        raw_data: {sheet_name: DataFrame}
        analyses: {tab_idx: {analysis_type, params, result}}
        chart_bytes: {label: PNG bytes}
        project_context: {project_name, characteristics, fmea_items, ...} (可选)
        cases: 改善案例 schema v0 dict 列表 (可选；写入 cases.json)
        """
        if not path.endswith(".qap"):
            path += ".qap"

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
            "cases": [case dict, ...],   # schema v0；旧文件为 []
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
    """共享目录首次使用时迁移旧品牌数据（保留旧目录）。"""
    if SHARED_DIR != _DEFAULT_SHARED_DIR:   # 测试/自定义目录不做旧数据搬迁
        return
    migrate_legacy_dir(legacy_home_dir("shared"), SHARED_DIR)


class SharedProjectManager:
    """团队共享 .qap 项目管理"""

    @staticmethod
    def save_shared(path: str, raw_data: dict[str, pd.DataFrame],
                    analyses: dict[int, dict], chart_bytes: dict[str, bytes],
                    department: str, annotations: str = "",
                    project_context: dict[str, Any] | None = None) -> str:
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
        return ProjectManager.save_project(full_path, raw_data, analyses, chart_bytes, annotations, project_context)

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
