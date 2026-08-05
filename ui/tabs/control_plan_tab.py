"""控制计划 Tab — 工序→特性→规格→测量→控制方法的交互编辑表"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors


CP_HEADERS = [
    "工序编号", "工序名称", "特性(产品/过程)", "规格/公差",
    "测量方法", "样本量", "抽样频率", "控制方法", "反应计划",
]


class ControlPlanTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._rows: list = []
        super().__init__(parent)
        self._setup_ui()
        self._new_default()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("控制计划 (Control Plan)")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("+ 添加工序")
        self.btn_add.setStyleSheet(BUTTON_SECONDARY)
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._add_row)
        toolbar.addWidget(self.btn_add)

        self.btn_delete = QPushButton("删除选中行")
        self.btn_delete.setStyleSheet(BUTTON_SECONDARY)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete_row)
        toolbar.addWidget(self.btn_delete)

        toolbar.addStretch()

        self.btn_export = QPushButton("导出Excel")
        self.btn_export.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export)
        toolbar.addWidget(self.btn_export)

        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(CP_HEADERS))
        self.table.setHorizontalHeaderLabels(CP_HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setMinimumHeight(300)
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table, 1)

    def _new_default(self):
        self._rows = [
            ["OP10", "来料检验", "尺寸规格", "10±0.05mm",
             "卡尺", "5", "每批", "首件检验", "隔离+通知供应商"],
            ["OP20", "CNC加工", "孔径", "8.0±0.02mm",
             "气动量仪", "3", "每小时", "XBar-R控制图", "调整刀具补偿"],
            ["OP30", "热处理", "硬度", "58-62 HRC",
             "硬度计", "2", "每炉", "记录曲线", "调整温度/时间"],
            ["OP40", "最终检验", "外观", "无划伤/凹陷",
             "目视", "100%", "全检", "不合格品标识", "返工或报废"],
        ]
        self._rebuild_table()

    def _add_row(self):
        self._rows.append([f"OP{len(self._rows)*10+10}", "", "", "", "", "", "", "", ""])
        self._rebuild_table()

    def _delete_row(self):
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return
        for r in sorted(rows, reverse=True):
            if r < len(self._rows):
                del self._rows[r]
        self._rebuild_table()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出控制计划", "Control_Plan.xlsx", "Excel (*.xlsx)")
        if path:
            import pandas as pd
            df = pd.DataFrame(self._rows, columns=CP_HEADERS)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "导出完成", f"已保存到 {path}")

    def _on_cell_changed(self, row: int, col: int):
        if row >= len(self._rows):
            return
        item = self.table.item(row, col)
        if item:
            while len(self._rows) <= row:
                self._rows.append([""] * len(CP_HEADERS))
            self._rows[row][col] = item.text().strip()

    def _rebuild_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        self.table.blockSignals(False)
