"""帮助中心 — 使用指南 HTML + 帮助菜单集成

覆盖: guide.html 内容结构 / 打包注册 / 菜单入口与 F1 / 浏览器打开路径
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from pathlib import Path

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "config" / "help" / "guide.html"


def test_guide_html_exists_with_sections_and_faq():
    assert GUIDE.exists(), "config/help/guide.html 缺失"
    html = GUIDE.read_text(encoding="utf-8")
    for anchor in ("quick-start", "data-import", "modules", "charts", "export", "ai", "hardware", "realtime", "faq", "support"):
        assert f'id="{anchor}"' in html, f"缺少锚点 {anchor}"
    assert html.count("<details") >= 4  # FAQ 折叠块
    assert "使用指南" in html
    # 过时内容不得回归（登录系统已于 v3.2 取消）
    assert "admin" not in html and "登录密码" not in html


def test_build_scripts_package_help_dir():
    src = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    assert '("config/help", "config/help")' in src


def test_version_numbers_correspond():
    """版本号对应: app/构建脚本/安装器/帮助页 版本一致"""
    from config.settings import APP_VERSION
    assert APP_VERSION == "3.7.0"

    build = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    assert f'APP_VERSION = "{APP_VERSION}"' in build

    iss = (ROOT / "packaging" / "QA-Tool-installer.iss").read_text(encoding="utf-8")
    assert f'MyAppVersion "{APP_VERSION}"' in iss

    guide = GUIDE.read_text(encoding="utf-8")
    assert f"v{APP_VERSION}" in guide, "帮助页版本标签与应用版本不一致"


def test_help_menu_guide_action_and_browser_open(monkeypatch):
    from PySide6.QtGui import QDesktopServices

    from ui.main_window import MainWindow

    win = MainWindow()
    try:
        help_menu = next(a.menu() for a in win.menuBar().actions() if "帮助" in a.text())
        texts = [a.text() for a in help_menu.actions()]
        assert any("使用指南" in t for t in texts)
        assert any("关于" in t for t in texts)

        guide_act = next(a for a in help_menu.actions() if "使用指南" in a.text())
        assert guide_act.shortcut().toString().upper() == "F1"

        opened = {}
        monkeypatch.setattr(QDesktopServices, "openUrl",
                            staticmethod(lambda url: opened.__setitem__("url", url)))
        guide_act.trigger()
        url = opened.get("url")
        assert url is not None and url.isLocalFile()
        assert url.toLocalFile().endswith("guide.html")

        # 视图菜单补显示模式入口（对应 F11 行为）
        view_menu = next(a.menu() for a in win.menuBar().actions() if "显示" in a.text())
        assert any("显示模式" in a.text() for a in view_menu.actions())
    finally:
        win.close()
