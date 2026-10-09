"""标准版本记录（v4.3.0 B3）— 只读时间线：对象 / 生效区间 / 原因 / 变更人。"""

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from core.standard_record import StandardRegistry

TYPE_LABELS = {
    "spec_limit": "规格限",
    "control_limit": "控制限",
    "standard_time": "标准工时",
    "work_combination": "作业组合票",
    "control_plan_row": "控制计划条目",
}

HEADERS = ["对象", "类型", "生效自", "生效至", "变更原因", "变更人", "记录 ID"]


class StandardHistoryDialog(QDialog):
    def __init__(self, registry: StandardRegistry | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("标准版本记录")
        self.resize(900, 460)
        layout = QVBoxLayout(self)

        records = list(getattr(registry, "records", []) or [])
        records.sort(key=lambda record: record.recorded_at, reverse=True)
        if not records:
            layout.addWidget(QLabel("尚无标准版本记录。"))
        else:
            table = QTableWidget(len(records), len(HEADERS), self)
            table.setHorizontalHeaderLabels(HEADERS)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.horizontalHeader().setStretchLastSection(True)
            for row, record in enumerate(records):
                values = [
                    record.object_ref,
                    TYPE_LABELS.get(record.object_type, record.object_type),
                    record.valid_from,
                    record.valid_to or "现行",
                    record.change_reason,
                    record.changed_by or "-",
                    record.record_id,
                ]
                for column, value in enumerate(values):
                    table.setItem(row, column, QTableWidgetItem(str(value)))
            table.resizeColumnsToContents()
            layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
