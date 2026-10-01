"""P5 验收 — 告警引擎去抖/通道 / 产线拓扑 / 实时 OEE。

验收: 拓扑错误态(离线)5s 内反映 · 告警去抖只发一次 · OEE 窗口计算。
"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.devices.driver import Sample
from core.plant import PlantConfig, Station, Line
from core.streaming.alerts import (AlertEngine, AlertRule, make_email_handler,
                                   make_webhook_handler, rules_from_plant)
from core.streaming.bus import StreamBus
from core.streaming.oee_live import LiveOEEComputer


class Recorder:
    def __init__(self):
        self.events = []

    def notify(self, e):
        self.events.append(e)


@pytest.fixture
def plant():
    return PlantConfig(lines=[
        Line(name="1号线", stations=[
            Station(name="工位A", device="dev-a", channels=["CH0"], usl=110.0, lsl=90.0),
            Station(name="工位B", device="dev-b", channels=["CH0"]),
        ])])


def test_plant_config_roundtrip(tmp_path):
    p = tmp_path / "plant.json"
    cfg = PlantConfig(lines=[Line(name="L1", stations=[
        Station(name="S1", device="d1", channels=["CH0", "CH1"], usl=5.0)])])
    cfg.save(p)
    loaded = PlantConfig.load(p)
    assert loaded.lines[0].stations[0].usl == 5.0
    assert loaded.lines[0].stations[0].channels == ["CH0", "CH1"]


def test_plant_load_default_when_missing():
    cfg = PlantConfig.load("/nope/plant.json")
    assert cfg.lines and cfg.lines[0].stations[0].channels


def test_rules_from_plant(plant):
    rules = rules_from_plant(plant)
    assert len(rules) == 2
    assert rules[0].device == "dev-a" and rules[0].usl == 110.0


def test_alert_fires_once_with_debounce():
    bus = StreamBus()
    rec = Recorder()
    rule = AlertRule("dev-a", "CH0", usl=110.0, lsl=90.0, cooldown_s=30.0)
    engine = AlertEngine(bus, [rule], [rec])
    engine.start()
    try:
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, t) for t in range(30)])
        rec.events.clear()  # 基线规则7(15点±1σ)事件剔除
        bus.publish("dev-a", [Sample("dev-a", "CH0", 130.0, time.time())])
        engine.wait_pending()
        kinds_1 = {e.kind for e in rec.events}
        assert "oos" in kinds_1
        n_after_1 = len(rec.events)
        # 冷却期内再次越限 => 同 key 不再触发
        bus.publish("dev-a", [Sample("dev-a", "CH0", 132.0, time.time())])
        engine.wait_pending()
        assert len(rec.events) == n_after_1, "冷却期内重复违规只应触发一次"
        assert all(e.device == "dev-a" for e in rec.events)
    finally:
        engine.stop()


def test_debounce_requires_streak():
    bus = StreamBus()
    rec = Recorder()
    rule = AlertRule("dev-a", "CH0", usl=110.0, debounce_n=2, cooldown_s=30.0)
    engine = AlertEngine(bus, [rule], [rec])
    engine.start()
    try:
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, t) for t in range(30)])
        rec.events.clear()
        bus.publish("dev-a", [Sample("dev-a", "CH0", 130.0, 1.0)])
        engine.wait_pending()
        assert rec.events == []  # 仅第 1 点, 未达连续 2
        bus.publish("dev-a", [Sample("dev-a", "CH0", 131.0, 2.0)])
        engine.wait_pending()
        assert len(rec.events) >= 1
    finally:
        engine.stop()


def test_webhook_handler_posts(monkeypatch):
    import urllib.request

    captured = {}

    class Resp:
        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, **kw):
        captured["data"] = req.data
        captured["headers"] = dict(req.header_items()).get("Content-type")
        return Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    import json
    handler = make_webhook_handler("http://x/alerts")
    from core.streaming.alerts import AlertEvent
    handler(AlertEvent("d", "c", "oos", "超规格上界", 42.0, 123.0))
    payload = json.loads(captured["data"])
    assert payload["event"] == "akia-alert"
    assert payload["channel"] == "c" and payload["value"] == 42.0
    assert payload["kind"] == "oos"
    assert captured["headers"] == "application/json"


def test_live_oee_computer(plant):
    bus = StreamBus()
    oee = LiveOEEComputer(bus, plant, window_s=600.0)
    t = time.time()
    bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, t - 5),
                          Sample("dev-a", "CH1", 100.0, t - 4),
                          Sample("dev-a", "CH0", 120.0, t - 1)])  # 超 USL
    snap = oee.snapshot()
    m = snap["1号线"]
    assert m["samples"] == 3
    assert m["availability"] == 1.0
    assert m["quality"] == pytest.approx(2 / 3, abs=1e-3)
    assert m["oee"] == pytest.approx(2 / 3, abs=1e-3)
    oee.stop()




def test_slow_handler_does_not_block_ingest_thread():
    """B7: 慢速通知通道(邮件10s超时)必须异步执行, 不阻塞采集。"""
    import threading as _t

    bus = StreamBus()
    started = _t.Event()
    released = _t.Event()

    class SlowHandler:
        def notify(self, e):
            started.set()
            released.wait(timeout=2.0)

    handler = SlowHandler()
    rule = AlertRule("dev-a", "CH0", usl=110.0, cooldown_s=0.01)
    engine = AlertEngine(bus, [rule], [handler])
    engine.start()
    try:
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, t) for t in range(30)])
        t0 = time.time()
        bus.publish("dev-a", [Sample("dev-a", "CH0", 130.0, time.time())])
        elapsed = time.time() - t0
        assert started.wait(timeout=1.0), "通知应在后台线程启动"
        assert elapsed < 0.5, f"publish 被慢 handler 阻塞 {elapsed:.2f}s"
        released.set()
        engine.wait_pending(timeout=2.0)
    finally:
        released.set()
        engine.stop()


def test_email_starttls_flag(monkeypatch):
    """B6: STARTTLS 为配置开关; 纯 SMTP(25) 不强制 TLS。"""
    import smtplib
    from core.streaming.alerts import AlertEvent

    calls = {"starttls": 0, "login": 0, "sends": []}

    class FakeSMTP:
        def __init__(self, host, port, timeout=10.0):
            calls["host"] = (host, port)
            calls["starttls"] = 0

        def starttls(self):
            calls["starttls"] += 1

        def login(self, *a):
            calls["login"] += 1

        def send_message(self, m):
            calls["sends"].append(m)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    e = AlertEvent("d", "c", "oos", "超限", 1.0, time.time())
    make_email_handler("mail.host", 25, "", "", "to@x") (e)
    assert calls["starttls"] == 0, "默认不强制 STARTTLS"
    make_email_handler("mail.host", 587, "u", "p", "to@x", use_tls=True)(e)
    assert calls["starttls"] == 1, "use_tls=True 应调用 starttls"
    assert calls["login"] == 1
