"""FMEA 工作表 Tab — DFMEA/PFMEA 交互编辑 + RPN 自动计算 + 风险着色"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from core.i18n import i18n
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors
from core.fmea_engine import FMEAItem, FMEAEngine


class FMEATab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._engine = FMEAEngine()
        self._items: list = []
        self._mode = "pfmea"
        super().__init__(parent)
        self._setup_ui()
        self._new_analysis()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("FMEA 失效模式与影响分析")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        # 工具栏
        toolbar = QHBoxLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["PFMEA (过程)", "DFMEA (设计)"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(QLabel("模式:"))
        toolbar.addWidget(self.mode_combo)

        toolbar.addSpacing(12)

        self.btn_add = QPushButton("+ 添加行")
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

        self.btn_sort = QPushButton("按RPN排序")
        self.btn_sort.setStyleSheet(BUTTON_SECONDARY)
        self.btn_sort.setCursor(Qt.PointingHandCursor)
        self.btn_sort.clicked.connect(self._sort)
        toolbar.addWidget(self.btn_sort)

        self.btn_export = QPushButton("导出Excel")
        self.btn_export.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._export)
        toolbar.addWidget(self.btn_export)

        layout.addLayout(toolbar)

        # 风险统计
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self.stats_label)

        # FMEA 主表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(FMEAItem.HEADERS))
        self.table.setHorizontalHeaderLabels(FMEAItem.HEADERS)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setMinimumHeight(300)
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table, 1)

    def _new_analysis(self):
        self._items = self._engine.create_default(self._mode)
        self._rebuild_table()

    def _on_mode_changed(self, idx: int):
        new_mode = "dfmea" if idx == 1 else "pfmea"
        if new_mode == self._mode:
            return
        reply = QMessageBox.question(self, "切换模式",
                                     f"切换到{self.mode_combo.currentText()}模式? 当前数据将丢失。")
        if reply == QMessageBox.Yes:
            self._mode = new_mode
            self._new_analysis()
        else:
            # 恢复 combo 到当前模式
            self.mode_combo.blockSignals(True)
            self.mode_combo.setCurrentIndex(0 if self._mode == "pfmea" else 1)
            self.mode_combo.blockSignals(False)

    def _add_row(self):
        item = FMEAItem(function=f"新增功能{len(self._items)+1}")
        self._items.append(item)
        self._rebuild_table()

    def _delete_row(self):
        rows = set(i.row() for i in self.table.selectedIndexes())
        if not rows:
            return
        for r in sorted(rows, reverse=True):
            if r < len(self._items):
                del self._items[r]
        self._rebuild_table()

    def _sort(self):
        self._items = self._engine.sort_by_rpn(self._items)
        self._rebuild_table()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出FMEA", "FMEA.xlsx", "Excel (*.xlsx)")
        if path:
            df = self._engine.to_dataframe(self._items)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "导出完成", f"已保存到 {path}")

    def _on_cell_changed(self, row: int, col: int):
        """单元格编辑后自动更新 RPN 和着色"""
        if row >= len(self._items):
            return
        item = self.table.item(row, col)
        if item is None:
            return
        text = item.text().strip()

        # 更新 FMEAItem 数据
        fmea = self._items[row]
        headers = FMEAItem.HEADERS
        if col == 0: fmea.function = text
        elif col == 1: fmea.failure_mode = text
        elif col == 2: fmea.effect = text
        elif col == 3:
            try: fmea.severity = max(1, min(10, int(text)))
            except ValueError: pass
        elif col == 4: fmea.cause = text
        elif col == 5:
            try: fmea.occurrence = max(1, min(10, int(text)))
            except ValueError: pass
        elif col == 6: fmea.control = text
        elif col == 7:
            try: fmea.detection = max(1, min(10, int(text)))
            except ValueError: pass
        elif col == 8: pass  # RPN 只读
        elif col == 9: fmea.recommended_action = text
        elif col == 10: fmea.responsible = text
        elif col == 11: fmea.action_status = text

        # 自动计算 RPN 并更新列
        if col in (3, 5, 7):
            rpn = fmea.calc_rpn()
            self.table.blockSignals(True)
            rpn_item = QTableWidgetItem(str(rpn))
            rpn_item.setFlags(rpn_item.flags() & ~Qt.ItemIsEditable)
            self._color_cell(rpn_item, fmea.risk_level)
            self.table.setItem(row, 8, rpn_item)
            self.table.blockSignals(False)
            self._update_stats()

    def _rebuild_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._items))
        for i, fmea in enumerate(self._items):
            fmea.calc_rpn()
            for j, val in enumerate(fmea.to_row()):
                item = QTableWidgetItem(val)
                if j == 8:  # RPN 列只读
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self._color_cell(item, fmea.risk_level)
                self.table.setItem(i, j, item)
        self.table.blockSignals(False)
        self._update_stats()

    def _color_cell(self, item: QTableWidgetItem, level: str):
        if level == "high":
            item.setBackground(QColor("#5a1a1a"))
            item.setForeground(QColor("#ff6b6b"))
        elif level == "medium":
            item.setBackground(QColor("#5a3a1a"))
            item.setForeground(QColor("#ffa726"))
        else:
            item.setBackground(QColor("#1a3a1a"))
            item.setForeground(QColor("#51cf66"))

    def _update_stats(self):
        stats = self._engine.get_stats(self._items)
        self.stats_label.setText(
            f"共 {stats['total']} 项 | "
            f"高风险(RPN≥100): {stats['high']} | "
            f"中风险(≥50): {stats['medium']} | "
            f"低风险: {stats['low']} | "
            f"最高RPN: {stats['max_rpn']} | "
            f"Top3: {', '.join(stats['top3'])}"
        )
