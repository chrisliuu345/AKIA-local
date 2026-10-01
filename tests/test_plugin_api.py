"""插件接口 v2 测试 — manifest/版本门禁/信任/贡献点/旧式兼容。"""
import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from core.agent.tools import ToolRegistry
from core.plugin_api import (
    PLUGIN_API_VERSION,
    PluginError,
    PluginManifest,
    api_compatible,
    version_satisfies,
)
from core.plugin_manager import PluginManager


@pytest.fixture(autouse=True)
def _reset_manager():
    PluginManager().reset()
    yield
    PluginManager().reset()


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """插件信任写入隔离配置，避免污染真实 user_config.json。"""
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return settings


def _write_plugin(root: Path, plugin_id: str, *, api_version="2.0",
                  requires=None, available=True, with_tab=True,
                  with_tools=True):
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "id": plugin_id, "name": f"插件 {plugin_id}", "version": "1.2",
        "api_version": api_version,
        "entry": f"{plugin_id}_impl:Plugin",
        "requires": requires or {},
        "capabilities": [c for c, ok in
                         (("tab", with_tab), ("agent_tools", with_tools)) if ok],
        "optional_deps": [{"module": "cv2", "hint": "pip install opencv"}],
    }, ensure_ascii=False), encoding="utf-8")
    impl = f'''
from PySide6.QtWidgets import QLabel
from core.agent.tools import ToolResult
from core.plugin_api import IAKIAPlugin, PluginManifest


class Plugin(IAKIAPlugin):
    manifest = PluginManifest(
        id="{plugin_id}", name="插件 {plugin_id}", version="1.2",
        entry="{plugin_id}_impl:Plugin",
        capabilities={[c for c, ok in (("tab", with_tab), ("agent_tools", with_tools)) if ok]!r})

    def is_available(self):
        return {available!r}, "" if {available!r} else "缺少可选依赖 cv2"

    def create_tab(self, host, parent=None):
        return QLabel("ok")

    def register_agent_tools(self, registry, context=None):
        @registry.tool("hello", "Hello", "测试工具")
        def _hello(context=None):
            return ToolResult("hello", text="hi")
'''
    (plugin_dir / f"{plugin_id}_impl.py").write_text(impl, encoding="utf-8")
    return plugin_dir


# ---------- manifest / 版本 ----------


def test_manifest_validation():
    manifest = PluginManifest.from_dict({
        "id": "vision", "name": "视觉", "capabilities": ["tab", "agent_tools"]})
    assert manifest.id == "vision"
    assert manifest.api_version == PLUGIN_API_VERSION
    assert manifest.supports("agent_tools")
    with pytest.raises(PluginError):
        PluginManifest.from_dict({"id": "Bad-ID", "name": "x"})
    with pytest.raises(PluginError):
        PluginManifest.from_dict({"id": "okid", "capabilities": ["unknown"]})


def test_version_helpers():
    assert version_satisfies(">=3.8", "3.8.0")
    assert version_satisfies(">=3.8,<5", "4.0.0")
    assert not version_satisfies(">=3.8,<4", "4.0.0")
    assert version_satisfies("", "3.7.2")
    assert api_compatible("2.0") and api_compatible("2.9")
    assert not api_compatible("1.0") and not api_compatible("3.0")


# ---------- 发现 / 信任 / 贡献点 ----------


def test_user_plugin_requires_trust_then_registers(tmp_path, monkeypatch,
                                                   isolated_config):
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "demoplug")
    monkeypatch.setenv("AKIA_PLUGIN_DIRS", str(plugin_root))

    manager = PluginManager()
    manager.discover()
    record = manager.get_record("demoplug")
    assert record is not None
    assert record.trusted is False
    assert record.instance is None                 # 未信任不导入代码
    assert "信任" in record.reason

    manager.trust("demoplug")
    record = manager.get_record("demoplug")
    assert record.trusted is True and record.available is True
    assert record.supports("tab") and record.supports("agent_tools")

    registry = ToolRegistry()
    added = manager.register_agent_tools(registry, None)
    assert "demoplug_hello" in registry        # 自动加插件前缀，避免冲突
    assert "demoplug_hello" in added


def test_unavailable_plugin_reports_reason(tmp_path, monkeypatch, isolated_config):
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "noplug", available=False)
    monkeypatch.setenv("AKIA_PLUGIN_DIRS", str(plugin_root))

    manager = PluginManager()
    manager.discover()
    manager.trust("noplug")
    record = manager.get_record("noplug")
    assert record.available is False
    assert "cv2" in record.reason
    assert record not in manager.tab_plugins()


def test_api_version_and_app_version_gates(tmp_path, monkeypatch, isolated_config):
    plugin_root = tmp_path / "plugins"
    _write_plugin(plugin_root, "badapi", api_version="9.0")
    _write_plugin(plugin_root, "badver", requires={"akia": ">=99.0"})
    monkeypatch.setenv("AKIA_PLUGIN_DIRS", str(plugin_root))

    manager = PluginManager()
    manager.discover()
    bad_api = manager.get_record("badapi")
    bad_ver = manager.get_record("badver")
    assert bad_api.available is False and "不兼容" in bad_api.error
    assert bad_ver.available is False and "要求主程序" in bad_ver.error


def test_bundled_legacy_plugin_still_loads(_qt_application):
    manager = PluginManager()
    manager.discover()
    record = manager.get_record("example_plugin")
    assert record is not None
    assert record.source == "bundled" and record.trusted is True
    assert record.legacy is True and record.available is True
    assert record in manager.tab_plugins()
    tab = manager.create_tab(record, None, None)
    assert tab is not None


def test_plugin_host_readonly_facade():
    from ui.plugin_host import PluginHost

    class _Window:
        current_data = {"raw_data": {"S1": [1, 2, 3]}}
        analyses = {1: {"a": 1}}

    host = PluginHost(_Window())
    assert list(host.data_frames()) == ["S1"]
    assert host.analyses() == {1: {"a": 1}}
    assert PluginHost(None).data_frames() == {}
