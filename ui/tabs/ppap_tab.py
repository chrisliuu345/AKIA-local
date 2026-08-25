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

        # 零件信息
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

        # PSW
        psw_group = QGroupBox("PSW 零件提交保证书")
        psw_layout = QVBoxLayout(psw_group)
        self.psw_text = QTextEdit()
        self.psw_text.setMaximumHeight(80)
        psw_layout.addWidget(self.psw_text)
        layout.addWidget(psw_group)

        # 操作
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

    def _auto_fill_from_analyses(self):
        """从主窗口的分析结果自动填充 PPAP"""
        main_win = self.window()
        if main_win and hasattr(main_win, 'analyses'):
            self.auto_populate_from_analyses(main_win.analyses)
        else:
            QMessageBox.information(self, "自动填充", "无法获取分析结果。请先运行分析。")

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
        """A2: 状态变更实时刷新完成度"""
        self._update_pct()

    def _calc_capability(self):
        for r in range(self.dim_table.rowCount()):
            try:
                usl = float(self.dim_table.item(r, 2).text() or 0)
                lsl = float(self.dim_table.item(r, 3).text() or 0)
                vals_str = self.dim_table.item(r, 4).text() if self.dim_table.item(r, 4) else ""
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
        # 同步状态矩阵到引擎 items
        for r in range(18):
            status = self.matrix.cellWidget(r, 2).currentText()
            self.report.items[r].status = status
        pct = self.report.completion_pct
        self.pct_label.setText(f"完成度: {pct}% (等级{level}: {len(self.report.required_items())}项)")

    def auto_populate_from_analyses(self, analyses: dict):
        """从分析结果自动填充 PPAP 项目状态

        Args:
            analyses: {tab_idx: {analysis_type, params, result}} 分析结果字典
        """
        updated = []

        # 扫描分析结果，填充 #8 (MSA) 和 #11 (初始能力)
        for idx, analysis in analyses.items():
            analysis_type = analysis.get("analysis_type", "")
            result = analysis.get("result", {})

            # #8: MSA — Gage R&R 或 Type 1
            if "R&R" in analysis_type or "Type 1" in analysis_type or "MSA" in analysis_type:
                pct_grr = result.get("percentages", {}).get("pct_grr", 0)
                cap = result.get("capability", {})
                is_capable = cap.get("is_capable", False) if cap else (pct_grr < 30)

                status = "complete" if is_capable else "in_progress"
                self.report.items[7].status = status  # PPAP #8 (index 7)
                cb = self.matrix.cellWidget(7, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#8 MSA: {status}")

            # #11: 初始能力 — Capability 分析
            elif "能力" in analysis_type or "Capability" in analysis_type:
                cap = result.get("capability", {})
                cpk = cap.get("cpk", 0)
                cpk_a = CAPABILITY_GRADES["A"][0]  # 1.33
                is_capable = cpk >= cpk_a if cpk else False

                status = "complete" if is_capable else "in_progress"
                self.report.items[10].status = status  # PPAP #11 (index 10)
                cb = self.matrix.cellWidget(10, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#11 能力: Cpk={cpk:.2f} → {status}")

            # #4: DFMEA — FMEA 分析
            elif "FMEA" in analysis_type:
                status = "complete"
                self.report.items[3].status = status  # PPAP #4 (index 3)
                cb = self.matrix.cellWidget(3, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#4 FMEA: {status}")

            # #7: 控制计划
            elif "控制计划" in analysis_type or "Control Plan" in analysis_type:
                status = "complete"
                self.report.items[6].status = status  # PPAP #7 (index 6)
                cb = self.matrix.cellWidget(6, 2)
                if cb:
                    cb.setCurrentText(status)
                updated.append(f"#7 控制计划: {status}")

        self._update_pct()

        if updated:
            QMessageBox.information(self, "PPAP 自动填充",
                                    f"已更新以下项目:\n" + "\n".join(updated))
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
