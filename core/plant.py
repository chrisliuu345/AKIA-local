"""产线拓扑 — 产线→工位→设备/通道的 JSON 模型。

位置: data/plant.json（与 user_config.json 同目录规则）。不存在的字段
用默认配置兜底, 界面后编辑即生效。

v3.8.0 扩展: 工位节拍 / 产线成本参数 / 班次日历 + 表格行双向映射
（`plant_to_rows` / `rows_to_plant`），供桌面可视化配置与模板导入复用。
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

ROW_COLUMNS: list[tuple[str, str]] = [
    ("line", "产线"),
    ("station", "工位"),
    ("device", "设备/主题"),
    ("channels", "通道(逗号分隔)"),
    ("usl", "USL"),
    ("lsl", "LSL"),
    ("ideal_cycle_time_s", "节拍(s)"),
    ("unit_cost", "单位成本"),
    ("scrap_cost", "废品成本"),
    ("downtime_cost_per_min", "停机成本/分"),
    ("shift", "班次(如 08:00-20:00)"),
]

# 行内属于产线层（非工位层）的字段
_LINE_LEVEL_FIELDS = ("unit_cost", "scrap_cost", "downtime_cost_per_min", "shift")

DEFAULT_SAMPLE = {
    "lines": [
        {
            "name": "示例产线",
            "stations": [
                {"name": "工位A", "device": "mock-01", "channels": ["CH0"],
                 "usl": None, "lsl": None, "ideal_cycle_time_s": None},
                {"name": "工位B", "device": "mock-02", "channels": ["CH0"],
                 "usl": None, "lsl": None, "ideal_cycle_time_s": None},
            ],
        }
    ]
}


def _opt_float(value) -> float | None:
    """宽松数值解析 — 空串/None/非法值 → None。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_channels(value) -> list[str]:
    """通道字段解析 — 支持 list 或 'CH0, CH1' / 'CH0;CH1' 文本。"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).replace(";", ",").split(",")
            if part.strip()]


@dataclass
class Station:
    name: str
    device: str
    channels: list[str] = field(default_factory=list)
    usl: float | None = None
    lsl: float | None = None
    ideal_cycle_time_s: float | None = None


@dataclass
class Line:
    name: str
    stations: list[Station] = field(default_factory=list)
    ideal_cycle_time_s: float | None = None
    unit_cost: float = 0.0
    scrap_cost: float | None = None          # 单件废品损失（缺省 → unit_cost）
    downtime_cost_per_min: float = 0.0
    shift: str = ""                          # 班次窗口 "08:00-20:00"（缺省 → 全天）

    def cycle_time_for(self, station: Station | None = None) -> float | None:
        """有效节拍 — 工位优先，回退产线；均未配置 → None。"""
        if station is not None and station.ideal_cycle_time_s:
            return float(station.ideal_cycle_time_s)
        if self.ideal_cycle_time_s:
            return float(self.ideal_cycle_time_s)
        return None

    def loss_per_unit(self) -> float:
        """单件废品损失 — 未单独配置废品成本时按单位成本计。"""
        if self.scrap_cost is not None:
            return float(self.scrap_cost)
        return float(self.unit_cost or 0.0)


@dataclass
class PlantConfig:
    lines: list[Line] = field(default_factory=list)
    path: Path | None = None

    def to_dict(self) -> dict:
        return {"lines": [
            {"name": l.name,
             "ideal_cycle_time_s": l.ideal_cycle_time_s,
             "unit_cost": l.unit_cost,
             "scrap_cost": l.scrap_cost,
             "downtime_cost_per_min": l.downtime_cost_per_min,
             "shift": l.shift,
             "stations": [
                 {"name": s.name, "device": s.device, "channels": list(s.channels),
                  "usl": s.usl, "lsl": s.lsl,
                  "ideal_cycle_time_s": s.ideal_cycle_time_s} for s in l.stations
             ]} for l in self.lines
        ]}

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("未指定保存路径")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                          encoding="utf-8")

    def reload(self) -> "PlantConfig":
        """就地重读 JSON — 保持对象标识不变，看板/OEE/告警无需重新注入。"""
        fresh = self.load(self.path)
        self.lines = fresh.lines
        self.path = fresh.path
        return self

    @classmethod
    def load(cls, path: str | Path | None = None) -> "PlantConfig":
        target = Path(path) if path else default_plant_path()
        if path is None and not target.exists():
            _migrate_legacy_plant(target)
        if target.exists():
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                lines = [Line(name=l.get("name", "产线"), stations=[
                    Station(name=s.get("name", "工位"), device=s.get("device", ""),
                            channels=list(s.get("channels", [])),
                            usl=_opt_float(s.get("usl")), lsl=_opt_float(s.get("lsl")),
                            ideal_cycle_time_s=_opt_float(s.get("ideal_cycle_time_s")))
                    for s in l.get("stations", [])
                ], ideal_cycle_time_s=_opt_float(l.get("ideal_cycle_time_s")),
                    unit_cost=_opt_float(l.get("unit_cost")) or 0.0,
                    scrap_cost=_opt_float(l.get("scrap_cost")),
                    downtime_cost_per_min=_opt_float(l.get("downtime_cost_per_min")) or 0.0,
                    shift=str(l.get("shift") or ""))
                    for l in data.get("lines", [])]
                return cls(lines=lines, path=target)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("plant config 解析失败, 使用默认: %s", e)
        cfg = cls(lines=[Line(name=l["name"], stations=[
            Station(name=s["name"], device=s["device"], channels=list(s["channels"]),
                    usl=s.get("usl"), lsl=s.get("lsl")) for s in l["stations"]
        ]) for l in DEFAULT_SAMPLE["lines"]], path=target)
        return cfg


def default_plant_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "plant.json"


def legacy_plant_path() -> Path:
    """v3.7.0/3.7.1 误算路径（仓库上一级 data/）— 仅用于一次性迁移。"""
    return Path(__file__).resolve().parent.parent.parent / "data" / "plant.json"


def _migrate_legacy_plant(target: Path) -> bool:
    """把旧版误放位置的 plant.json 迁移到正确目录（成功返回 True）。"""
    legacy = legacy_plant_path()
    try:
        if not legacy.exists() or legacy == target:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info("plant config 迁移: %s → %s", legacy, target)
        return True
    except OSError as e:
        logger.warning("plant config 迁移失败: %s", e)
        return False


def plant_to_rows(cfg: PlantConfig) -> list[dict]:
    """PlantConfig → 表格行（可视化编辑器 / 模板导出共用）。"""
    rows: list[dict] = []
    for line in cfg.lines:
        for st in line.stations:
            rows.append({
                "line": line.name,
                "station": st.name,
                "device": st.device,
                "channels": ", ".join(st.channels),
                "usl": st.usl,
                "lsl": st.lsl,
                "ideal_cycle_time_s": st.ideal_cycle_time_s,
                "unit_cost": line.unit_cost,
                "scrap_cost": line.scrap_cost,
                "downtime_cost_per_min": line.downtime_cost_per_min,
                "shift": line.shift,
            })
    return rows


def rows_to_plant(rows: list[dict], path: str | Path | None = None) -> PlantConfig:
    """表格行 → PlantConfig。产线层字段按行内首个非空值归并（同产线一致）。"""
    lines: list[Line] = []
    index: dict[str, Line] = {}
    for raw in rows:
        line_name = str(raw.get("line") or "").strip()
        device = str(raw.get("device") or "").strip()
        if not line_name and not device:
            continue
        line = index.get(line_name or "默认产线")
        if line is None:
            line = Line(name=line_name or "默认产线")
            index[line.name] = line
            lines.append(line)
        for fname in _LINE_LEVEL_FIELDS:
            value = raw.get(fname)
            if value in (None, ""):
                continue
            if fname == "shift":
                line.shift = str(value).strip()
            else:
                parsed = _opt_float(value)
                if parsed is not None:
                    setattr(line, fname, parsed)
        if not device:
            # 无设备的行视为产线级参数行（节拍/成本）
            line.ideal_cycle_time_s = (_opt_float(raw.get("ideal_cycle_time_s"))
                                       or line.ideal_cycle_time_s)
            continue
        line.stations.append(Station(
            name=str(raw.get("station") or device).strip(),
            device=device,
            channels=_as_channels(raw.get("channels")),
            usl=_opt_float(raw.get("usl")),
            lsl=_opt_float(raw.get("lsl")),
            ideal_cycle_time_s=_opt_float(raw.get("ideal_cycle_time_s")),
        ))
    return PlantConfig(lines=lines, path=Path(path) if path else None)


def rows_from_excel(path: str | Path) -> list[dict]:
    """Excel/CSV 模板 → 表格行（表头用 ROW_COLUMNS 中文名或字段名）。"""
    import pandas as pd

    df = pd.read_csv(path) if str(path).lower().endswith(".csv") else pd.read_excel(path)
    alias = {label: key for key, label in ROW_COLUMNS}
    alias.update({key: key for key, _ in ROW_COLUMNS})
    out: list[dict] = []
    for _, series in df.iterrows():
        row = {}
        for col, value in series.items():
            key = alias.get(str(col).strip())
            if key is None or pd.isna(value):
                continue
            row[key] = value
        out.append(row)
    return out
