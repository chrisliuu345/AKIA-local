"""v3.8.0-⑤ 实时 OEE 真人化 — 节拍性能 P / 停机原因码 / 班次日历。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.devices.driver import Sample
from core.plant import Line, PlantConfig, Station
from core.streaming.bus import StreamBus
from core.streaming.downtime import DowntimeTracker
from core.streaming.oee_live import (
    LiveOEEComputer, parse_shift, shift_seconds_in_window,
)


def _plant(**line_kwargs):
    return PlantConfig(lines=[Line(name="L1", stations=[
        Station(name="S1", device="dev-a", channels=["CH0"], usl=110.0, lsl=90.0),
    ], **line_kwargs)])


def _feed(bus, n=10, base=100.0, interval=30.0, oos_every=0):
    now = time.time()
    samples = []
    for i in range(n):
        value = 200.0 if (oos_every and i % oos_every == 0) else base
        samples.append(Sample("dev-a", "CH0", value, now - (n - 1 - i) * interval))
    bus.publish("dev-a", samples)


# ---------- 班次日历 ----------

def test_parse_shift_forms():
    assert parse_shift("08:00-20:00") == (480, 1200)
    assert parse_shift("20:00-08:00") == (1200, 480)   # 跨零点
    assert parse_shift("") is None
    assert parse_shift("abc") is None
    assert parse_shift("25:00-08:00") is None


def test_shift_seconds_in_window_daytime():
    import datetime as dt
    start = dt.datetime(2026, 9, 10, 7, 0).timestamp()
    end = dt.datetime(2026, 9, 10, 9, 0).timestamp()
    # 08:00-20:00 班次内只覆盖 08:00-09:00 = 3600s
    assert shift_seconds_in_window("08:00-20:00", start, end) == pytest.approx(3600.0, abs=1)
    # 无班次 → 全窗口
    assert shift_seconds_in_window("", start, end) == pytest.approx(7200.0, abs=1)


def test_shift_seconds_crossing_midnight():
    import datetime as dt
    start = dt.datetime(2026, 9, 10, 23, 0).timestamp()
    end = dt.datetime(2026, 9, 11, 1, 0).timestamp()
    # 20:00-08:00 → 两小时全在班次内
    assert shift_seconds_in_window("20:00-08:00", start, end) == pytest.approx(7200.0, abs=1)


# ---------- 性能 P ----------

def test_performance_uses_cycle_time():
    bus = StreamBus()
    plant = _plant(ideal_cycle_time_s=30.0)
    oee = LiveOEEComputer(bus, plant, window_s=600.0)
    try:
        _feed(bus, n=10, interval=60.0)      # 10 件 / 600s 窗口
        m = oee.snapshot()["L1"]
        # P = 30s × 10 / 600s = 0.5
        assert m["performance"] == pytest.approx(0.5, abs=1e-3)
        assert m["ideal_cycle_time_s"] == 30.0
    finally:
        oee.stop()


def test_performance_defaults_to_one_without_cycle_time():
    bus = StreamBus()
    oee = LiveOEEComputer(bus, _plant(), window_s=600.0)
    try:
        _feed(bus)
        m = oee.snapshot()["L1"]
        assert m["performance"] == 1.0
        assert m["ideal_cycle_time_s"] is None
    finally:
        oee.stop()


def test_station_cycle_overrides_line_bottleneck():
    bus = StreamBus()
    plant = PlantConfig(lines=[Line(name="L1", ideal_cycle_time_s=10.0, stations=[
        Station(name="S1", device="dev-a", channels=["CH0"], ideal_cycle_time_s=60.0),
    ])])
    oee = LiveOEEComputer(bus, plant, window_s=600.0)
    try:
        _feed(bus, n=5, interval=120.0)
        m = oee.snapshot()["L1"]
        assert m["ideal_cycle_time_s"] == 60.0     # 瓶颈工位优先
        assert m["performance"] == pytest.approx(60.0 * 5 / 600.0, abs=1e-3)
    finally:
        oee.stop()


def test_performance_and_oee_never_exceed_one():
    """节拍配置偏大（或单位不一致）时 P 截断为 100%，OEE 不失真 >1。"""
    bus = StreamBus()
    plant = _plant(ideal_cycle_time_s=600.0)     # 极端节拍
    oee = LiveOEEComputer(bus, plant, window_s=600.0)
    try:
        _feed(bus, n=30, interval=20.0)
        m = oee.snapshot()["L1"]
        assert m["performance"] == 1.0
        assert 0.0 <= m["oee"] <= 1.0
    finally:
        oee.stop()


def test_out_of_shift_reports_no_oee():
    """班次外（计划时间为 0）→ A/P/OEE 归零并标记 in_shift=False。"""
    import datetime as dt
    midnight = dt.datetime.now().replace(hour=0, minute=0, second=0,
                                         microsecond=0).timestamp()
    now = midnight - 60                       # 今天 00:00 之前 = 昨天深夜
    bus = StreamBus()
    plant = _plant(shift="08:00-20:00", ideal_cycle_time_s=30.0)
    oee = LiveOEEComputer(bus, plant, window_s=600.0, now_fn=lambda: now)
    try:
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, now - 30),
                              Sample("dev-a", "CH0", 100.0, now - 10)])
        m = oee.snapshot()["L1"]
        assert m["in_shift"] is False and m["shift_active"] is False
        assert m["planned_s"] == 0.0
        assert m["availability"] == 0.0 and m["performance"] == 0.0
        assert m["oee"] == 0.0
        assert m["samples"] == 2              # 数据仍计入质量统计
    finally:
        oee.stop()


def test_quality_and_defects_counted():
    bus = StreamBus()
    oee = LiveOEEComputer(bus, _plant(), window_s=600.0)
    try:
        _feed(bus, n=10, interval=30.0, oos_every=5)   # 2 件超规格
        m = oee.snapshot()["L1"]
        assert m["defects"] == 2
        assert m["quality"] == pytest.approx(0.8, abs=1e-3)
    finally:
        oee.stop()


# ---------- 停机 ----------

def test_downtime_tracker_lifecycle():
    t = DowntimeTracker()
    rec = t.start("L1", "换型", ts=1000.0)
    assert t.is_down("L1")
    assert t.start("L1", "故障", ts=1010.0).reason == "换型"   # 已停机 → 原记录
    t.end("L1", ts=1060.0)
    assert not t.is_down("L1")
    assert rec.duration() == pytest.approx(60.0)
    assert t.end("L1") is None
    assert t.snapshot(now=1100.0)["L1"]["downtime_s"] == pytest.approx(60.0)
    assert t.breakdown(now=1100.0)["L1"]["换型"] == pytest.approx(60.0)


def test_downtime_unknown_reason_falls_back():
    t = DowntimeTracker()
    assert t.start("L1", "外星人入侵", ts=0.0).reason == "其他"
    assert t.normalize_reason("故障") == "故障"
    assert t.normalize_reason("") == "其他"


def test_downtime_window_overlap_clips():
    t = DowntimeTracker()
    t.start("L1", "故障", ts=100.0)
    t.end("L1", ts=200.0)
    # 窗口 [150, 250] → 重叠 50s
    assert t.downtime_seconds("L1", window_s=100.0, now=250.0) == pytest.approx(50.0)
    assert t.downtime_seconds("L1", now=1000.0) == pytest.approx(100.0)


def test_oee_availability_with_shift_and_downtime():
    bus = StreamBus()
    tracker = DowntimeTracker()
    plant = _plant(shift="00:00-23:59", ideal_cycle_time_s=30.0)
    oee = LiveOEEComputer(bus, plant, window_s=600.0, downtime=tracker)
    try:
        tracker.start("L1", "故障", ts=time.time() - 120)   # 最近 2 分钟停机
        _feed(bus, n=5, interval=60.0)
        m = oee.snapshot()["L1"]
        assert m["shift_active"] is True
        assert m["downtime_s"] == pytest.approx(120.0, abs=2)
        assert m["availability"] == pytest.approx((600 - 120) / 600, abs=0.02)
        assert m["run_time_s"] == pytest.approx(480.0, abs=2)
        assert m["performance"] == pytest.approx(30 * 5 / 480, abs=0.02)
        assert m["oee"] == pytest.approx(m["availability"] * m["performance"]
                                         * m["quality"], abs=1e-3)
        assert m["downtime_reason"] == "故障"
    finally:
        oee.stop()


def test_oee_legacy_behaviour_without_shift_keeps_availability():
    """向后兼容: 无班次/无节拍 → A 沿用样本口径(1.0), P=1.0。"""
    bus = StreamBus()
    oee = LiveOEEComputer(bus, _plant(), window_s=600.0)
    try:
        _feed(bus, n=3, interval=1.0, oos_every=3)
        m = oee.snapshot()["L1"]
        assert m["availability"] == 1.0
        assert m["performance"] == 1.0
        assert m["shift_active"] is False
        assert m["quality"] == pytest.approx(2 / 3, abs=1e-3)
    finally:
        oee.stop()


def test_oee_ignores_samples_outside_window_and_unknown_devices():
    bus = StreamBus()
    oee = LiveOEEComputer(bus, _plant(), window_s=60.0)
    try:
        now = time.time()
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, now - 3600)])
        bus.publish("other", [Sample("other", "CH0", 100.0, now)])
        m = oee.snapshot()["L1"]
        assert m["samples"] == 0 and m["oee"] == 0.0
    finally:
        oee.stop()
