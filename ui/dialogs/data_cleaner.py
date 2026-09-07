"""
数据清洗助手对话框
"""

import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QSplitter,
)
from PySide6.QtCore import Qt
from ui.theme import colors as theme_colors
import re


INVALID_PATTERNS = re.compile(
    r"^(?:"
    r"\*+\s*$|"
    r"N/?A\s*$|"
    r"[Nn][Oo][Nn][Ee]\s*$|"
    r"[Nn][Uu][Ll][Ll]\s*$|"
    r"[-—/]+$|"
    r"[?？]+$|"
    r"[#＃]+$|"
    r"^\s*$|"
    r"[Ee][Rr][Rr][Oo][Rr]|"
    r"[Ff][Aa][Ii][Ll][Ee][Dd]|"
    r"[Ee][Rr][Rr]"
    r")$"
)


class DataCleaner(QDialog):
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.original_df = df.copy()
        self.cleaned_df = df.copy()
        self.apply_df = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("数据清洗助手")
        self.resize(900, 650)
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        tabs.addTab(self._missing_tab(), "缺失值处理")
        tabs.addTab(self._outlier_tab(), "异常值处理")
        tabs.addTab(self._invalid_tab(), "无效值")
        tabs.addTab(self._column_tab(), "列操作")

        layout.addWidget(tabs)

        splitter = QSplitter(Qt.Horizontal)

        self.before_table = QTableWidget()
        self.before_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.before_table.setAlternatingRowColors(True)
        self._show_preview(self.before_table, self.original_df)

        self.after_table = QTableWidget()
        self.after_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.after_table.setAlternatingRowColors(True)
        self._show_preview(self.after_table, self.cleaned_df)

        container_before = QWidget()
        bl = QVBoxLayout(container_before)
        bl.setContentsMargins(0, 0, 0, 0)
        lbl_before = QLabel("原始数据")
        lbl_before.setStyleSheet(f"color: {tc['text_primary']}; font-weight: bold;")
        bl.addWidget(lbl_before)
        bl.addWidget(self.before_table)

        container_after = QWidget()
        al = QVBoxLayout(container_after)
        al.setContentsMargins(0, 0, 0, 0)
        bl2 = QHBoxLayout()
        lbl_after = QLabel("清洗后数据")
        lbl_after.setStyleSheet(f"color: {tc['text_primary']}; font-weight: bold;")
        bl2.addWidget(lbl_after)
        bl2.addStretch()
        self.null_label = QLabel("")
        bl2.addWidget(self.null_label)
        al.addLayout(bl2)
        al.addWidget(self.after_table)

        splitter.addWidget(container_before)
        splitter.addWidget(container_after)
        layout.addWidget(splitter, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.apply_btn = QPushButton("应用到所有Tab")
        self.apply_btn.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px 18px; border-radius: 6px;")
        self.apply_btn.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.apply_btn)

        self.export_btn = QPushButton("导出为Excel")
        self.export_btn.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px 18px; border-radius: 6px;")
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _show_preview(self, table, df: pd.DataFrame):
        n = min(50, len(df))
        table.setRowCount(n)
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(list(df.columns))
        for i in range(n):
            for j, _col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                table.setItem(i, j, item)

    def _missing_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.missing_method = QComboBox()
        self.missing_method.addItems(["删除含缺失的行", "均值填充", "中位数填充", "前值填充", "0 填充"])
        layout.addRow("处理方式:", self.missing_method)

        self.missing_col = QComboBox()
        self.missing_col.addItem("所有数值列")
        self.missing_col.addItems([c for c in self.original_df.columns])
        layout.addRow("目标列:", self.missing_col)

        btn = QPushButton("执行缺失值处理")
        btn.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px; border-radius: 6px;")
        btn.clicked.connect(self._do_missing)
        layout.addRow(btn)
        return w

    def _outlier_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.outlier_method = QComboBox()
        self.outlier_method.addItems(["IQR (1.5倍)", "Z-Score (3σ)"])
        layout.addRow("检测方法:", self.outlier_method)

        self.outlier_action = QComboBox()
        self.outlier_action.addItems(["删除异常值", "替换为边界值", "替换为均值"])
        layout.addRow("处理:", self.outlier_action)

        self.outlier_col = QComboBox()
        self.outlier_col.addItem("所有数值列")
        self.outlier_col.addItems([c for c in self.original_df.columns])
        layout.addRow("目标列:", self.outlier_col)

        btn = QPushButton("执行异常值处理")
        btn.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px; border-radius: 6px;")
        btn.clicked.connect(self._do_outliers)
        layout.addRow(btn)
        return w

    def _invalid_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)

        self.invalid_col = QComboBox()
        self.invalid_col.addItem("所有列")
        self.invalid_col.addItems([c for c in self.original_df.columns])
        layout.addRow("检测范围:", self.invalid_col)

        self.invalid_label = QLabel("未检测")
        self.invalid_label.setStyleSheet(f"color: {theme_colors()['text_muted']};")
        layout.addRow("状态:", self.invalid_label)

        btn_detect = QPushButton("检测并删除无效值")
        btn_detect.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px; border-radius: 6px;")
        btn_detect.clicked.connect(self._do_invalid)
        layout.addRow(btn_detect)

        lbl = QLabel("无效值示例: ***, N/A, none, null, ---, ???, 空白")
        lbl.setStyleSheet(f"color: {theme_colors()['text_muted']}; font-size: 11px;")
        layout.addRow(lbl)
        return w

    def _do_invalid(self):
        sel = self.invalid_col.currentText()
        cols = list(self.cleaned_df.columns) if sel == "所有列" else [sel]

        def _is_invalid(val):
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return True
            s = str(val).strip()
            if not s:
                return True
            return bool(INVALID_PATTERNS.match(s))

        mask = pd.Series([False] * len(self.cleaned_df), index=self.cleaned_df.index)
        for col in cols:
            if col in self.cleaned_df.columns:
                mask |= self.cleaned_df[col].apply(_is_invalid)

        removed = mask.sum()
        self.cleaned_df = self.cleaned_df[~mask].reset_index(drop=True)
        self.invalid_label.setText(f"已删除 {removed} 行")
        self._show_preview(self.after_table, self.cleaned_df)

    def _column_tab(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.drop_col = QComboBox()
        self.drop_col.addItems([c for c in self.original_df.columns])
        layout.addRow("删除列:", self.drop_col)

        btn_del = QPushButton("删除选中列")
        btn_del.setStyleSheet("background-color: #1b5faa; color: white; padding: 8px; border-radius: 6px;")
        btn_del.clicked.connect(self._do_drop_column)
        layout.addRow(btn_del)
        return w

    def _get_target_cols(self, combo) -> list:
        sel = combo.currentText()
        if sel == "所有数值列":
            return self.cleaned_df.select_dtypes(include="number").columns.tolist()
        return [sel] if sel in self.cleaned_df.columns else []

    def _do_missing(self):
        cols = self._get_target_cols(self.missing_col)
        if not cols:
            return
        method = self.missing_method.currentText()
        for col in cols:
            if method == "删除含缺失的行":
                self.cleaned_df = self.cleaned_df.dropna(subset=[col])
            elif method == "均值填充":
                self.cleaned_df[col] = self.cleaned_df[col].fillna(self.cleaned_df[col].mean())
            elif method == "中位数填充":
                self.cleaned_df[col] = self.cleaned_df[col].fillna(self.cleaned_df[col].median())
            elif method == "前值填充":
                self.cleaned_df[col] = self.cleaned_df[col].ffill()
            elif method == "0 填充":
                self.cleaned_df[col] = self.cleaned_df[col].fillna(0)
        self._show_preview(self.after_table, self.cleaned_df)
        self.null_label.setText(f"缺失值: {self.cleaned_df.isnull().sum().sum()}")

    def _do_outliers(self):
        cols = self._get_target_cols(self.outlier_col)
        if not cols:
            return
        method = self.outlier_method.currentText()
        action = self.outlier_action.currentText()
        for col in cols:
            data = pd.to_numeric(self.cleaned_df[col], errors="coerce")
            if method == "IQR (1.5倍)":
                q1, q3 = data.quantile(0.25), data.quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            else:
                mu, sigma = data.mean(), data.std()
                lower, upper = mu - 3 * sigma, mu + 3 * sigma
            if action == "删除异常值":
                self.cleaned_df = self.cleaned_df[(data >= lower) & (data <= upper) | data.isna()]
            elif action == "替换为边界值":
                self.cleaned_df[col] = data.clip(lower=lower, upper=upper)
            elif action == "替换为均值":
                m = data[(data >= lower) & (data <= upper)].mean()
                self.cleaned_df.loc[(data < lower) | (data > upper), col] = m
        self._show_preview(self.after_table, self.cleaned_df)

    def _do_drop_column(self):
        col = self.drop_col.currentText()
        if col in self.cleaned_df.columns:
            self.cleaned_df = self.cleaned_df.drop(columns=[col])
            for combo in [self.missing_col, self.outlier_col, self.drop_col]:
                if col in [combo.itemText(i) for i in range(combo.count())]:
                    combo.removeItem(combo.findText(col))
        self._show_preview(self.after_table, self.cleaned_df)

    def _on_apply(self):
        self.apply_df = self.cleaned_df.copy()
        self.accept()

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出清洗数据", "cleaned_data.xlsx", "Excel (*.xlsx)")
        if path:
            self.cleaned_df.to_excel(path, index=False)
            QMessageBox.information(self, "导出成功", f"已保存到:\n{path}")

    def get_cleaned_df(self):
        return self.apply_df
