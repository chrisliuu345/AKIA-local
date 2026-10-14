"""抽样检验 Tab — AQL查表 + 随机/分层/系统抽样 + 序贯 + 计量型 + C=0"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
    QMessageBox,
)
from PySide6.QtGui import QColor
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import (
    BUTTON_PRIMARY_STRETCH,
    BUTTON_SECONDARY,
    BUTTON_TOGGLE,
    FONT_18B,
)
from ui.theme import colors as theme_colors
from core.sampling_engine import SamplingEngine
from core.sampling_plan import scope_key_for

_BATCH_METHODS = {"随机": "random", "分层": "stratified", "系统": "systematic"}
_BATCH_STATES = {"normal": "正常", "tightened": "加严", "reduced": "放宽"}
_BATCH_OVERRIDES = {"正常": "normal", "加严": "tightened", "放宽": "reduced"}


class SamplingTab(BaseAnalysisTab):
    def __init__(self, p=None):
        self._sampling_manager = None
        self._batch_plan = None
        super().__init__(p)
        self._setup_ui()

    def set_data(self, df, info=None):
        BaseAnalysisTab.set_data(self, df, info)
        if df is not None:
            self._populate()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.title_label = QLabel("抽样检验")
        self.title_label.setFont(FONT_18B)
        layout.addWidget(self.title_label)
        mb = QHBoxLayout()
        self.btn_aql = QPushButton("AQL 查表")
        self.btn_aql.setCheckable(True)
        self.btn_aql.setChecked(True)
        self.btn_aql.setStyleSheet(BUTTON_TOGGLE)
        self.btn_aql.clicked.connect(lambda: self._switch(0))
        self.btn_rand = QPushButton("随机抽样")
        self.btn_rand.setCheckable(True)
        self.btn_rand.setStyleSheet(BUTTON_TOGGLE)
        self.btn_rand.clicked.connect(lambda: self._switch(1))
        self.btn_seq = QPushButton("序贯检验")
        self.btn_seq.setCheckable(True)
        self.btn_seq.setStyleSheet(BUTTON_TOGGLE)
        self.btn_seq.clicked.connect(lambda: self._switch(2))
        self.btn_measure = QPushButton("计量型抽样")
        self.btn_measure.setCheckable(True)
        self.btn_measure.setStyleSheet(BUTTON_TOGGLE)
        self.btn_measure.clicked.connect(lambda: self._switch(3))
        self.btn_czero = QPushButton("C=0 抽样")
        self.btn_czero.setCheckable(True)
        self.btn_czero.setStyleSheet(BUTTON_TOGGLE)
        self.btn_czero.clicked.connect(lambda: self._switch(4))
        self.btn_batch = QPushButton("批检验（转移）")
        self.btn_batch.setCheckable(True)
        self.btn_batch.setStyleSheet(BUTTON_TOGGLE)
        self.btn_batch.setToolTip("供应商·产品线转移状态机 / 检验批历史 / 抽样留痕（v4.4.0 B3）")
        self.btn_batch.clicked.connect(lambda: self._switch(5))
        mb.addWidget(self.btn_aql)
        mb.addWidget(self.btn_rand)
        mb.addWidget(self.btn_seq)
        mb.addWidget(self.btn_measure)
        mb.addWidget(self.btn_czero)
        mb.addWidget(self.btn_batch)
        mb.addStretch()
        layout.addLayout(mb)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._aql_panel(tc))
        self.stack.addWidget(self._random_panel(tc))
        self.stack.addWidget(self._sequential_panel(tc))
        self.stack.addWidget(self._measurement_panel(tc))
        self.stack.addWidget(self._czero_panel(tc))
        self.stack.addWidget(self._batch_panel(tc))
        layout.addWidget(self.stack)
        self.result = QTableWidget()
        self.result.setAlternatingRowColors(True)
        layout.addWidget(self.result, 1)

    def _switch(self, i):
        for b, j in [
            (self.btn_aql, 0),
            (self.btn_rand, 1),
            (self.btn_seq, 2),
            (self.btn_measure, 3),
            (self.btn_czero, 4),
            (self.btn_batch, 5),
        ]:
            b.setChecked(j == i)
        self.stack.setCurrentIndex(i)

    def _aql_panel(self, tc):
        w = QWidget()
        l = QFormLayout(w)
        self.aql_lot = QSpinBox()
        self.aql_lot.setRange(1, 9999999)
        self.aql_lot.setValue(1000)
        l.addRow("批量:", self.aql_lot)
        self.aql_val = QComboBox()
        self.aql_val.addItems(
            [
                "0.01",
                "0.015",
                "0.025",
                "0.04",
                "0.065",
                "0.10",
                "0.15",
                "0.25",
                "0.40",
                "0.65",
                "1.0",
                "1.5",
                "2.5",
                "4.0",
                "6.5",
                "10",
                "15",
                "25",
                "40",
                "65",
                "100",
            ]
        )
        self.aql_val.setCurrentText("1.0")
        l.addRow("AQL:", self.aql_val)
        self.btn_lookup = QPushButton("查表")
        self.btn_lookup.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_lookup.clicked.connect(self._do_aql)
        l.addRow(self.btn_lookup)
        return w

    def _do_aql(self):
        r = SamplingEngine.aql_lookup(
            self.aql_lot.value(), float(self.aql_val.currentText())
        )
        self.result.setColumnCount(6)
        self.result.setHorizontalHeaderLabels(
            ["字码", "样本量", "Ac", "Re", "AQL", "批量"]
        )
        self.result.setRowCount(1)
        for j, v in enumerate(
            [
                r["code"],
                str(r["sample_size"]),
                str(r["accept"]),
                str(r["reject"]),
                str(r["aql_actual"]),
                str(r["lot_size"]),
            ]
        ):
            self.result.setItem(0, j, QTableWidgetItem(v))
        self.result.resizeColumnsToContents()

    def _random_panel(self, tc):
        w = QWidget()
        l = QFormLayout(w)
        self.rand_col = QComboBox()
        l.addRow("分层列(可选):", self.rand_col)
        self.rand_n = QSpinBox()
        self.rand_n.setRange(1, 99999)
        self.rand_n.setValue(10)
        l.addRow("抽样数量:", self.rand_n)
        self.rand_mode = QComboBox()
        self.rand_mode.addItems(["随机", "分层", "系统"])
        l.addRow("方式:", self.rand_mode)
        self.btn_sample = QPushButton("执行抽样")
        self.btn_sample.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_sample.clicked.connect(self._do_sample)
        l.addRow(self.btn_sample)
        return w

    def _populate(self):
        if self.df is None:
            return
        self.rand_col.clear()
        self.rand_col.addItem("(无)")
        for c in self.df.columns:
            self.rand_col.addItem(str(c))
        if hasattr(self, "measure_col"):
            self.measure_col.clear()
            self.measure_col.addItem("(无)")
            for c in self.df.columns:
                self.measure_col.addItem(str(c))
        if hasattr(self, "czero_col"):
            self.czero_col.clear()
            self.czero_col.addItem("(无)")
            for c in self.df.columns:
                self.czero_col.addItem(str(c))
        if hasattr(self, "batch_strat_col"):
            self.batch_strat_col.clear()
            self.batch_strat_col.addItem("(无)")
            for c in self.df.columns:
                self.batch_strat_col.addItem(str(c))

    def _do_sample(self):
        if self.df is None:
            QMessageBox.information(self, "提示", "请先导入数据")
            return
        n = self.rand_n.value()
        m = self.rand_mode.currentText()
        col = self.rand_col.currentText()
        if m == "分层" and col != "(无)":
            df = SamplingEngine.stratified_sample(self.df, col, n)
        elif m == "系统":
            df = SamplingEngine.systematic_sample(self.df, n)
        else:
            df = SamplingEngine.random_sample(self.df, n)
        self._show_df(df)

    # ------------------------------------------------------------ 批检验（v4.4.0 B3）
    def set_sampling_context(self, manager):
        """接入主窗口的抽样状态编排器（转移状态机/批历史/账本留痕）。"""
        self._sampling_manager = manager
        self._batch_plan = None
        self._refresh_batch_ui()

    def _batch_panel(self, tc):
        w = QWidget()
        outer = QVBoxLayout(w)

        top = QFormLayout()
        self.batch_supplier = QLineEdit()
        self.batch_supplier.setPlaceholderText("供应商 / 来源")
        top.addRow("供应商:", self.batch_supplier)
        self.batch_product = QLineEdit()
        self.batch_product.setPlaceholderText("产品 / 产线")
        top.addRow("产品线:", self.batch_product)
        self.batch_lot_size = QSpinBox()
        self.batch_lot_size.setRange(1, 9_999_999)
        self.batch_lot_size.setValue(2000)
        top.addRow("批量:", self.batch_lot_size)
        self.batch_aql = QComboBox()
        self.batch_aql.addItems(
            ["0.01", "0.015", "0.025", "0.04", "0.065", "0.10", "0.15",
             "0.25", "0.40", "0.65", "1.0", "1.5", "2.5", "4.0", "6.5",
             "10", "15", "25", "40", "65", "100"])
        self.batch_aql.setCurrentText("1.0")
        top.addRow("AQL:", self.batch_aql)
        self.batch_level = QComboBox()
        self.batch_level.addItems(["I", "II", "III"])
        self.batch_level.setCurrentText("II")
        top.addRow("检验水平:", self.batch_level)
        self.batch_state_label = QLabel("当前状态: 正常（未接入）")
        top.addRow("", self.batch_state_label)
        outer.addLayout(top)
        self.btn_batch_plan = QPushButton("查询方案（按当前检验状态）")
        self.btn_batch_plan.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_batch_plan.clicked.connect(self._do_batch_plan)
        outer.addWidget(self.btn_batch_plan)

        sample_form = QFormLayout()
        self.batch_method = QComboBox()
        self.batch_method.addItems(list(_BATCH_METHODS))
        sample_form.addRow("抽样方式:", self.batch_method)
        self.batch_strat_col = QComboBox()
        self.batch_strat_col.addItem("(无)")
        sample_form.addRow("分层列(可选):", self.batch_strat_col)
        self.batch_seed = QSpinBox()
        self.batch_seed.setRange(0, 999_999)
        self.batch_seed.setValue(42)
        sample_form.addRow("种子(可复现):", self.batch_seed)
        outer.addLayout(sample_form)
        self.btn_batch_sample = QPushButton("执行抽样（同参数重跑逐行一致）")
        self.btn_batch_sample.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_batch_sample.clicked.connect(self._do_batch_sample)
        outer.addWidget(self.btn_batch_sample)
        self.batch_fingerprint_label = QLabel("")
        self.batch_fingerprint_label.setStyleSheet("color: #9aa4b2; font-size: 11px;")
        outer.addWidget(self.batch_fingerprint_label)

        judge = QFormLayout()
        self.batch_inspected = QSpinBox()
        self.batch_inspected.setRange(0, 9_999_999)
        self.batch_inspected.setValue(50)
        judge.addRow("检验数:", self.batch_inspected)
        self.batch_defects = QSpinBox()
        self.batch_defects.setRange(0, 9_999_999)
        judge.addRow("不合格数:", self.batch_defects)
        self.batch_serious = QCheckBox("严重不合格（立即加严）")
        judge.addRow("", self.batch_serious)
        self.batch_decision = QComboBox()
        self.batch_decision.addItems(["接收", "拒收"])
        judge.addRow("判定:", self.batch_decision)
        outer.addLayout(judge)
        self.btn_batch_record = QPushButton("登记检验批（触发转移评估）")
        self.btn_batch_record.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_batch_record.clicked.connect(self._do_batch_record)
        outer.addWidget(self.btn_batch_record)
        self.batch_result_label = QLabel("")
        self.batch_result_label.setWordWrap(True)
        outer.addWidget(self.batch_result_label)

        override = QFormLayout()
        self.batch_override_state = QComboBox()
        self.batch_override_state.addItems(list(_BATCH_OVERRIDES))
        override.addRow("覆盖为:", self.batch_override_state)
        self.batch_override_reason = QLineEdit()
        self.batch_override_reason.setPlaceholderText("必填：覆盖原因（进证据账本）")
        override.addRow("覆盖原因:", self.batch_override_reason)
        outer.addLayout(override)
        self.btn_batch_override = QPushButton("应用覆盖")
        self.btn_batch_override.setStyleSheet(BUTTON_SECONDARY)
        self.btn_batch_override.clicked.connect(self._do_batch_override)
        outer.addWidget(self.btn_batch_override)

        self.batch_timeline = QTableWidget(0, 4)
        self.batch_timeline.setHorizontalHeaderLabels(
            ["时间", "类型", "对象", "说明"])
        self.batch_timeline.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_timeline.horizontalHeader().setStretchLastSection(True)
        outer.addWidget(self.batch_timeline, 1)
        return w

    def _batch_scope(self) -> str:
        return scope_key_for(self.batch_supplier.text().strip(),
                             self.batch_product.text().strip())

    def _batch_method_key(self) -> str:
        return _BATCH_METHODS.get(self.batch_method.currentText(), "random")

    def _require_batch_manager(self) -> bool:
        if self._sampling_manager is None:
            QMessageBox.information(self, "批检验",
                                    "未接入抽样状态编排器（请从主界面进入后使用）")
            return False
        return True

    def _do_batch_plan(self):
        if not self._require_batch_manager():
            return
        scope = self._batch_scope()
        if scope == "-|-":
            QMessageBox.warning(self, "批检验", "请先填写供应商或产品线")
            return
        try:
            self._batch_plan = self._sampling_manager.select_plan(
                scope, lot_size=self.batch_lot_size.value(),
                aql=float(self.batch_aql.currentText()),
                level=self.batch_level.currentText(),
                method=self._batch_method_key(),
                seed=self.batch_seed.value())
        except ValueError as exc:
            QMessageBox.warning(self, "方案查询失败", str(exc))
            return
        plan = self._batch_plan["plan"]
        self.result.setColumnCount(6)
        self.result.setHorizontalHeaderLabels(
            ["字码", "样本量", "Ac", "Re", "AQL", "检验状态"])
        self.result.setRowCount(1)
        for column, value in enumerate([
                plan["code"], str(plan["sample_size"]), str(plan["accept"]),
                str(plan["reject"]), str(plan["aql_actual"]),
                _BATCH_STATES.get(self._batch_plan["state"],
                                  self._batch_plan["state"])]):
            self.result.setItem(0, column, QTableWidgetItem(str(value)))
        self.result.resizeColumnsToContents()
        self._refresh_batch_ui()

    def _do_batch_sample(self):
        if not self._require_batch_manager():
            return
        if self.df is None:
            QMessageBox.information(self, "批检验", "请先导入数据")
            return
        if self._batch_plan is None:
            QMessageBox.information(self, "批检验", "请先查询方案")
            return
        method = self._batch_method_key()
        column = self.batch_strat_col.currentText()
        if method == "stratified" and column in ("", "(无)"):
            QMessageBox.warning(self, "批检验", "分层抽样请选择分层列")
            return
        try:
            sampled, decision = self._sampling_manager.sample(
                self.df, self._batch_scope(), method=method,
                column="" if column == "(无)" else column,
                seed=self.batch_seed.value())
        except ValueError as exc:
            QMessageBox.warning(self, "抽样失败", str(exc))
            return
        self._show_df(sampled)
        fingerprint = decision.row_fingerprint if decision else ""
        self.batch_fingerprint_label.setText(
            f"样本 {len(sampled)} 行 · 种子 {self.batch_seed.value()} · 指纹 {fingerprint}")
        self._refresh_batch_ui()

    def _do_batch_record(self):
        if not self._require_batch_manager():
            return
        if self._batch_plan is None:
            QMessageBox.information(self, "批检验", "请先查询方案")
            return
        decision = "accept" if self.batch_decision.currentText() == "接收" else "reject"
        serious = self.batch_serious.isChecked()
        if serious and decision != "reject":
            QMessageBox.warning(self, "批检验", "严重不合格仅适用于拒收批")
            return
        try:
            result = self._sampling_manager.record_lot(
                scope_key=self._batch_scope(),
                supplier=self.batch_supplier.text().strip(),
                product=self.batch_product.text().strip(),
                qty=self.batch_lot_size.value(),
                inspected=self.batch_inspected.value(),
                defects=self.batch_defects.value(),
                decision=decision, serious=serious)
        except ValueError as exc:
            QMessageBox.warning(self, "登记失败", str(exc))
            return
        text = (f"批次 {result['lot'].lot_id} 已登记 · 状态 "
                f"{_BATCH_STATES.get(result['state'], result['state'])}")
        if result["changed"]:
            text += f" · 发生转移：{result['transfer'].reason}"
        self.batch_result_label.setText(text)
        self._refresh_batch_ui()

    def _do_batch_override(self):
        if not self._require_batch_manager():
            return
        reason = self.batch_override_reason.text().strip()
        if not reason:
            QMessageBox.warning(self, "批检验", "手动覆盖必须填写原因")
            return
        target = _BATCH_OVERRIDES[self.batch_override_state.currentText()]
        try:
            state = self._sampling_manager.manual_override(
                self._batch_scope(), target, reason)
        except ValueError as exc:
            QMessageBox.warning(self, "覆盖失败", str(exc))
            return
        self.batch_result_label.setText(
            f"已手动覆盖为 {_BATCH_STATES.get(state.state, state.state)}"
            f"（原因已留痕）")
        self.batch_override_reason.clear()
        self._refresh_batch_ui()

    def _refresh_batch_ui(self):
        manager = self._sampling_manager
        if manager is None:
            self.batch_state_label.setText("当前状态: 正常（未接入）")
            self.batch_timeline.setRowCount(0)
            return
        scope = self._batch_scope()
        snapshot = manager.snapshot(scope)
        state_text = _BATCH_STATES.get(snapshot["state"], snapshot["state"])
        color = {"normal": "#2ecc71", "tightened": "#f39c12",
                 "reduced": "#4da6ff"}.get(snapshot["state"], "#e1e2e6")
        extra = (f" · 批数 {snapshot['lots_total']}"
                 + (f" · 覆盖原因: {snapshot['override_reason']}"
                    if snapshot["override_reason"] else ""))
        self.batch_state_label.setText(
            f"当前状态: <span style='color:{color};font-weight:bold'>"
            f"{state_text}</span>{extra}")
        rows = manager.timeline(scope, limit=50)
        self.batch_timeline.setRowCount(len(rows))
        kind_labels = {"plan": "方案", "lot": "检验批", "transfer": "状态转移"}
        for row, item in enumerate(rows):
            values = (item["at"], kind_labels.get(item["kind"], item["kind"]),
                      item["title"], item["text"])
            for column, value in enumerate(values):
                self.batch_timeline.setItem(row, column, QTableWidgetItem(value))
        self.batch_timeline.resizeColumnsToContents()

    def _show_df(self, df):
        self.result.setColumnCount(len(df.columns))
        self.result.setHorizontalHeaderLabels(list(df.columns))
        m = min(100, len(df))
        self.result.setRowCount(m)
        for i in range(m):
            for j, _c in enumerate(df.columns):
                self.result.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))
        self.result.resizeColumnsToContents()

    def _sequential_panel(self, tc):
        w = QWidget()
        l = QFormLayout(w)
        self.seq_ac = QSpinBox()
        self.seq_ac.setRange(0, 99)
        self.seq_ac.setValue(2)
        l.addRow("Ac(接收):", self.seq_ac)
        self.seq_re = QSpinBox()
        self.seq_re.setRange(1, 99)
        self.seq_re.setValue(5)
        l.addRow("Re(拒收):", self.seq_re)
        self.seq_n = QSpinBox()
        self.seq_n.setRange(1, 9999)
        self.seq_n.setValue(20)
        l.addRow("模拟样本数:", self.seq_n)
        self.btn_seq_run = QPushButton("模拟序贯判定")
        self.btn_seq_run.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_seq_run.clicked.connect(self._do_seq)
        l.addRow(self.btn_seq_run)
        return w

    def _do_seq(self):
        ac = self.seq_ac.value()
        re = self.seq_re.value()
        n = self.seq_n.value()
        results = np.random.choice([0, 1], size=n, p=[0.9, 0.1]).tolist()
        dec, d, ins = SamplingEngine.sequential_decision(results, ac, re)
        self.result.setColumnCount(4)
        self.result.setHorizontalHeaderLabels(["判定", "缺陷数", "检查数", "Ac/Re"])
        self.result.setRowCount(1)
        for j, v in enumerate([dec, str(d), str(ins), f"{ac}/{re}"]):
            item = QTableWidgetItem(v)
            if dec == "accept":
                item.setForeground(QColor("#27ae60"))
            elif dec == "reject":
                item.setForeground(QColor("#e74c3c"))
            self.result.setItem(0, j, item)
        self.result.resizeColumnsToContents()

    def _measurement_panel(self, tc):
        w = QWidget()
        l = QFormLayout(w)
        self.measure_lot = QSpinBox()
        self.measure_lot.setRange(1, 9999999)
        self.measure_lot.setValue(1000)
        l.addRow("批量:", self.measure_lot)
        self.measure_aql = QComboBox()
        self.measure_aql.addItems(
            ["0.10", "0.15", "0.25", "0.40", "0.65", "1.0", "1.5", "2.5", "4.0", "6.5"]
        )
        self.measure_aql.setCurrentText("1.0")
        l.addRow("AQL:", self.measure_aql)
        self.measure_usl = QDoubleSpinBox()
        self.measure_usl.setRange(-1e9, 1e9)
        self.measure_usl.setDecimals(4)
        self.measure_usl.setValue(10.0)
        l.addRow("USL:", self.measure_usl)
        self.measure_lsl = QDoubleSpinBox()
        self.measure_lsl.setRange(-1e9, 1e9)
        self.measure_lsl.setDecimals(4)
        self.measure_lsl.setValue(0.0)
        l.addRow("LSL:", self.measure_lsl)
        self.measure_level = QComboBox()
        self.measure_level.addItems(["I", "II", "III"])
        self.measure_level.setCurrentText("II")
        l.addRow("检验水平:", self.measure_level)
        self.measure_col = QComboBox()
        l.addRow("数据列(判定用):", self.measure_col)
        self.btn_measure_lookup = QPushButton("查表")
        self.btn_measure_lookup.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_measure_lookup.clicked.connect(self._do_measure_lookup)
        l.addRow(self.btn_measure_lookup)
        self.btn_measure_decide = QPushButton("执行判定")
        self.btn_measure_decide.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_measure_decide.clicked.connect(self._do_measure_decide)
        l.addRow(self.btn_measure_decide)
        return w

    def _do_measure_lookup(self):
        r = SamplingEngine.measurement_sampling(
            self.measure_lot.value(),
            float(self.measure_aql.currentText()),
            self.measure_usl.value(),
            self.measure_lsl.value(),
            level=self.measure_level.currentText(),
        )
        self.result.setColumnCount(7)
        self.result.setHorizontalHeaderLabels(
            ["字码", "样本量", "k因子", "AQL", "USL", "LSL", "sigma"]
        )
        self.result.setRowCount(1)
        for j, v in enumerate(
            [
                r.get("code", ""),
                str(r.get("sample_size", "")),
                str(r.get("k_factor", "")),
                str(r.get("aql_actual", "")),
                str(r.get("usl", "")),
                str(r.get("lsl", "")),
                str(r.get("sigma_used", "")),
            ]
        ):
            self.result.setItem(0, j, QTableWidgetItem(v))
        self.result.resizeColumnsToContents()

    def _do_measure_decide(self):
        if self.df is None:
            QMessageBox.information(self, "提示", "请先导入数据")
            return
        col = self.measure_col.currentText()
        if col == "(无)" or not col:
            QMessageBox.information(self, "提示", "请选择数据列")
            return
        data = self.df[col].dropna().values
        r = SamplingEngine.measurement_sampling(
            self.measure_lot.value(),
            float(self.measure_aql.currentText()),
            self.measure_usl.value(),
            self.measure_lsl.value(),
            level=self.measure_level.currentText(),
        )
        dec = SamplingEngine.measurement_decision(
            data, r["k_factor"], self.measure_usl.value(), self.measure_lsl.value()
        )
        self.result.setColumnCount(5)
        self.result.setHorizontalHeaderLabels(
            ["判定", "样本量", "均值", "标准差", "k因子"]
        )
        self.result.setRowCount(1)
        item = QTableWidgetItem(dec["decision"])
        if dec["decision"] == "accept":
            item.setForeground(QColor("#27ae60"))
        else:
            item.setForeground(QColor("#e74c3c"))
        self.result.setItem(0, 0, item)
        for j, v in enumerate(
            [
                str(dec.get("sample_size", "")),
                str(dec.get("x_bar", "")),
                str(dec.get("s", "")),
                str(dec.get("k_factor", "")),
            ]
        ):
            self.result.setItem(0, j + 1, QTableWidgetItem(v))
        self.result.resizeColumnsToContents()

    def _czero_panel(self, tc):
        w = QWidget()
        l = QFormLayout(w)
        self.czero_lot = QSpinBox()
        self.czero_lot.setRange(1, 9999999)
        self.czero_lot.setValue(1000)
        l.addRow("批量:", self.czero_lot)
        self.czero_aql = QDoubleSpinBox()
        self.czero_aql.setRange(0.01, 100)
        self.czero_aql.setValue(0.10)
        self.czero_aql.setDecimals(2)
        l.addRow("AQL:", self.czero_aql)
        self.czero_col = QComboBox()
        l.addRow("数据列(判定用):", self.czero_col)
        self.btn_czero_lookup = QPushButton("查表")
        self.btn_czero_lookup.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_czero_lookup.clicked.connect(self._do_czero_lookup)
        l.addRow(self.btn_czero_lookup)
        self.btn_czero_decide = QPushButton("执行判定")
        self.btn_czero_decide.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_czero_decide.clicked.connect(self._do_czero_decide)
        l.addRow(self.btn_czero_decide)
        return w

    def _do_czero_lookup(self):
        r = SamplingEngine.c_zero_sampling(
            self.czero_lot.value(), self.czero_aql.value()
        )
        self.result.setColumnCount(5)
        self.result.setHorizontalHeaderLabels(["批量", "样本量", "Ac", "Re", "AQL"])
        self.result.setRowCount(1)
        for j, v in enumerate(
            [
                str(r.get("lot_size", "")),
                str(r.get("sample_size", "")),
                str(r.get("accept_number", "")),
                str(r.get("reject_number", "")),
                str(r.get("aql_actual", "")),
            ]
        ):
            self.result.setItem(0, j, QTableWidgetItem(v))
        self.result.resizeColumnsToContents()

    def _do_czero_decide(self):
        if self.df is None:
            QMessageBox.information(self, "提示", "请先导入数据")
            return
        col = self.czero_col.currentText()
        if col == "(无)" or not col:
            QMessageBox.information(self, "提示", "请选择数据列")
            return
        data = self.df[col].dropna().values.astype(int).tolist()
        dec = SamplingEngine.c_zero_decision(data)
        self.result.setColumnCount(4)
        self.result.setHorizontalHeaderLabels(["判定", "缺陷数", "检验数", "缺陷率%"])
        self.result.setRowCount(1)
        item = QTableWidgetItem(dec["decision"])
        if dec["decision"] == "accept":
            item.setForeground(QColor("#27ae60"))
        else:
            item.setForeground(QColor("#e74c3c"))
        self.result.setItem(0, 0, item)
        for j, v in enumerate(
            [
                str(dec.get("defects", "")),
                str(dec.get("sample_size", "")),
                str(dec.get("defect_rate", "")),
            ]
        ):
            self.result.setItem(0, j + 1, QTableWidgetItem(v))
        self.result.resizeColumnsToContents()
