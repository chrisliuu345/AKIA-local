"""示例插件 — 展示 IPlugin 接口的最简实现"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from core.plugin_manager import IPlugin


class ExamplePlugin(IPlugin):
    name = "示例插件"
    version = "0.1"
    category = "engineering"
    icon = "📦"
    description = "一个演示第三方插件开发的示例"

    def create_tab(self, parent=None):
        w = QWidget(parent)
        layout = QVBoxLayout(w)
        lbl = QLabel("这是第三方插件示例")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 18px; color: #e1e2e6;")
        layout.addWidget(lbl)
        btn = QPushButton("点击测试")
        btn.clicked.connect(lambda: self.analyze(None))
        layout.addWidget(btn)
        layout.addStretch()
        return w

    def analyze(self, df):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "示例插件", "插件运行正常!")


PLUGIN = ExamplePlugin()
