"""PPAP Tab 回归 — 提交等级切换不得崩溃（第 2 列为 cellWidget 非 item）。

原始报错:
    ui/tabs/ppap_tab.py:134 in _refresh_matrix
    self.matrix.item(row, c).setForeground(...)
    AttributeError: 'NoneType' object has no attribute 'setForeground'
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from analysis.quality.ppap_engine import SUBMISSION_ITEMS
from ui.tabs.ppap_tab import PPAPTab


@pytest.fixture
def tab(_qt_application):
    t = PPAPTab()
    yield t
    t.deleteLater()


@pytest.fixture
def no_modal(monkeypatch):
    """屏蔽模态弹窗 — _calc_capability 结束时用 QMessageBox 提示，测试中会阻塞。"""
    from PySide6.QtWidgets import QMessageBox

    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda *a, **k: QMessageBox.Ok))




def test_matrix_status_column_has_widget_not_item(tab):
    """状态列是下拉框单元格 — 断言前提，防止未来改成 item 后测试失效。"""
    assert tab.matrix.item(0, 2) is None
    assert tab.matrix.cellWidget(0, 2) is not None
    assert tab.matrix.item(0, 0) is not None


def test_refresh_matrix_all_levels_no_crash(tab):
    """逐个切换 1~5 级（原始崩溃路径）。"""
    for idx in range(tab.level_combo.count()):
        tab.level_combo.setCurrentIndex(idx)     # 触发 currentIndexChanged
        tab._refresh_matrix()
        level = tab.level_combo.currentData()
        assert tab.report.submission_level == level
        assert "完成度" in tab.pct_label.text()


def test_required_items_are_highlighted_and_others_reset(tab):
    # 选等级 3（必交 12 项），验证高亮与还原
    idx = tab.level_combo.findData(3)
    tab.level_combo.setCurrentIndex(idx)
    required = set(SUBMISSION_ITEMS[3])
    for row in range(tab.matrix.rowCount()):
        n = row + 1
        name_item = tab.matrix.item(row, 1)
        if n in required:
            assert name_item.font().bold() is True, f"必交项 {n} 未加粗"
        else:
            assert name_item.font().bold() is False, f"非必交项 {n} 仍加粗"

    # 切到等级 1（仅 PSW）→ 之前的必交项应还原为默认
    tab.level_combo.setCurrentIndex(tab.level_combo.findData(1))
    for row in range(tab.matrix.rowCount()):
        n = row + 1
        bold = tab.matrix.item(row, 1).font().bold()
        assert bold is (n in set(SUBMISSION_ITEMS[1]))


def test_update_pct_tracks_status_changes(tab):
    tab.level_combo.setCurrentIndex(tab.level_combo.findData(1))   # 只需 PSW(18)
    tab.matrix.cellWidget(17, 2).setCurrentText("complete")
    tab._update_pct()
    assert "100.0%" in tab.pct_label.text()
    assert "1项" in tab.pct_label.text()


def test_initial_state_is_rendered(tab):
    """构造后即应有等级样式（不需要先切一次等级）。"""
    level = tab.level_combo.currentData()
    required = set(SUBMISSION_ITEMS[level])
    for row in range(tab.matrix.rowCount()):
        if (row + 1) in required:
            assert tab.matrix.item(row, 1).font().bold() is True


def test_calc_capability_handles_empty_and_filled_rows(tab, no_modal):
    """尺寸报告：空行给提示不崩溃，填好数据的行算出 Cp/Cpk。"""
    from PySide6.QtWidgets import QTableWidgetItem

    tab.dim_table.setRowCount(2)
    tab._calc_capability()                       # 两行全空
    assert tab.dim_table.item(0, 5).text() == "缺少 USL/LSL"

    for col, value in ((0, "直径"), (2, "10.5"), (3, "9.5"),
                       (4, "10.0, 10.1, 9.9, 10.05, 9.95")):
        tab.dim_table.setItem(0, col, QTableWidgetItem(value))
    tab._calc_capability()
    assert tab.dim_table.item(0, 5).text().startswith("Cp=")
    assert tab.dim_table.item(1, 5).text() == "缺少 USL/LSL"


def test_calc_capability_flags_invalid_limits(tab, no_modal):
    from PySide6.QtWidgets import QTableWidgetItem

    tab.dim_table.setRowCount(1)
    for col, value in ((2, "9.5"), (3, "10.5"), (4, "10.0, 10.1")):
        tab.dim_table.setItem(0, col, QTableWidgetItem(value))
    tab._calc_capability()
    assert tab.dim_table.item(0, 5).text() == "USL≤LSL 无效"
