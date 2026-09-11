"""test_five_chain_ui.py — 五链贯通的 UI 装配层测试

此前 test_five_chain.py 只覆盖引擎与 ProjectContext 数据结构，漏掉了
MainWindow 的桥接方法，导致 FMEA → CP / CP → SPC 静默失效长期未被发现。
本文件补上装配层闭环：

1. FMEA._generate_cp()  → 控制计划 Tab 追加行 + 自动切换 + 上下文写入
2. CP._generate_spc_list() → SPC Tab CP 监控清单可见 + 上下文快照
3. 8D 从 ProjectContext 导入 FMEA 原因到 D4 鱼骨图
4. 打开 .qap 场景下 load_from_context 恢复 CP 行 / SPC 监控清单
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QMessageBox

from core.fmea_engine import FMEAItem
from ui._tab_registry import TAB_INDEX


@pytest.fixture
def patched_message_boxes(monkeypatch):
    """阻断模态弹窗：question → Yes，information/warning → Ok"""
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: QMessageBox.Ok))


@pytest.fixture
def main_window(_qt_application, patched_message_boxes):
    from ui.main_window import MainWindow

    window = MainWindow()
    yield window
    window.close()
    window.deleteLater()


def _seed_fmea(tab):
    """写入两条条目：1 条高风险(RPN=144) + 1 条低风险(RPN=24)"""
    tab._items = [
        FMEAItem(function="车削", failure_mode="尺寸超差", effect="装配不良",
                 severity=9, cause="刀具磨损", occurrence=8,
                 control="XBar-R控制图", detection=2),
        FMEAItem(function="打磨", failure_mode="表面粗糙", effect="外观不良",
                 severity=2, cause="砂轮钝化", occurrence=3,
                 control="目视检查", detection=4),
    ]
    for item in tab._items:
        item.calc_rpn()
    tab._rebuild_table()


class TestFmeaItemRoundtrip:
    def test_to_dict_from_dict_preserves_rpn(self):
        item = FMEAItem(function="车削", failure_mode="尺寸超差",
                        severity=9, occurrence=8, detection=2, cause="刀具磨损")
        item.calc_rpn()

        restored = FMEAItem.from_dict(item.to_dict())

        assert restored.rpn == item.rpn == 144
        assert restored.risk_level == "high"
        assert restored.cause == "刀具磨损"

    def test_from_dict_tolerates_missing_fields(self):
        restored = FMEAItem.from_dict({"function": "钻孔", "severity": "bad"})
        assert restored.function == "钻孔"
        assert restored.severity == 1


class TestFmeaToControlPlan:
    def test_generate_cp_appends_rows_and_switches_tab(self, main_window):
        w = main_window
        fmea = w._lazy_load_tab(TAB_INDEX["fmea"])
        cp = w._lazy_load_tab(TAB_INDEX["control_plan"])
        _seed_fmea(fmea)
        before = len(cp._rows)

        fmea._generate_cp()

        assert len(cp._rows) == before + 1, "仅高风险项(RPN>=100)应生成控制计划行"
        assert w.stack.currentIndex() == TAB_INDEX["control_plan"]
        assert cp._rows[-1][1] == "车削"

    def test_generate_cp_writes_project_context(self, main_window):
        w = main_window
        fmea = w._lazy_load_tab(TAB_INDEX["fmea"])
        _seed_fmea(fmea)

        fmea._generate_cp()

        assert len(w.project_context.fmea_items) == 2
        assert w.project_context.control_plan_rows
        last = w.project_context.control_plan_rows[-1]
        assert last["工序名称"] == "车削"
        assert "尺寸超差" in last["特性(产品/过程)"]

    def test_fmea_sync_updates_context_on_edit(self, main_window):
        w = main_window
        fmea = w._lazy_load_tab(TAB_INDEX["fmea"])
        _seed_fmea(fmea)
        assert len(w.project_context.fmea_items) == 2


class TestControlPlanToSpc:
    def test_generate_spc_list_surfaces_monitoring_table(self, main_window):
        w = main_window
        cp = w._lazy_load_tab(TAB_INDEX["control_plan"])
        cp._rows = []
        cp._rebuild_table()
        cp.append_rows([["OP10", "车削", "轴径", "10±0.05", "卡尺",
                         "5", "每小时", "XBar-R控制图", "隔离"]])

        cp._generate_spc_list()

        spc = w._tab_cache[TAB_INDEX["spc"]]
        assert w.stack.currentIndex() == TAB_INDEX["spc"], "应自动切换到 SPC Tab"
        assert len(spc._cp_monitoring_list) == 1
        assert spc.cp_table.rowCount() == 1
        assert not spc.cp_group.isHidden(), "监控清单分组应在导入后可见"
        assert "1" in spc.cp_group.title()

    def test_generate_spc_list_writes_context_snapshot(self, main_window):
        w = main_window
        cp = w._lazy_load_tab(TAB_INDEX["control_plan"])
        cp._rows = []
        cp._rebuild_table()
        cp.append_rows([["OP20", "钻孔", "孔径", "8.0±0.02", "气动量仪",
                         "3", "每小时", "SPC控制图", "调整刀具补偿"]])

        cp._generate_spc_list()

        snapshot = w.project_context.get_analysis_snapshot("spc_monitoring")
        assert snapshot is not None
        assert len(snapshot["items"]) == 1
        assert snapshot["items"][0]["process"] == "钻孔"

    def test_non_spc_rows_produce_no_items(self, main_window):
        w = main_window
        cp = w._lazy_load_tab(TAB_INDEX["control_plan"])
        cp._rows = []
        cp._rebuild_table()
        cp.append_rows([["OP30", "热处理", "硬度", "58-62 HRC", "硬度计",
                         "2", "每炉", "记录曲线", "调整温度"]])

        cp._generate_spc_list()

        assert not cp.current_result, "无 SPC 控制项时不应产生结果"


class TestContextRestore:
    def test_control_plan_load_from_context(self, main_window):
        w = main_window
        cp = w._lazy_load_tab(TAB_INDEX["control_plan"])
        w.project_context.set_control_plan([
            {"工序编号": "OP99", "工序名称": "磨削", "特性(产品/过程)": "圆度",
             "规格/公差": "0.01", "测量方法": "圆度仪", "样本量": "5",
             "抽样频率": "每小时", "控制方法": "XBar-R控制图", "反应计划": "停机调整"},
        ])

        cp.load_from_context()

        assert len(cp._rows) == 1
        assert cp._rows[0][1] == "磨削"
        assert cp.table.item(0, 2).text() == "圆度"

    def test_spc_load_from_context_restores_monitoring_list(self, main_window):
        w = main_window
        spc = w._lazy_load_tab(TAB_INDEX["spc"])
        w.project_context.set_analysis_snapshot("spc_monitoring", {
            "items": [{"process": "OP10", "characteristic": "孔径",
                       "tolerance": "8±0.02", "method": "XBar-R控制图",
                       "sample_size": "5", "frequency": "每小时"}],
            "source": "control_plan",
        })

        spc.load_from_context()

        assert len(spc._cp_monitoring_list) == 1
        assert spc.cp_table.rowCount() == 1
        assert not spc.cp_group.isHidden()

    def test_eight_d_imports_causes_from_context(self, main_window):
        w = main_window
        d8 = w._lazy_load_tab(TAB_INDEX["eight_d"])
        w.project_context.set_fmea_items([
            {"cause": "刀具磨损", "effect": "尺寸超差", "rpn": 144},
            {"cause": "培训不足", "effect": "操作失误", "rpn": 120},
        ])

        d8._import_from_fmea()

        canvas = d8._w["d4_fishbone"]
        assert len(canvas._branches) >= 1, "FMEA 原因应注入 D4 鱼骨图"
        assert len(canvas._causes) >= 1

    def test_eight_d_save_writes_report_to_context(self, main_window):
        w = main_window
        d8 = w._lazy_load_tab(TAB_INDEX["eight_d"])
        d8._w["title"].setText("8D-001")

        d8._save()
        d8._save()

        assert len(w.project_context.eight_d_reports) == 1
        assert w.project_context.eight_d_reports[0]["title"] == "8D-001"
