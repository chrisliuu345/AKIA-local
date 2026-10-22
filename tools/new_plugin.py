#!/usr/bin/env python3
"""Generate a directory-style AKIA plugin scaffold."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
CAPABILITIES = ("tab", "agent_tools", "settings", "data_source")


def _implementation(plugin_id: str, class_name: str, capabilities: list[str]) -> str:
    lines = [
        f'"""{plugin_id} plugin implementation."""',
        "",
        "from core.plugin_api import IAKIAPlugin, PluginManifest",
        "",
        "",
        "class Plugin(IAKIAPlugin):",
        "    manifest = PluginManifest(",
        f'        id="{plugin_id}",',
        f'        name="{plugin_id}",',
        '        version="0.1.0",',
        f'        capabilities={tuple(capabilities)!r},',
        "    )",
        "",
        "    def is_available(self):",
        '        return True, ""',
    ]
    if "tab" in capabilities:
        lines.extend([
            "",
            "    def create_tab(self, host, parent=None):",
            "        from PySide6.QtWidgets import QLabel",
            "",
            f'        return QLabel("Plugin {plugin_id} is loaded", parent)',
        ])
    if "agent_tools" in capabilities:
        lines.extend([
            "",
            "    def register_agent_tools(self, registry, context=None):",
            "        from core.agent.tools import ToolResult",
            "",
            '        @registry.tool("echo", "Echo", "Return the supplied text",',
            '                       {"text": "text to return"})',
            "        def _echo(context, text: str = \"\"):",
            '            return ToolResult("echo", data={"text": text}, text=text)',
        ])
    if "settings" in capabilities:
        lines.extend([
            "",
            "    def create_settings_page(self, host, parent=None):",
            "        from PySide6.QtWidgets import QLabel",
            "",
            f'        return QLabel("Plugin {plugin_id} settings", parent)',
        ])
    if "data_source" in capabilities:
        lines.extend([
            "",
            "    def provide_measurements(self, context=None):",
            "        # Return MeasurementEvent instances or serializable dicts.",
            "        return []",
        ])
    return "\n".join(lines) + "\n"


def build_scaffold(plugin_id: str, name: str, capabilities: list[str],
                   output: str | Path) -> Path:
    from core.plugin_api import PLUGIN_API_VERSION

    if not PLUGIN_ID_RE.fullmatch(plugin_id):
        raise ValueError("插件 id 需为小写字母开头、2-32 位 [a-z0-9_]")
    invalid = sorted(set(capabilities) - set(CAPABILITIES))
    if invalid:
        raise ValueError(f"未知能力: {', '.join(invalid)}")
    if not capabilities:
        raise ValueError("至少声明一个能力")
    target = Path(output).expanduser().resolve() / plugin_id
    if target.exists():
        raise FileExistsError(f"目标已存在，拒绝覆盖: {target}")
    target.mkdir(parents=True)
    class_name = "Plugin"
    manifest = {
        "id": plugin_id,
        "name": name,
        "version": "0.1.0",
        "api_version": PLUGIN_API_VERSION,
        "entry": f"{plugin_id}_impl:{class_name}",
        "description": f"{name} plugin for AKIA",
        "category": "engineering",
        "icon": "🔌",
        "requires": {"akia": ">=4.4"},
        "capabilities": capabilities,
        "optional_deps": [],
    }
    (target / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (target / f"{plugin_id}_impl.py").write_text(
        _implementation(plugin_id, class_name, capabilities), encoding="utf-8")
    (target / "README.md").write_text(
        f"# {name}\n\n"
        f"AKIA plugin id: `{plugin_id}`\n\n"
        f"Capabilities: {', '.join(capabilities)}\n\n"
        "Validate before distribution:\n\n"
        f"```bash\npython tools/plugin_check.py {target}\n```\n",
        encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 AKIA 插件脚手架")
    parser.add_argument("--id", required=True, help="插件 id（小写 snake_case）")
    parser.add_argument("--name", required=True, help="插件显示名称")
    parser.add_argument("--output", required=True, help="父目录，将在其中创建 <id>/")
    parser.add_argument("--capabilities", default="tab",
                        help="逗号分隔：tab,agent_tools,settings,data_source")
    args = parser.parse_args(argv)
    capabilities = [item.strip() for item in args.capabilities.split(",")
                    if item.strip()]
    try:
        target = build_scaffold(args.id, args.name, capabilities, args.output)
    except (ValueError, FileExistsError, OSError) as exc:
        print(f"生成失败: {exc}", file=sys.stderr)
        return 1
    print(target)
    print(f"校验: python tools/plugin_check.py {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
