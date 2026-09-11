"""PPAP 生产件批准 Tab — 18项矩阵 + 尺寸报告 + PSW"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QLineEdit, QTextEdit, QMessageBox, QFileDialog,
    QGroupBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import numpy as np

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH
from analysis.quality.ppap_engine import (
    PPAPReport, PPAP_ITEMS, SUBMISSION_LEVELS
)
from config.settings import CAPABILITY_GRADES


class PPAPTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        self._project_context = None
        super().__init__(parent)
        self.report = PPAPReport()
        self._setup_ui()

    def set_project_context(self, ctx):
        self._project_context = ctx

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("零件号:"))
        self.part_no = QLineEdit()
        self.part_no.setMinimumWidth(120)
        info_row.addWidget(self.part_no)
        info_row.addWidget(QLabel("零件名:"))
        self.part_name = QLineEdit()
        self.part_name.setMinimumWidth(120)
        info_row.addWidget(self.part_name)
        info_row.addWidget(QLabel("供应商:"))
        self.supplier = QLineEdit()
        self.supplier.setMinimumWidth(120)
        info_row.addWidget(self.supplier)
        info_row.addWidget(QLabel("等级:"))
        self.level_combo = QComboBox()
        self.level_combo.setMinimumWidth(150)
        for lv, desc in SUBMISSION_LEVELS.items():
            self.level_combo.addItem(f"Lv{lv}: {desc}", lv)
        self.level_combo.currentIndexChanged.connect(self._refresh_matrix)
        info_row.addWidget(self.level_combo)
        layout.addLayout(info_row)

        self.pct_label = QLabel("完成度: 0%")
        self.pct_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4da6ff;")
        layout.addWidget(self.pct_label)

        self.matrix = QTableWidget(18, 3)
        self.matrix.setHorizontalHeaderLabels(["#", "提交项目", "状态"])
        self.matrix.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.matrix.verticalHeader().setVisible(False)
        for row, (n, name, _key) in enumerate(PPAP_ITEMS):
            self.matrix.setItem(row, 0, QTableWidgetItem(str(n)))
            self.matrix.setItem(row, 1, QTableWidgetItem(name))
            cb = QComboBox()
            cb.addItems(["pending", "in_progress", "complete", "n_a"])
            cb.currentTextChanged.connect(lambda v, r=row: self._on_status_change(r, v))
            self.matrix.setCellWidget(row, 2, cb)
        layout.addWidget(self.matrix)

        dim_group = QGroupBox("关键尺寸报告")
        dim_layout = QVBoxLayout(dim_group)
        self.dim_table = QTableWidget(0, 6)
        self.dim_table.setHorizontalHeaderLabels(["特性", "名义值", "USL", "LSL", "测量值(逗号分隔)", "Cp/Cpk(自动)"])
        dim_hdr = self.dim_table.horizontalHeader()
        dim_hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        dim_hdr.setMinimumSectionSize(60)
        for i in range(1, 6):
            dim_hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
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

        psw_group = QGroupBox("PSW 零件提交保证书")
        psw_layout = QVBoxLayout(psw_group)
        self.psw_text = QTextEdit()
        self.psw_text.setMaximumHeight(80)
        psw_layout.addWidget(self.psw_text)
        layout.addWidget(psw_group)

        btn_row = QHBoxLayout()
        auto_btn = QPushButton("自动填充 (从分析结果)")
        auto_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        auto_btn.clicked.connect(self._auto_fill_from_analyses)
        btn_row.addWidget(auto_btn)
        save_btn = QPushButton("保存 PPAP")
        save_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        export_btn = QPushButton("导出 Excel")
        export_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        export_btn.clicked.connect(self._export_xlsx)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)
        self._refresh_matrix()      # 初始等级即渲染必交项样式（切换前也有提示）

    def _auto_fill_from_analyses(self):
        """从主窗口的分析结果自动填充 PPAP"""
        main_win = self.window()
        if main_win and hasattr(main_win, 'analyses'):
            self.auto_populate_from_analyses(main_win.analyses)
        else:
            QMessageBox.information(self, "自动填充", "无法获取分析结果。请先运行分析。")

    def _refresh_matrix(self):
        """提交等级切换 → 重绘 18 项矩阵的必交 / 非必交样式。

        修复: 第 2 列是 setCellWidget(状态下拉框)，没有对应的 QTableWidgetItem，
        原实现对 range(3) 无条件 `.item(row, c).setForeground(...)`，切换等级时
        必然抛 AttributeError: 'NoneType' object has no attribute 'setForeground'。
        现跳过空单元格，并顺带补上"必交项高亮"（原分支是 pass，形同未实现）。
        """
        level = self.level_combo.currentData()
        self.report.submission_level = level
        required = set(self.report.required_items())
        for row in range(self.matrix.rowCount()):
            num_item = self.matrix.item(row, 0)
            if num_item is None:
                continue
            is_required = (row + 1) in required
            for col in range(self.matrix.columnCount()):
                cell = self.matrix.item(row, col)      # 状态列为 cellWidget → None
                if cell is None:
                    continue
                if is_required:
                    cell.setForeground(QColor("#4da6ff"))
                else:
                    cell.setData(Qt.ForegroundRole, None)   # 还原默认前景/背景
                    cell.setData(Qt.BackgroundRole, None)
                font = cell.font()
                font.setBold(bool(is_required and col == 1))
                cell.setFont(font)
        self._update_pct()

    def _on_status_change(self, row, status):
        """A2: 状态变更实时刷新完成度"""
        self._update_pct()

    def _calc_capability(self):
        for r in range(self.dim_table.rowCount()):
            try:
                # 空单元格 → item() 为 None（与矩阵同类的崩溃隐患），显式提示
                usl_item, lsl_item = self.dim_table.item(r, 2), self.dim_table.item(r, 3)
                if not (usl_item and lsl_item and usl_item.text().strip()
                        and lsl_item.text().strip()):
                    self.dim_table.setItem(r, 5, QTableWidgetItem("缺少 USL/LSL"))
                    continue
                usl = float(usl_item.text())
                lsl = float(lsl_item.text())
                vals_item = self.dim_table.item(r, 4)
                vals_str = vals_item.text() if vals_item else ""
                vals = [float(v.strip()) for v in vals_str.split(",") if v.strip()]
                if len(vals) < 2:
                    self.dim_table.setItem(r, 5, QTableWidgetItem("样本不足(n<2)"))
                    continue
                if usl <= lsl:
                    self.dim_table.setItem(r, 5, QTableWidgetItem("USL≤LSL 无效"))
                    continue
                arr = np.array(vals)
                sigma = arr.std(ddof=1)
                if sigma == 0:
                    self.dim_table.setItem(r, 5, QTableWidgetItem("σ=0 无法计算"))
                    continue
                cp = (usl - lsl) / (6 * sigma)
                cpk = min((usl - arr.mean()) / (3 * sigma), (arr.mean() - lsl) / (3 * sigma))
                self.dim_table.setItem(r, 5, QTableWidgetItem(f"Cp={cp:.2f} Cpk={cpk:.2f}"))
            except (ValueError, AttributeError):
                continue
        QMessageBox.information(self, "计算完成", "Cp/Cpk 已更新")

    def _update_pct(self):
        """A3: 使用引擎 completion_pct（按提交等级要求项目计算，非全部18项）"""
        level = self.level_combo.currentData() or 3
        self.report.submission_level = level
        for r in range(18):
            status = self.matrix.cellWidget(r, 2).currentText()
            self.report.items[r].status = status
        pct = self.report.completion_pct
        self.pct_label.setText(f"完成度: {pct}% (等级{level}: {len(self.report.required_items())}项)")
        self._sync_context()

    def _sync_context(self):
        """将 PPAP 状态写入项目上下文（五链贯通 → 8D/报告）"""
        if self._project_context is None:
            return
        items = {}
        for r in range(18):
            n_item = self.matrix.item(r, 0)
            cb = self.matrix.cellWidget(r, 2)
            items[n_item.text() if n_item else str(r + 1)] = (
                cb.currentText() if cb else "pending")
        self._project_context.set_ppap_report({
            "part_number": self.part_no.text(),
            "part_name": self.part_name.text(),
            "supplier": self.supplier.text(),
            "submission_level": self.level_combo.currentData(),
            "completion_pct": self.report.completion_pct,
            "items": items,
        })

    def auto_populate_from_analyses(self, analyses: dict):
        """从分析结果自动填充 PPAP 项目状态

        Args:
            analyses: {tab_idx: {analysis_type, params, result}} 分析结果字典
        """
        updated = []

        for _idx, analysis in analyses.items():
            analysis_type = analysis.get("analysis_type", "")
            result = analysis.get("result", {})

            if "R&R" in analysis_type or "Type 1" in analysis_type or "MSA" in analysis_type:
                pct_grr = result.get("percentages", {}).get("pct_grr", 0)
                cap = result.get("capability", {})
                is_capable = cap.get("is_capable", False) if cap else (pct_grr < 30)

                status = "complete" if is_capable else "in_progress"
                self.report.items[7].status = status
                cb = self.matrix.cellWidget(7, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#8 MSA: {status}")

            elif "能力" in analysis_type or "Capability" in analysis_type:
                cap = result.get("capability", {})
                cpk = cap.get("cpk", 0)
                cpk_a = CAPABILITY_GRADES["A"][0]
                is_capable = cpk >= cpk_a if cpk else False

                status = "complete" if is_capable else "in_progress"
                self.report.items[10].status = status
                cb = self.matrix.cellWidget(10, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#11 能力: Cpk={cpk:.2f} → {status}")

            elif "FMEA" in analysis_type:
                status = "complete"
                self.report.items[3].status = status
                cb = self.matrix.cellWidget(3, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#4 FMEA: {status}")

            elif "控制计划" in analysis_type or "Control Plan" in analysis_type:
                status = "complete"
                self.report.items[6].status = status
                cb = self.matrix.cellWidget(6, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#7 控制计划: {status}")

        self._update_pct()

        if updated:
            QMessageBox.information(self, "PPAP 自动填充",
                                    "已更新以下项目:\n" + "\n".join(updated))
        else:
            QMessageBox.information(self, "PPAP 自动填充",
                                    "未找到可填充的分析结果。\n"
                                    "请先运行 MSA/能力/FMEA 分析。")

    def _save(self):
        self.report.part_number = self.part_no.text()
        self.report.part_name = self.part_name.text()
        self.report.supplier = self.supplier.text()
        self.report.psw_notes = self.psw_text.toPlainText()
        self._update_pct()
        QMessageBox.information(self, "保存完成", f"PPAP 报告已暂存 (完成度: {self.report.completion_pct}%)")

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
