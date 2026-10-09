"""插件数据源 API 2.1 测试（v4.3.0 B2-3/B2-4）。"""

import json
import textwrap
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.case_workflow import CaseWorkflow
from core.evidence_ledger import EvidenceLedger
from core.measurement_event import MeasurementEvent
from core.measurement_store import MeasurementStore
from core.plugin_api import (
    PLUGIN_API_VERSION,
    PluginError,
    PluginManifest,
    api_compatible,
)
from core.plugin_manager import PluginManager
from core.streaming.bus import StreamBus


@pytest.fixture(autouse=True)
def _reset_manager():
    PluginManager().reset()
    yield
    PluginManager().reset()


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return settings


def _write_source_plugin(root: Path, provider_body: str, *,
                        plugin_id: str = "src_plugin",
                        capabilities=("data_source",), api_version="2.1",
                        available=True) -> Path:
    plugin_dir = root / plugin_id
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(json.dumps({
        "id": plugin_id, "name": "源码插件", "version": "1.0",
        "api_version": api_version,
        "entry": f"{plugin_id}_impl:Plugin",
        "capabilities": list(capabilities),
    }, ensure_ascii=False), encoding="utf-8")
    code = f'''
from core.plugin_api import IAKIAPlugin, PluginManifest


class Plugin(IAKIAPlugin):
    manifest = PluginManifest(id="{plugin_id}", name="源码插件", version="1.0",
                              capabilities={tuple(capabilities)!r})

    def is_available(self):
        return {available!r}, "" if {available!r} else "缺少可选依赖"

    def provide_measurements(self, context=None):
{textwrap.indent(provider_body, "        ")}
'''
    (plugin_dir / f"{plugin_id}_impl.py").write_text(code, encoding="utf-8")
    return plugin_dir


def _trusted_manager(tmp_path, monkeypatch, isolated_config,
                     provider_body, **kwargs) -> PluginManager:
    root = tmp_path / "plugins"
    _write_source_plugin(root, provider_body, **kwargs)
    monkeypatch.setenv("AKIA_PLUGIN_DIRS", str(root))
    manager = PluginManager()
    manager.discover()
    plugin_id = kwargs.get("plugin_id", "src_plugin")
    manager.trust(plugin_id)
    return manager


_SIMPLE = "return [MeasurementEvent.from_manual(1.0)]"
_BAD = ('return [MeasurementEvent.from_manual(1.0).to_dict(),\n'
        '        {"schema_version": "1"}, 42]')


class TestApiContract:
    def test_api_version_is_21(self):
        assert PLUGIN_API_VERSION == "2.1"
        assert api_compatible("2.0") and api_compatible("2.1")

    def test_manifest_accepts_data_source(self):
        manifest = PluginManifest.from_dict({
            "id": "vision", "name": "视觉", "capabilities": ["data_source"]})
        assert manifest.supports("data_source")
        with pytest.raises(PluginError):
            PluginManifest.from_dict({"id": "bad", "capabilities": ["unknown"]})


class TestCollection:
    def test_forces_plugin_provenance(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   "from core.measurement_event import MeasurementEvent\n" + _SIMPLE,
                                   plugin_id="provenance_plugin")
        records = manager.data_source_plugins()
        assert [r.id for r in records] == ["provenance_plugin"]
        events = manager.collect_measurements()
        assert len(events) == 1
        assert events[0].source_kind == "plugin"
        assert events[0].source_id == "provenance_plugin"
        assert events[0].source_name == "源码插件"

    def test_bad_events_isolated(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(
            tmp_path, monkeypatch, isolated_config,
            "from core.measurement_event import MeasurementEvent\n" + _BAD,
            plugin_id="bad_event_plugin")
        events = manager.collect_measurements()
        assert len(events) == 1
        assert "无效" in manager.get_record("bad_event_plugin").error

    def test_non_list_return_isolated(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   "return {'not': 'a list'}",
                                   plugin_id="nonlist_plugin")
        assert manager.collect_measurements() == []
        assert "必须返回列表" in manager.get_record("nonlist_plugin").error

    def test_provider_exception_isolated(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   'raise RuntimeError("boom")',
                                   plugin_id="boom_plugin")
        assert manager.collect_measurements() == []
        assert "boom" in manager.get_record("boom_plugin").error

    def test_timeout_isolated(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(
            tmp_path, monkeypatch, isolated_config,
            "import time\ntime.sleep(0.5)\nreturn []",
            plugin_id="slow_plugin")
        assert manager.collect_measurements(timeout_s=0.05) == []
        assert "超时" in manager.get_record("slow_plugin").error

    def test_empty_batch_is_ok(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   "return []", plugin_id="empty_plugin")
        assert manager.collect_measurements() == []
        assert manager.get_record("empty_plugin").error == ""

    def test_untrusted_plugin_not_called(self, tmp_path, monkeypatch, isolated_config):
        root = tmp_path / "plugins"
        _write_source_plugin(root, _SIMPLE, plugin_id="untrusted_plugin")
        monkeypatch.setenv("AKIA_PLUGIN_DIRS", str(root))
        manager = PluginManager()
        manager.discover()
        record = manager.get_record("untrusted_plugin")
        assert record.trusted is False and record.instance is None
        assert manager.data_source_plugins() == []
        assert manager.collect_measurements() == []

    def test_unavailable_plugin_skipped(self, tmp_path, monkeypatch, isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   _SIMPLE, available=False,
                                   plugin_id="unavail_plugin")
        record = manager.get_record("unavail_plugin")
        assert record.available is False
        assert manager.data_source_plugins() == []

    def test_tab_plugin_without_data_source_ignored(self, tmp_path, monkeypatch,
                                                    isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   _SIMPLE, capabilities=("tab",),
                                   plugin_id="tabonly_plugin")
        assert manager.data_source_plugins() == []
        assert manager.collect_measurements() == []


class TestPluginHostInjection:
    @pytest.fixture
    def host(self):
        from ui.plugin_host import PluginHost

        class _Window:
            def __init__(self):
                self.measurement_store = MeasurementStore()
                self.stream_bus = StreamBus()

        window = _Window()
        return PluginHost(window), window

    def test_submit_measurements_forces_provenance(self, host):
        plugin_host, window = host
        events = [MeasurementEvent.from_manual(1.0),
                  MeasurementEvent.from_manual(2.0)]
        ids = plugin_host.submit_measurements(events, plugin_id="vision")
        assert len(ids) == 2
        stored = window.measurement_store.get(ids[0])
        assert stored.source_kind == "plugin"
        assert stored.source_id == "vision"

    def test_submit_is_atomic_on_bad_event(self, host):
        plugin_host, window = host
        with pytest.raises(ValueError, match="第 2 条"):
            plugin_host.submit_measurements(
                [MeasurementEvent.from_manual(1.0).to_dict(), {"bad": True}],
                plugin_id="vision")
        assert len(window.measurement_store) == 0

    def test_recent_measurements_from_bus(self, host):
        from core.devices.driver import Sample

        plugin_host, window = host
        window.stream_bus.publish("dev-1", [
            Sample("dev-1", "CH0", 1.0, 100.0),
            Sample("dev-1", "CH0", 2.0, 101.0)])
        assert plugin_host.connector_topics() == ["dev-1"]
        events = plugin_host.recent_measurements("dev-1")
        assert len(events) == 1
        assert events[0].summary["n"] == 2
        assert plugin_host.measurement_events() == []


class TestFixturePluginE2E:
    _E2E_PROVIDER = '''
import pandas as pd
from core.measurement_event import MeasurementEvent

baseline = [32.0, 31.8, 32.2, 31.9, 32.1, 32.3, 31.7, 32.0,
            32.2, 31.9, 32.1, 32.0, 31.8, 32.3, 31.9]
after = [28.0, 27.8, 28.2, 27.9, 28.1, 28.3, 27.7, 28.0,
         28.2, 27.9, 28.1, 28.0, 27.8, 28.3, 27.9]
return [
    MeasurementEvent.from_dataframe(
        pd.DataFrame({"cycle": baseline}), source_kind="plugin",
        channel="cycle", method="vision-time-study"),
    MeasurementEvent.from_dataframe(
        pd.DataFrame({"cycle": after}), source_kind="plugin",
        channel="cycle", method="vision-time-study"),
]
'''

    def test_plugin_events_drive_case_closure(self, tmp_path, monkeypatch,
                                              isolated_config):
        manager = _trusted_manager(tmp_path, monkeypatch, isolated_config,
                                   self._E2E_PROVIDER, plugin_id="vision_plugin")
        events = manager.collect_measurements()
        assert len(events) == 2
        store = MeasurementStore(events)
        baseline, after = store.events
        assert baseline.values and after.values

        before = pd.Series(store.get(baseline.event_id).values, dtype=float)
        after_series = pd.Series(store.get(after.event_id).values, dtype=float)
        ledger = EvidenceLedger()
        workflow = CaseWorkflow(title="视觉插件闭环", owner="李四", ledger=ledger)
        workflow.record_step("baseline", {"mean": float(before.mean())},
                             data_ref="plugin:vision_plugin",
                             measurement_refs=[baseline.event_id])
        workflow.record_step("remeasure", {"mean": float(after_series.mean())},
                             data_ref="plugin:vision_plugin",
                             measurement_refs=[after.event_id])
        workflow.run_paired_test(before, after_series,
                                 data_ref="plugin:vision_plugin",
                                 measurement_refs=[baseline.event_id,
                                                   after.event_id])
        workflow.close_case("插件测量显示显著改善")

        assert workflow.case.status == "closed"
        assert baseline.event_id in workflow.case.measurement_refs
        assert after.event_id in workflow.case.measurement_refs
        assert ledger.verify()["ok"] is True
        assert [e.event_type for e in ledger.events][-1] == "case_closed"
