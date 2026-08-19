"""
.qap 项目文件管理 — zip 打包: 数据 + 分析结果 + 图表 + 元信息
"""

import json
import os
import io
import zipfile
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from PySide6.QtCore import QSettings

import pandas as pd

VERSION = "1.5"
RECENT_MAX = 8


class ProjectManager:
    """QA-Tool 项目文件 (.qap) 管理器"""

    # ── 保存 ──────────────────────────────────────────
    @staticmethod
    def save_project(path: str, raw_data: Dict[str, pd.DataFrame],
                     analyses: Dict[int, Dict[str, Any]],
                     chart_bytes: Dict[str, bytes],
                     annotations: str = "") -> str:
        """保存项目为 .qap 文件。

        raw_data: {sheet_name: DataFrame}
        analyses: {tab_idx: {analysis_type, params, result}}
        chart_bytes: {label: PNG bytes}
        """
        if not path.endswith(".qap"):
            path += ".qap"

        manifest = {
            "version": VERSION,
            "created": datetime.now().isoformat(),
            "sheet_count": len(raw_data),
            "analysis_count": len(analyses),
            "tab_indices": list(analyses.keys()),
        }

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            # manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            # data — 每个 sheet 存为 CSV
            for sname, df in raw_data.items():
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                zf.writestr(f"data/{_safe_name(sname)}.csv", buf.getvalue())

            # analyses
            analyses_serializable = {}
            for idx, a in analyses.items():
                analyses_serializable[str(idx)] = {
                    "analysis_type": a.get("analysis_type", ""),
                    "params": a.get("params", {}),
                    "result": _sanitize_for_json(a.get("result", {})),
                }
            zf.writestr("analyses.json",
                        json.dumps(analyses_serializable, indent=2, ensure_ascii=False, default=str))

            # charts
            for label, png_data in chart_bytes.items():
                zf.writestr(f"charts/{_safe_name(label)}.png", png_data)

            # annotations
            if annotations:
                zf.writestr("annotations.txt", annotations)

        ProjectManager.add_recent(path, os.path.basename(path))
        return path

    # ── 加载 ──────────────────────────────────────────
    @staticmethod
    def load_project(path: str) -> Dict[str, Any]:
        """从 .qap 加载项目，返回完整上下文字典。

        Returns: {
            "manifest": dict,
            "raw_data": {sheet_name: DataFrame},
            "analyses": {tab_idx: {...}},
            "chart_bytes": {label: PNG bytes},
            "annotations": str,
        }
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"项目文件不存在: {path}")

        raw_data: Dict[str, pd.DataFrame] = {}
        analyses: Dict[int, Dict] = {}
        chart_bytes: Dict[str, bytes] = {}
        manifest: Dict = {}
        annotations = ""

        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name == "manifest.json":
                    manifest = json.loads(zf.read(name).decode("utf-8"))
                elif name.startswith("data/") and name.endswith(".csv"):
                    sname = name[5:-4]  # strip "data/" and ".csv"
                    df = pd.read_csv(io.BytesIO(zf.read(name)))
                    raw_data[sname] = df
                elif name == "analyses.json":
                    raw = json.loads(zf.read(name).decode("utf-8"))
                    for k, v in raw.items():
                        analyses[int(k)] = v
                elif name.startswith("charts/") and name.endswith(".png"):
                    label = name[7:-4]  # strip "charts/" and ".png"
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
        }

    # ── 只读元信息 ────────────────────────────────────
    @staticmethod
    def get_project_info(path: str) -> Dict[str, Any]:
        """仅读取 manifest，不解压全部内容"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"项目文件不存在: {path}")
        with zipfile.ZipFile(path, "r") as zf:
            if "manifest.json" in zf.namelist():
                return json.loads(zf.read("manifest.json").decode("utf-8"))
        return {}

    # ── 最近项目 ──────────────────────────────────────
    @staticmethod
    def recent_projects() -> List[Dict[str, str]]:
        settings = QSettings("QA-Tool", "RecentProjects")
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
        settings = QSettings("QA-Tool", "RecentProjects")
        settings.setValue("list", json.dumps(recent, ensure_ascii=False))


# ── 辅助 ──────────────────────────────────────────────
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


# ── 共享项目 (Phase 8.4 基础协同) ────────────────────
SHARED_DIR = os.path.join(os.path.expanduser("~"), ".qa_tool_shared")
PUBLIC_DEPT = "公共"


class SharedProjectManager:
    """团队共享 .qap 项目管理"""

    @staticmethod
    def save_shared(path: str, raw_data: Dict[str, pd.DataFrame],
                    analyses: Dict[int, Dict], chart_bytes: Dict[str, bytes],
                    department: str, annotations: str = "") -> str:
        """保存项目到共享目录"""
        safe_dept = os.path.basename(department or PUBLIC_DEPT)
        dept_dir = os.path.join(SHARED_DIR, safe_dept)
        real_dept_dir = os.path.abspath(dept_dir)
        real_shared_dir = os.path.abspath(SHARED_DIR)
        if not real_dept_dir.startswith(real_shared_dir + os.sep):
            raise ValueError(f"非法的部门目录: {department}")
        os.makedirs(dept_dir, exist_ok=True)
        basename = os.path.basename(path)
        if not basename.endswith(".qap"):
            basename += ".qap"
        full_path = os.path.join(dept_dir, basename)
        return ProjectManager.save_project(full_path, raw_data, analyses, chart_bytes, annotations)

    @staticmethod
    def list_shared(department: str = "", role: str = "") -> List[Dict[str, str]]:
        """列出共享项目。admin 看到全部；其他人看到本部门+公共。"""
        projects = []
        if not os.path.exists(SHARED_DIR):
            return projects
        for dept_name in os.listdir(SHARED_DIR):
            dept_path = os.path.join(SHARED_DIR, dept_name)
            if not os.path.isdir(dept_path):
                continue
            # 权限过滤
            if role == "admin":
                pass
            elif department and dept_name not in (department, PUBLIC_DEPT):
                continue
            elif not department and dept_name != PUBLIC_DEPT:
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
    def load_shared(path: str) -> Dict[str, Any]:
        """加载共享项目（与 load_project 相同）"""
        return ProjectManager.load_project(path)
