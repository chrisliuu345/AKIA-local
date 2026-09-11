"""分析模板格式说明弹窗。

内容中的分析类型 / 必填字段 / 可选字段全部由 core.template_parser.TemplateParser
常量派生（单一事实源），避免帮助文档与解析器漂移。

注意：本文件的帮助文本是普通字符串 + 占位符替换（不是 f-string），
因为文本内嵌 JSON 示例含大量 `{`/`}`——v3.6.0 曾用 f-string 拼接，
导致 `{"analyses": [...]}` 被当成格式化字段并在打开弹窗时抛
`ValueError: Invalid format specifier`。
"""
from itertools import chain

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QLabel, QPushButton, QScrollArea, QVBoxLayout,
)

from core.template_parser import TemplateParser
from ui.font_config import get_ui_font

# 类型分组仅用于排版；未列出的新类型会自动归入「其他」并出现在界面上
_TYPE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SPC 控制图", ("xbar_r", "xbar_s", "imr", "p_chart", "np_chart",
                    "c_chart", "u_chart")),
    ("过程能力", ("normal_capability", "non_normal_capability",
                  "between_within_capability")),
    ("MSA", ("gage_rr_crossed", "gage_rr_nested", "linearity_bias",
             "attribute_agreement")),
    ("假设检验", ("t_test_1sample", "t_test_2sample", "t_test_paired",
                  "anova_oneway", "anova_twoway", "normality_test",
                  "variance_test")),
    ("DOE", ("factorial_design", "response_surface", "doe_analysis",
             "box_behnken")),
)

_HELP_TEMPLATE = """<style>
body { color: #d0d3da; background: #1e1e28; font-family: "{font}", sans-serif; }
h3 { margin-top: 14px; color: #4da6ff; }
code { background: #35354a; color: #e0a040; padding: 2px 5px; border-radius: 3px; }
pre { background: #14141e; color: #c0c4ce; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #1b5faa; }
table { border-collapse: collapse; width: 100%; }
th { background: #2c2c3a; color: #d0d3da; padding: 4px 8px; border: 1px solid #3a3a48; text-align: left; }
td { color: #b0b4be; padding: 4px 8px; border: 1px solid #3a3a48; }
td.k { color: #4da6ff; }
</style>

<h3>支持格式</h3>
<p>JSON (<code>.json</code>) / Excel (<code>.xlsx</code> <code>.xls</code> <code>.xlsm</code>)</p>

<h3>JSON 格式（3 种写法）</h3>
<p><b>写法 A — 多分析数组</b></p>
<pre>{
  "analyses": [{
    "analysis_type": "xbar_r",
    "data_sheet": "Sheet1",
    "measurement_column": "直径",
    "subgroup_size": 5,
    "usl": 10.5,
    "lsl": 9.5
  }]
}</pre>

<p><b>写法 B — 单分析对象</b></p>
<pre>{
  "analysis": {
    "analysis_type": "imr",
    "measurement_column": "厚度"
  }
}</pre>

<p><b>写法 C — 扁平键值对</b></p>
<pre>{
  "analysis_type": "xbar_r",
  "data_sheet": "Sheet1",
  "measurement_column": "值"
}</pre>

<h3>Excel 格式</h3>
<p>每个 Sheet = 一个分析配置。A 列 = 参数名，B 列 = 参数值。</p>
<table>
<tr><th>参数</th><th>示例值</th></tr>
<tr><td class="k">analysis_type</td><td>xbar_r</td></tr>
<tr><td class="k">data_sheet</td><td>Sheet1</td></tr>
<tr><td class="k">measurement_column</td><td>直径</td></tr>
<tr><td class="k">subgroup_size</td><td>5</td></tr>
<tr><td class="k">usl</td><td>10.5</td></tr>
<tr><td class="k">lsl</td><td>9.5</td></tr>
</table>

<h3>可用分析类型（{type_count} 种）</h3>
{type_sections}

<h3>必填字段</h3>
<p>{required_fields}</p>

<h3>可选字段</h3>
<p>{optional_fields}</p>

<h3>用法</h3>
<p>菜单「文件 → 导入分析模板」选择模板文件后，系统按模板中的每个配置依次运行分析并生成报告；
也可从「工具 → 批量调度」对多个模板排队执行。</p>
"""


def _type_sections() -> tuple[str, int]:
    """按分组渲染分析类型，返回 (HTML 片段, 类型总数)。"""
    valid = list(TemplateParser.VALID_ANALYSIS_TYPES)
    covered = set(chain.from_iterable(types for _title, types in _TYPE_GROUPS))
    groups = list(_TYPE_GROUPS)
    extra = [t for t in valid if t not in covered]
    if extra:
        groups.append(("其他", tuple(extra)))
    html = "".join(
        f"<p><b>{title}：</b><br><code>{' '.join(types)}</code></p>"
        for title, types in groups
    )
    return html, len(valid)


def _get_help_text() -> str:
    """渲染帮助 HTML（普通 replace 占位符，JSON 花括号原样保留）。"""
    type_sections, type_count = _type_sections()
    return (_HELP_TEMPLATE
            .replace("{font}", get_ui_font())
            .replace("{type_count}", str(type_count))
            .replace("{type_sections}", type_sections)
            .replace("{required_fields}",
                     "、".join(f"<b>{f}</b>" for f in TemplateParser.REQUIRED_FIELDS))
            .replace("{optional_fields}", ", ".join(TemplateParser.OPTIONAL_FIELDS)))


class TemplateHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分析模板格式说明")
        self.setMinimumSize(720, 520)
        self.setStyleSheet("background-color: #1e1e28;")
        layout = QVBoxLayout(self)

        title = QLabel("分析模板格式说明")
        title.setFont(QFont(get_ui_font(), 14))
        title.setStyleSheet("color: #d0d3da;")
        layout.addWidget(title)

        help_label = QLabel(_get_help_text())
        help_label.setWordWrap(True)
        help_label.setTextFormat(Qt.RichText)
        help_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(help_label)
        layout.addWidget(scroll, 1)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(36)
        close_btn.setStyleSheet(
            "QPushButton { background-color: #1b5faa; color: #fff; border: none;"
            "border-radius: 6px; padding: 6px 24px; }"
            "QPushButton:hover { background-color: #15508f; }"
        )
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
