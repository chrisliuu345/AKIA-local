"""数据清洗自动化向导 — 一键扫描 + 批量修复 + 预览对比"""

import pandas as pd, numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QMessageBox, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY

class DataCleanWizard(QDialog):
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.original = df.copy()
        self.cleaned = df.copy()
        self._issues = []
        self._fixes_applied = []
        self.setWindowTitle("数据清洗向导")
        self.setMinimumSize(800, 600); self.resize(900, 680)
        self._setup_ui(); self._scan()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']};")
        root = QVBoxLayout(self); root.setSpacing(10)

        # 标题 + 统计
        hdr = QHBoxLayout()
        self.title = QLabel("数据清洗向导"); self.title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        hdr.addWidget(self.title); hdr.addStretch()
        self.summary = QLabel(""); self.summary.setFont(QFont("Microsoft YaHei", 10))
        self.summary.setStyleSheet(f"color: {tc['text_secondary']};")
        hdr.addWidget(self.summary)
        root.addLayout(hdr)

        # 发现的问题
        self.issue_list = QLabel("正在扫描...")
        self.issue_list.setFont(QFont("Microsoft YaHei", 10))
        self.issue_list.setStyleSheet(f"color: {tc['text_secondary']}; padding: 4px 8px; background: {tc['bg_card']}; border-radius: 6px;")
        self.issue_list.setWordWrap(True)
        root.addWidget(self.issue_list)

        # 对比表格
        splitter = QSplitter(Qt.Horizontal)
        left = QWidget(); ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0)
        ll.addWidget(QLabel("原始数据")); self.before_table = self._make_table(); ll.addWidget(self.before_table)
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0)
        rl.addWidget(QLabel("清洗后")); self.after_table = self._make_table(); rl.addWidget(self.after_table)
        splitter.addWidget(left); splitter.addWidget(right)
        root.addWidget(splitter, 1)

        # 按钮栏
        btns = QHBoxLayout()
        self.btn_rescan = QPushButton("重新扫描"); self.btn_rescan.setStyleSheet(BUTTON_SECONDARY)
        self.btn_rescan.clicked.connect(self._scan); btns.addWidget(self.btn_rescan)
        self.btn_fix_all = QPushButton("一键修复全部"); self.btn_fix_all.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_fix_all.setFont(QFont("Microsoft YaHei", 11, QFont.Bold)); self.btn_fix_all.clicked.connect(self._fix_all)
        btns.addWidget(self.btn_fix_all)
        self.btn_apply = QPushButton("应用并关闭"); self.btn_apply.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_apply.clicked.connect(self.accept); btns.addWidget(self.btn_apply)
        root.addLayout(btns)

    def _make_table(self):
        t = QTableWidget(); t.setAlternatingRowColors(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        return t

    def _show_df(self, table, df, n=30):
        table.setColumnCount(len(df.columns)); table.setHorizontalHeaderLabels(list(df.columns))
        m = min(n, len(df)); table.setRowCount(m)
        for i in range(m):
            for j, c in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val[:30] + (".." if len(val) > 30 else ""))
                table.setItem(i, j, item)
        table.resizeColumnsToContents()

    def _scan(self):
        self._issues = []
        df = self.original; numeric = df.select_dtypes(include="number").columns

        for col in numeric:
            s = pd.to_numeric(df[col], errors="coerce")
            miss = s.isna().sum()
            if miss > 0:
                self._issues.append({"type": "missing", "col": col, "count": int(miss), "pct": f"{miss/len(df)*100:.1f}%", "fix": "fill_median"})
            # IQR 异常值
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()
                if outliers > 0:
                    self._issues.append({"type": "outlier", "col": col, "count": int(outliers), "pct": f"{outliers/len(df)*100:.1f}%", "fix": "clip_iqr"})
            # Z-score 异常
            if s.std() > 0:
                z_out = (np.abs((s - s.mean()) / s.std()) > 3).sum()
                if z_out > 0 and z_out < len(s) * 0.1:
                    self._issues.append({"type": "zscore", "col": col, "count": int(z_out), "pct": f"{z_out/len(df)*100:.1f}%", "fix": "clip_3sigma"})

        # 重复行
        dup = df.duplicated().sum()
        if dup > 0:
            self._issues.append({"type": "duplicate", "col": "—", "count": int(dup), "pct": f"{dup/len(df)*100:.1f}%", "fix": "drop_dup"})

        # 常数检测
        for col in numeric:
            if df[col].nunique() == 1:
                self._issues.append({"type": "constant", "col": col, "count": 1, "pct": "—", "fix": "warn_only"})

        self._update_display()

    def _update_display(self):
        tc = theme_colors()
        if not self._issues:
            self.issue_list.setText(" 未发现数据问题 — 数据质量良好")
            self.issue_list.setStyleSheet(f"color: #27ae60; padding: 4px 8px; background: {tc['bg_card']}; border-radius: 6px;")
        else:
            lines = [f" 发现 {len(self._issues)} 个问题:"]
            for iss in self._issues:
                lines.append(f"  • [{iss['type']}] {iss['col']}: {iss['count']}处 ({iss['pct']}) → 修复: {iss['fix']}")
            self.issue_list.setText("\n".join(lines))
            self.issue_list.setStyleSheet(f"color: #ffa726; padding: 6px 8px; background: {tc['bg_card']}; border-radius: 6px;")

        self._show_df(self.before_table, self.original)
        self._show_df(self.after_table, self.cleaned)
        self.summary.setText(f"{len(self.original)}行 × {len(self.original.columns)}列 | {len(self._issues)}个问题")

    def _fix_all(self):
        self.cleaned = self.original.copy(); self._fixes_applied = []
        for iss in self._issues:
            col, fix = iss["col"], iss["fix"]
            if fix == "fill_median" and col in self.cleaned.columns:
                self.cleaned[col] = pd.to_numeric(self.cleaned[col], errors="coerce")
                med = self.cleaned[col].median()
                self.cleaned[col] = self.cleaned[col].fillna(med)
                self._fixes_applied.append(f"'{col}' 缺失值→中位数 {med:.2f}")
            elif fix == "clip_iqr" and col in self.cleaned.columns:
                s = pd.to_numeric(self.cleaned[col], errors="coerce")
                q1, q3 = s.quantile(0.25), s.quantile(0.75); iqr = q3 - q1
                self.cleaned[col] = s.clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
                self._fixes_applied.append(f"'{col}' IQR异常值→截尾 [{q1 - 1.5 * iqr:.1f}, {q3 + 1.5 * iqr:.1f}]")
            elif fix == "clip_3sigma" and col in self.cleaned.columns:
                s = pd.to_numeric(self.cleaned[col], errors="coerce")
                mu, std = s.mean(), s.std()
                self.cleaned[col] = s.clip(mu - 3 * std, mu + 3 * std)
                self._fixes_applied.append(f"'{col}' Z异常值→截尾 [{mu - 3 * std:.1f}, {mu + 3 * std:.1f}]")
            elif fix == "drop_dup":
                self.cleaned = self.cleaned.drop_duplicates()
                self._fixes_applied.append(f"删除 {iss['count']} 行重复数据")
        self._issues = [i for i in self._issues if i["fix"] != "warn_only"]
        self._update_display()
        QMessageBox.information(self, "修复完成", "已应用:\n" + "\n".join(self._fixes_applied))

    def get_result(self):
        return self.cleaned
