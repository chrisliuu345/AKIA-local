"""分析模板格式说明弹窗"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


HELP_TEXT = """<style>
body { color: #d0d3da; background: #1e1e28; font-family: "Microsoft YaHei", sans-serif; }
h3 { margin-top: 14px; color: #4da6ff; }
code { background: #35354a; color: #e0a040; padding: 2px 5px; border-radius: 3px; }
pre { background: #14141e; color: #c0c4ce; padding: 8px 12px; border-radius: 4px; border-left: 3px solid #1b5faa; }
table { border-collapse: collapse; width: 100%; }
th { background: #2c2c3a; color: #d0d3da; padding: 4px 8px; border: 1px solid #3a3a48; text-align: left; }
td { color: #b0b4be; padding: 4px 8px; border: 1px solid #3a3a48; }
</style>

<h3>支持格式</h3>
<p>JSON (<code>.json</code>) / Excel (<code>.xlsx</code> <code>.xls</code>)</p>

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
<tr><th>analysis_type</th><td>xbar_r</td></tr>
<tr><th>data_sheet</th><td>Sheet1</td></tr>
<tr><th>measurement_column</th><td>直径</td></tr>
<tr><th>subgroup_size</th><td>5</td></tr>
<tr><th>usl</th><td>10.5</td></tr>
<tr><th>lsl</th><td>9.5</td></tr>
</table>

<h3>可用分析类型（34 种）</h3>
<p><b>SPC 控制图:</b><br>
<code>xbar_r xbar_s imr p_chart np_chart c_chart u_chart cusum ewma</code></p>
<p><b>过程能力:</b><br>
<code>normal_capability non_normal_capability between_within_capability</code></p>
<p><b>MSA:</b><br>
<code>gage_rr_crossed gage_rr_nested linearity_bias attribute_agreement</code></p>
<p><b>假设检验:</b><br>
<code>t_test_1sample t_test_2sample t_test_paired anova_oneway anova_twoway normality_test variance_test</code></p>
<p><b>DOE:</b><br>
<code>factorial_design response_surface doe_analysis box_behnken</code></p>
<p><b>回归:</b><br>
<code>linear_regression correlation_heatmap</code></p>

<h3>必填字段</h3>
<p><b>analysis_type</b>（分析类型）、<b>data_sheet</b>（数据所在 Sheet 名）、<b>measurement_column</b>（测量数据列名）</p>

<h3>可选字段</h3>
<p>subgroup_column, subgroup_size, usl, lsl, target, confidence_level, title, description, output_format, output_path, chart_options</p>
"""


class TemplateHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分析模板格式说明")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("background-color: #1e1e28;")
        layout = QVBoxLayout(self)

        title = QLabel("分析模板格式说明")
        title.setFont(QFont("Microsoft YaHei", 14))
        title.setStyleSheet("color: #d0d3da;")

        layout.addWidget(title)

        help_label = QLabel(HELP_TEXT)
        help_label.setWordWrap(True)
        help_label.setTextFormat(Qt.RichText)
        from PySide6.QtWidgets import QScrollArea
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
