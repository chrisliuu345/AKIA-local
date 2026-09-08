"""设备驱动抽象层 — DeviceDriver 统一接口，底层协议可替换。

Driver 契约: open() → poll() 增量读取 → close()。poll 返回自上次以来的全部新
采样，无新数据返回空列表，非阻塞。
"""
import abc
import math
import random
import time
from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True)
class Sample:
    device: str
    channel: str
    value: float
    ts: float


class DeviceDriver(abc.ABC):
    name: str = "driver"

    @abc.abstractmethod
    def open(self) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @abc.abstractmethod
    def poll(self) -> list[Sample]: ...

    @property
    def state(self) -> str:
        return "running"


class MockDriver(DeviceDriver):
    """可调速率/波形的仿真采集器，供测试与无硬件演示。

    按时间推进采样（不 sleep），支持跳变注入（OOC 模拟）。
    """

    def __init__(self, name: str = "mock-01", channels: tuple[str, ...] = ("CH0", "CH1"),
                 rate_hz: float = 100.0, mean: float = 100.0, amplitude: float = 5.0,
                 freq_hz: float = 0.5, noise: float = 0.2):
        self.name = name
        self.channels = tuple(channels)
        self.rate_hz = rate_hz
        self.mean = mean
        self.amplitude = amplitude
        self.freq_hz = freq_hz
        self.noise = noise
        self._t0 = 0.0
        self._last_ts = 0.0
        self._seen = 0
        self.jump_value = 0.0
        self.jump_until = 0.0
        self._closed = False

    def open(self) -> None:
        self._t0 = time.time()
        self._last_ts = self._t0

    def close(self) -> None:
        self._closed = True

    def inject_jump(self, amount: float, duration: float = 1.0) -> None:
        """注入常数偏移 — 生产 OOC/OOS 样本。"""
        self.jump_value = amount
        self.jump_until = time.time() + duration

    def poll(self) -> list[Sample]:
        if self._closed:
            return []
        now = time.time()
        interval = 1.0 / self.rate_hz
        if now - self._last_ts < interval:
            return []
        samples: list[Sample] = []
        while True:
            next_ts = self._last_ts + interval
            if next_ts > now:
                break
            self._last_ts = next_ts
            jump = self.jump_value if next_ts < self.jump_until else 0.0
            for ci, channel in enumerate(self.channels):
                value = self.mean
                if self.amplitude:
                    value += self.amplitude * math.sin(
                        2 * math.pi * self.freq_hz * next_ts + ci * math.pi / 2)
                value += random.gauss(0, self.noise) + jump
                samples.append(Sample(self.name, channel, value, next_ts))
            self._seen += 1
        return samples


class MonitorAdapterDriver(DeviceDriver):
    """桥接现有 DeviceMonitor 的 Esp32InputDevice — 增量转 Sample。"""

    def __init__(self, device, on_event: Callable | None = None):
        from core.devices.device import Esp32InputDevice
        self.device = device
        self.name = device.device_id
        self._channels: list[str] = []
        self._drained = 0
        self._on_event = on_event
        self._is_input = isinstance(device, Esp32InputDevice)

    def open(self) -> None:
        self.update_channels()

    def close(self) -> None:
        self._on_event = None

    def update_channels(self) -> None:
        if self._is_input:
            self._channels = list(self.device.channel_labels())

    def poll(self) -> list[Sample]:
        if not self._is_input:
            return []
        data = self.device.get_recent_data(self.device.data_count)
        if not data:
            return []
        total = self.device.data_count
        if self._drained >= total:
            return []
        new_samples = data[self._drained:]
        self._drained = total
        if not self._channels:
            self.update_channels()
        labels = self._channels or [f"CH{i}" for i in range(max(len(s) for s in new_samples))]
        samples: list[Sample] = []
        now = time.time()
        for row in new_samples:
            for i, value in enumerate(row):
                channel = labels[i] if i < len(labels) else f"CH{i}"
                samples.append(Sample(self.device.device_id, channel, float(value), now))
        return samples

    @property
    def state(self) -> str:
        if self.device.transport and self.device.transport.is_open():
            return "running"
        return "idle"
