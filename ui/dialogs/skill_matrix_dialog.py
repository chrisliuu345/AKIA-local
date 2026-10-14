"""技能矩阵编辑器（v4.4.0 B5）— 人员×工序熟练度 + 工序技能要求。

保存时经 ``core.skill_matrix.SkillMatrix`` 全量校验（等级 1~5、重复项拒绝），
通过 ``on_save`` 回调交给主窗口（持久化到 ``.qap`` 的 ``skills`` 段）。
"""

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.skill_matrix import MAX_SKILL_LEVEL, MIN_SKILL_LEVEL, SkillMatrix
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY


def _item(text: str) -> QTableWidgetItem:
    return QTableWidgetItem(str(text))


class SkillMatrixDialog(QDialog):
    """两个表格：技能矩阵（人员/工序/等级）+ 工序技能要求（工序/最低等级）。"""

    def __init__(self, matrix: SkillMatrix, parent=None, on_save=None):
        super().__init__(parent)
        self.matrix = matrix
        self.on_save = on_save
        self.setWindowTitle("技能矩阵与工序要求")
        self.resize(760, 560)
        self._build_ui()
        self._load(matrix)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("技能矩阵（人员 × 工序 → 熟练度 1~5）:"))
        self.skill_table = QTableWidget(0, 3)
        self.skill_table.setHorizontalHeaderLabels(["人员", "工序", "等级"])
        self.skill_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        self.skill_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        layout.addWidget(self.skill_table, 3)
        skill_btn_row = QHBoxLayout()
        self.add_skill_btn = QPushButton("+ 添加技能")
        self.add_skill_btn.setStyleSheet(BUTTON_SECONDARY)
        self.add_skill_btn.clicked.connect(self._on_add_skill)
        self.del_skill_btn = QPushButton("删除选中技能")
        self.del_skill_btn.setStyleSheet(BUTTON_SECONDARY)
        self.del_skill_btn.clicked.connect(
            lambda: self._remove_selected(self.skill_table))
        skill_btn_row.addWidget(self.add_skill_btn)
        skill_btn_row.addWidget(self.del_skill_btn)
        skill_btn_row.addStretch()
        layout.addLayout(skill_btn_row)

        layout.addWidget(QLabel("工序技能要求（未设置最低等级 → 需有任意录入）:"))
        self.req_table = QTableWidget(0, 2)
        self.req_table.setHorizontalHeaderLabels(["工序", "最低等级"])
        self.req_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch)
        layout.addWidget(self.req_table, 2)
        req_btn_row = QHBoxLayout()
        self.add_req_btn = QPushButton("+ 添加要求")
        self.add_req_btn.setStyleSheet(BUTTON_SECONDARY)
        self.add_req_btn.clicked.connect(self._on_add_req)
        self.del_req_btn = QPushButton("删除选中要求")
        self.del_req_btn.setStyleSheet(BUTTON_SECONDARY)
        self.del_req_btn.clicked.connect(
            lambda: self._remove_selected(self.req_table))
        req_btn_row.addWidget(self.add_req_btn)
        req_btn_row.addWidget(self.del_req_btn)
        req_btn_row.addStretch()
        layout.addLayout(req_btn_row)

        buttons = QDialogButtonBox(self)
        self.save_button = buttons.addButton("保存", QDialogButtonBox.ActionRole)
        self.save_button.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.save_button.clicked.connect(self._on_save)
        buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------ 表格操作
    def _on_add_skill(self, *_args) -> None:
        self._add_skill_row()

    def _on_add_req(self, *_args) -> None:
        self._add_req_row()

    @staticmethod
    def _level_spin(value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(MIN_SKILL_LEVEL, MAX_SKILL_LEVEL)
        spin.setValue(int(value))
        return spin

    def _add_skill_row(self, operator: str = "", process_id: str = "",
                       level: int = 1) -> int:
        row = self.skill_table.rowCount()
        self.skill_table.insertRow(row)
        self.skill_table.setItem(row, 0, _item(operator))
        self.skill_table.setItem(row, 1, _item(process_id))
        self.skill_table.setCellWidget(row, 2, self._level_spin(level))
        return row

    def _add_req_row(self, process_id: str = "", min_level: int = 1) -> int:
        row = self.req_table.rowCount()
        self.req_table.insertRow(row)
        self.req_table.setItem(row, 0, _item(process_id))
        self.req_table.setCellWidget(row, 1, self._level_spin(min_level))
        return row

    @staticmethod
    def _remove_selected(table: QTableWidget) -> None:
        rows = sorted({index.row() for index in table.selectedIndexes()},
                      reverse=True)
        for row in rows:
            table.removeRow(row)

    # ------------------------------------------------------------ 数据
    def _load(self, matrix: SkillMatrix) -> None:
        self.skill_table.setRowCount(0)
        self.req_table.setRowCount(0)
        for entry in matrix.entries:
            self._add_skill_row(str(entry.get("operator", "")),
                                str(entry.get("process_id", "")),
                                int(entry.get("level", 1)))
        for req in matrix.requirements:
            self._add_req_row(str(req.get("process_id", "")),
                              int(req.get("min_level", 1)))

    def build_matrix(self) -> SkillMatrix:
        """表格 → SkillMatrix（做全量校验；空行跳过）。"""
        entries = []
        for row in range(self.skill_table.rowCount()):
            operator = self.skill_table.item(row, 0)
            process = self.skill_table.item(row, 1)
            spin = self.skill_table.cellWidget(row, 2)
            operator_text = operator.text().strip() if operator else ""
            process_text = process.text().strip() if process else ""
            if not operator_text and not process_text:
                continue
            entries.append({"operator": operator_text,
                            "process_id": process_text,
                            "level": spin.value() if spin else 1})
        requirements = []
        for row in range(self.req_table.rowCount()):
            process = self.req_table.item(row, 0)
            spin = self.req_table.cellWidget(row, 1)
            process_text = process.text().strip() if process else ""
            if not process_text:
                continue
            requirements.append({"process_id": process_text,
                                 "min_level": spin.value() if spin else 1})
        return SkillMatrix(entries=entries, requirements=requirements)

    def _on_save(self) -> None:
        try:
            matrix = self.build_matrix()
        except ValueError as exc:
            QMessageBox.warning(self, "技能矩阵无效", str(exc))
            return
        if callable(self.on_save):
            self.on_save(matrix)
        self.matrix = matrix
        QMessageBox.information(
            self, "技能矩阵",
            f"已保存：技能 {len(matrix.entries)} 条 · 工序要求 "
            f"{len(matrix.requirements)} 条\n指纹 {matrix.fingerprint()[:24]}…")


__all__ = ["SkillMatrixDialog"]
