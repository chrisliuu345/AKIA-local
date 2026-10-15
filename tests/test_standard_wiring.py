"""标准版本 UI 写入口与凭证接线测试（v4.3.0 B3-2/B3-3/B3-4）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMessageBox

from core.project_context import ProjectContext


@pytest.fixture(autouse=True)
def _silence_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: None))


class TestControlPlanWiring:
    def test_cell_edit_versions_rows(self):
        from ui.tabs.control_plan_tab import ControlPlanTab

        tab = ControlPlanTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        try:
            tab._sync_context("初始控制计划")
            key = "OP10|尺寸规格"
            first = ctx.standards.current(key)
            assert first is not None
            tab._rows[0][3] = "10±0.08mm"
            tab._sync_context("公差放宽")
            history = ctx.standards.history(key)
            assert len(history) == 2
            assert history[0].payload["row"]["规格/公差"] == "10±0.05mm"
            assert history[1].payload["row"]["规格/公差"] == "10±0.08mm"
        finally:
            tab.close()

    def test_cell_edit_throttles_versions(self):
        """逐格编辑节流（B7-3）：连续编辑合并为一个版本，显式 flush 才落库。"""
        from ui.tabs.control_plan_tab import ControlPlanTab

        tab = ControlPlanTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        try:
            tab._sync_context("初始控制计划")
            key = "OP10|尺寸规格"
            assert len(ctx.standards.history(key)) == 1
            tab.table.item(0, 3).setText("10±0.07mm")
            tab._on_cell_changed(0, 3)
            tab.table.item(0, 3).setText("10±0.08mm")
            tab._on_cell_changed(0, 3)
            assert len(ctx.standards.history(key)) == 1, "节流窗口内不应立即产生版本"
            tab._flush_pending_sync()
            history = ctx.standards.history(key)
            assert len(history) == 2
            assert history[-1].payload["row"]["规格/公差"] == "10±0.08mm"
            assert history[-1].change_reason == "控制计划条目编辑（自动保存）"
        finally:
            tab.close()


class TestCapabilityWiring:
    def test_save_specification_versions(self):
        from ui.tabs.capability_tab import CapabilityTab

        tab = CapabilityTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab.col_combo.addItem("轴径")
        tab.usl_spin.setValue(10.1)
        tab.lsl_spin.setValue(9.9)
        tab.target_spin.setValue(10.0)
        try:
            first = tab.save_specification_standard("初始版本")
            assert first.object_ref == "轴径"
            assert ctx.standards.current("轴径").payload["usl"] == 10.1
            tab.usl_spin.setValue(10.2)
            tab.lsl_spin.setValue(9.8)
            second = tab.save_specification_standard("客户放宽公差")
            assert second.record_id != first.record_id
            assert len(ctx.standards.history("轴径")) == 2
            assert first.valid_to == second.valid_from
            assert tab.standard_object_ref == "轴径"
        finally:
            tab.close()

    def test_identical_limits_do_not_create_version(self):
        from ui.tabs.capability_tab import CapabilityTab

        tab = CapabilityTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab.col_combo.addItem("轴径")
        tab.usl_spin.setValue(10.1)
        tab.lsl_spin.setValue(9.9)
        try:
            tab.save_specification_standard("初始版本")
            tab.save_specification_standard("重复保存")
            assert len(ctx.standards) == 1
        finally:
            tab.close()


class TestSpcWiring:
    def test_save_spec_and_control_limits(self):
        from ui.tabs.spc_tab import SPCTab

        tab = SPCTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab.col_combo.addItem("轴径")
        tab.spec_check.setChecked(True)
        tab.usl_spin.setValue(10.1)
        tab.lsl_spin.setValue(9.9)
        tab.current_result = {
            "analysis_type": "I-MR",
            "params": {"column": "轴径", "subgroup_size": 1, "chart_type": "I-MR"},
            "result": {"i_chart": {"cl": 10.0, "ucl": 10.2, "lcl": 9.8}},
        }
        try:
            created = tab.save_standard("初始版本")
            assert {r.object_type for r in created} == {"spec_limit", "control_limit"}
            assert ctx.standards.current("轴径").payload["usl"] == 10.1
            control = ctx.standards.current("轴径:I-MR")
            assert control.payload["ucl"] == 10.2 and control.payload["lcl"] == 9.8
        finally:
            tab.close()

    def test_multi_chart_control_limits_all_recorded(self):
        """XBar-R 的均值图与极差图控制限全部入标准（B7-3）。"""
        from ui.tabs.spc_tab import SPCTab

        tab = SPCTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab.col_combo.addItem("轴径")
        tab.current_result = {
            "analysis_type": "XBar-R",
            "params": {"column": "轴径", "subgroup_size": 5,
                       "chart_type": "XBar-R"},
            "result": {
                "xbar_chart": {"cl": 10.0, "ucl": 10.3, "lcl": 9.7},
                "r_chart": {"cl": 1.0, "ucl": 2.1, "lcl": 0.0},
            },
        }
        try:
            created = tab.save_standard("初始版本")
            refs = {record.object_ref for record in created}
            assert refs == {"轴径:XBar-R", "轴径:XBar-R:r_chart"}
            range_record = ctx.standards.current("轴径:XBar-R:r_chart")
            assert range_record.payload["ucl"] == 2.1
            assert range_record.payload["chart_type"] == "XBar-R"
        finally:
            tab.close()


class TestIeStandardsWiring:
    def test_time_study_standard_time_versions(self):
        from ui.tabs.time_study_tab import TimeStudyTab

        tab = TimeStudyTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab.current_result = {
            "analysis_type": "时间研究",
            "params": {},
            "result": {"results": [
                {"process_id": "OP10", "operator": "张三", "cycles": 10,
                 "standard_time": 28.0, "normal_time": 25.0,
                 "allowance_pct": 12.0, "rating": 1.0},
                {"process_id": "OP20", "operator": "李四", "cycles": 10,
                 "standard_time": 31.5, "normal_time": 28.0,
                 "allowance_pct": 12.0, "rating": 1.0},
            ]},
        }
        try:
            created = tab.save_standard_time("初始标准工时")
            assert len(created) == 2
            assert ctx.standards.current("OP10").payload["standard_time_s"] == 28.0
            assert ctx.standards.current("OP20").payload["standard_time_s"] == 31.5
        finally:
            tab.close()

    def test_work_combination_standard(self):
        from ui.tabs.std_work_combo_tab import StdWorkComboTab

        tab = StdWorkComboTab()
        ctx = ProjectContext()
        tab.set_project_context(ctx)
        tab._last_combination = {
            "steps": [{"name": "取料", "manual_s": 5, "auto_s": 10, "walk_s": 2}],
            "total_s": 17, "takt_s": 90, "slack_s": 73,
        }
        try:
            record = tab.save_work_combination_standard("初始组合票")
            assert record.object_type == "work_combination"
            assert ctx.standards.current("作业组合票").payload["total_s"] == 17
        finally:
            tab.close()


class TestCredentialStandardRef:
    def test_analysis_credential_carries_standard_ref(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        ctx = ProjectContext()
        first = ctx.record_specification("轴径", usl=10.1, lsl=9.9,
                                         change_reason="初始版本")
        window.project_context = ctx
        result = {"analysis_type": "正态过程能力",
                  "params": {"column": "轴径", "usl": 10.1, "lsl": 9.9},
                  "result": {}}
        try:
            credential = window._make_analysis_credential(2, result)
            assert credential["params"]["standard_ref"] == first.record_id
            assert credential["params"]["standard_object_ref"] == "轴径"
            second = ctx.record_specification("轴径", usl=10.2, lsl=9.8,
                                              change_reason="放宽")
            changed = window._make_analysis_credential(2, result)
            assert changed["params"]["standard_ref"] == second.record_id
            assert changed["params"]["standard_ref"] != credential["params"]["standard_ref"]
        finally:
            window.close()


class TestStandardHistoryUi:
    def test_dialog_lists_versions(self):
        from PySide6.QtWidgets import QTableWidget

        from ui.dialogs.standard_history_dialog import StandardHistoryDialog

        ctx = ProjectContext()
        ctx.record_specification("轴径", usl=10.1, lsl=9.9, change_reason="初始版本")
        ctx.record_specification("轴径", usl=10.2, lsl=9.8, change_reason="客户放宽")
        dialog = StandardHistoryDialog(ctx.standards)
        try:
            table = dialog.findChild(QTableWidget)
            assert table is not None and table.rowCount() == 2
            reasons = {table.item(row, 4).text() for row in range(table.rowCount())}
            assert reasons == {"初始版本", "客户放宽"}
            assert table.item(0, 1).text() == "规格限"
        finally:
            dialog.close()

    def test_empty_registry_shows_message(self):
        from PySide6.QtWidgets import QLabel

        from ui.dialogs.standard_history_dialog import StandardHistoryDialog

        dialog = StandardHistoryDialog(ProjectContext().standards)
        try:
            texts = [label.text() for label in dialog.findChildren(QLabel)]
            assert any("尚无标准版本记录" in text for text in texts)
        finally:
            dialog.close()

    def test_tools_menu_entry_exists(self):
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            tools_menu = next(action.menu() for action in window.menuBar().actions()
                              if "工具" in action.text())
            texts = [action.text() for action in tools_menu.actions()]
            assert any("标准版本记录" in text for text in texts)
        finally:
            window.close()


class TestControlPlanSaveFlush:
    """保存工程前必须冲刷控制计划节流窗口内的挂起编辑（2026-10-15 审查修复）。

    回归背景：逐格编辑 1.5s 节流合并落版；窗口内直接「保存工程」会写出旧值
    （静默丢最后一笔编辑）。
    """

    def test_save_project_flushes_throttled_edit(self, tmp_path, monkeypatch):
        import pandas as pd
        from PySide6.QtWidgets import QFileDialog

        from core.project_manager import ProjectManager
        from ui.main_window import MainWindow

        window = MainWindow()
        try:
            window.current_data = {
                "source": "/tmp/line_a.xlsx",
                "raw_data": {"S": pd.DataFrame({"x": [1.0, 2.0, 3.0]})},
            }
            tab = window._lazy_load_tab(17)  # 控制计划 Tab
            assert tab is not None
            tab._sync_context("初始控制计划")
            tab.table.item(0, 3).setText("10±0.01mm")
            tab._on_cell_changed(0, 3)
            assert tab._pending_reason, "编辑应进入节流窗口（尚未落库）"

            path = str(tmp_path / "flush.qap")
            monkeypatch.setattr(
                QFileDialog, "getSaveFileName",
                staticmethod(lambda *a, **k: (path, "")))
            window._on_save_project()

            project = ProjectManager.load_project(path)
            rows = project["project_context"]["control_plan_rows"]
            assert rows[0]["规格/公差"] == "10±0.01mm", \
                "保存工程必须先冲刷节流窗口内的编辑"
        finally:
            window.close()
