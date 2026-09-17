"""IE 导入接线回归 — 空状态按钮路由 / 导入后遮罩消失 / 自包含 IE Tab 无遮罩。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton

from core.data_objects import Process, TimeObservation


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    QApplication.processEvents()
    yield win
    win.close()
    win.deleteLater()


class TestIeEmptyStateRouting:
    def test_ie_tab_button_routes_to_ie_import(self, window, monkeypatch):
        calls = {"ie": 0, "quality": 0}
        monkeypatch.setattr(window, "_on_import_ie",
                            lambda: calls.__setitem__("ie", calls["ie"] + 1))
        monkeypatch.setattr(window, "_on_import_quality",
                            lambda: calls.__setitem__("quality", calls["quality"] + 1))
        tab = window._lazy_load_tab(9)   # 必须在 patch 后加载以连到新 handler
        window._switch_tab(9)
        QApplication.processEvents()

        buttons = tab._empty_overlay.findChildren(QPushButton)
        assert buttons and buttons[0].text() == "导入 IE 数据"
        buttons[0].click()
        QApplication.processEvents()
        assert calls["ie"] == 1
        assert calls["quality"] == 0

    def test_worksheet_tab_still_routes_to_quality_import(self, window, monkeypatch):
        calls = {"ie": 0, "quality": 0}
        monkeypatch.setattr(window, "_on_import_ie",
                            lambda: calls.__setitem__("ie", calls["ie"] + 1))
        monkeypatch.setattr(window, "_on_import_quality",
                            lambda: calls.__setitem__("quality", calls["quality"] + 1))
        tab = window._lazy_load_tab(1)   # SPC：工作表导入
        window._switch_tab(1)
        QApplication.processEvents()

        buttons = tab._empty_overlay.findChildren(QPushButton)
        assert buttons and buttons[0].text() == "导入数据"
        buttons[0].click()
        QApplication.processEvents()
        assert calls == {"ie": 0, "quality": 1}


class TestIeImportClearsEmptyState:
    def test_menu_ie_import_populates_tab_and_hides_overlay(self, window, monkeypatch):
        """菜单「导入 IE 数据」全链路：Tab 填充 + 遮罩立即消失。"""
        import pandas as pd

        import ui.main_window as main_window

        class FakeDialog:
            def __init__(self, parent=None, mode=""):
                self.mode = mode

            def exec(self):
                return True

            def get_selection(self):
                return "fake_ie.xls", []

        monkeypatch.setattr(main_window, "ImportDialog", FakeDialog)
        monkeypatch.setattr(window.data_loader, "load",
                            lambda path: {"Sheet1": pd.DataFrame({"a": [1]})})
        monkeypatch.setattr(
            window.data_loader, "load_ie_data",
            lambda: {"Process": [Process(process_id="P1", process_name="装配",
                                         cycle_time=30.0)]})

        tab = window._lazy_load_tab(9)
        window._switch_tab(9)
        QApplication.processEvents()
        assert tab._empty_overlay.isVisible()

        window._on_import_ie()
        QApplication.processEvents()

        assert len(tab.ie_processes) == 1
        assert not tab._empty_overlay.isVisible()

    def test_line_balance_ie_data_hides_overlay(self, window):
        tab = window._lazy_load_tab(9)
        window._switch_tab(9)
        QApplication.processEvents()
        assert tab._empty_overlay.isVisible()

        tab.set_ie_data([Process(process_id="P1", process_name="装配", cycle_time=30.0)])
        window._update_tab_empty_state(9)
        assert not tab._empty_overlay.isVisible()

        # 菜单导入后切走再切回：遮罩保持隐藏（原缺陷场景）
        window._switch_tab(1)
        window._switch_tab(9)
        QApplication.processEvents()
        assert not tab._empty_overlay.isVisible()

    def test_time_study_ie_data_hides_overlay(self, window):
        tab = window._lazy_load_tab(7)
        window._switch_tab(7)
        QApplication.processEvents()
        assert tab._empty_overlay.isVisible()

        tab.set_ie_data([TimeObservation(process_id="P1", operator="A",
                                         cycle=1, observation_time=30.0)])
        window._switch_tab(1)
        window._switch_tab(7)
        QApplication.processEvents()
        assert not tab._empty_overlay.isVisible()

    def test_self_contained_ie_tabs_skip_empty_state(self, window):
        for idx in (8, 21, 22):
            window._switch_tab(idx)
            QApplication.processEvents()
            tab = window.stack.widget(idx)
            overlay = getattr(tab, "_empty_overlay", None)
            assert overlay is None or not overlay.isVisible()
