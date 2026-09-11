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
    for anchor in ("quick-start", "data-import", "templates", "modules", "charts",
                   "export", "ai", "realtime", "hardware", "faq", "support"):
        assert f'id="{anchor}"' in html, f"缺少锚点 {anchor}"
    # 目录需覆盖新增章节（避免正文有、导航找不到）
    for anchor in ("#templates", "#realtime"):
        assert f'href="{anchor}"' in html, f"目录缺少 {anchor} 链接"
    assert html.count("<details") >= 4  # FAQ 折叠块
    assert "使用指南" in html
    # 过时内容不得回归（登录系统已于 v3.2 取消）
    assert "admin" not in html and "登录密码" not in html


def test_guide_template_types_match_parser():
    """使用指南的分析类型清单必须与模板解析器一致（单一事实源同步）。"""
    from core.template_parser import TemplateParser

    html = GUIDE.read_text(encoding="utf-8")
    for atype in TemplateParser.VALID_ANALYSIS_TYPES:
        assert atype in html, f"指南缺少分析类型 {atype}"
    assert f"{len(TemplateParser.VALID_ANALYSIS_TYPES)} 种" in html
    # 历史文档曾宣传解析器不支持的类型
    assert "34 种" not in html


def test_guide_documents_realtime_tooling():
    html = GUIDE.read_text(encoding="utf-8")
    for item in ("产线配置 (plant.json)", "告警中心", "连接器健康", "实时看板",
                 "dashboard_token", "ts_raw_retention_days", "A+"):
        assert item in html, f"指南缺少 {item} 说明"


def test_build_scripts_package_help_dir():
    src = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    assert '("config/help", "config/help")' in src


def test_version_numbers_correspond():
    """版本号对应: 安装器/帮助页跟随即 config.settings.APP_VERSION（单一事实源）"""
    from config.settings import APP_VERSION

    build = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    assert "from config.settings import APP_VERSION" in build, \
        "构建脚本应从 config.settings 导入版本号"
    assert 'APP_VERSION = "' not in build, "构建脚本不应硬编码版本号"

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
