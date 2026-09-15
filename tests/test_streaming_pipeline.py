"""P1 验收 — 设备驱动 / 数据流总线 / SQLite 时序层 / 采集编排 端到端。

验收对应: 数据流延迟 <500ms（设备→存储）· 批量入库 · 订阅回填 · Mock 跳变。
"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")  # 项目测试惯例（本模块不依赖 Qt，保持一致性）

from core.devices.driver import Sample
from core.devices.driver import MockDriver
from core.storage.timeseries import TimeseriesStore, default_store_path, StreamingStatus
from core.streaming.bus import StreamBus
from core.streaming.collector import IngestRunner


@pytest.fixture
def store(tmp_path):
    s = TimeseriesStore(tmp_path / "ts.db")
    yield s
    s.close()


def test_mock_driver_generates_rate_bounded_samples(tmp_path):
    d = MockDriver(name="mock-01", rate_hz=100.0, channels=("CH0",))
    d.open()
    time.sleep(0.05)
    samples = d.poll()
    d.close()
    assert len(samples) >= 1
    assert all(s.device == "mock-01" and s.channel == "CH0" for s in samples)
    # 速率约束: 0.1s 内不应超过 ~15 个采样（100Hz, 允许抖动）
    assert len(samples) <= 30
    ts = [s.ts for s in samples]
    assert ts == sorted(ts)


def test_mock_jump_produces_offset_samples():
    d = MockDriver(name="mock-01", rate_hz=50.0, channels=("CH0", "CH1"))
    d.open()
    time.sleep(0.02)
    normal = d.poll()
    # 跳变窗口放宽到 0.6s：避免满载回归时调度抖动把窗口耗尽（原 0.1s 会偶发失败）
    d.inject_jump(10.0, duration=0.6)
    time.sleep(0.1)
    jumped = d.poll()
    d.close()
    assert jumped, "跳变窗口内应采到样本"
    assert any(s.value > 108.0 for s in jumped), "跳变期间应有 >108 的样本"
    assert not any(s.value > 108.0 for s in normal), "注入前的基线样本不应带跳变"


def test_bus_publish_subscribe_and_recent():
    bus = StreamBus(maxlen=10)
    got = []
    unsub = bus.subscribe("mock-01", got.append)
    s1 = Sample("mock-01", "CH0", 1.0, 1.0)
    s2 = Sample("mock-01", "CH0", 2.0, 2.0)
    bus.publish("mock-01", [s1])
    assert got == [[s1]]
    bus.publish("mock-01", [s2])
    assert got == [[s1], [s2]]
    assert bus.recent("mock-01", n=1) == [s2]
    assert unsub() is True and unsub() is False
    bus.publish("mock-01", [s1])
    assert len(got) == 2  # 退订后不再收到


def test_bus_ring_buffer_caps_memory():
    bus = StreamBus(maxlen=5)
    bus.publish("t", [Sample("d", "c", float(i), float(i)) for i in range(20)])
    recent = bus.recent("t")
    assert len(recent) == 5
    assert recent[-1].value == 19.0 and recent[0].value == 15.0


def test_store_roundtrip_and_query(store):
    samples = [Sample("dev", "CH0", float(i), 1000.0 + i) for i in range(5)]
    store.insert_samples(samples)
    assert store.count("dev") == 5
    got = store.query("dev", "CH0")
    assert [s.value for s in got] == [0.0, 1.0, 2.0, 3.0, 4.0]
    got = store.query("dev", "CH0", since_ts=1002.0)
    assert [s.value for s in got] == [2.0, 3.0, 4.0]
    got = store.query("dev", "CH0", limit=2)
    assert [s.value for s in got] == [0.0, 1.0]
    # 持久化: 重开库仍可查
    store2 = TimeseriesStore(store._path)
    assert store2.count("dev") == 5
    store2.close()


def test_filter_by_channel_and_prune(store):
    store.insert_samples([
        Sample("dev", "CH0", 1.0, 1.0),
        Sample("dev", "CH1", 2.0, 1.0),
        Sample("dev", "CH0", 3.0, 2.0),
    ])
    assert len(store.query("dev", "CH1")) == 1
    deleted = store.prune_older_than(1.5)
    assert deleted == 2, "B5: prune 应返回实际删除行数"
    assert len(store.query("dev")) == 1


def test_ingest_pipeline_end_to_end(tmp_path):
    store = TimeseriesStore(tmp_path / "pipe.db")
    bus = StreamBus()
    received = []
    bus.subscribe("mock-01", lambda batch: received.extend(batch))
    runner = IngestRunner(bus, store, [MockDriver(name="mock-01", rate_hz=200.0)],
                          poll_interval=0.01)
    runner.start()
    time.sleep(0.4)
    runner.stop()
    assert store.count("mock-01") > 20
    assert len(received) == store.count("mock-01")
    # 验收: 设备(采样生成)→存储 延迟 <500ms
    assert runner.status.max_latency_ms < 500.0, \
        f"max latency {runner.status.max_latency_ms:.1f}ms 超出验收标准"
    assert runner.status.samples_total > 20
    assert not runner.is_running()


def test_ingest_isolates_failing_driver(tmp_path):
    store = TimeseriesStore(tmp_path / "iso.db")
    bus = StreamBus()

    class BrokenDriver(MockDriver):
        def poll(self):
            raise RuntimeError("boom")

    ok = MockDriver(name="ok", rate_hz=100.0)
    runner = IngestRunner(bus, store, [BrokenDriver(name="bad", rate_hz=10.0), ok],
                          poll_interval=0.01)
    runner.start()
    time.sleep(0.2)
    runner.stop()
    assert store.count("ok") > 0  # 坏驱动不影响好驱动入库


def test_status_latency_report():
    st = StreamingStatus()
    now = time.time()
    st.report([Sample("d", "c", 1.0, now - 0.1)])
    assert st.last_latency_ms == pytest.approx(100.0, abs=5.0)
    assert st.samples_total == 1


def test_default_store_path():
    p = default_store_path()
    assert "QA-Tool" in str(p) and p.name == "timeseries.db"
