"""菜单动作离屏冒烟清单（v4.4.0 B7-2，制度化）。

v4.3.0 审查教训：「共享保存必然失败」「配对错配」都属于主窗口菜单动作
端到端无人跑的盲区。本清单要求：**每一个菜单叶动作至少被真实触发一次**
（弹窗/文件对话框统一桩掉，避免阻塞）；少数有外部副作用的动作显式登记
跳过原因，且跳过名单必须与菜单一一对应（防止名单腐化）。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

#: 显式跳过（必须存在于菜单中，防止名单腐化）；其余动作全部触发
SKIP_ACTIONS = {
    "退出": "关闭应用（专项：closeEvent/_shutdown_runtime 测试覆盖）",
    "实时看板": "启动后台 uvicorn 线程（专项：test_dashboard_auth / 看板测试覆盖）",
    "显示模式": "全屏展示窗口（专项：test_display_mode 覆盖）",
}


def _menu_actions(window) -> list:
    """递归收集菜单栏下的全部叶动作（去掉分隔符与子菜单容器）。"""
    actions = []

    def walk(menu):
        for action in menu.actions():
            if action.isSeparator():
                continue
            if action.menu() is not None:
                walk(action.menu())
                continue
            if action.text().strip():
                actions.append(action)

    for action in window.menuBar().actions():
        if action.menu() is not None:
            walk(action.menu())
    return actions


@pytest.fixture
def main_window():
    from ui.main_window import MainWindow

    window = MainWindow()
    window.current_data = {
        "source": "/tmp/line_a.xlsx",
        "raw_data": {"工时": pd.DataFrame({"cycle": [31.0, 32.0, 33.0]})},
    }
    try:
        yield window
    finally:
        window.close()


def _install_patches(monkeypatch, main_window):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QDialog, QFileDialog, QInputDialog, QMessageBox,
    )

    monkeypatch.setattr(QDialog, "exec", lambda self: 0)
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.No))
    for name in ("getSaveFileName", "getOpenFileName", "getExistingDirectory"):
        monkeypatch.setattr(QFileDialog, name,
                            staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames",
                        staticmethod(lambda *a, **k: ([], "")))
    monkeypatch.setattr(QInputDialog, "getText",
                        staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QInputDialog, "getItem",
                        staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QInputDialog, "getDouble",
                        staticmethod(lambda *a, **k: (0.0, False)))
    monkeypatch.setattr(QInputDialog, "getInt",
                        staticmethod(lambda *a, **k: (0, False)))
    monkeypatch.setattr(QInputDialog, "getMultiLineText",
                        staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        staticmethod(lambda url: True))


class TestMenuSmoke:
    def test_every_leaf_action_triggers_without_error(self, main_window,
                                                      monkeypatch):
        _install_patches(monkeypatch, main_window)
        switched: list[int] = []

        def spy_switch(index, *args, **kwargs):
            switched.append(int(index))
            return None

        monkeypatch.setattr(main_window, "_switch_tab", spy_switch)
        actions = _menu_actions(main_window)
        assert len(actions) >= 40, f"菜单动作过少（{len(actions)}），清单可能失效"
        texts = {action.text() for action in actions}
        for name in SKIP_ACTIONS:
            assert any(name in text for text in texts), \
                f"跳过名单条目「{name}」已不在菜单中，请更新清单"
        failures: list[str] = []
        triggered = 0
        for action in actions:
            label = action.text()
            if any(name in label for name in SKIP_ACTIONS):
                continue
            try:
                action.trigger()
                triggered += 1
            except Exception as exc:  # 清单用途是收集全部失败点
                failures.append(f"{label}: {type(exc).__name__}: {exc}")
        assert not failures, "菜单动作触发失败:\n" + "\n".join(failures)
        assert triggered >= len(actions) - len(SKIP_ACTIONS)
        # 分析菜单的 Tab 跳转应真实命中（spy 记录）
        assert switched, "Tab 跳转类菜单动作未被触发"
