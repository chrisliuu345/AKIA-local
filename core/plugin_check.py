"""Static plugin contract checks that never import or execute plugin code."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import APP_VERSION
from core.plugin_api import (
    PLUGIN_API_VERSION,
    PluginError,
    PluginManifest,
    api_compatible,
    version_satisfies,
)

CAPABILITY_METHODS = {
    "tab": "create_tab",
    "agent_tools": "register_agent_tools",
    "settings": "create_settings_page",
    "data_source": "provide_measurements",
}


@dataclass(frozen=True)
class PluginIssue:
    level: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "code": self.code, "message": self.message}


@dataclass
class PluginCheckReport:
    plugin_dir: Path
    manifest: dict[str, Any] | None = None
    issues: list[PluginIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[PluginIssue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[PluginIssue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "plugin_dir": str(self.plugin_dir),
            "ok": self.ok,
            "manifest": self.manifest,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [issue.as_dict() for issue in self.issues],
        }

    def add(self, level: str, code: str, message: str) -> None:
        self.issues.append(PluginIssue(level, code, message))


def _module_path(base_dir: Path, module_name: str) -> Path | None:
    parts = [part for part in module_name.split(".") if part]
    if not parts or any(not part.isidentifier() for part in parts):
        return None
    module_file = base_dir.joinpath(*parts).with_suffix(".py")
    if module_file.is_file():
        return module_file
    package_file = base_dir.joinpath(*parts, "__init__.py")
    return package_file if package_file.is_file() else None


def _class_methods(path: Path, class_name: str) -> set[str] | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        return {
            item.name for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return set()


def check_plugin_dir(path: str | Path, *,
                     app_version: str = APP_VERSION) -> PluginCheckReport:
    """Validate one directory-style plugin without importing its implementation."""
    plugin_dir = Path(path).expanduser().resolve()
    report = PluginCheckReport(plugin_dir=plugin_dir)
    manifest_path = plugin_dir / "plugin.json"
    if not plugin_dir.is_dir():
        report.add("error", "directory_missing", f"插件目录不存在: {plugin_dir}")
        return report
    if not manifest_path.is_file():
        report.add("error", "manifest_missing", "缺少 plugin.json")
        return report
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report.add("error", "manifest_invalid", f"plugin.json 无法解析: {exc}")
        return report
    if not isinstance(raw, dict):
        report.add("error", "manifest_invalid", "plugin.json 顶层必须是对象")
        return report
    report.manifest = raw
    try:
        manifest = PluginManifest.from_dict(raw)
    except (PluginError, TypeError, ValueError) as exc:
        report.add("error", "manifest_invalid", str(exc))
        return report

    if manifest.id != plugin_dir.name:
        report.add(
            "error", "id_directory_mismatch",
            f"插件 id {manifest.id!r} 与目录名 {plugin_dir.name!r} 不一致")
    if not api_compatible(manifest.api_version):
        report.add(
            "error", "api_incompatible",
            f"插件 API {manifest.api_version} 与主程序 {PLUGIN_API_VERSION} 不兼容")
    required_app = str((manifest.requires or {}).get("akia") or "")
    if required_app and not version_satisfies(required_app, app_version):
        report.add(
            "error", "app_incompatible",
            f"要求主程序 {required_app}，检查目标为 {app_version}")
    if not manifest.capabilities:
        report.add("warning", "capabilities_empty", "插件未声明任何能力")

    module_name, separator, class_name = manifest.entry.partition(":")
    if not separator or not module_name or not class_name:
        report.add("error", "entry_invalid", "entry 必须使用 module:Class 形式")
        return report
    module_path = _module_path(plugin_dir, module_name)
    if module_path is None:
        report.add(
            "error", "entry_missing",
            f"entry 模块不存在: {module_name}（需要 .py 或包 __init__.py）")
        return report
    methods = _class_methods(module_path, class_name)
    if methods is None:
        report.add("error", "source_invalid", f"无法解析插件源码: {module_path.name}")
        return report
    if not methods:
        report.add("error", "entry_class_missing", f"未找到入口类 {class_name}")
        return report
    for capability in manifest.capabilities:
        method = CAPABILITY_METHODS.get(capability)
        if method and method not in methods:
            report.add(
                "error", "capability_method_missing",
                f"能力 {capability} 需要实现 {method}()")
    if "is_available" not in methods:
        report.add(
            "warning", "is_available_missing",
            "未实现 is_available()；主程序将按默认可用处理")
    return report


def discover_plugin_dirs(path: str | Path) -> list[Path]:
    """Accept one plugin directory or a parent containing several plugins."""
    root = Path(path).expanduser().resolve()
    if (root / "plugin.json").is_file():
        return [root]
    if not root.is_dir():
        return []
    return sorted(
        child for child in root.iterdir()
        if child.is_dir() and (child / "plugin.json").is_file()
    )
