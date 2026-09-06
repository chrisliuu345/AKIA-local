"""
图表类型图库面板 — 可折叠分类网格，替代纯下拉框

默认折叠为一行标题，展开后按类别分组的图块网格（点击即选图表类型）。
"""

from typing import List, Tuple

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout,
)
from PySide6.QtGui import QFont

from ui.font_config import get_ui_font
from ui.widgets.chart_icons import get_chart_icon

GALLERY_GROUPS: List[Tuple[str, List[str]]] = [
    ("分布分析", ["直方图", "箱线图", "概率图"]),
    ("相关与比较", ["散点图", "矩阵图", "散点矩阵图", "残差图"]),
    ("质量工具", ["帕累托图", "小多图"]),
    ("试验设计 DOE", ["主效应图", "交互效应图", "等值线图", "3D曲面图"]),
    ("时间序列", ["时间序列图"]),
    ("商务图表", ["气泡图", "雷达图", "瀑布图"]),
]

_ICON_SIZE = QSize(22, 22)

_SELECTED_QSS = """
    QPushButton {
        background: #2a5f9e;
        color: #ffffff;
        border: 1px solid #4da6ff;
        border-radius: 6px;
        padding: 4px 6px;
        text-align: left;
    }
"""
_TILE_QSS = """
    QPushButton {
        background: #262632;
        color: #d8d9de;
        border: 1px solid #3a3a48;
        border-radius: 6px;
        padding: 4px 6px;
        text-align: left;
    }
    QPushButton:hover { background: #2f2f3d; border-color: #4a4a58; }
"""


class ChartGallery(QWidget):
    """图表类型图库：分类网格，点击切换"""

    type_chosen = Signal(str)

    def __init__(self, chart_types: List[str], parent=None):
        super().__init__(parent)
        self._expanded = False
        self._current: str = ""
        self._tile_buttons = {}
        self._chart_types = list(chart_types)
        self._setup_ui()
        if self._chart_types:
            self.set_current(self._chart_types[0])

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)

        icon = QLabel("🖼")
        icon.setFont(QFont(get_ui_font(), 13))
        header.addWidget(icon)

        self._title = QLabel("图表类型库")
        self._title.setFont(QFont(get_ui_font(), 12, QFont.Weight.Bold))
        header.addWidget(self._title)

        self._current_label = QLabel("")
        self._current_label.setStyleSheet("color: #4da6ff; font-size: 12px;")
        header.addWidget(self._current_label)
        header.addStretch()

        self._toggle_btn = QPushButton("展开")
        self._toggle_btn.setFixedWidth(76)
        self._toggle_btn.setFixedHeight(28)
        self._toggle_btn.setStyleSheet(
            "QPushButton { background: #3a3a48; color: #e1e2e6; border: none;"
            " border-radius: 6px; font-size: 12px; }"
            "QPushButton:hover { background: #4a4a58; }")
        self._toggle_btn.clicked.connect(self.toggle_expand)
        header.addWidget(self._toggle_btn)

        layout.addLayout(header)

        self._body = QWidget()
        self._body.setVisible(False)
        self._groups_layout = QVBoxLayout(self._body)
        self._groups_layout.setContentsMargins(2, 2, 2, 2)
        self._groups_layout.setSpacing(8)
        self._build_groups()
        layout.addWidget(self._body)

    def _build_groups(self):
        known = set(self._chart_types)
        while self._groups_layout.count():
            item = self._groups_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._tile_buttons.clear()

        for category, names in GALLERY_GROUPS:
            tiles = [n for n in names if n in known]
            if not tiles:
                continue
            cat_lbl = QLabel(category)
            cat_lbl.setStyleSheet("color: #8a8d9a; font-size: 11px;")
            cat_lbl.setFont(QFont(get_ui_font(), 10, QFont.Weight.Bold))
            self._groups_layout.addWidget(cat_lbl)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(6)
            for idx, name in enumerate(tiles):
                btn = QPushButton(f"  {name}")
                icon = get_chart_icon(name)
                if not icon.isNull():
                    btn.setIcon(icon)
                    btn.setIconSize(_ICON_SIZE)
                btn.setFont(QFont(get_ui_font(), 11))
                btn.setMinimumHeight(52)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(_TILE_QSS)
                btn.clicked.connect(lambda _=False, t=name: self._on_tile_clicked(t))
                grid.addWidget(btn, idx // 2, idx % 2)
                self._tile_buttons[name] = btn
            self._groups_layout.addLayout(grid)

    def _on_tile_clicked(self, chart_type: str):
        self.set_current(chart_type)
        self.type_chosen.emit(chart_type)
        self.collapse()

    def set_current(self, chart_type: str):
        """高亮当前类型并同步标题"""
        self._current = chart_type
        self._current_label.setText(chart_type)
        for name, btn in self._tile_buttons.items():
            btn.setStyleSheet(_SELECTED_QSS if name == chart_type else _TILE_QSS)

    def current_type(self) -> str:
        return self._current

    def toggle_expand(self):
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self._expanded = True
        self._body.setVisible(True)
        self._toggle_btn.setText("收起")

    def collapse(self):
        self._expanded = False
        self._body.setVisible(False)
        self._toggle_btn.setText("展开")

    def is_expanded(self) -> bool:
        return self._expanded
