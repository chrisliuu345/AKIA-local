"""模型调用审计查看与导出 — 只读展示本地 JSONL 记录。"""
import json

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
)


class ModelAuditDialog(QDialog):
    def __init__(self, audit, parent=None):
        super().__init__(parent)
        self.audit = audit
        self.setWindowTitle("模型调用审计")
        self.resize(1050, 640)
        layout = QVBoxLayout(self)
        splitter = QSplitter(self)
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            ["时间", "类型", "状态", "供应商", "模型", "耗时(ms)"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.currentCellChanged.connect(self._show_selected)
        splitter.addWidget(self.table)
        self.detail = QTextEdit(self)
        self.detail.setReadOnly(True)
        splitter.addWidget(self.detail)
        splitter.setSizes([600, 450])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.export_button = QPushButton("导出 JSON", self)
        self.export_button.clicked.connect(self._export)
        self.refresh_button = QPushButton("刷新", self)
        self.refresh_button.clicked.connect(self.refresh)
        self.close_button = QPushButton("关闭", self)
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.export_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self):
        self._records = self.audit.records(limit=500)
        self.table.setRowCount(len(self._records))
        for row, record in enumerate(self._records):
            config = record.get("config") or {}
            values = [record.get("created_at", ""), record.get("kind", ""),
                      record.get("status", ""), config.get("provider", ""),
                      config.get("model", ""), f"{record.get('elapsed_ms', 0):.0f}"]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
        if self._records:
            self.table.setCurrentCell(0, 0)
        else:
            self.detail.setPlainText("暂无模型调用审计记录。")

    def _show_selected(self, row, *_):
        if 0 <= row < len(self._records):
            self.detail.setPlainText(json.dumps(
                self._records[row], ensure_ascii=False, indent=2))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出模型调用审计", "model_audit.json", "JSON (*.json)")
        if not path:
            return
        try:
            self.audit.export(path)
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"模型审计已导出: {path}")
