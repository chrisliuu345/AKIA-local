"""实时 OEE 看板 — 产线级运行指标（滑动窗口）。

v3.8.0-⑤ 「真人化」:
  availability: 有班次日历时 = (计划时间 − 停机时间) / 计划时间；无班次沿用
                样本占比（向后兼容 v3.7.0 行为）
  performance:  配置节拍(ideal_cycle_time_s)时 = 节拍 × 产量 / 运行时间；
                未配置节拍时报告 1.0（避免伪精确）
  quality:      1 − 超规格样本占比
  OEE = A × P × Q；窗口默认最近 10 分钟。
"""
import time
from datetime import datetime, timedelta

from core.plant import PlantConfig
from core.streaming.bus import StreamBus


def parse_shift(shift: str) -> tuple[int, int] | None:
    """解析班次窗口 "08:00-20:00" → (开始分钟, 结束分钟)；非法 → None。

    支持跨零点（如 "20:00-08:00"：结束分钟 < 开始分钟）。
    """
    text = (shift or "").strip().replace("~", "-").replace("—", "-")
    if not text or "-" not in text:
        return None
    start_s, _, end_s = text.partition("-")
    try:
        sh, sm = (int(x) for x in start_s.strip().split(":")[:2])
        eh, em = (int(x) for x in end_s.strip().split(":")[:2])
    except (ValueError, TypeError):
        return None
    if not (0 <= sh < 24 and 0 <= sm < 60 and 0 <= eh < 24 and 0 <= em < 60):
        return None
    return sh * 60 + sm, eh * 60 + em


def shift_seconds_in_window(shift: str, start_ts: float, end_ts: float) -> float:
    """[start_ts, end_ts] 与班次日历的有效重叠秒数（无班次 → 全窗口）。"""
    win = parse_shift(shift)
    if win is None or end_ts <= start_ts:
        return max(0.0, end_ts - start_ts)
    start_min, end_min = win
    if end_min == start_min:
        return 0.0
    cur = datetime.fromtimestamp(start_ts).replace(hour=0, minute=0, second=0,
                                                   microsecond=0)
    total = 0.0
    while cur.timestamp() < end_ts:
        day_start = cur
        if end_min > start_min:
            s = day_start + timedelta(minutes=start_min)
            e = day_start + timedelta(minutes=end_min)
            total += max(0.0, min(e.timestamp(), end_ts)
                         - max(s.timestamp(), start_ts))
        else:  # 跨零点: [start, 24:00) + [00:00, end)
            s1 = day_start + timedelta(minutes=start_min)
            e1 = day_start + timedelta(days=1)
            total += max(0.0, min(e1.timestamp(), end_ts)
                         - max(s1.timestamp(), start_ts))
            e2 = day_start + timedelta(minutes=end_min)
            total += max(0.0, min(e2.timestamp(), end_ts)
                         - max(day_start.timestamp(), start_ts))
        cur = day_start + timedelta(days=1)
    return max(0.0, min(total, end_ts - start_ts))


class LiveOEEComputer:
    def __init__(self, bus: StreamBus, plant: PlantConfig, window_s: float = 600.0,
                 downtime=None, now_fn=None):
        self.bus = bus
        self.plant = plant
        self.window_s = window_s
        self.downtime = downtime
        self._now = now_fn or time.time
        # (ts, 在产标记, 超规格标记, 设备) — 在产标记恒真表示"有数据即在产"
        self._buf: dict[str, list[tuple[float, bool, bool, str]]] = {}
        self._unsub = bus.subscribe(None, self._on_samples)

    def _on_samples(self, samples: list) -> None:
        now = self._now()
        for s in samples:
            key = self._line_for_device(s.device)
            if key is None:
                continue
            usl, lsl = self._spec_for(s.device, s.channel)
            oos = (usl is not None and s.value > usl) or (lsl is not None and s.value < lsl)
            self._buf.setdefault(key, []).append((s.ts, True, oos, s.device))
        cutoff = now - self.window_s
        for key in list(self._buf):
            self._buf[key] = [it for it in self._buf[key] if it[0] >= cutoff]
            if not self._buf[key]:
                del self._buf[key]

    def stop(self):
        self._unsub()

    def snapshot(self) -> dict:
        now = self._now()
        out = {}
        for line in self.plant.lines:
            key = line.name
            data = [it for it in self._buf.get(key, []) if it[0] >= now - self.window_s]
            total = len(data)
            downtime_s = 0.0
            reason = ""
            if self.downtime is not None:
                downtime_s = self.downtime.downtime_seconds(key, self.window_s, now)
                current = self.downtime.current(key)
                reason = current.reason if current is not None else ""
            if total == 0:
                out[key] = {"availability": 0.0, "performance": 1.0,
                            "quality": 1.0, "oee": 0.0, "samples": 0,
                            "defects": 0, "downtime_s": round(downtime_s, 2),
                            "downtime_reason": reason, "pieces": 0,
                            "run_time_s": 0.0, "shift_active": False,
                            "shift_configured": bool(parse_shift(line.shift)),
                            "in_shift": False, "planned_s": 0.0,
                            "ideal_cycle_time_s": line.ideal_cycle_time_s}
                continue
            defects = sum(1 for _t, _ok, oos, _d in data if oos)
            quality = 1.0 - defects / total
            availability, planned_s = self._availability(line, data, total,
                                                         downtime_s, now)
            run_time_s = max(0.0, planned_s - downtime_s)
            cycle = self._effective_cycle_time(line, data)
            shift_cfg = bool(parse_shift(line.shift))
            in_shift = shift_cfg and planned_s > 0
            # 已配置班次但当前在班次外（计划时间 0）→ 不计入 OEE，
            # 避免用非计划时间粉饰效率；未配置班次则沿用样本口径。
            out_of_shift = shift_cfg and not in_shift
            performance = (0.0 if out_of_shift
                           else self._performance(cycle, total, run_time_s))
            out[key] = {
                "availability": round(availability, 4),
                "performance": round(performance, 4),
                "quality": round(quality, 4),
                "oee": round(min(1.0, max(0.0, availability * performance
                                           * quality)), 4),
                "samples": total,
                "defects": defects,
                "downtime_s": round(downtime_s, 2),
                "downtime_reason": reason,
                "pieces": total,
                "run_time_s": round(run_time_s, 2),
                "planned_s": round(planned_s, 2),
                "in_shift": in_shift,
                "shift_configured": shift_cfg,
                "shift_active": in_shift,
                "ideal_cycle_time_s": cycle,
            }
        return out

    def _availability(self, line, data, total: int, downtime_s: float,
                      now: float) -> tuple[float, float]:
        """返回 (可用率, 计划时长秒)。"""
        if parse_shift(line.shift):
            planned = shift_seconds_in_window(line.shift, now - self.window_s, now)
            if planned <= 0:
                return 0.0, 0.0
            return max(0.0, min(1.0, (planned - downtime_s) / planned)), planned
        # 无班次日历 → 沿用 v3.7.0 样本占比口径
        in_production = sum(1 for _t, ok, _o, _d in data if ok)
        return (in_production / total if total else 0.0), float(self.window_s)

    @staticmethod
    def _effective_cycle_time(line, data) -> float | None:
        """产线节拍 — 取有数据的工位节拍最大值（瓶颈工位），回退产线节拍。"""
        devices = {d for _t, _ok, _o, d in data}
        cycles = [line.cycle_time_for(st) for st in line.stations
                  if st.device in devices]
        cycles = [c for c in cycles if c]
        if cycles:
            return max(cycles)
        return line.ideal_cycle_time_s or None

    def _performance(self, cycle: float | None, pieces: int,
                     run_time_s: float) -> float:
        if not cycle or run_time_s <= 0:
            return 1.0
        # 节拍配置偏大 / 单位不一致时比值会 >1；按 100% 截断，否则 OEE 会失真 >1
        return max(0.0, min(1.0, (float(cycle) * pieces) / run_time_s))

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
