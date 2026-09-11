"""v3.8.0-⑥ 数据保留与降采样 — 分钟聚合 / 幂等重算 / 保留期清理 / 采集接线。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.devices.driver import Sample
from core.storage.timeseries import TimeseriesStore
from core.streaming.bus import StreamBus
from core.streaming.collector import IngestRunner


@pytest.fixture
def store(tmp_path):
    s = TimeseriesStore(tmp_path / "ts.db")
    yield s
    s.close()


def _minute_samples(base_ts: float, bucket: int, values, device="dev-a",
                    channel="CH0"):
    return [Sample(device, channel, v, base_ts + bucket + i * 0.1)
            for i, v in enumerate(values)]


def test_rollup_aggregates_complete_buckets_only(store):
    t0 = (1_700_000_000 // 60) * 60.0    # 与分钟桶对齐
    # 两个完整分钟桶 + 一个尚未结束的桶
    store.insert_samples(_minute_samples(t0, 0, [1.0, 3.0]))
    store.insert_samples(_minute_samples(t0, 60, [5.0, 10.0, 0.0]))
    store.insert_samples(_minute_samples(t0, 120, [100.0]))
    assert store.rollup(bucket_s=60, until_ts=t0 + 120) == 2

    pts = store.query_rollup("dev-a")
    assert len(pts) == 2
    first, second = pts
    assert first.bucket_ts == t0 and first.avg == pytest.approx(2.0)
    assert first.min == 1.0 and first.max == 3.0 and first.n == 2
    assert second.avg == pytest.approx(5.0) and second.n == 3
    assert second.min == 0.0 and second.max == 10.0


def test_rollup_is_idempotent_and_recomputes(store):
    t0 = (1_700_000_000 // 60) * 60.0
    store.insert_samples(_minute_samples(t0, 0, [1.0]))
    store.rollup(bucket_s=60, until_ts=t0 + 60)
    store.rollup(bucket_s=60, until_ts=t0 + 60)
    assert store.count_rollup() == 1
    assert store.query_rollup("dev-a")[0].avg == pytest.approx(1.0)

    store.insert_samples(_minute_samples(t0, 0, [9.0]))
    store.rollup(bucket_s=60, until_ts=t0 + 60)
    assert store.count_rollup() == 1
    pt = store.query_rollup("dev-a")[0]
    assert pt.avg == pytest.approx(5.0) and pt.n == 2


def test_query_rollup_filters_channel_and_since(store):
    t0 = (1_700_000_000 // 60) * 60.0
    for ch in ("CH0", "CH1"):
        store.insert_samples(_minute_samples(t0, 0, [1.0], channel=ch))
        store.insert_samples(_minute_samples(t0, 60, [2.0], channel=ch))
    store.rollup(bucket_s=60, until_ts=t0 + 120)
    assert len(store.query_rollup("dev-a")) == 4
    assert len(store.query_rollup("dev-a", "CH1")) == 2
    assert len(store.query_rollup("dev-a", since_ts=t0 + 60)) == 2
    assert len(store.query_rollup("dev-a", limit=1)) == 1
    assert store.query_rollup("missing") == []
    assert store.query_rollup("dev-a")[0].as_dict()["ch"] == "CH0"


def test_maintain_rolls_up_then_prunes_raw(store):
    now = time.time()
    old = (now - 3 * 86400) // 60 * 60      # 与分钟桶对齐，两行落入同桶
    store.insert_samples([Sample("dev-a", "CH0", 1.0, old),
                          Sample("dev-a", "CH0", 3.0, old + 10)])
    store.insert_samples([Sample("dev-a", "CH0", 9.0, now - 1)])

    result = store.maintain(raw_retention_s=86400, rollup_retention_s=30 * 86400,
                            now=now)
    assert result["rolled_buckets"] >= 1
    assert result["pruned_raw"] == 2          # 3 天前的原始点被清理
    assert store.count("dev-a") == 1          # 最近点保留
    assert store.count_rollup("dev-a") == 1   # 聚合点保留
    assert store.query_rollup("dev-a")[0].n == 2


def test_maintain_prunes_expired_rollups(store):
    now = time.time()
    old = now - 40 * 86400
    store.insert_samples([Sample("d", "CH0", 1.0, old)])
    store.maintain(raw_retention_s=None, rollup_retention_s=7 * 86400, now=now)
    assert store.count("d") == 1              # 未配置原始保留 → 不动
    assert store.count_rollup("d") == 0       # 聚合点超期清理


def test_ingest_runner_calls_maintenance(tmp_path):
    calls = []

    class FakeStore:
        def insert_samples(self, samples):
            return len(samples)

        def maintain(self, raw_retention_s=None, rollup_retention_s=None, now=None):
            calls.append((raw_retention_s, rollup_retention_s))
            return {"rolled_buckets": 1, "pruned_raw": 0, "pruned_rollup": 0}

    class OneShotDriver:
        name = "fake"

        def __init__(self):
            self.done = False

        def open(self):
            pass

        def poll(self):
            if self.done:
                return []
            self.done = True
            return [Sample("fake", "CH0", 1.0, time.time())]

        def close(self):
            pass

    runner = IngestRunner(StreamBus(), FakeStore(), [OneShotDriver()],
                          poll_interval=0.01, raw_retention_s=60.0,
                          rollup_retention_s=600.0, maintain_interval_s=1.0)
    runner.start()
    deadline = time.time() + 3
    while time.time() < deadline and not calls:
        time.sleep(0.05)
    runner.stop()
    assert calls and calls[0] == (60.0, 600.0)
    assert runner.last_maintenance["rolled_buckets"] == 1


def test_ingest_runner_skips_maintenance_when_unconfigured(tmp_path):
    class FakeStore:
        def insert_samples(self, samples):
            return len(samples)

        def maintain(self, *a, **kw):
            raise AssertionError("未配置保留期时不应调用 maintain")

    class SilentDriver:
        name = "silent"

        def open(self):
            pass

        def poll(self):
            return []

        def close(self):
            pass

    runner = IngestRunner(StreamBus(), FakeStore(), [SilentDriver()],
                          poll_interval=0.01, maintain_interval_s=0.01)
    runner.start()
    time.sleep(0.1)
    runner.stop()
    assert runner.last_maintenance is None
