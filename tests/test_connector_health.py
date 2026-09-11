"""v3.8.0-⑦ 连接器健康页 — 退避重连 / 采集接线 / 规格解析 / UI 状态。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from connectors.health import (
    STATUS_DEGRADED, STATUS_ERROR, STATUS_ONLINE, STATUS_STOPPED,
    HealthRegistry,
)
from connectors.registry import create_drivers, specs_from_settings
from core.devices.driver import Sample
from core.storage.timeseries import TimeseriesStore
from core.streaming.bus import StreamBus
from core.streaming.collector import IngestRunner


class Clock:
    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# ---------- 退避策略 ----------

def test_backoff_grows_exponentially_and_caps():
    reg = HealthRegistry(base_backoff_s=1.0, max_backoff_s=8.0, factor=2.0)
    assert [reg.backoff_for(n) for n in (1, 2, 3, 4, 5, 9)] == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]


def test_mark_error_sets_status_and_retry_window():
    clock = Clock()
    reg = HealthRegistry(base_backoff_s=2.0, error_threshold=2, clock=clock)
    reg.register("c1")
    assert reg.should_poll("c1") is True

    state = reg.mark_error("c1", "超时")
    assert state.status == STATUS_DEGRADED and state.consecutive_errors == 1
    assert state.next_retry_ts == pytest.approx(1002.0)
    assert reg.should_poll("c1") is False
    assert reg.retry_in("c1") == pytest.approx(2.0)

    clock.advance(2.0)
    assert reg.should_poll("c1") is True
    state = reg.mark_error("c1", "再次超时")
    assert state.status == STATUS_ERROR                  # 达到阈值
    assert state.backoff_s == pytest.approx(4.0)
    assert state.total_errors == 2


def test_mark_ok_resets_and_counts_samples():
    reg = HealthRegistry(base_backoff_s=5.0)
    reg.register("c1")
    reg.mark_error("c1", "boom")
    reg.mark_error("c1", "boom")
    state = reg.mark_ok("c1", samples=7)
    assert state.status == STATUS_ONLINE
    assert state.consecutive_errors == 0 and state.backoff_s == 0.0
    assert state.next_retry_ts == 0.0 and state.last_error == ""
    assert state.samples == 7 and state.total_ok == 1


def test_registry_snapshot_and_stopped_state():
    reg = HealthRegistry()
    reg.register("a", kind="connector")
    reg.register("b", kind="device")
    reg.mark_ok("a", samples=3)
    reg.mark_stopped("b")
    snap = reg.snapshot()
    assert snap["a"]["status"] == STATUS_ONLINE
    assert snap["a"]["status_label"] == "在线"
    assert snap["b"]["status"] == STATUS_STOPPED
    assert reg.names() == ["a", "b"]
    reg.clear()
    assert reg.snapshot() == {}


def test_unknown_source_is_pollable():
    reg = HealthRegistry()
    assert reg.should_poll("nobody") is True


# ---------- 规格解析 ----------

def test_specs_from_settings_shapes():
    assert specs_from_settings(None) == []
    assert specs_from_settings(["modbus_tcp"]) == [
        {"plugin": "modbus_tcp", "name": "modbus_tcp", "config": {}}]
    specs = specs_from_settings([
        {"plugin": "mqtt_sub", "name": "line1", "config": {"topic": "qa"}},
        {"type": "cmm_dmis", "config": {"name": "cmm1"}},
        {"plugin": "opcua", "enabled": False},
        {"nope": 1},
    ])
    assert [s["name"] for s in specs] == ["line1", "cmm1"]
    assert specs[0]["config"]["topic"] == "qa"


def test_create_drivers_reports_errors_without_aborting():
    drivers, errors = create_drivers([
        {"plugin": "no_such_plugin", "name": "bad"},
        {"plugin": "cmm_dmis", "name": "cmm", "config": {"source": "file",
                                                         "path": "/tmp/x.txt"}},
    ])
    assert len(drivers) == 1 and drivers[0].name == "cmm"
    assert errors and errors[0][0] == "bad"


# ---------- 采集接线 ----------

class FlakyDriver:
    """先失败 N 次，之后恢复正常 —— 验证退避与自动重连。"""

    def __init__(self, name="flaky", fail_times=2):
        self.name = name
        self.fail_times = fail_times
        self.polls = 0
        self.opens = 0
        self.closed = 0

    def open(self):
        self.opens += 1

    def close(self):
        self.closed += 1

    def poll(self):
        self.polls += 1
        if self.polls <= self.fail_times:
            raise RuntimeError("读取超时")
        return [Sample(self.name, "CH0", 1.0, time.time())]


def test_runner_marks_error_and_skips_during_backoff(tmp_path):
    clock = Clock()
    reg = HealthRegistry(base_backoff_s=1.0, clock=clock)
    store = TimeseriesStore(tmp_path / "h.db")
    driver = FlakyDriver(fail_times=2)
    runner = IngestRunner(StreamBus(), store, [driver], poll_interval=0.001,
                          health=reg)
    runner.start()
    deadline = time.time() + 3
    while time.time() < deadline and reg.get("flaky").consecutive_errors < 1:
        time.sleep(0.02)
    state = reg.get("flaky")
    assert state.status == STATUS_DEGRADED
    assert state.last_error == "poll 异常"
    assert reg.should_poll("flaky") is False   # 退避窗口内不再轮询
    polls_at_backoff = driver.polls
    time.sleep(0.15)
    assert driver.polls == polls_at_backoff     # 未到重试时间 → 不轮询
    runner.stop()
    assert reg.get("flaky").status == STATUS_STOPPED
    store.close()


def test_runner_auto_reconnects_after_backoff(tmp_path):
    clock = Clock()
    reg = HealthRegistry(base_backoff_s=0.05, max_backoff_s=0.05, clock=clock)
    store = TimeseriesStore(tmp_path / "h2.db")
    driver = FlakyDriver(fail_times=1)
    runner = IngestRunner(StreamBus(), store, [driver], poll_interval=0.001,
                          health=reg)
    runner.start()
    try:
        deadline = time.time() + 3
        while time.time() < deadline and reg.get("flaky").status != STATUS_ONLINE:
            clock.advance(0.06)                 # 推进退避时钟
            time.sleep(0.02)
        state = reg.get("flaky")
        assert state.status == STATUS_ONLINE
        assert state.samples >= 1
        assert driver.opens >= 2                # 初次 open + 自动重连 open
        assert store.count("flaky") >= 1
    finally:
        runner.stop()
        store.close()


def test_runner_manual_reconnect(tmp_path):
    clock = Clock()
    reg = HealthRegistry(base_backoff_s=99.0, clock=clock)
    store = TimeseriesStore(tmp_path / "h3.db")
    driver = FlakyDriver(fail_times=99)
    runner = IngestRunner(StreamBus(), store, [driver], poll_interval=0.001,
                          health=reg)
    runner.start()
    try:
        deadline = time.time() + 3
        while time.time() < deadline and reg.get("flaky").consecutive_errors < 1:
            time.sleep(0.02)
        assert runner.reconnect("flaky") is True
        assert driver.opens >= 2
        assert reg.get("flaky").consecutive_errors == 0
        assert reg.should_poll("flaky") is True
        assert runner.reconnect("missing") is False
    finally:
        runner.stop()
        store.close()


# ---------- UI ----------

def test_health_dialog_shows_states_and_plugins():
    from ui.dialogs.connector_health_dialog import ConnectorHealthDialog

    reg = HealthRegistry()
    reg.register("dev-a", kind="connector")
    reg.mark_ok("dev-a", samples=5)
    reg.register("dev-b")
    reg.mark_error("dev-b", "连接被拒绝")

    dlg = ConnectorHealthDialog(reg, runner=None, auto_refresh_ms=0)
    assert dlg.health_table.rowCount() == 2
    assert dlg.plugin_table.rowCount() >= 5
    states = {dlg.health_table.item(r, 0).text(): dlg.health_table.item(r, 2).text()
              for r in range(2)}
    assert states["dev-a"] == "在线" and states["dev-b"] == "重连中"
    dlg.deleteLater()


def test_health_dialog_reconnect_calls_runner():
    from ui.dialogs.connector_health_dialog import ConnectorHealthDialog

    class Runner:
        def __init__(self):
            self.reconnected = []

        def reconnect(self, name):
            self.reconnected.append(name)
            return True

    reg = HealthRegistry()
    reg.register("dev-a")
    reg.mark_error("dev-a", "x")
    runner = Runner()
    dlg = ConnectorHealthDialog(reg, runner=runner, auto_refresh_ms=0)
    dlg.health_table.selectRow(0)
    dlg._on_reconnect()
    assert runner.reconnected == ["dev-a"]
    dlg.deleteLater()
