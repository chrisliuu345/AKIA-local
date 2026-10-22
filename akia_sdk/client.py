"""Headless AKIA client built on the same analysis engines used by the GUI."""

from __future__ import annotations

import base64
import dataclasses
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import APP_VERSION, SUPPORTED_EXCEL_EXTENSIONS
from core.agent.tools import AgentContext, build_default_registry
from core.data_loader import DataLoader

SDK_API_VERSION = "1.0"
OUTPUT_SCHEMA_VERSION = "1.0"
SUPPORTED_DATA_EXTENSIONS = (".csv", *SUPPORTED_EXCEL_EXTENSIONS)


class SDKError(ValueError):
    """Base error for invalid SDK input or unsupported operations."""

    code = "sdk_error"


class InputError(SDKError):
    """A data or project input cannot be read or selected."""

    code = "input_error"


class ToolNotFoundError(SDKError):
    """The requested analysis tool is not registered."""

    code = "tool_not_found"


class InvalidParameterError(SDKError):
    """The requested tool does not accept one or more supplied parameters."""

    code = "invalid_parameters"


class OutputError(SDKError):
    """A requested output path cannot be written safely."""

    code = "output_error"


def to_jsonable(value: Any) -> Any:
    """Convert analysis payloads into deterministic JSON-safe Python values."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return [to_jsonable(item) for item in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return to_jsonable(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return to_jsonable(value.tolist())
    if hasattr(value, "to_dict"):
        return to_jsonable(value.to_dict())
    return str(value)


def _select_sheets(raw_data: dict[str, pd.DataFrame],
                   sheets: list[str] | None) -> dict[str, pd.DataFrame]:
    if not sheets:
        return dict(raw_data)
    available = {str(name).lower(): name for name in raw_data}
    selected: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for requested in sheets:
        name = available.get(str(requested).lower())
        if name is None:
            missing.append(str(requested))
        else:
            selected[name] = raw_data[name]
    if missing:
        raise InputError(
            f"工作表不存在: {', '.join(missing)}；可用: {', '.join(raw_data)}")
    return selected


def load_data_file(path: str | Path, *,
                   sheets: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Load CSV or Excel data without importing PySide6."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise InputError(f"数据文件不存在: {source}")
    extension = source.suffix.lower()
    if extension not in SUPPORTED_DATA_EXTENSIONS:
        raise InputError(
            f"不支持的数据格式: {extension or '(无扩展名)'}；"
            f"支持: {', '.join(SUPPORTED_DATA_EXTENSIONS)}")
    try:
        if extension == ".csv":
            frame = pd.read_csv(source, dtype=str)
            frame.columns = [str(column).strip() for column in frame.columns]
            raw = {"Sheet1": frame}
            return _select_sheets(raw, sheets)
        return DataLoader().load(str(source), sheet_names=sheets)
    except SDKError:
        raise
    except Exception as exc:
        raise InputError(f"读取数据文件失败: {source}: {exc}") from exc


@dataclass(frozen=True)
class SDKResult:
    """Stable result envelope returned by ``AKIAClient.run``."""

    tool: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    text: str = ""
    error: str = ""
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "sdk_api_version": SDK_API_VERSION,
            "app_version": APP_VERSION,
            "kind": "tool_result",
            "tool": self.tool,
            "ok": self.ok,
            "data": to_jsonable(self.data),
            "text": self.text,
            "error": self.error,
            "duration_ms": round(float(self.duration_ms), 1),
        }


class AKIAClient:
    """Reusable headless client for registered AKIA analysis tools."""

    def __init__(self, data_frames: dict[str, pd.DataFrame], *,
                 analyses: dict[int, dict[str, Any]] | None = None,
                 project_context: Any = None,
                 source: str = "",
                 include_plugins: bool = False):
        if not isinstance(data_frames, dict):
            raise InputError("data_frames 必须是 {工作表名: DataFrame}")
        invalid = [name for name, frame in data_frames.items()
                   if not isinstance(frame, pd.DataFrame)]
        if invalid:
            raise InputError(f"以下工作表不是 DataFrame: {', '.join(map(str, invalid))}")
        self.data_frames = dict(data_frames)
        self.source = str(source)
        self.context = AgentContext(
            data_frames=self.data_frames,
            analyses=dict(analyses or {}),
            project_context=project_context,
        )
        # Headless callers must opt in to third-party code execution explicitly.
        self.registry = build_default_registry(
            self.context, include_plugins=include_plugins)

    @classmethod
    def from_dataframes(cls, data_frames: dict[str, pd.DataFrame], *,
                        include_plugins: bool = False) -> AKIAClient:
        return cls(data_frames, include_plugins=include_plugins)

    @classmethod
    def from_file(cls, path: str | Path, *, sheets: list[str] | None = None,
                  include_plugins: bool = False) -> AKIAClient:
        source = Path(path).expanduser()
        return cls(load_data_file(source, sheets=sheets), source=str(source),
                   include_plugins=include_plugins)

    @classmethod
    def from_project(cls, path: str | Path, *, sheets: list[str] | None = None,
                     include_plugins: bool = False) -> AKIAClient:
        """Load a ``.qap`` project without requiring a Qt installation."""
        source = Path(path).expanduser()
        if not source.is_file():
            raise InputError(f"项目文件不存在: {source}")
        if source.suffix.lower() != ".qap":
            raise InputError(f"项目文件扩展名应为 .qap: {source}")
        try:
            from core.project_context import ProjectContext
            from core.project_manager import ProjectManager

            payload = ProjectManager.load_project(
                str(source), record_recent=False)
        except Exception as exc:
            raise InputError(f"读取项目文件失败: {source}: {exc}") from exc
        context_payload = payload.get("project_context")
        project_context = (ProjectContext.from_dict(context_payload)
                           if isinstance(context_payload, dict) else None)
        return cls(_select_sheets(payload["raw_data"], sheets),
                   analyses=payload.get("analyses"),
                   project_context=project_context,
                   source=str(source),
                   include_plugins=include_plugins)

    def tool_specs(self, category: str | None = None) -> list[dict[str, Any]]:
        """Return versioned, JSON-ready descriptions of available tools."""
        specs = []
        for spec in self.registry.specs():
            if category and spec.category != category:
                continue
            specs.append({
                "name": spec.name,
                "title": spec.title,
                "description": spec.description,
                "parameters": dict(spec.parameters),
                "category": spec.category,
                "returns": spec.returns,
            })
        return specs

    def run(self, tool: str, params: dict[str, Any] | None = None) -> SDKResult:
        """Run a registered analysis tool and return its stable result envelope."""
        name = str(tool or "").strip()
        spec = self.registry.get(name)
        if spec is None:
            raise ToolNotFoundError(f"未知分析工具: {name}")
        arguments = dict(params or {})
        unknown = sorted(set(arguments) - set(spec.parameters))
        if unknown:
            raise InvalidParameterError(
                f"工具 {name} 不接受参数: {', '.join(unknown)}；"
                f"支持: {', '.join(spec.parameters) or '(无)'}")
        self._validate_references(arguments)
        result = self.registry.call(name, arguments, self.context)
        return SDKResult(
            tool=name,
            ok=bool(result.ok),
            data=dict(result.data or {}),
            text=str(result.text or ""),
            error=str(result.error or ""),
            duration_ms=float(result.duration_ms or 0.0),
        )

    def _validate_references(self, arguments: dict[str, Any]) -> None:
        """Reject explicit sheet/column references that would trigger fallback."""
        frame = self.context.frame(arguments.get("sheet"))
        requested_sheet = arguments.get("sheet")
        if requested_sheet not in (None, "") and frame is None:
            raise InvalidParameterError(
                f"工作表不存在: {requested_sheet}；可用: {', '.join(self.data_frames)}")
        if frame is None:
            return
        columns = [str(name) for name in frame.columns]
        lowered = {name.lower(): name for name in columns}
        requested: list[str] = []
        for key, value in arguments.items():
            if not (key == "column" or key.endswith(("_column", "_col"))
                    or key == "columns"):
                continue
            if value in (None, ""):
                continue
            if key == "columns" and isinstance(value, str):
                items = [item.strip() for item in value.replace("；", ",")
                         .replace(";", ",").split(",")]
            elif isinstance(value, (list, tuple, set, frozenset)):
                items = list(value)
            else:
                items = [value]
            requested.extend(str(item).strip() for item in items
                             if str(item).strip())
        missing = [name for name in requested
                   if name not in columns and name.lower() not in lowered]
        if missing:
            raise InvalidParameterError(
                f"列不存在: {', '.join(missing)}；可用: {', '.join(columns[:20])}")

    def profile(self) -> dict[str, Any]:
        """Return the same deterministic data profile used by one-click analysis."""
        from core.data_profiler import DataProfiler

        return to_jsonable(DataProfiler().profile(self.data_frames))

    def one_click(self, selected: list[str] | None = None) -> dict[str, Any]:
        """Run profiling, recommendations, analysis, and local fallback synthesis."""
        from core.one_click_analyzer import OneClickAnalyzer

        result = OneClickAnalyzer().run(self.data_frames, selected)
        return to_jsonable(result)
