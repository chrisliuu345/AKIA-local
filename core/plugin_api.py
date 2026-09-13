"""QA-Tool 插件接口 v2（v3.8.1）— 主应用只提供接口，不内置具体能力插件。

贡献点:
  - Tab: `create_tab(host, parent)`
  - Agent 工具: `register_agent_tools(registry, context)`
  - 设置页: `create_settings_page(host, parent)`
  - 能力/依赖声明: manifest + `is_available()`

分发方式:
  - 随包 `plugins/<id>/plugin.json`（目录式）或 `plugins/<name>.py`（旧式单文件）
  - 用户目录 `~/.qa_tool_plugins/`
  - pip 包 entry point `qa_tool.plugins`

安全: 插件即本机 Python 代码。随包插件默认信任；用户目录 / pip 插件首次需显式信任，
未信任只解析 manifest、不导入不执行。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

PLUGIN_API_VERSION = "2.0"
PLUGIN_ENTRY_POINT_GROUP = "qa_tool.plugins"
CAPABILITIES = ("tab", "agent_tools", "settings")

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


class PluginError(RuntimeError):
    """插件声明/加载/兼容性错误。"""


def _version_tuple(text: Any) -> tuple[int, int, int]:
    parts = [int(p) for p in re.findall(r"\d+", str(text or ""))[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def version_satisfies(required: str, current: str) -> bool:
    """支持 `>=3.8`、`>=3.8,<5`、`==3.8.1` 等简化表达式（空=通过）。"""
    requirement = str(required or "").strip()
    if not requirement:
        return True
    cur = _version_tuple(current)
    for clause in re.split(r"[,\s]+", requirement):
        match = re.fullmatch(r"(>=|<=|>|<|==)?\s*(\d+(?:\.\d+)*)", clause)
        if not match:
            continue
        op = match.group(1) or ">="
        target = _version_tuple(match.group(2))
        if op == ">=" and not cur >= target:
            return False
        if op == "<=" and not cur <= target:
            return False
        if op == ">" and not cur > target:
            return False
        if op == "<" and not cur < target:
            return False
        if op == "==" and not cur == target:
            return False
    return True


def api_compatible(plugin_api: str, host_api: str = PLUGIN_API_VERSION) -> bool:
    """同一大版本内向后兼容（2.x 插件可跑在 2.y 主程序上）。"""
    return _version_tuple(plugin_api)[0] == _version_tuple(host_api)[0]


@dataclass(frozen=True)
class Dependency:
    module: str
    hint: str = ""

    @classmethod
    def parse(cls, value: Any) -> "Dependency":
        if isinstance(value, Dependency):
            return value
        if isinstance(value, dict):
            return cls(module=str(value.get("module") or ""),
                       hint=str(value.get("hint") or ""))
        return cls(module=str(value or ""))

    def to_dict(self) -> dict:
        return {"module": self.module, "hint": self.hint}


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str = "0.1"
    api_version: str = PLUGIN_API_VERSION
    entry: str = ""
    description: str = ""
    category: str = "engineering"
    icon: str = "🔌"
    requires: dict = field(default_factory=dict)
    optional_deps: tuple[Dependency, ...] = ()
    capabilities: tuple[str, ...] = ("tab",)

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "version": self.version,
            "api_version": self.api_version, "entry": self.entry,
            "description": self.description, "category": self.category,
            "icon": self.icon, "requires": dict(self.requires),
            "optional_deps": [d.to_dict() for d in self.optional_deps],
            "capabilities": list(self.capabilities),
        }

    @classmethod
    def from_dict(cls, data: dict, defaults: "PluginManifest | None" = None) -> "PluginManifest":
        base = defaults
        raw = dict(data or {})
        plugin_id = str(raw.get("id") or (base.id if base else "")).strip().lower()
        if not _ID_RE.fullmatch(plugin_id):
            raise PluginError(
                f"插件 id 非法: {plugin_id!r}（需为小写字母开头、2-32 位 [a-z0-9_]）")
        name = str(raw.get("name") or (base.name if base else plugin_id))
        capabilities = raw.get("capabilities")
        if capabilities is None:
            capabilities = list(base.capabilities) if base else ["tab"]
        capabilities = tuple(str(c) for c in capabilities)
        unknown = [c for c in capabilities if c not in CAPABILITIES]
        if unknown:
            raise PluginError(f"插件 {plugin_id} 声明了未知能力: {unknown}")
        deps = raw.get("optional_deps")
        if deps is None:
            deps = list(base.optional_deps) if base else []
        return cls(
            id=plugin_id, name=name,
            version=str(raw.get("version") or (base.version if base else "0.1")),
            api_version=str(raw.get("api_version")
                           or (base.api_version if base else PLUGIN_API_VERSION)),
            entry=str(raw.get("entry") or (base.entry if base else "")),
            description=str(raw.get("description")
                            or (base.description if base else "")),
            category=str(raw.get("category")
                         or (base.category if base else "engineering")),
            icon=str(raw.get("icon") or (base.icon if base else "🔌")),
            requires=dict(raw.get("requires") or (base.requires if base else {})),
            optional_deps=tuple(Dependency.parse(d) for d in deps),
            capabilities=capabilities,
        )


class PluginToolRegistry:
    """工具注册代理 — 插件工具自动加 `<id>_` 前缀，避免与主应用工具冲突。"""

    def __init__(self, registry, plugin_id: str, category_prefix: str = "插件"):
        self._registry = registry
        self.plugin_id = plugin_id
        self.category_prefix = category_prefix

    def prefixed(self, name: str) -> str:
        raw = str(name or "").strip()
        prefix = f"{self.plugin_id}_"
        if raw.startswith((prefix, f"plugin_{prefix}")):
            return raw
        return f"{prefix}{raw}"

    def tool(self, name, title, description, parameters=None, category="通用",
             returns=""):
        return self._registry.tool(
            self.prefixed(name), title, description, parameters=parameters,
            category=f"{self.category_prefix}·{self.plugin_id}" if category == "通用"
            else f"{self.category_prefix}·{self.plugin_id}·{category}",
            returns=returns)

    def register(self, spec):
        return self._registry.register(replace(spec, name=self.prefixed(spec.name)))

    def get(self, name):
        return self._registry.get(self.prefixed(name))

    def names(self):
        return [n for n in self._registry.names()
                if n.startswith(f"{self.plugin_id}_")]

    def __contains__(self, name) -> bool:
        return self.prefixed(name) in self._registry


class IQAToolPlugin:
    """插件基类 v2 — 至少声明 manifest；按 capabilities 实现对应方法。"""

    manifest: PluginManifest = PluginManifest(id="plugin", name="插件")

    def is_available(self) -> tuple[bool, str]:
        """依赖探测: 返回 (可用, 原因/安装指引)。默认可用。"""
        return True, ""

    def create_tab(self, host, parent=None):
        return None

    def register_agent_tools(self, registry: PluginToolRegistry, context=None):
        return None

    def create_settings_page(self, host, parent=None):
        return None

    def on_load(self, host):
        pass

    def on_unload(self):
        pass


class IPlugin:
    """旧式插件接口（v1）— 保留兼容；核心属性与 IQAToolPlugin 对齐。"""

    name: str = "Unnamed"
    version: str = "0.1"
    category: str = "engineering"
    icon: str = "🔌"
    description: str = ""

    def create_tab(self, parent=None):
        raise NotImplementedError

    def analyze(self, df) -> dict:
        return {}


def manifest_from_legacy(instance: IPlugin, plugin_id: str) -> PluginManifest:
    return PluginManifest(
        id=plugin_id, name=str(getattr(instance, "name", plugin_id)),
        version=str(getattr(instance, "version", "0.1")),
        api_version="1.0",
        description=str(getattr(instance, "description", "")),
        category=str(getattr(instance, "category", "engineering")),
        icon=str(getattr(instance, "icon", "🔌")),
        capabilities=("tab",),
    )
