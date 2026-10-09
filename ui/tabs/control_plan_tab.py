"""控制计划 Tab — 工序→特性→规格→测量→控制方法的交互编辑表"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font


CP_HEADERS = [
    "工序编号", "工序名称", "特性(产品/过程)", "规格/公差",
    "测量方法", "样本量", "抽样频率", "控制方法", "反应计划",
]


class ControlPlanTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        self._rows: list = []
        self._project_context = None
        super().__init__(parent)
        self._setup_ui()
        self._new_default()

    def set_project_context(self, ctx):
        self._project_context = ctx

    def _setup_ui(self):
        theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("控制计划 (Control Plan)")
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
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

        self.btn_gen_spc = QPushButton("生成SPC清单")
        self.btn_gen_spc.setStyleSheet(BUTTON_SECONDARY)
        self.btn_gen_spc.setCursor(Qt.PointingHandCursor)
        self.btn_gen_spc.setToolTip("将控制计划中的控制项生成 SPC 监控清单")
        self.btn_gen_spc.clicked.connect(self._generate_spc_list)
        toolbar.addWidget(self.btn_gen_spc)

        toolbar.addStretch()

        self.btn_standard = QPushButton("保存标准版本")
        self.btn_standard.setStyleSheet(BUTTON_SECONDARY)
        self.btn_standard.setCursor(Qt.PointingHandCursor)
        self.btn_standard.setToolTip("为控制计划条目记录带变更原因的标准版本")
        self.btn_standard.clicked.connect(self._save_standard_version)
        toolbar.addWidget(self.btn_standard)

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

    def append_rows(self, rows: list) -> int:
        """追加控制计划行（供 FMEA → CP 链路调用）。返回实际追加行数。"""
        added = 0
        for row in rows:
            if not isinstance(row, (list, tuple)):
                continue
            normalized = [str(v) if v is not None else "" for v in row][:len(CP_HEADERS)]
            normalized += [""] * (len(CP_HEADERS) - len(normalized))
            self._rows.append(normalized)
            added += 1
        if added:
            self._rebuild_table()
        return added

    def rows_as_dicts(self) -> list:
        """当前控制计划行 → 列名到值的 dict 列表（写入项目上下文用）"""
        out = []
        for row in self._rows:
            padded = list(row) + [""] * (len(CP_HEADERS) - len(row))
            out.append({h: str(padded[i]) for i, h in enumerate(CP_HEADERS)})
        return out

    @staticmethod
    def rows_from_dicts(dicts: list) -> list:
        """项目上下文 dict 列表 → 控制计划行（兼容旧项目中的 list 行）"""
        rows = []
        for d in dicts or []:
            if isinstance(d, dict):
                rows.append([str(d.get(h, "")) for h in CP_HEADERS])
            elif isinstance(d, (list, tuple)):
                padded = [str(v) for v in d][:len(CP_HEADERS)]
                padded += [""] * (len(CP_HEADERS) - len(padded))
                rows.append(padded)
        return rows

    def _sync_context(self, change_reason: str = "控制计划条目更新"):
        """将当前行写入项目上下文（唯一事实源）"""
        if self._project_context is not None:
            self._project_context.set_control_plan(
                self.rows_as_dicts(), change_reason=change_reason, changed_by="user")

    def _save_standard_version(self):
        if self._project_context is None:
            QMessageBox.warning(self, "无项目上下文", "请先保存/加载一个 .qap 项目")
            return
        reason, ok = QInputDialog.getText(self, "保存控制计划标准", "变更原因:")
        if not ok or not str(reason or "").strip():
            return
        before = len(self._project_context.standards)
        self._sync_context(change_reason=str(reason).strip())
        created = len(self._project_context.standards) - before
        if created:
            QMessageBox.information(self, "标准已记录",
                                    f"新增 {created} 条控制计划标准版本")
        else:
            QMessageBox.information(self, "标准未变化", "条目与现行版本一致")

    def load_from_context(self):
        """从项目上下文恢复行（打开 .qap 后调用）"""
        if self._project_context is None or not self._project_context.control_plan_rows:
            return
        rows = self.rows_from_dicts(self._project_context.control_plan_rows)
        if rows:
            self._rows = rows
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
            self._sync_context()

    def _generate_spc_list(self):
        """从控制计划生成 SPC 监控清单"""
        spc_items = []
        for row in self._rows:
            control_method = row[7] if len(row) > 7 else ""
            if "控制图" in control_method or "SPC" in control_method.upper():
                spc_items.append({
                    "process": row[1] if len(row) > 1 else "",
                    "characteristic": row[2] if len(row) > 2 else "",
                    "tolerance": row[3] if len(row) > 3 else "",
                    "method": control_method,
                    "sample_size": row[5] if len(row) > 5 else "",
                    "frequency": row[6] if len(row) > 6 else "",
                })

        if not spc_items:
            QMessageBox.information(self, "生成SPC清单",
                                    "控制计划中没有包含控制图的监控项。\n"
                                    "请在控制方法列中填写如'XBar-R控制图'等SPC方法。")
            return

        lines = ["=== SPC 监控清单 ===\n"]
        for i, item in enumerate(spc_items, 1):
            lines.append(f"{i}. {item['process']} - {item['characteristic']}")
            lines.append(f"   规格: {item['tolerance']}")
            lines.append(f"   方法: {item['method']}")
            lines.append(f"   样本: {item['sample_size']}, 频率: {item['frequency']}")
            lines.append("")

        self.current_result = {
            "analysis_type": "CP → SPC",
            "params": {},
            "result": {"spc_items": spc_items, "source": "control_plan"},
            "chart_data": {},
        }

        if self._project_context is not None:
            self._project_context.set_analysis_snapshot(
                "spc_monitoring",
                {"items": spc_items, "source": "control_plan"},
            )

        main_win = self.window()
        imported = False
        if hasattr(main_win, '_import_spc_from_cp'):
            imported = bool(main_win._import_spc_from_cp(spc_items))
        self.analysis_completed.emit()

        if imported:
            QMessageBox.information(
                self, "生成完成",
                f"已生成 {len(spc_items)} 个 SPC 监控项，已在 SPC Tab 的"
                "「CP 监控清单」中显示。\n请在 SPC Tab 中选择对应列进行分析。")
        else:
            QMessageBox.warning(
                self, "生成完成",
                f"已生成 {len(spc_items)} 个 SPC 监控项，但未能同步到 SPC Tab。\n"
                "请手动打开 SPC Tab 后重试。")

    def _rebuild_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        for i, row in enumerate(self._rows):
            for j, val in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(val)))
        self.table.blockSignals(False)
        self._sync_context()
