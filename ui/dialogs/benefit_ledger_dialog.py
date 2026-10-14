"""收益账本对话框（v4.4.0 B4）— 改善收益 / COPQ 四类 / ROI / 月度复算。

汇总仅计置信 A/A-/B 的记录；C 级在"待完善"清单可见但不入汇总。
"""

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ui.theme import BUTTON_SECONDARY

_COLUMNS = ("月份", "案例", "类别", "分区", "置信", "金额", "标准版本", "来源", "备注")
_KIND_LABELS = {"improvement": "改善", "cost_of_quality": "COPQ"}


class BenefitLedgerDialog(QDialog):
    """收益账本总览 + 月度复算入口。"""

    def __init__(self, ledger, parent=None, *, recompute=None):
        super().__init__(parent)
        self.ledger = ledger
        self.recompute = recompute
        self.setWindowTitle("收益账本")
        self.resize(960, 560)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.summary_label)

        grid = QGridLayout()
        self.breakdown_labels = {}
        for column, name in enumerate(("预防", "鉴定", "内部失败", "外部失败")):
            grid.addWidget(QLabel(f"{name}:"), 0, column * 2)
            label = QLabel("0.00")
            grid.addWidget(label, 0, column * 2 + 1)
            self.breakdown_labels[name] = label
        layout.addLayout(grid)

        month_row = QHBoxLayout()
        month_row.addWidget(QLabel("复算月份:"))
        self.month_edit = QLineEdit()
        self.month_edit.setPlaceholderText("YYYY-MM（当月复算口径前移；历史月冻结）")
        month_row.addWidget(self.month_edit)
        self.recompute_button = QPushButton("复算本月")
        self.recompute_button.setStyleSheet(BUTTON_SECONDARY)
        self.recompute_button.clicked.connect(self._on_recompute)
        month_row.addWidget(self.recompute_button)
        month_row.addStretch()
        layout.addLayout(month_row)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels(list(_COLUMNS))
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(self)
        refresh_button = buttons.addButton("刷新", QDialogButtonBox.ActionRole)
        refresh_button.clicked.connect(self.refresh)
        buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------ 数据
    def refresh(self) -> None:
        summary = self.ledger.summary()
        roi = summary["roi"]
        roi_text = f"{roi:.2f}" if roi is not None else "—（无 COPQ 基数）"
        self.summary_label.setText(
            f"改善收益合计 <b>{summary['improvement_total']:,.2f}</b> · "
            f"COPQ 合计 <b>{summary['copq_total']:,.2f}</b> · "
            f"ROI <b>{roi_text}</b> · "
            f"记录 {summary['count']} 条 · 待完善(C) {summary['pending_count']} 条")
        for name, value in summary["copq_breakdown"].items():
            self.breakdown_labels[name].setText(f"{value:,.2f}")
        records = list(self.ledger.records)
        self.table.setRowCount(len(records))
        for row, record in enumerate(reversed(records)):
            basis = record.basis or {}
            standard = str(basis.get("standard_ref") or "—")
            if len(standard) > 22:
                standard = standard[:22] + "…"
            values = (
                record.month,
                record.case_id,
                record.category,
                _KIND_LABELS.get(record.ledger_kind, record.ledger_kind),
                record.confidence + ("" if record.admits_to_summary else "（待完善）"),
                f"{record.amount:,.2f}",
                standard,
                record.source,
                record.note,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def _on_recompute(self) -> None:
        month = self.month_edit.text().strip()
        if not month:
            QMessageBox.information(self, "月度复算", "请填写复算月份（YYYY-MM）")
            return
        if not callable(self.recompute):
            QMessageBox.information(self, "月度复算", "当前入口未接入复算")
            return
        try:
            result = self.recompute(month)
        except ValueError as exc:
            QMessageBox.warning(self, "复算失败", str(exc))
            return
        self.refresh()
        if result.get("frozen"):
            QMessageBox.information(
                self, "月度复算",
                f"{month} 为历史月：口径已冻结，仅生成快照（未改写记录）")
        else:
            count = len(result.get("updates") or [])
            text = (f"{month} 复算完成：更新 {count} 条记录的标准口径"
                    + ("（均为最新版本）" if count == 0 else ""))
            QMessageBox.information(self, "月度复算", text)


__all__ = ["BenefitLedgerDialog"]
