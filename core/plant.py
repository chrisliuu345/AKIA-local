"""产线拓扑 — 产线→工位→设备/通道的 JSON 模型。

位置: data/plant.json（与 user_config.json 同目录规则）。不存在的字段
用默认配置兜底, 界面后编辑即生效。
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE = {
    "lines": [
        {
            "name": "示例产线",
            "stations": [
                {"name": "工位A", "device": "mock-01", "channels": ["CH0"],
                 "usl": None, "lsl": None},
                {"name": "工位B", "device": "mock-02", "channels": ["CH0"],
                 "usl": None, "lsl": None},
            ],
        }
    ]
}


@dataclass
class Station:
    name: str
    device: str
    channels: list[str] = field(default_factory=list)
    usl: float | None = None
    lsl: float | None = None


@dataclass
class Line:
    name: str
    stations: list[Station] = field(default_factory=list)


@dataclass
class PlantConfig:
    lines: list[Line] = field(default_factory=list)
    path: Path | None = None

    def to_dict(self) -> dict:
        return {"lines": [
            {"name": l.name, "stations": [
                {"name": s.name, "device": s.device, "channels": list(s.channels),
                 "usl": s.usl, "lsl": s.lsl} for s in l.stations
            ]} for l in self.lines
        ]}

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("未指定保存路径")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                          encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "PlantConfig":
        target = Path(path) if path else default_plant_path()
        if target.exists():
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                lines = [Line(name=l.get("name", "产线"), stations=[
                    Station(name=s.get("name", "工位"), device=s.get("device", ""),
                            channels=list(s.get("channels", [])),
                            usl=s.get("usl"), lsl=s.get("lsl"))
                    for s in l.get("stations", [])
                ]) for l in data.get("lines", [])]
                return cls(lines=lines, path=target)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("plant config 解析失败, 使用默认: %s", e)
        cfg = cls(lines=[Line(name=l["name"], stations=[
            Station(name=s["name"], device=s["device"], channels=list(s["channels"]),
                    usl=s.get("usl"), lsl=s.get("lsl")) for s in l["stations"]
        ]) for l in DEFAULT_SAMPLE["lines"]], path=target)
        return cfg


def default_plant_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "plant.json"
