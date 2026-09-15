"""v4.1.0 B3 — 全局命令面板（条目构建 / 过滤 / 执行 / 快捷键）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    yield win
    win.close()
    win.deleteLater()


def test_entries_cover_all_tabs_and_key_actions(window):
    from ui._tab_registry import TAB_REGISTRY

    entries = window._build_command_entries()
    tab_indices = {e["payload"] for e in entries if e.get("kind") == "tab"}
    assert {idx for idx, *_ in TAB_REGISTRY} <= tab_indices
    labels = {e["label"] for e in entries}
    for required in ("导入数据文件", "批量分析", "设置", "QAM Harness",
                     "使用指南", "显示模式"):
        assert required in labels, f"命令面板缺少「{required}」"
    # 每组条目都有 kind，便于统一执行
    assert all(e.get("kind") in ("tab", "action") for e in entries)


def test_palette_filters_by_keyword(window):
    from ui.dialogs.command_palette import CommandPaletteDialog

    dlg = CommandPaletteDialog(window._build_command_entries(), window)
    try:
        dlg.search.setText("SPC")
        labels = [dlg.list.item(i).text() for i in range(dlg.list.count())]
        assert labels and any("SPC" in text for text in labels)

        dlg.search.setText("批量")
        labels = [dlg.list.item(i).text() for i in range(dlg.list.count())]
        assert any("批量分析" in text for text in labels)

        dlg.search.setText("绝对不存在的命令")
        assert dlg.list.count() == 0
    finally:
        dlg.close()
        dlg.deleteLater()


def test_palette_executes_tab_jump(window):
    from ui.dialogs.command_palette import CommandPaletteDialog

    dlg = CommandPaletteDialog(window._build_command_entries(), window)
    captured = []
    dlg.triggered.connect(captured.append)
    try:
        dlg.search.setText("过程能力")
        assert dlg.execute_current() is True
        assert captured and captured[0]["kind"] == "tab"
        window._execute_command(captured[0])
        QApplication.processEvents()
        assert window.stack.currentIndex() == captured[0]["payload"]
    finally:
        dlg.close()
        dlg.deleteLater()


def test_palette_action_executes_callback(window):
    from ui.dialogs.command_palette import CommandPaletteDialog

    calls = []
    entries = [{"label": "测试操作", "category": "操作", "hint": "",
                "kind": "action", "callback": lambda: calls.append(1),
                "keywords": "test"}]
    dlg = CommandPaletteDialog(entries, window)
    try:
        assert dlg.execute_current() is True
        window._execute_command(entries[0])
        assert calls == [1]
    finally:
        dlg.close()
        dlg.deleteLater()


def test_view_menu_registers_palette_shortcuts(window):
    shortcuts = set()
    for action in window.menuBar().actions():
        menu = action.menu()
        if menu is None:
            continue
        for sub in menu.actions():
            shortcuts.update(seq.toString() for seq in sub.shortcuts())
    assert "Ctrl+K" in shortcuts
    assert "Ctrl+P" in shortcuts
