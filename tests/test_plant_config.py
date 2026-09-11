"""v3.8.0-② 产线配置 — 表格行双向映射 / 扩展字段持久化 / 可视化编辑器。
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.plant import (
    Line, PlantConfig, PlantConfig as _PC, ROW_COLUMNS, Station,
    default_plant_path, legacy_plant_path, plant_to_rows, rows_from_excel,
    rows_to_plant,
)


def _cfg():
    return PlantConfig(lines=[
        Line(name="1号线", stations=[
            Station(name="工位A", device="dev-a", channels=["CH0", "CH1"],
                    usl=110.0, lsl=90.0, ideal_cycle_time_s=30.0),
            Station(name="工位B", device="dev-b", channels=["CH0"]),
        ], ideal_cycle_time_s=45.0, unit_cost=12.5, scrap_cost=20.0,
            downtime_cost_per_min=3.0, shift="08:00-20:00"),
    ])


def test_rows_roundtrip_preserves_station_fields():
    cfg = _cfg()
    rows = plant_to_rows(cfg)
    assert len(rows) == 2
    assert rows[0]["channels"] == "CH0, CH1"

    back = rows_to_plant(rows)
    st = back.lines[0].stations[0]
    assert st.device == "dev-a"
    assert st.channels == ["CH0", "CH1"]
    assert st.usl == 110.0 and st.lsl == 90.0
    assert st.ideal_cycle_time_s == 30.0
    assert back.lines[0].unit_cost == 12.5
    assert back.lines[0].scrap_cost == 20.0
    assert back.lines[0].shift == "08:00-20:00"


def test_rows_to_plant_accepts_text_numbers_and_channels():
    rows = [{"line": "L1", "station": "S1", "device": "d1",
             "channels": "CH0; CH1", "usl": "10.5", "lsl": "",
             "ideal_cycle_time_s": "7.5", "unit_cost": "2.0"}]
    cfg = rows_to_plant(rows)
    st = cfg.lines[0].stations[0]
    assert st.channels == ["CH0", "CH1"]
    assert st.usl == 10.5 and st.lsl is None
    assert st.ideal_cycle_time_s == 7.5
    assert cfg.lines[0].unit_cost == 2.0


def test_rows_to_plant_line_level_row_without_device():
    rows = [{"line": "L1", "device": "", "ideal_cycle_time_s": "20"},
            {"line": "L1", "station": "S1", "device": "d1", "channels": "CH0"}]
    cfg = rows_to_plant(rows)
    assert cfg.lines[0].ideal_cycle_time_s == 20.0
    assert len(cfg.lines[0].stations) == 1


def test_cycle_time_and_loss_per_unit_fallbacks():
    line = Line(name="L", unit_cost=5.0)
    st = Station(name="S", device="d")
    assert line.cycle_time_for(st) is None
    line.ideal_cycle_time_s = 12.0
    assert line.cycle_time_for(st) == 12.0
    st.ideal_cycle_time_s = 8.0
    assert line.cycle_time_for(st) == 8.0
    assert line.loss_per_unit() == 5.0
    line.scrap_cost = 9.0
    assert line.loss_per_unit() == 9.0


def test_save_load_roundtrip_with_extended_fields(tmp_path):
    path = tmp_path / "plant.json"
    _cfg().save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["lines"][0]["unit_cost"] == 12.5
    loaded = PlantConfig.load(path)
    assert loaded.lines[0].shift == "08:00-20:00"
    assert loaded.lines[0].stations[0].ideal_cycle_time_s == 30.0
    assert loaded.lines[0].cycle_time_for(loaded.lines[0].stations[1]) == 45.0


def test_legacy_json_without_new_fields_loads(tmp_path):
    path = tmp_path / "plant.json"
    path.write_text(json.dumps({"lines": [
        {"name": "旧产线", "stations": [
            {"name": "S", "device": "d", "channels": ["CH0"],
             "usl": "5", "lsl": None}]}]}), encoding="utf-8")
    cfg = PlantConfig.load(path)
    line = cfg.lines[0]
    assert line.unit_cost == 0.0 and line.shift == ""
    assert line.stations[0].usl == 5.0
    assert line.stations[0].ideal_cycle_time_s is None


def test_reload_in_place_keeps_identity(tmp_path):
    path = tmp_path / "plant.json"
    _cfg().save(path)
    cfg = PlantConfig.load(path)
    obj_id = id(cfg)
    changed = _PC(lines=[Line(name="2号线", stations=[
        Station(name="S9", device="d9")])])
    changed.save(path)
    assert cfg.reload() is cfg
    assert id(cfg) == obj_id
    assert cfg.lines[0].name == "2号线"


def test_default_plant_path_points_inside_repo():
    """v3.7.2 修复: 旧版多算一层 parent，配置被读写到仓库上一级目录。"""
    path = default_plant_path()
    assert path.parent.name == "data"
    assert path.parent.parent.name == "QA-Tool"
    assert legacy_plant_path() != path


def test_legacy_plant_file_is_migrated(monkeypatch, tmp_path):
    from core import plant as plant_mod

    legacy = tmp_path / "legacy" / "data" / "plant.json"
    legacy.parent.mkdir(parents=True)
    _cfg().save(legacy)
    target = tmp_path / "repo" / "data" / "plant.json"
    monkeypatch.setattr(plant_mod, "default_plant_path", lambda: target)
    monkeypatch.setattr(plant_mod, "legacy_plant_path", lambda: legacy)

    cfg = PlantConfig.load()
    assert target.exists() and cfg.lines[0].name == "1号线"
    assert cfg.lines[0].unit_cost == 12.5


def test_rows_from_excel_csv_template(tmp_path):
    csv = tmp_path / "t.csv"
    headers = [label for _key, label in ROW_COLUMNS]
    csv.write_text(
        ",".join(headers) + "\n" +
        "A线,工位1,dev-1,\"CH0, CH1\",10,9,25,1.5,2.5,0.5,08:00-20:00\n",
        encoding="utf-8")
    rows = rows_from_excel(csv)
    assert rows and rows[0]["device"] == "dev-1"
    cfg = rows_to_plant(rows)
    st = cfg.lines[0].stations[0]
    assert st.channels == ["CH0", "CH1"]
    assert st.usl == 10.0 and st.lsl == 9.0
    assert cfg.lines[0].scrap_cost == 2.5


def test_dialog_edits_and_saves(tmp_path):
    from ui.dialogs.plant_config_dialog import PlantConfigDialog

    path = tmp_path / "plant.json"
    _cfg().save(path)
    dlg = PlantConfigDialog(path=path)
    assert dlg.table.rowCount() == 2
    assert dlg.table.columnCount() == len(ROW_COLUMNS)

    # 新增一行并填写设备
    dlg._on_add_row()
    last = dlg.table.rowCount() - 1
    dlg.table.item(last, 0).setText("2号线")
    dlg.table.item(last, 1).setText("工位C")
    dlg.table.item(last, 2).setText("dev-c")
    dlg.table.item(last, 3).setText("CH0, CH1")
    dlg.table.item(last, 4).setText("12")
    cfg = dlg.current_config()
    assert cfg.lines[-1].stations[0].usl == 12.0

    out = tmp_path / "out.json"
    dlg.save_to(out)
    reloaded = PlantConfig.load(out)
    assert [l.name for l in reloaded.lines] == ["1号线", "2号线"]
    assert reloaded.lines[0].unit_cost == 12.5
    dlg.deleteLater()


def test_dialog_remove_row_and_blank_filter(tmp_path):
    from ui.dialogs.plant_config_dialog import PlantConfigDialog

    path = tmp_path / "plant.json"
    _cfg().save(path)
    dlg = PlantConfigDialog(path=path)
    dlg._on_add_row()
    dlg._on_remove_rows()          # 无选中 → 删除最后一行
    assert dlg.table.rowCount() == 2
    dlg._on_add_row()
    dlg.table.selectRow(dlg.table.rowCount() - 1)
    dlg._on_remove_rows()
    assert dlg.table.rowCount() == 2
    # 空行不进入配置
    dlg.append_row({})
    assert len(dlg.current_config().lines[0].stations) == 2
    dlg.deleteLater()
