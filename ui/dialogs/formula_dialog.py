"""公式编辑器对话框 — 新建/编辑/删除自定义 KPI 公式 (v2.4 F3)

- 左侧: 已保存公式列表 (选中加载编辑)
- 右侧: 名称 + 表达式 + 实时求值预览 + 可用变量列表 (双击插入)
- QSettings("QA-Tool", "Formulas") 持久化 {name: expr}
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

from core.i18n import i18n
from core.kpi_formula import (
    evaluate, FormulaError, describe_variables, variable_list,
)
from ui.theme import BUTTON_SECONDARY, colors as theme_colors


class FormulaDialog(QDialog):
    def __init__(self, parent=None, analyses: dict = None, df=None):
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("formula.title"))
        self.setMinimumSize(720, 480)
        self.resize(780, 520)
        self._analyses = analyses or {}
        self._df = df
        self._editing_name = None
        self._settings = QSettings("QA-Tool", "Formulas")
        self._setup_ui()
        self._load_formulas()

    # ── UI ───────────────────────────────────────────────
    def _setup_ui(self):
        tc = theme_colors()
        splitter = QSplitter(Qt.Horizontal)
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        # 左侧: 已保存公式
        left = QVBoxLayout()
        left.addWidget(QLabel(i18n.tr("formula.saved_list")))
        self.formula_list = QListWidget()
        self.formula_list.currentItemChanged.connect(self._on_select)
        left.addWidget(self.formula_list, 1)
        btn_new = QPushButton("+ " + i18n.tr("formula.new"))
        btn_new.setStyleSheet(BUTTON_SECONDARY)
        btn_new.clicked.connect(self._new_formula)
        left.addWidget(btn_new)
        btn_del = QPushButton(i18n.tr("formula.delete"))
        btn_del.setStyleSheet(BUTTON_SECONDARY)
        btn_del.clicked.connect(self._delete_formula)
        left.addWidget(btn_del)
        left_widget = _wrap_layout(left)
        splitter.addWidget(left_widget)

        # 右侧: 编辑区
        right = QVBoxLayout()
        right.setSpacing(8)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(i18n.tr("formula.name")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(i18n.tr("formula.name_ph"))
        name_row.addWidget(self.name_edit, 1)
        right.addLayout(name_row)

        expr_row = QHBoxLayout()
        expr_row.addWidget(QLabel(i18n.tr("formula.expression")))
        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText(i18n.tr("formula.expr_ph"))
        self.expr_edit.textChanged.connect(self._update_preview)
        expr_row.addWidget(self.expr_edit, 1)
        right.addLayout(expr_row)

        # 实时预览
        self.preview_label = QLabel(i18n.tr("formula.preview") + " —")
        self.preview_label.setStyleSheet(
            f"color: {tc['accent_bright']}; font-weight: bold; padding: 4px 0;")
        right.addWidget(self.preview_label)

        # 变量列表 (双击插入)
        right.addWidget(QLabel(i18n.tr("formula.variables")))
        self.var_list = QListWidget()
        self.var_list.setMaximumHeight(160)
        self.var_list.itemDoubleClicked.connect(self._insert_variable)
        right.addWidget(self.var_list)

        # 状态反馈 (内联, 不弹模态框)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {tc['accent_bright']};")
        right.addWidget(self.status_label)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton(i18n.tr("formula.save"))
        save_btn.setStyleSheet(BUTTON_SECONDARY)
        save_btn.clicked.connect(self._save_formula)
        btn_row.addWidget(save_btn)
        close_btn = QPushButton(i18n.tr("dlg.cancel"))
        close_btn.setStyleSheet(BUTTON_SECONDARY)
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        right.addLayout(btn_row)
        right_widget = _wrap_layout(right)
        splitter.addWidget(right_widget)
        splitter.setSizes([260, 500])

        self._refresh_variables()

    # ── 变量 ─────────────────────────────────────────────
    def _refresh_variables(self):
        self.var_list.clear()
        variables = describe_variables(self._analyses, self._df)
        self._variables = variables
        if not variables:
            self.var_list.addItem(i18n.tr("formula.empty_vars"))
            return
        for name, value in variable_list(variables):
            item = QListWidgetItem(f"{name}  =  {value}")
            item.setData(Qt.UserRole, name)
            self.var_list.addItem(item)

    def _insert_variable(self, item: QListWidgetItem):
        name = item.data(Qt.UserRole)
        if not name:
            return
        self.expr_edit.insert(name)

    # ── 预览 ─────────────────────────────────────────────
    def _update_preview(self):
        expr = self.expr_edit.text().strip()
        if not expr:
            self.preview_label.setText(i18n.tr("formula.preview") + " —")
            return
        try:
            result = evaluate(expr, self._variables)
            self.preview_label.setText(
                f"{i18n.tr('formula.preview')} {result:.4f}")
        except FormulaError as e:
            self.preview_label.setText(f"⚠ {e}")

    # ── 持久化 ───────────────────────────────────────────
    def _load_formulas(self):
        self.formula_list.clear()
        formulas = self._settings.value("formulas", {})
        if isinstance(formulas, dict):
            for name in sorted(formulas.keys()):
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, name)
                self.formula_list.addItem(item)

    def _on_select(self, item: QListWidgetItem, _prev=None):
        if item is None:
            return
        name = item.data(Qt.UserRole)
        formulas = self._settings.value("formulas", {})
        if not isinstance(formulas, dict):  # QSettings 损坏数据防御
            return
        self._editing_name = name
        self.name_edit.setText(name)
        self.expr_edit.setText(str(formulas.get(name, "")))
        # textChanged 已触发 _update_preview, 无需重复调用

    def _new_formula(self):
        self._editing_name = None
        self.name_edit.clear()
        self.expr_edit.clear()
        self.formula_list.clearSelection()
        self.name_edit.setFocus()

    def _save_formula(self):
        name = self.name_edit.text().strip()
        expr = self.expr_edit.text().strip()
        if not name:
            QMessageBox.warning(self, i18n.tr("formula.title"), i18n.tr("formula.invalid_name"))
            return
        if not expr:
            QMessageBox.warning(self, i18n.tr("formula.title"), i18n.tr("formula.invalid_expr"))
            return
        try:
            evaluate(expr, self._variables)
        except FormulaError as e:
            QMessageBox.warning(self, i18n.tr("formula.title"), str(e))
            return

        formulas = self._settings.value("formulas", {})
        if not isinstance(formulas, dict):
            formulas = {}
        old_name = getattr(self, "_editing_name", None)
        # 与其他已有公式重名: 先拒绝, 防静默覆盖 (重命名到已有名称也拦截)
        if name in formulas and name != old_name:
            QMessageBox.warning(self, i18n.tr("formula.title"),
                                i18n.tr("formula.duplicate_name"))
            return
        # 重命名保存: 删除旧键, 避免产生重复条目
        if old_name and old_name != name and old_name in formulas:
            del formulas[old_name]
            self._editing_name = None
        formulas[name] = expr
        self._settings.setValue("formulas", formulas)
        self._load_formulas()
        self.status_label.setText(f"✓ {i18n.tr('formula.saved')}")

    def _delete_formula(self):
        item = self.formula_list.currentItem()
        if item is None:
            return
        name = item.data(Qt.UserRole)
        formulas = self._settings.value("formulas", {})
        if isinstance(formulas, dict) and name in formulas:
            del formulas[name]
            self._settings.setValue("formulas", formulas)
            self._load_formulas()
            self._new_formula()
            self.status_label.setText(f"✓ {i18n.tr('formula.deleted')}")

    @staticmethod
    def load_formulas(settings: QSettings = None) -> dict:
        """静态读取已保存公式 {name: expr} — 供 Dashboard 渲染"""
        s = settings or QSettings("QA-Tool", "Formulas")
        formulas = s.value("formulas", {})
        return formulas if isinstance(formulas, dict) else {}


def _wrap_layout(layout):
    from PySide6.QtWidgets import QWidget
    w = QWidget()
    w.setLayout(layout)
    return w
