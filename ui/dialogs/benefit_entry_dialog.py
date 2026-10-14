"""案例收益录入对话框（v4.4.0 B4）— 关闭案例后登记收益/COPQ 记录。

金额口径（与 `core.benefit_ledger` 一致）：
- 改善收益 = (基线值 − 新值) × 数量 × 单价；
- COPQ 四类 = 数量 × 单价（损失/投入方向）。
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLabel, QLineEdit, QVBoxLayout,
)


class BenefitEntryDialog(QDialog):
    """收益/COPQ 录入（可编辑后再入账；C 级只登记不计入汇总）。"""

    def __init__(self, parent=None, *, default_currency: str = ""):
        super().__init__(parent)
        self.setWindowTitle("登记收益（改善效果量化）")
        self.resize(460, 420)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.month_edit = QLineEdit(datetime.now().astimezone().strftime("%Y-%m"))
        form.addRow("月份:", self.month_edit)
        self.category_combo = QComboBox()
        self.category_combo.addItems(
            ["改善收益", "预防", "鉴定", "内部失败", "外部失败"])
        form.addRow("类别:", self.category_combo)
        self.confidence_combo = QComboBox()
        self.confidence_combo.addItems(["A", "A-", "B", "C"])
        self.confidence_combo.setCurrentText("B")
        form.addRow("置信分级:", self.confidence_combo)
        self.baseline_spin = QDoubleSpinBox()
        self.baseline_spin.setRange(-1e12, 1e12)
        self.baseline_spin.setDecimals(4)
        form.addRow("基线值:", self.baseline_spin)
        self.new_value_spin = QDoubleSpinBox()
        self.new_value_spin.setRange(-1e12, 1e12)
        self.new_value_spin.setDecimals(4)
        form.addRow("新值:", self.new_value_spin)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1e12)
        self.quantity_spin.setDecimals(2)
        self.quantity_spin.setValue(1.0)
        form.addRow("数量:", self.quantity_spin)
        self.unit_cost_spin = QDoubleSpinBox()
        self.unit_cost_spin.setRange(0, 1e12)
        self.unit_cost_spin.setDecimals(4)
        form.addRow("单价:", self.unit_cost_spin)
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("计量单位（如 秒 / 件 / 元）")
        form.addRow("单位:", self.unit_edit)
        self.currency_edit = QLineEdit(default_currency)
        self.currency_edit.setPlaceholderText("币种（如 CNY）")
        form.addRow("币种:", self.currency_edit)
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("备注 / 口径说明（可选）")
        form.addRow("备注:", self.note_edit)
        layout.addLayout(form)
        hint = QLabel("改善收益 = (基线值 − 新值) × 数量 × 单价；\n"
                      "COPQ 四类 = 数量 × 单价；C 级仅登记，不计入汇总。")
        hint.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def draft(self) -> dict:
        """表单 → `record_case_benefit` 关键字参数。"""
        category = self.category_combo.currentText()
        return {
            "month": self.month_edit.text().strip(),
            "category": category,
            "ledger_kind": ("improvement" if category == "改善收益"
                            else "cost_of_quality"),
            "confidence": self.confidence_combo.currentText(),
            "baseline_value": self.baseline_spin.value(),
            "new_value": self.new_value_spin.value(),
            "quantity": self.quantity_spin.value(),
            "unit_cost": self.unit_cost_spin.value(),
            "unit": self.unit_edit.text().strip(),
            "currency": self.currency_edit.text().strip(),
            "note": self.note_edit.text().strip(),
        }


__all__ = ["BenefitEntryDialog"]
