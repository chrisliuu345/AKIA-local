"""PPAP 生产件批准 Tab — 18项矩阵 + 尺寸报告 + PSW"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QTextEdit, QMessageBox, QFileDialog,
    QGroupBox,
)
import numpy as np

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH
from analysis.quality.ppap_engine import (
    PPAPReport, PPAP_ITEMS, SUBMISSION_LEVELS
)


class PPAPTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.report = PPAPReport()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # 零件信息
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("零件号:"))
        self.part_no = QLineEdit()
        info_row.addWidget(self.part_no)
        info_row.addWidget(QLabel("零件名:"))
        self.part_name = QLineEdit()
        info_row.addWidget(self.part_name)
        info_row.addWidget(QLabel("供应商:"))
        self.supplier = QLineEdit()
        info_row.addWidget(self.supplier)
        info_row.addWidget(QLabel("等级:"))
        self.level_combo = QComboBox()
        for lv, desc in SUBMISSION_LEVELS.items():
            self.level_combo.addItem(f"Lv{lv}: {desc}", lv)
        self.level_combo.currentIndexChanged.connect(self._refresh_matrix)
        info_row.addWidget(self.level_combo)
        layout.addLayout(info_row)

        # 完成度
        self.pct_label = QLabel("完成度: 0%")
        self.pct_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4da6ff;")
        layout.addWidget(self.pct_label)

        # 18项状态矩阵
        self.matrix = QTableWidget(18, 3)
        self.matrix.setHorizontalHeaderLabels(["#", "提交项目", "状态"])
        self.matrix.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.matrix.verticalHeader().setVisible(False)
        for row, (n, name, key) in enumerate(PPAP_ITEMS):
            self.matrix.setItem(row, 0, QTableWidgetItem(str(n)))
            self.matrix.setItem(row, 1, QTableWidgetItem(name))
            cb = QComboBox()
            cb.addItems(["pending", "in_progress", "complete", "n_a"])
            cb.currentTextChanged.connect(lambda v, r=row: self._on_status_change(r, v))
            self.matrix.setCellWidget(row, 2, cb)
        layout.addWidget(self.matrix)

        # 尺寸报告
        dim_group = QGroupBox("关键尺寸报告")
        dim_layout = QVBoxLayout(dim_group)
        self.dim_table = QTableWidget(0, 6)
        self.dim_table.setHorizontalHeaderLabels(["特性", "名义值", "USL", "LSL", "测量值(逗号分隔)", "Cp/Cpk(自动)"])
        self.dim_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        dim_layout.addWidget(self.dim_table)
        dim_btn = QHBoxLayout()
        add_btn = QPushButton("+ 添加尺寸")
        add_btn.clicked.connect(lambda: self.dim_table.setRowCount(self.dim_table.rowCount() + 1))
        dim_btn.addWidget(add_btn)
        calc_btn = QPushButton("计算 Cp/Cpk")
        calc_btn.clicked.connect(self._calc_capability)
        dim_btn.addWidget(calc_btn)
        dim_btn.addStretch()
        dim_layout.addLayout(dim_btn)
        layout.addWidget(dim_group)

        # PSW
        psw_group = QGroupBox("PSW 零件提交保证书")
        psw_layout = QVBoxLayout(psw_group)
        self.psw_text = QTextEdit()
        self.psw_text.setMaximumHeight(80)
        psw_layout.addWidget(self.psw_text)
        layout.addWidget(psw_group)

        # 操作
        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存 PPAP")
        save_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        export_btn = QPushButton("导出 Excel")
        export_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        export_btn.clicked.connect(self._export_xlsx)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

    def _refresh_matrix(self):
        level = self.level_combo.currentData()
        required = self.report.required_items() if self.report.submission_level == level else set()
        # update report level
        self.report.submission_level = level
        required = set(self.report.required_items())
        for row in range(18):
            n = row + 1
            item = self.matrix.item(row, 0)
            if item and n not in required:
                item.setBackground(QTableWidgetItem().background())  # reset
                for c in range(3):
                    self.matrix.item(row, c).setForeground(QTableWidgetItem().foreground())
            elif item and n in required:
                # highlight required items
                pass  # keep default style

    def _on_status_change(self, row, status):
        """状态变更回调（保留供未来行着色）"""

    def _calc_capability(self):
        for r in range(self.dim_table.rowCount()):
            try:
                usl = float(self.dim_table.item(r, 2).text() or 0)
                lsl = float(self.dim_table.item(r, 3).text() or 0)
                vals_str = self.dim_table.item(r, 4).text() if self.dim_table.item(r, 4) else ""
                vals = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
                if vals and usl > lsl:
                    arr = np.array(vals)
                    sigma = arr.std(ddof=1) if len(arr) > 1 else 0.001
                    cp = (usl - lsl) / (6 * sigma) if sigma > 0 else 0
                    cpk = min((usl - arr.mean()) / (3 * sigma), (arr.mean() - lsl) / (3 * sigma)) if sigma > 0 else 0
                    self.dim_table.setItem(r, 5, QTableWidgetItem(f"Cp={cp:.2f} Cpk={cpk:.2f}"))
            except (ValueError, AttributeError):
                continue
        QMessageBox.information(self, "计算完成", "Cp/Cpk 已更新")

    def _save(self):
        self.report.part_number = self.part_no.text()
        self.report.part_name = self.part_name.text()
        self.report.supplier = self.supplier.text()
        self.report.submission_level = self.level_combo.currentData() or 3
        self.report.psw_notes = self.psw_text.toPlainText()
        done = sum(1 for r in range(18) if self.matrix.cellWidget(r, 2).currentText() in ("complete", "n_a"))
        pct = round(done / 18 * 100, 1)
        self.pct_label.setText(f"完成度: {pct}%")
        QMessageBox.information(self, "保存完成", f"PPAP 报告已暂存 (完成度: {pct}%)")

    def _export_xlsx(self):
        self._save()
        path, _ = QFileDialog.getSaveFileName(self, "导出 PPAP Excel", "ppap_report.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        try:
            import pandas as pd
            rows = []
            for r in range(18):
                n = self.matrix.item(r, 0).text()
                name = self.matrix.item(r, 1).text()
                status = self.matrix.cellWidget(r, 2).currentText()
                rows.append({"#": n, "项目": name, "状态": status})
            df_items = pd.DataFrame(rows)
            df_dim = pd.DataFrame(columns=["特性", "名义值", "USL", "LSL", "测量值", "Cp/Cpk"])
            for r in range(self.dim_table.rowCount()):
                row_data = {}
                for c in range(6):
                    item = self.dim_table.item(r, c)
                    row_data[df_dim.columns[c]] = item.text() if item else ""
                df_dim = pd.concat([df_dim, pd.DataFrame([row_data])], ignore_index=True)
            with pd.ExcelWriter(path) as w:
                df_items.to_excel(w, sheet_name="PPAP清单", index=False)
                df_dim.to_excel(w, sheet_name="尺寸报告", index=False)
            QMessageBox.information(self, "导出完成", "PPAP Excel 已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
