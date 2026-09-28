"""采集编排 — 后台线程轮询 drivers → 总线发布 + SQLite 入库。

单线程串行轮询所有驱动（每驱动错误隔离），poll_interval 控制延迟上限；
验收: 设备→存储延迟 <500ms（Mock 高频下实测通常 <100ms）。
"""
import contextlib
import threading
import time
import logging

from core.devices.driver import DeviceDriver
from core.storage.timeseries import StreamingStatus, TimeseriesStore
from core.streaming.bus import StreamBus

logger = logging.getLogger(__name__)


class IngestRunner:
    def __init__(self, bus: StreamBus, store: TimeseriesStore,
                 drivers: list[DeviceDriver], poll_interval: float = 0.05,
                 raw_retention_s: float | None = None,
                 rollup_retention_s: float | None = None,
                 maintain_interval_s: float = 300.0, health=None,
                 auto_reconnect: bool = True):
        self.bus = bus
        self.store = store
        self.drivers = drivers
        self.poll_interval = poll_interval
        self.raw_retention_s = raw_retention_s
        self.rollup_retention_s = rollup_retention_s
        self.maintain_interval_s = max(1.0, float(maintain_interval_s))
        self.health = health                 # connectors.health.HealthRegistry | None
        self.auto_reconnect = auto_reconnect
        self.status = StreamingStatus()
        self.last_maintenance: dict | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_maintain = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        for d in self.drivers:
            try:
                d.open()
                if self.health is not None:
                    self.health.register(self._driver_name(d))
            except Exception:
                logger.exception("driver open failed: %s", d.name)
                if self.health is not None:
                    self.health.mark_error(self._driver_name(d), "open 失败")
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
            if self.health is not None:
                self.health.mark_stopped(self._driver_name(d))

    @staticmethod
    def _driver_name(driver) -> str:
        return str(getattr(driver, "name", None) or driver.__class__.__name__)

    def reconnect(self, name: str) -> bool:
        """手动重连（连接器健康页按钮）— 重开驱动并复位退避状态。"""
        driver = next((d for d in self.drivers if self._driver_name(d) == name), None)
        if driver is None:
            return False
        if self.health is not None:
            self.health.reset(name)
        try:
            with contextlib.suppress(Exception):
                driver.close()
            driver.open()
        except Exception as e:
            if self.health is not None:
                self.health.mark_error(name, f"手动重连失败: {e}")
            return False
        return True

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.time()
            for d in self.drivers:
                name = self._driver_name(d)
                if self.health is not None:
                    self.health.register(name)
                    if not self.health.should_poll(name):
                        continue          # 退避窗口内跳过（v3.8.0-⑦）
                    if not self._maybe_reconnect(d, name):
                        continue
                try:
                    samples = d.poll()
                except Exception:
                    logger.exception("driver poll failed: %s", d.name)
                    if self.health is not None:
                        self.health.mark_error(name, "poll 异常")
                    continue
                if self.health is not None:
                    self.health.mark_ok(name, len(samples or []))
                if samples:
                    self.bus.publish(d.name, samples)
                    self.store.insert_samples(samples)
                    self.status.report(samples)
            self._maybe_maintain(started)
            interval = self.poll_interval - (time.time() - started)
            if interval > 0:
                time.sleep(interval)

    def _maybe_reconnect(self, driver, name: str) -> bool:
        """退避到期后的自动重连 — 仅在上一轮失败且未恢复时执行。

        返回是否可以继续轮询该驱动（重连失败 → False，等下一个退避窗口）。
        """
        if not self.auto_reconnect or self.health is None:
            return True
        state = self.health.get(name)
        if state is None or not state.last_error:
            return True
        with contextlib.suppress(Exception):
            driver.close()
        try:
            driver.open()
        except Exception as e:
            logger.warning("auto reconnect failed: %s (%s)", name, e)
            self.health.mark_error(name, f"自动重连失败: {e}")
            return False
        return True

    def _maybe_maintain(self, now: float) -> None:
        """周期降采样 + 保留期清理（v3.8.0-⑥）；未配置保留期时跳过。"""
        if self.raw_retention_s is None and self.rollup_retention_s is None:
            return
        if now - self._last_maintain < self.maintain_interval_s:
            return
        self._last_maintain = now
        try:
            self.last_maintenance = self.store.maintain(
                self.raw_retention_s, self.rollup_retention_s, now=now)
        except Exception:
            logger.exception("timeseries maintenance failed")
