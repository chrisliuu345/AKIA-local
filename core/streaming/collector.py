"""采集编排 — 后台线程轮询 drivers → 总线发布 + SQLite 入库。

单线程串行轮询所有驱动（每驱动错误隔离），poll_interval 控制延迟上限；
验收: 设备→存储延迟 <500ms（Mock 高频下实测通常 <100ms）。
"""
import threading
import time
import logging

from core.devices.driver import DeviceDriver
from core.storage.timeseries import StreamingStatus, TimeseriesStore
from core.streaming.bus import StreamBus

logger = logging.getLogger(__name__)


class IngestRunner:
    def __init__(self, bus: StreamBus, store: TimeseriesStore,
                 drivers: list[DeviceDriver], poll_interval: float = 0.05):
        self.bus = bus
        self.store = store
        self.drivers = drivers
        self.poll_interval = poll_interval
        self.status = StreamingStatus()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        for d in self.drivers:
            try:
                d.open()
            except Exception:
                logger.exception("driver open failed: %s", d.name)
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ingest-runner")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        for d in self.drivers:
            try:
                d.close()
            except Exception:
                logger.exception("driver close failed: %s", d.name)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.time()
            for d in self.drivers:
                try:
                    samples = d.poll()
                except Exception:
                    logger.exception("driver poll failed: %s", d.name)
                    continue
                if samples:
                    self.bus.publish(d.name, samples)
                    self.store.insert_samples(samples)
                    self.status.report(samples)
            interval = self.poll_interval - (time.time() - started)
            if interval > 0:
                time.sleep(interval)
