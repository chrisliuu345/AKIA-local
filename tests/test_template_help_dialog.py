"""模板格式说明弹窗测试 — JSON 示例可解析 / 内容与解析器同步 / 菜单入口不崩溃。

回归背景: v3.6.0 起帮助文本用 f-string 拼接, JSON 示例中的花括号被当作
格式化字段, 打开弹窗抛 ValueError: Invalid format specifier。
"""
import json
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.template_parser import TemplateParser
from ui.dialogs.template_help_dialog import TemplateHelpDialog, _get_help_text


@pytest.fixture(scope="module")
def help_text() -> str:
    return _get_help_text()


def test_help_text_renders_without_format_error(help_text):
    assert isinstance(help_text, str) and len(help_text) > 800
    assert "分析类型" in help_text
    assert "必填字段" in help_text and "可选字段" in help_text


def test_json_examples_are_valid_json(help_text):
    blocks = re.findall(r"<pre>(.*?)</pre>", help_text, re.S)
    assert len(blocks) == 3, "应包含 JSON 写法 A/B/C 三个示例"
    parsed = [json.loads(block) for block in blocks]
    assert parsed[0]["analyses"][0]["analysis_type"] == "xbar_r"
    assert parsed[1]["analysis"]["analysis_type"] == "imr"
    assert parsed[2]["measurement_column"] == "值"


def test_type_list_matches_parser(help_text):
    """帮助页类型必须与解析器常量一致（既不缺也不多报）。"""
    valid = list(TemplateParser.VALID_ANALYSIS_TYPES)
    for atype in valid:
        assert atype in help_text, f"帮助页缺少分析类型 {atype}"
    assert f"{len(valid)} 种" in help_text
    # 历史文档曾列出解析器不支持的类型
    for bogus in ("cusum", "ewma", "linear_regression", "correlation_heatmap"):
        assert f">{bogus}<" not in help_text, f"帮助页不应宣传不支持的类型 {bogus}"


def test_required_and_optional_fields_from_parser(help_text):
    for field in TemplateParser.REQUIRED_FIELDS:
        assert field in help_text
    for field in TemplateParser.OPTIONAL_FIELDS:
        assert field in help_text


def test_unknown_new_type_falls_back_to_extra_group(monkeypatch):
    """新增分析类型未登记分组时也应出现在帮助页（避免再次漂移）。"""
    from ui.dialogs import template_help_dialog as mod

    monkeypatch.setattr(TemplateParser, "VALID_ANALYSIS_TYPES",
                        [*TemplateParser.VALID_ANALYSIS_TYPES, "brand_new_type"])
    text = mod._get_help_text()
    assert "brand_new_type" in text
    assert f"{len(TemplateParser.VALID_ANALYSIS_TYPES)} 种" in text


def test_dialog_constructs_and_shows_types():
    dlg = TemplateHelpDialog()
    try:
        assert dlg.windowTitle() == "分析模板格式说明"
        from PySide6.QtWidgets import QLabel
        texts = [w.text() for w in dlg.findChildren(QLabel)]
        assert any("xbar_r" in t for t in texts)
    finally:
        dlg.deleteLater()


def test_main_window_menu_entry_opens_dialog(monkeypatch):
    """复现原始报错路径: 帮助 → 模板格式说明。"""
    from ui.dialogs import template_help_dialog as mod
    from ui.main_window import MainWindow

    opened = {}
    original_init = mod.TemplateHelpDialog.__init__

    def spy_init(self, parent=None):
        opened["title"] = True
        return original_init(self, parent)

    monkeypatch.setattr(mod.TemplateHelpDialog, "__init__", spy_init)
    monkeypatch.setattr(mod.TemplateHelpDialog, "exec", lambda self: 0)

    win = MainWindow()
    try:
        win._on_template_help()          # 修复前此处抛 ValueError
        assert opened.get("title") is True
    finally:
        win.close()
