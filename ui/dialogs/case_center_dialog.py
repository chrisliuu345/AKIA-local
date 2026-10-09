"""改善案例中心（v4.3.0 B1-4）— 查看/新建/打开当前项目的改善案例。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QInputDialog, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.case_workflow import PHASES, CaseWorkflow

STATUS_LABELS = {
    "draft": "草稿",
    "active": "进行中",
    "verifying": "验证中",
    "closed": "已关闭",
    "abandoned": "已放弃",
}


class CaseCenterDialog(QDialog):
    """案例列表 + 新建/打开/导出；双击行等价于「打开工作台」。"""

    def __init__(self, workflows=None, parent=None, create_callback=None):
        super().__init__(parent)
        self.workflows: list = workflows if workflows is not None else []
        self.create_callback = create_callback
        self.setWindowTitle("改善案例中心")
        self.resize(860, 480)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        hint = QLabel("案例随项目保存：新建/打开后请用「文件 → 保存项目」写入 .qap。")
        hint.setStyleSheet("color: #8a8f98;")
        layout.addWidget(hint)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["案例号", "标题", "状态", "阶段进度", "负责人", "更新时间"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(lambda *_: self._on_open())
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.new_button = QPushButton("新建案例", self)
        self.open_button = QPushButton("打开工作台", self)
        self.export_button = QPushButton("导出 Markdown", self)
        self.new_button.clicked.connect(self._on_new)
        self.open_button.clicked.connect(self._on_open)
        self.export_button.clicked.connect(self._on_export)
        actions.addWidget(self.new_button)
        actions.addWidget(self.open_button)
        actions.addWidget(self.export_button)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------ 数据
    def refresh(self):
        self.table.setRowCount(len(self.workflows))
        for row, workflow in enumerate(self.workflows):
            done = len(PHASES) - len(workflow.missing_phases())
            values = [
                workflow.case.id,
                workflow.case.title,
                STATUS_LABELS.get(workflow.case.status, workflow.case.status),
                f"{done}/{len(PHASES)}",
                workflow.owner or workflow.case.owner or "-",
                workflow.case.updated_at,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        has_rows = bool(self.workflows)
        self.open_button.setEnabled(has_rows)
        self.export_button.setEnabled(has_rows)
        if has_rows and self.table.currentRow() < 0:
            self.table.selectRow(0)

    def selected_workflow(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.workflows):
            return None
        return self.workflows[row]

    # ------------------------------------------------------------ 动作
    def _on_new(self):
        title, ok = QInputDialog.getText(self, "新建改善案例", "案例标题:",
                                         text="改善案例")
        if not ok:
            return
        workflow = None
        if callable(self.create_callback):
            workflow = self.create_callback(str(title or "").strip())
        if workflow is None:
            workflow = CaseWorkflow(title=str(title or "").strip() or "改善案例")
            self.workflows.append(workflow)
        elif workflow not in self.workflows:
            self.workflows.append(workflow)
        self.refresh()
        self.table.selectRow(len(self.workflows) - 1)

    def _on_open(self):
        if self.selected_workflow() is not None:
            self.accept()

    def _on_export(self):
        workflow = self.selected_workflow()
        if workflow is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出改善案例", f"{workflow.case.id}.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(workflow.to_markdown())
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"已导出：{path}")
