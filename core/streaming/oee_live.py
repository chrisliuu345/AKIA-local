"""实时 OEE 看板 — 产线级运行指标（滑动窗口）。

availability: 线上工位有数据(在产)样本占比
performance:  无节拍数据时报告为 1.0（规划: 未来由节拍测算填入）
quality:      1 - 超规格样本占比
OEE = A × P × Q；窗口默认最近 10 分钟。
"""
import time

from core.plant import PlantConfig
from core.streaming.bus import StreamBus


class LiveOEEComputer:
    def __init__(self, bus: StreamBus, plant: PlantConfig, window_s: float = 600.0):
        self.bus = bus
        self.plant = plant
        self.window_s = window_s
        self._buf: dict[str, list[tuple[float, bool, bool]]] = {}
        self._unsub = bus.subscribe(None, self._on_samples)

    def _on_samples(self, samples: list) -> None:
        now = time.time()
        for s in samples:
            key = self._line_for_device(s.device)
            if key is None:
                continue
            # 通道规格限查表
            usl, lsl = self._spec_for(s.device, s.channel)
            oos = (usl is not None and s.value > usl) or (lsl is not None and s.value < lsl)
            self._buf.setdefault(key, []).append((s.ts, True, oos))
        cutoff = now - self.window_s
        for key in list(self._buf):
            self._buf[key] = [it for it in self._buf[key] if it[0] >= cutoff]
            if not self._buf[key]:
                del self._buf[key]

    def stop(self):
        self._unsub()

    def snapshot(self) -> dict:
        now = time.time()
        out = {}
        for line in self.plant.lines:
            key = line.name
            data = [it for it in self._buf.get(key, []) if it[0] >= now - self.window_s]
            total = len(data)
            if total == 0:
                out[key] = {"availability": 0.0, "performance": 1.0,
                            "quality": 1.0, "oee": 0.0, "samples": 0}
                continue
            availability = sum(1 for _t, ok, _o in data if ok) / total
            quality = 1.0 - sum(1 for _t, _o, o in data if o) / total
            performance = 1.0
            out[key] = {
                "availability": round(availability, 4),
                "performance": performance,
                "quality": round(quality, 4),
                "oee": round(availability * performance * quality, 4),
                "samples": total,
            }
        return out

    def _line_for_device(self, device: str) -> str | None:
        for line in self.plant.lines:
            if any(st.device == device for st in line.stations):
                return line.name
        return None

    def _spec_for(self, device: str, channel: str):
        for line in self.plant.lines:
            for st in line.stations:
                if st.device == device and channel in st.channels:
                    return st.usl, st.lsl
        return None, None
