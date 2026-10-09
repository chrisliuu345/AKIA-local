"""证据视图（v4.3.0 B4-2）— 结论 → 凭证 → 账本事件 → 原始引用。

支持：账本哈希链校验（篡改定位）、凭证指纹重算、同数据重跑 diff、
追溯码定位（报告页脚 → 分析结论 → 账本事件）。
"""

import html

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout,
)

from core.evidence import ConclusionCredential, credential_trace_code


class EvidenceViewDialog(QDialog):
    def __init__(self, analyses: dict, ledger, parent=None, *, registry=None,
                 measurements=None, frame_provider=None, ledger_failures: int = 0):
        super().__init__(parent)
        self.analyses = dict(analyses or {})
        self.ledger = ledger
        self.registry = registry
        self.measurements = measurements
        self.frame_provider = frame_provider
        self.ledger_failures = int(ledger_failures or 0)
        self._fingerprint_result = ""
        self._verify_result = None
        self.setWindowTitle("证据视图")
        self.resize(1080, 680)
        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        locate_row = QHBoxLayout()
        locate_row.addWidget(QLabel("追溯码定位:"))
        self.trace_edit = QLineEdit(self)
        self.trace_edit.setPlaceholderText("粘贴报告页脚 12 位追溯码")
        locate_row.addWidget(self.trace_edit)
        self.locate_button = QPushButton("定位", self)
        self.locate_button.clicked.connect(self._locate_trace)
        locate_row.addWidget(self.locate_button)
        locate_row.addStretch()
        layout.addLayout(locate_row)

        splitter = QSplitter(self)
        self.list_widget = QListWidget(self)
        self.list_widget.currentRowChanged.connect(lambda *_: self._show_selected())
        splitter.addWidget(self.list_widget)

        right = QVBoxLayout()
        self.detail = QTextBrowser(self)
        right.addWidget(self.detail, 2)
        self.event_table = QTableWidget(0, 6, self)
        self.event_table.setHorizontalHeaderLabels(
            ["序号", "时间", "类型", "操作者", "对象引用", "摘要"])
        self.event_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.event_table.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self.event_table, 3)
        splitter.addWidget(self._wrap(right))
        splitter.setSizes([280, 780])
        layout.addWidget(splitter)

        buttons = QDialogButtonBox(self)
        self.verify_button = buttons.addButton("重新校验账本链",
                                               QDialogButtonBox.ActionRole)
        self.fingerprint_button = buttons.addButton("重算数据指纹",
                                                    QDialogButtonBox.ActionRole)
        buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        self.verify_button.clicked.connect(self._verify_chain)
        self.fingerprint_button.clicked.connect(self._recompute_fingerprint)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _wrap(layout):
        from PySide6.QtWidgets import QWidget

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    # ------------------------------------------------------------ 数据
    def _refresh_list(self):
        self.list_widget.clear()
        for key in sorted(self.analyses, key=str):
            analysis = self.analyses.get(key) or {}
            trace = credential_trace_code([analysis.get("credential")])
            label = (f"[{key}] {analysis.get('analysis_type', '?')} · "
                     + (trace or "无凭证"))
            item = QListWidgetItem(label)
            item.setData(256, key)
            self.list_widget.addItem(item)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)
        else:
            self.detail.setHtml("<p>当前没有可查看的分析结论。</p>")

    def _selected_key(self):
        item = self.list_widget.currentItem()
        return item.data(256) if item is not None else None

    def _show_selected(self):
        key = self._selected_key()
        if key is None:
            return
        analysis = self.analyses.get(key) or {}
        credential = analysis.get("credential")
        if not credential:
            self.detail.setHtml(
                "<h3>不可复核</h3><p>该分析记录缺少判定凭证，无法追溯计算过程。</p>")
            self._fill_events(key, "", "")
            return
        try:
            cred = ConclusionCredential.from_dict(credential)
        except (TypeError, ValueError) as exc:
            self.detail.setHtml(f"<h3>凭证无效</h3><p>{exc}</p>")
            self._fill_events(key, "", "")
            return
        params = cred.params or {}
        trace = credential_trace_code([credential])
        chain = self._verify_result or (self.ledger.verify() if self.ledger is not None
                                        else {"ok": None, "reason": "无账本"})
        chain_color = "#2ecc71" if chain.get("ok") else "#e74c3c"
        chain_text = ("账本链校验通过" if chain.get("ok")
                      else f"账本链校验失败：{chain.get('reason', '')}")
        diff = analysis.get("rerun_diff") or {}
        diff_text = "无重跑记录"
        if diff:
            if not diff.get("comparable"):
                diff_text = "不可比较（缺少旧凭证）"
            elif diff.get("identical"):
                diff_text = "同数据重跑结果一致"
            else:
                diff_text = ("同数据重跑存在差异："
                             f"凭证变化 {list((diff.get('credential_changes') or {}).keys())}，"
                             f"结果变化={diff.get('result_changed')}")
        rows = [
            ("分析", f"[{key}] {analysis.get('analysis_type', '?')}"),
            ("完成时间", str(analysis.get("_completed_at", ""))),
            ("规则版本", cred.rule_version),
            ("数据指纹", cred.data_fingerprint),
            ("软件版本", cred.app_version),
            ("判定参数", str(params)),
            ("标准版本", str(params.get("standard_ref", "")) or "未关联"),
            ("标准生效", str(params.get("standard_as_of", "")) or "—"),
            ("追溯码", trace or "无"),
            ("复核", diff_text),
            ("指纹重算", self._fingerprint_result or "未执行"),
        ]
        parts = [f'<h3>[{key}] {analysis.get("analysis_type", "?")}</h3>',
                 f'<p style="color:{chain_color}"><b>{chain_text}</b></p>']
        if self.ledger_failures:
            parts.append(f'<p style="color:#e74c3c">账本写入失败累计：'
                         f'{self.ledger_failures} 次</p>')
        parts.append("<table>" + "".join(
            f"<tr><td><b>{html.escape(str(name))}</b></td>"
            f"<td>{html.escape(str(value))}</td></tr>"
            for name, value in rows) + "</table>")
        self.detail.setHtml("".join(parts))
        self._fill_events(key, cred.data_fingerprint, trace)

    def _fill_events(self, key, fingerprint: str, trace: str = ""):
        events = []
        seen = set()
        if self.ledger is not None:
            refs = [f"tab:{key}"]
            if fingerprint:
                refs.append(fingerprint)
            if trace:
                refs.append(f"trace:{trace}")
            for ref in refs:
                for event in self.ledger.events_for(ref):
                    if event.seq not in seen:
                        seen.add(event.seq)
                        events.append(event)
        events.sort(key=lambda event: event.seq)
        self.event_table.setRowCount(len(events))
        for row, event in enumerate(events):
            summary = ", ".join(f"{k}={v}" for k, v in list(event.payload.items())[:3])
            values = [str(event.seq), event.at, event.event_type, event.actor,
                      "、".join(event.object_refs[:3]), summary[:120]]
            for column, value in enumerate(values):
                self.event_table.setItem(row, column, QTableWidgetItem(value))
        self.event_table.resizeColumnsToContents()

    # ------------------------------------------------------------ 动作
    def _verify_chain(self):
        if self.ledger is None:
            QMessageBox.information(self, "账本校验", "当前项目没有证据账本")
            return
        self._verify_result = self.ledger.verify()
        self._show_selected()
        QMessageBox.information(
            self, "账本校验",
            "校验通过" if self._verify_result.get("ok")
            else f"校验失败：{self._verify_result.get('reason', '')}")

    def _recompute_fingerprint(self):
        key = self._selected_key()
        analysis = self.analyses.get(key) or {}
        credential = analysis.get("credential")
        if not credential:
            QMessageBox.information(self, "指纹重算", "该结论没有凭证，不可复核")
            return
        if not callable(self.frame_provider):
            QMessageBox.information(self, "指纹重算", "当前没有可用的数据来源")
            return
        frame = self.frame_provider(key)
        if frame is None:
            QMessageBox.information(self, "指纹重算", "分析数据不可用（无法重算）")
            return
        matches = ConclusionCredential.from_dict(credential).verify_dataframe(frame)
        self._fingerprint_result = "一致" if matches else "不一致（数据已变化）"
        self._show_selected()
        QMessageBox.information(self, "指纹重算", self._fingerprint_result)

    def _locate_trace(self):
        target = self.trace_edit.text().strip().upper()
        if not target:
            return
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            key = item.data(256)
            analysis = self.analyses.get(key) or {}
            if credential_trace_code([analysis.get("credential")]) == target:
                self.list_widget.setCurrentRow(row)
                return
        QMessageBox.information(self, "追溯码定位", "未找到匹配的结论")
