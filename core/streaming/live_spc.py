"""实时 SPC 引擎 — 滚动窗口 + 增量检测（复用现有 I-MR / XBar-R 分析）。

feed() 一次吃一个批量，立即返回:
  - 控制图数据（window 内全部点 + CL/UCL/LCL）
  - 新增 Nelson 判异（窗口中点越线等）
  - OOC（判异）/ OOS（超规格）bool
跳变样本在 feed 同一调用内即报违规（P2 验收: 500ms 内）。
"""
from dataclasses import dataclass, field
from collections import deque

import pandas as pd


@dataclass
class LiveEvent:
    kind: str  # "nelson" | "ooc" | "oos"
    point: int
    desc: str
    value: float
    rule: int | str = 0


@dataclass
class LiveFrame:
    cl: float = 0.0
    ucl: float = 0.0
    lcl: float = 0.0
    data: list[float] = field(default_factory=list)
    violations: list[dict] = field(default_factory=list)
    events: list[LiveEvent] = field(default_factory=list)
    ooc: bool = False
    oos: bool = False
    point_index: int = 0
    chart: dict | None = None

    def as_chart_data(self, mode: str = "imr") -> dict:
        """输出给 create_control_chart 的 chart_data。"""
        code = {"imr": "I-MR", "xbar": "XBar-R"}.get(mode, "I-MR")
        out = {"chart_type": code}
        if mode == "xbar":
            out["xbar_chart"] = self.chart or {
                "data": self.data, "cl": self.cl, "ucl": self.ucl, "lcl": self.lcl,
                "violations": self.violations,
            }
        else:
            out["i_chart"] = self.chart or {
                "data": self.data, "cl": self.cl, "ucl": self.ucl, "lcl": self.lcl,
                "violations": self.violations,
            }
            out["mr_chart"] = {
                "data": [float("nan")] + [b - a for a, b in zip(self.data, self.data[1:], strict=False)],
                "cl": 0.0, "ucl": 0.0, "lcl": 0.0, "violations": [],
            }
        return out


class LiveSPC:
    """滚动窗口 SPC。mode: 'imr'（单值）或 'xbar'（子组 XBar-R）。"""

    def __init__(self, channel: str, mode: str = "imr", subgroup_size: int = 5,
                 window: int = 30, usl: float | None = None, lsl: float | None = None):
        self.channel = channel
        self.mode = mode
        self.subgroup_size = subgroup_size
        self.window = window
        self.usl = usl
        self.lsl = lsl
        self._buf: deque[float] = deque(maxlen=max(window, subgroup_size * 4))
        self._frame = LiveFrame()
        self._point_index = 0

    def reset(self) -> None:
        self._buf.clear()
        self._frame = LiveFrame()
        self._point_index = 0

    def feed(self, values: list[float]) -> LiveFrame:
        """批量喂入新采样值，返回最新帧与控制限。"""
        if not values:
            return self._frame
        self._buf.extend(float(v) for v in values)
        self._point_index += len(values)
        data = list(self._buf)
        # 新点在窗口内的起始序号（1-based）— 窗口满时从尾部定位
        first_new = max(1, len(data) - len(values) + 1)
        frame = LiveFrame(point_index=self._point_index, data=data)

        if len(data) >= 2:
            result = self._analyze(data)
            frame.cl, frame.ucl, frame.lcl = result["cl"], result["ucl"], result["lcl"]
            frame.violations = list(result["violations"])
            frame.chart = {"data": result["data"], "cl": result["cl"],
                           "ucl": result["ucl"], "lcl": result["lcl"],
                           "violations": result["violations"]}
            frame.events = self._detect(result, data, first_new)
            frame.ooc = any(e.kind in ("nelson", "ooc") for e in frame.events)
            frame.oos = any(e.kind == "oos" for e in frame.events)
        self._frame = frame
        return frame

    def _analyze(self, data: list[float]) -> dict:
        if self.mode == "xbar":
            from analysis.spc import xbar_r
            res = xbar_r.analyze(pd.Series(data), self.subgroup_size)
            xb = res["xbar_chart"]
            return {"data": xb["data"], "cl": xb["cl"], "ucl": xb["ucl"],
                    "lcl": xb["lcl"], "violations": xb["violations"]}
        from analysis.spc import imr
        res = imr.analyze(pd.Series(data))
        ic = res["i_chart"]
        return {"data": ic["data"], "cl": ic["cl"], "ucl": ic["ucl"],
                "lcl": ic["lcl"], "violations": ic["violations"]}

    def _detect(self, result: dict, data: list[float], first_new: int) -> list[LiveEvent]:
        """仅输出新增点（序号 >= first_new）上的事件，避免窗口重算刷屏。

        单点单事件: 同一新增点已报 nelson(规则1 越限)后不再叠加 ooc(极差越限)，
        防告警双发。
        """
        events: list[LiveEvent] = []
        seen_pts: set[int] = set()
        for v in result["violations"]:
            pt = int(v["point"])
            if pt < first_new:
                continue
            val = float(v.get("value")) if "value" in v else float(data[pt - 1])
            if v.get("rule") == "above_ucl" and pt in seen_pts:
                continue
            if v.get("rule") == "above_ucl":
                events.append(LiveEvent("ooc", pt, "极差/单值超上控制限", val, "mr"))
                seen_pts.add(pt)
            else:
                events.append(LiveEvent("nelson", pt, str(v.get("desc", "")), val, v.get("rule", 0)))
                seen_pts.add(pt)
        if (self.usl is not None or self.lsl is not None) and first_new <= len(data):
            for i in range(first_new - 1, len(data)):
                val = data[i]
                if self.usl is not None and val > self.usl:
                    events.append(LiveEvent("oos", i + 1, f"超规格上界 {self.usl}", val, "usl"))
                if self.lsl is not None and val < self.lsl:
                    events.append(LiveEvent("oos", i + 1, f"超规格下界 {self.lsl}", val, "lsl"))
        return events

    def recent_values(self) -> list[float]:
        return list(self._buf)
