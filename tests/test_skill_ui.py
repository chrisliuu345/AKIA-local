"""技能约束线平衡 UI 接线测试（v4.4.0 B5，离屏）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.data_objects import Process
from core.skill_matrix import SkillMatrix


@pytest.fixture
def main_window():
    from ui.main_window import MainWindow

    window = MainWindow()
    window.current_data = {
        "source": "/tmp/line_a.xlsx",
        "raw_data": {"工时": pd.DataFrame({"cycle": [10.0, 10.0, 10.0, 10.0]})},
    }
    try:
        yield window
    finally:
        window.close()


def _full_matrix(level: int = 3, requirements=None) -> SkillMatrix:
    return SkillMatrix(
        entries=[{"operator": operator, "process_id": f"P{i}", "level": level}
                 for operator in ("张三", "李四") for i in range(1, 5)],
        requirements=list(requirements or []))


def _ready_tab(window):
    tab = window._lazy_load_tab(9)  # 线平衡
    tab.set_ie_data([
        Process(process_id=f"P{i}", process_name=f"工序{i}", cycle_time=10.0)
        for i in range(1, 5)])
    tab.takt_spin.setValue(20.0)
    return tab


class TestTabWiring:
    def test_tab_receives_skill_context(self, main_window):
        tab = main_window._lazy_load_tab(9)
        assert tab is not None
        assert tab._skill_matrix is main_window.skill_matrix
        assert callable(tab._skill_saver)
        assert callable(tab._skill_record_step)

    def test_standalone_tab_guards(self, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from ui.tabs.line_balance_tab import LineBalanceTab

        notices = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: notices.append(a)))
        tab = LineBalanceTab()
        try:
            tab._open_skill_matrix()
            tab._record_skill_result("baseline")
            assert len(notices) == 2
        finally:
            tab.close()


class TestSkillDialog:
    def test_edit_save_and_validation(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        from ui.dialogs.skill_matrix_dialog import SkillMatrixDialog

        infos, warnings = [], []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))
        dialog = SkillMatrixDialog(main_window.skill_matrix, None,
                                   on_save=main_window.save_skill_matrix)
        try:
            dialog._add_skill_row("张三", "P1", 3)
            dialog._add_req_row("P1", 2)
            dialog._on_save()
            assert len(main_window.skill_matrix.entries) == 1
            assert main_window.skill_matrix.min_level_for("P1") == 2
            assert any("已保存" in str(item) for item in infos)
            # 工序已填但人员为空 → 校验失败且不落库
            dialog._add_skill_row("", "P2", 3)
            dialog._on_save()
            assert warnings, "非法行应触发校验告警"
            assert len(main_window.skill_matrix.entries) == 1
        finally:
            dialog.close()

    def test_load_existing(self, main_window):
        from ui.dialogs.skill_matrix_dialog import SkillMatrixDialog

        main_window.save_skill_matrix(_full_matrix(
            requirements=[{"process_id": "P1", "min_level": 2}]))
        dialog = SkillMatrixDialog(main_window.skill_matrix, None)
        try:
            assert dialog.skill_table.rowCount() == 8
            assert dialog.req_table.rowCount() == 1
        finally:
            dialog.close()


class TestScheduleRun:
    def test_feasible_run_outputs_roster(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        infos = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))
        main_window.save_skill_matrix(_full_matrix())
        tab = _ready_tab(main_window)
        tab._run_skill_schedule()
        plan = tab._last_skill_plan
        assert plan.feasible is True
        assert tab.skill_result_table.rowCount() == 4
        assert "平衡率" in tab.skill_status_label.text()
        assert "指纹" in tab.skill_status_label.text()
        assert any("排班可行" in str(item) for item in infos)

    def test_unmet_reports_details(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))
        main_window.save_skill_matrix(_full_matrix(
            level=2, requirements=[{"process_id": "P3", "min_level": 4}]))
        tab = _ready_tab(main_window)
        tab._run_skill_schedule()
        assert tab._last_skill_plan.feasible is False
        assert "不可行明细" in tab.skill_status_label.text()
        assert any("技能不满足" in str(item) for item in warnings)

    def test_missing_matrix_warns(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        warnings = []
        monkeypatch.setattr(QMessageBox, "warning",
                            staticmethod(lambda *a, **k: warnings.append(a)))
        tab = _ready_tab(main_window)
        tab._run_skill_schedule()
        assert warnings and "技能矩阵" in str(warnings[0])


class TestCaseRecording:
    def test_baseline_and_remeasure_steps(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        infos = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: infos.append(a)))
        main_window.save_skill_matrix(_full_matrix())
        tab = _ready_tab(main_window)
        tab._run_skill_schedule()
        tab._record_skill_result("baseline")
        workflow = main_window._last_case_workflow
        assert workflow is not None
        assert workflow.case.steps[0]["phase"] == "baseline"
        fingerprint = workflow.case.steps[0]["credential"]["params"].get(
            "skill_fingerprint")
        assert fingerprint == main_window.skill_matrix.fingerprint()
        tab._record_skill_result("re_measure")
        assert [step["phase"] for step in workflow.case.steps] == \
            ["baseline", "re_measure"]
        assert any("已记入案例" in str(item) for item in infos)

    def test_record_without_plan_warns(self, main_window, monkeypatch):
        from PySide6.QtWidgets import QMessageBox

        notices = []
        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: notices.append(a)))
        tab = _ready_tab(main_window)
        tab._record_skill_result("baseline")
        assert notices and "请先运行" in str(notices[0])


class TestPersistence:
    def test_roundtrip_and_rehook(self, main_window, tmp_path, monkeypatch):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from core.project_manager import ProjectManager

        monkeypatch.setattr(QMessageBox, "information",
                            staticmethod(lambda *a, **k: None))
        matrix = _full_matrix(requirements=[{"process_id": "P3", "min_level": 4}])
        main_window.save_skill_matrix(matrix)
        main_window._lazy_load_tab(9)  # 预加载页签以便验证重连
        path = str(tmp_path / "skills.qap")
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (path, "")))
        main_window._on_save_project()
        project = ProjectManager.load_project(path)
        assert project["manifest"]["skill_entry_count"] == 8
        main_window._apply_loaded_project(project, path)
        restored = main_window.skill_matrix
        assert len(restored.entries) == 8
        assert restored.min_level_for("P3") == 4
        assert restored.fingerprint() == matrix.fingerprint()
        assert main_window._tab_cache[9]._skill_matrix is restored
