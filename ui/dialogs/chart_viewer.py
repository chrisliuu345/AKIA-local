"""
图表查看器对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from ui.theme import colors as theme_colors


class ChartViewer(QDialog):
    def __init__(self, figure: Figure, parent=None, title: str = "图表查看"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.Window)
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']};")

        layout = QVBoxLayout(self)

        self.canvas = FigureCanvasQTAgg(figure)
        layout.addWidget(self.canvas, 1)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class MplCanvas(FigureCanvasQTAgg):
    """可嵌入PySide6的matplotlib画布"""

    def __init__(self, figure: Figure = None, parent=None):
        self.fig = figure or Figure(dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
