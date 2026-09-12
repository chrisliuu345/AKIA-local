"""插件管理器 v2 — 发现 / 信任 / 加载 / 贡献点注册（v3.8.1）。

发现顺序:
  1. 随包 `plugins/`（目录式 `plugin.json` 或旧式单文件 `.py`）— 默认信任
  2. 用户目录 `~/.qa_tool_plugins/`（可用 `QA_TOOL_PLUGIN_DIRS` 覆盖，os.pathsep 分隔）
  3. pip entry point 组 `qa_tool.plugins`

未信任插件只登记 manifest、不导入代码；在「设置 → 插件」中信任后重新扫描生效。
主应用只依赖本接口，不感知任何具体插件（如机器视觉）。
"""
from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.plugin_api import (
    IPlugin,
    IQAToolPlugin,
    PLUGIN_API_VERSION,
    PLUGIN_ENTRY_POINT_GROUP,
    PluginError,
    PluginManifest,
    PluginToolRegistry,
    api_compatible,
    manifest_from_legacy,
    version_satisfies,
)

_log = logging.getLogger("QA-Tool.Plugin")


@dataclass
class PluginRecord:
    """一个插件的登记信息（manifest + 运行时状态）。"""

    id: str
    manifest: PluginManifest
    source: str = ""                # bundled / user / entry_point
    instance: Any = None
    trusted: bool = True
    available: bool = True
    reason: str = ""
    error: str = ""
    legacy: bool = False

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def icon(self) -> str:
        return self.manifest.icon

    @property
    def description(self) -> str:
        return self.manifest.description

    def supports(self, capability: str) -> bool:
        return self.manifest.supports(capability)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "version": self.version,
            "api_version": self.manifest.api_version, "source": self.source,
            "trusted": self.trusted, "available": self.available,
            "reason": self.reason, "error": self.error, "legacy": self.legacy,
            "capabilities": list(self.manifest.capabilities),
            "optional_deps": [d.to_dict() for d in self.manifest.optional_deps],
        }


class LegacyPluginAdapter(IQAToolPlugin):
    """把旧式 IPlugin（依赖 create_tab(parent)）适配到 v2 接口。"""

    def __init__(self, legacy: IPlugin, manifest: PluginManifest):
        self._legacy = legacy
        self.manifest = manifest

    def create_tab(self, host, parent=None):
        return self._legacy.create_tab(parent)

    def register_agent_tools(self, registry, context=None):
        hook = getattr(self._legacy, "register_agent_tools", None)
        if callable(hook):
            hook(registry, context)


def _user_plugin_dirs() -> list[Path]:
    env = os.environ.get("QA_TOOL_PLUGIN_DIRS", "").strip()
    if env:
        return [Path(p) for p in env.split(os.pathsep) if p.strip()]
    return [Path.home() / ".qa_tool_plugins"]


class PluginManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._records: dict[str, PluginRecord] = {}
            cls._instance._loaded = False
            cls._instance._host = None
            cls._instance._errors: list[str] = []
        return cls._instance

    # ------------------------------------------------------------ 兼容属性
    @property
    def plugins(self) -> dict[str, Any]:
        """旧接口：id → 已加载实例（不可用/未信任插件不出现）。"""
        return {pid: rec.instance for pid, rec in self._records.items()
                if rec.instance is not None and rec.available}

    @property
    def host(self):
        return self._host

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def set_host(self, host):
        self._host = host

    def reset(self):
        """清空登记（测试/重新扫描用）。"""
        self._records.clear()
        self._errors.clear()
        self._loaded = False

    # ------------------------------------------------------------ 发现 / 加载
    def discover(self, plugin_dir: str | Path | None = None, force: bool = False):
        if self._loaded and not force:
            return self
        if force:
            self._records.clear()
            self._errors.clear()
        bundled = Path(plugin_dir) if plugin_dir else (
            Path(__file__).resolve().parent.parent / "plugins")
        if bundled.is_dir():
            self._scan_dir(bundled, source="bundled", bundled=True)
        for user_dir in _user_plugin_dirs():
            if user_dir.is_dir():
                self._scan_dir(user_dir, source="user", bundled=False)
        self._scan_entry_points()
        self._loaded = True
        return self

    def _scan_dir(self, directory: Path, source: str, bundled: bool):
        for name in sorted(os.listdir(directory)):
            if name.startswith("_") or name in ("__pycache__",):
                continue
            path = directory / name
            if path.is_dir():
                manifest_file = path / "plugin.json"
                if manifest_file.is_file():
                    self._load_dir_plugin(path, source, bundled)
            elif name.endswith(".py"):
                if bundled:
                    self._load_legacy_file(path)
                else:
                    self._register_error(
                        name[:-3], name[:-3], source,
                        "用户目录不支持旧式单文件插件，请改用 plugin.json 目录式插件")

    def _load_dir_plugin(self, path: Path, source: str, bundled: bool):
        try:
            data = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
            manifest = PluginManifest.from_dict(data)
        except Exception as e:
            self._register_error(path.name, path.name, source,
                                 f"plugin.json 解析失败: {e}")
            return
        self._register_manifest(manifest, source, bundled, base_dir=path)

    def _load_legacy_file(self, path: Path):
        plugin_id = path.stem.lower()
        try:
            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_id}", path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_id}"] = module
            spec.loader.exec_module(module)
            instance = getattr(module, "PLUGIN", None)
            if not isinstance(instance, IPlugin):
                raise PluginError("未找到 IPlugin 实例（PLUGIN = ...）")
        except Exception as e:
            self._register_error(plugin_id, plugin_id, "bundled",
                                 f"旧式插件加载失败: {e}")
            return
        manifest = manifest_from_legacy(instance, plugin_id)
        self._records[plugin_id] = PluginRecord(
            id=plugin_id, manifest=manifest, source="bundled",
            instance=LegacyPluginAdapter(instance, manifest), legacy=True)

    def _register_manifest(self, manifest: PluginManifest, source: str,
                           bundled: bool, base_dir: Path | None = None):
        plugin_id = manifest.id
        if not api_compatible(manifest.api_version):
            self._register_error(
                plugin_id, manifest.name, source,
                f"插件 API {manifest.api_version} 与主程序 "
                f"{PLUGIN_API_VERSION} 不兼容")
            return
        required = str((manifest.requires or {}).get("qa_tool", ""))
        try:
            from config.settings import APP_VERSION
        except Exception:
            APP_VERSION = "0"
        if not version_satisfies(required, APP_VERSION):
            self._register_error(
                plugin_id, manifest.name, source,
                f"要求主程序 {required}，当前 {APP_VERSION}")
            return

        trusted = bundled or self.is_trusted(plugin_id)
        record = PluginRecord(id=plugin_id, manifest=manifest, source=source,
                              trusted=trusted)
        if not trusted:
            record.available = False
            record.reason = "等待用户信任（设置 → 插件）"
            self._records[plugin_id] = record
            return
        try:
            instance = self._instantiate(manifest, base_dir)
        except Exception as e:
            record.available = False
            record.error = f"加载失败: {e}"
            self._records[plugin_id] = record
            _log.warning("插件 %s 加载失败: %s", plugin_id, e)
            return
        record.instance = instance
        self._probe(record)
        self._records[plugin_id] = record
        _log.info("已加载插件: %s v%s (%s)", manifest.name, manifest.version, source)

    def _instantiate(self, manifest: PluginManifest, base_dir: Path | None):
        entry = manifest.entry
        if not entry:
            raise PluginError("manifest 缺少 entry（module:Class）")
        module_name, _, cls_name = entry.partition(":")
        inserted = False
        if base_dir is not None and str(base_dir) not in sys.path:
            sys.path.insert(0, str(base_dir))
            inserted = True
        try:
            module = importlib.import_module(module_name)
        finally:
            if inserted:
                try:
                    sys.path.remove(str(base_dir))
                except ValueError:
                    pass
        obj = getattr(module, cls_name) if cls_name else module
        if isinstance(obj, type):
            obj = obj()
        if not isinstance(obj, IQAToolPlugin):
            raise PluginError(f"{entry} 未返回 IQAToolPlugin 实例")
        return obj

    def _scan_entry_points(self):
        try:
            entries = importlib.metadata.entry_points(group=PLUGIN_ENTRY_POINT_GROUP)
        except Exception as e:                      # 老版本/环境异常
            _log.debug("entry_points 读取失败: %s", e)
            return
        for ep in entries:
            plugin_id = ep.name.strip().lower()
            if plugin_id in self._records:
                continue
            if not self.is_trusted(plugin_id):
                manifest = PluginManifest(
                    id=plugin_id, name=ep.name, version="?",
                    description="pip 插件（等待信任）", capabilities=("tab",))
                record = PluginRecord(id=plugin_id, manifest=manifest,
                                      source="entry_point", trusted=False,
                                      available=False,
                                      reason="等待用户信任（设置 → 插件）")
                self._records[plugin_id] = record
                continue
            try:
                obj = ep.load()
                if isinstance(obj, type):
                    obj = obj()
            except Exception as e:
                self._register_error(plugin_id, ep.name, "entry_point",
                                     f"entry point 加载失败: {e}")
                continue
            manifest = getattr(obj, "manifest", None)
            if not isinstance(manifest, PluginManifest):
                manifest = PluginManifest(id=plugin_id, name=ep.name,
                                          entry=str(ep.value))
            record = PluginRecord(id=plugin_id, manifest=manifest,
                                  source="entry_point", instance=obj)
            self._probe(record)
            self._records[plugin_id] = record

    def _register_error(self, plugin_id: str, name: str, source: str, error: str):
        manifest = PluginManifest(id=plugin_id if plugin_id else "unknown",
                                  name=name or plugin_id)
        self._records[manifest.id] = PluginRecord(
            id=manifest.id, manifest=manifest, source=source,
            trusted=True, available=False, error=error)
        self._errors.append(f"{manifest.id}: {error}")
        _log.warning("插件 %s 不可用: %s", manifest.id, error)

    def _probe(self, record: PluginRecord):
        instance = record.instance
        if not isinstance(instance, IQAToolPlugin):
            record.available = True
            return
        try:
            ok, reason = instance.is_available()
        except Exception as e:
            ok, reason = False, f"依赖探测异常: {e}"
        record.available = bool(ok)
        record.reason = str(reason or "")

    # ------------------------------------------------------------ 信任
    def is_trusted(self, plugin_id: str) -> bool:
        try:
            from config.settings import get_setting
            return plugin_id in (get_setting("plugin_trusted", []) or [])
        except Exception:
            return False

    def trust(self, plugin_id: str):
        from config.settings import get_setting, save_config
        ids = list(get_setting("plugin_trusted", []) or [])
        if plugin_id not in ids:
            ids.append(plugin_id)
            save_config({"plugin_trusted": ids})
        self.discover(force=True)
        self.on_load_all()

    # ------------------------------------------------------------ 生命周期
    def on_load_all(self):
        for record in self._records.values():
            if record.instance is None or not record.available:
                continue
            hook = getattr(record.instance, "on_load", None)
            if callable(hook):
                try:
                    hook(self._host)
                except Exception as e:
                    record.error = f"on_load 失败: {e}"
                    record.available = False
                    _log.warning("插件 %s on_load 失败: %s", record.id, e)

    # ------------------------------------------------------------ 查询
    def records(self) -> list[PluginRecord]:
        return list(self._records.values())

    def get_record(self, plugin_id: str) -> PluginRecord | None:
        return self._records.get(str(plugin_id))

    def tab_plugins(self) -> list[PluginRecord]:
        return [r for r in self._records.values()
                if r.trusted and r.available and r.supports("tab")]

    def settings_plugins(self) -> list[PluginRecord]:
        return [r for r in self._records.values()
                if r.trusted and r.available and r.supports("settings")]

    def status_report(self) -> list[dict]:
        return [r.to_dict() for r in self._records.values()]

    # ------------------------------------------------------------ 贡献点
    def create_tab(self, record_or_id, host=None, parent=None):
        record = (record_or_id if isinstance(record_or_id, PluginRecord)
                  else self.get_record(str(record_or_id)))
        if record is None or record.instance is None or not record.available:
            return None
        return record.instance.create_tab(host or self._host, parent)

    def create_settings_page(self, record_or_id, host=None, parent=None):
        record = (record_or_id if isinstance(record_or_id, PluginRecord)
                  else self.get_record(str(record_or_id)))
        if record is None or record.instance is None or not record.available:
            return None
        return record.instance.create_settings_page(host or self._host, parent)

    def register_agent_tools(self, registry, context=None) -> list[str]:
        added: list[str] = []
        for record in self._records.values():
            if not (record.trusted and record.available
                    and record.supports("agent_tools")):
                continue
            proxy = PluginToolRegistry(registry, record.id)
            before = set(registry.names())
            try:
                record.instance.register_agent_tools(proxy, context)
            except Exception as e:
                record.error = f"工具注册失败: {e}"
                _log.warning("插件 %s 工具注册失败: %s", record.id, e)
                continue
            added.extend(sorted(set(registry.names()) - before))
        return added


__all__ = ["IPlugin", "IQAToolPlugin", "PluginManager", "PluginRecord",
           "LegacyPluginAdapter"]
