"""v3.8.0-④ 成本损失估算 — 超规格 × 单件损失 + 停机成本 + /api/cost。"""
import json
import os
import time
import urllib.request

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.devices.driver import Sample
from core.plant import Line, PlantConfig, Station
from core.streaming.bus import StreamBus
from core.streaming.cost import CostAnalyzer
from core.streaming.downtime import DowntimeTracker
from core.streaming.oee_live import LiveOEEComputer
from core.storage.timeseries import TimeseriesStore


def _plant():
    return PlantConfig(lines=[Line(
        name="L1", unit_cost=12.5, scrap_cost=20.0, downtime_cost_per_min=3.0,
        stations=[Station(name="S1", device="dev-a", channels=["CH0"],
                          usl=110.0, lsl=90.0)])])


def _samples(values):
    now = time.time()
    return [Sample("dev-a", "CH0", v, now - len(values) + i)
            for i, v in enumerate(values)]


def test_count_defects_handles_bounds_and_missing_spec():
    samples = _samples([100.0, 111.0, 89.0, 110.0, 90.0])
    assert CostAnalyzer.count_defects(samples, 110.0, 90.0) == 2   # 边界不算超差
    assert CostAnalyzer.count_defects(samples, None, None) == 0
    assert CostAnalyzer.count_defects(samples, 110.0, None) == 1
    assert CostAnalyzer.count_defects([100.0, 101.0], None, 100.0) == 0


def test_estimate_line_known_values():
    analyzer = CostAnalyzer(_plant(), currency="CNY")
    est = analyzer.estimate_line(_plant().lines[0],
                                 {"dev-a": _samples([100.0, 120.0, 120.0, 100.0])})
    assert est.samples == 4 and est.defects == 2
    assert est.defect_rate == 0.5
    assert est.scrap_loss == pytest.approx(40.0)      # 2 × 20.0（废品成本优先）
    assert est.downtime_loss == 0.0
    assert est.total_loss == pytest.approx(40.0)
    assert est.currency == "CNY"
    data = est.as_dict()
    assert data["line"] == "L1" and "total_loss" in data


def test_scrap_cost_defaults_to_unit_cost():
    plant = PlantConfig(lines=[Line(name="L", unit_cost=7.0, stations=[
        Station(name="S", device="d", channels=["CH0"], usl=10.0)])])
    analyzer = CostAnalyzer(plant)
    est = analyzer.estimate_line(plant.lines[0], {"d": _samples([11.0, 11.0, 1.0])})
    assert est.defects == 2
    assert est.scrap_loss == pytest.approx(14.0)


def test_downtime_cost_from_tracker():
    tracker = DowntimeTracker()
    tracker.start("L1", "故障", ts=time.time() - 300)
    tracker.end("L1", ts=time.time() - 60)      # 4 分钟停机
    analyzer = CostAnalyzer(_plant(), downtime=tracker)
    est = analyzer.estimate_line(_plant().lines[0], {"dev-a": _samples([100.0])})
    assert est.downtime_min == pytest.approx(4.0, abs=0.05)
    assert est.downtime_loss == pytest.approx(12.0, abs=0.2)
    assert est.total_loss == pytest.approx(12.0, abs=0.2)


def test_estimate_prefers_oee_snapshot():
    analyzer = CostAnalyzer(_plant())
    snapshot = {"L1": {"samples": 100, "defects": 5, "downtime_s": 120.0}}
    out = analyzer.estimate({}, snapshot)["L1"]
    assert out["samples"] == 100 and out["defects"] == 5
    assert out["defect_rate"] == 0.05
    assert out["scrap_loss"] == pytest.approx(100.0)     # 5 × 20.0


def test_estimate_without_data_is_zero():
    analyzer = CostAnalyzer(_plant())
    out = analyzer.estimate({}, None)["L1"]
    assert out["defects"] == 0 and out["total_loss"] == 0.0


def test_cost_api_reports_losses():
    from server.app import start_thread, stop_thread

    bus = StreamBus()
    store = TimeseriesStore(os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                         "qa_cost_api.db"))
    plant = _plant()
    tracker = DowntimeTracker()
    oee = LiveOEEComputer(bus, plant, window_s=600.0, downtime=tracker)
    port = 18770
    thread = start_thread(bus, store, host="127.0.0.1", port=port, plant=plant,
                          oee=oee, downtime=tracker)
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url + "/api/cost", timeout=1).read()
            break
        except Exception:
            time.sleep(0.2)
    else:
        pytest.fail("server did not start")
    try:
        bus.publish("dev-a", _samples([100.0, 120.0]))
        tracker.start("L1", "缺料", ts=time.time() - 60)
        raw = urllib.request.urlopen(url + "/api/cost", timeout=3).read()
        line = json.loads(raw)["lines"]["L1"]
        assert line["defects"] == 1
        assert line["scrap_loss"] == pytest.approx(20.0)
        assert line["downtime_min"] == pytest.approx(1.0, abs=0.1)

        # 停机记录 API（v3.8.0-⑤）
        req = urllib.request.Request(
            url + "/api/downtime",
            data=json.dumps({"line": "L1", "action": "end"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        assert json.loads(urllib.request.urlopen(req, timeout=3).read())["ok"] is True
        raw = urllib.request.urlopen(url + "/api/oee", timeout=3).read()
        oee_payload = json.loads(raw)
        assert "downtime" in oee_payload
        assert oee_payload["lines"]["L1"]["defects"] == 1
    finally:
        stop_thread(thread)
        oee.stop()
        store.close()
