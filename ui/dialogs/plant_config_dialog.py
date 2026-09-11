"""产线配置可视化编辑器（v3.8.0-②）— data/plant.json 表格化编辑。

对标 Minitab RTSPC Autoconfigure 思路：产线/工位/通道/规格限/节拍/成本
一次表格配置，支持 Excel·CSV 模板导入导出；保存即写回 plant.json，
看板与实时 OEE/告警读取同一份配置。
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.i18n import i18n
from core.plant import (
    ROW_COLUMNS, PlantConfig, default_plant_path, plant_to_rows,
    rows_from_excel, rows_to_plant,
)
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY


class PlantConfigDialog(QDialog):
    """plant.json 表格编辑器 — 逻辑薄，解析/归一化复用 core.plant。"""

    def __init__(self, parent=None, path: str | Path | None = None):
        super().__init__(parent)
        self.path = Path(path) if path else default_plant_path()
        self.cfg = PlantConfig.load(self.path)
        self.setWindowTitle(i18n.tr("plant.dialog_title"))
        self.resize(1080, 560)
        self._setup_ui()
        self.load_rows(plant_to_rows(self.cfg))

    # ---------- UI ----------
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(i18n.tr("plant.hint").format(path=str(self.path)))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        layout.addWidget(hint)

        self.table = QTableWidget()
        self.table.setColumnCount(len(ROW_COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _key, label in ROW_COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        row_bar = QHBoxLayout()
        for text_key, slot in (("plant.add_row", self._on_add_row),
                               ("plant.del_row", self._on_remove_rows),
                               ("plant.import", self._on_import_template),
                               ("plant.export", self._on_export_template)):
            btn = QPushButton(i18n.tr(text_key))
            btn.setStyleSheet(BUTTON_SECONDARY)
            btn.clicked.connect(slot)
            row_bar.addWidget(btn)
        row_bar.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        row_bar.addWidget(self.status_label)
        layout.addLayout(row_bar)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        cancel_btn = QPushButton(i18n.tr("plant.cancel"))
        cancel_btn.setStyleSheet(BUTTON_SECONDARY)
        cancel_btn.clicked.connect(self.reject)
        btn_bar.addWidget(cancel_btn)
        self.save_btn = QPushButton(i18n.tr("plant.save"))
        self.save_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.save_btn.clicked.connect(self._on_save)
        btn_bar.addWidget(self.save_btn)
        layout.addLayout(btn_bar)

    # ---------- 数据 ----------
    def load_rows(self, rows: list[dict]) -> None:
        self.table.setRowCount(0)
        for row in rows:
            self.append_row(row)

    def append_row(self, row: dict | None = None) -> None:
        row = row or {}
        idx = self.table.rowCount()
        self.table.insertRow(idx)
        for col, (key, _label) in enumerate(ROW_COLUMNS):
            value = row.get(key)
            text = "" if value is None else str(value)
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(idx, col, item)

    def table_rows(self) -> list[dict]:
        rows: list[dict] = []
        for r in range(self.table.rowCount()):
            row: dict = {}
            for c, (key, _label) in enumerate(ROW_COLUMNS):
                item = self.table.item(r, c)
                row[key] = item.text().strip() if item else ""
            if any(str(v).strip() for v in row.values()):
                rows.append(row)
        return rows

    def current_config(self) -> PlantConfig:
        cfg = rows_to_plant(self.table_rows(), self.path)
        cfg.path = self.path
        return cfg

    def save_to(self, path: str | Path) -> None:
        cfg = rows_to_plant(self.table_rows(), path)
        cfg.save(path)
        self.cfg = cfg

    # ---------- 槽 ----------
    def _on_add_row(self):
        self.append_row({"line": self.cfg.lines[0].name if self.cfg.lines else "",
                         "station": "", "device": ""})
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)

    def _on_remove_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        if not rows and self.table.rowCount():
            self.table.removeRow(self.table.rowCount() - 1)

    def _on_import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("plant.import"), "",
            "表格 (*.xlsx *.xls *.xlsm *.csv)")
        if not path:
            return
        try:
            rows = rows_from_excel(path)
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("plant.import"), str(e))
            return
        if not rows:
            QMessageBox.warning(self, i18n.tr("plant.import"),
                                i18n.tr("plant.import_empty"))
            return
        self.load_rows(rows)
        self.status_label.setText(i18n.tr("plant.imported").format(n=len(rows)))

    def _on_export_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("plant.export"), "plant_template.xlsx",
            "Excel (*.xlsx)")
        if not path:
            return
        try:
            import pandas as pd
            rows = self.table_rows()
            df = pd.DataFrame([{label: row.get(key, "")
                                for key, label in ROW_COLUMNS} for row in rows])
            df.to_excel(path, index=False)
        except Exception as e:
            QMessageBox.warning(self, i18n.tr("plant.export"), str(e))
            return
        self.status_label.setText(i18n.tr("plant.exported").format(path=path))

    def _on_save(self):
        rows = self.table_rows()
        if not rows:
            QMessageBox.warning(self, self.windowTitle(),
                                i18n.tr("plant.need_rows"))
            return
        cfg = rows_to_plant(rows, self.path)
        if not any(st.device for line in cfg.lines for st in line.stations):
            QMessageBox.warning(self.windowTitle(),
                                i18n.tr("plant.need_device"))
            return
        try:
            cfg.save(self.path)
        except Exception as e:
            QMessageBox.critical(self, self.windowTitle(), str(e))
            return
        self.cfg = cfg
        self.status_label.setText(i18n.tr("plant.saved").format(path=str(self.path)))
        self.accept()
