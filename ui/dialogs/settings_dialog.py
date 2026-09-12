"""
设置对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox, QHBoxLayout,
    QDoubleSpinBox, QDialogButtonBox, QCheckBox, QTabWidget, QWidget,
    QLineEdit, QPushButton, QLabel, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
)
from PySide6.QtCore import QThread, Signal

from config.settings import (
    FONT_FAMILY, CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_NDC_THRESHOLD, get_setting,
)
from ui.theme import colors as theme_colors


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setMinimumSize(520, 430)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.font_combo = QComboBox()
        self.font_combo.addItems(FONT_FAMILY)
        saved_font = get_setting("font_family", FONT_FAMILY[0])
        if saved_font in [self.font_combo.itemText(i) for i in range(self.font_combo.count())]:
            self.font_combo.setCurrentText(saved_font)
        general_layout.addRow("默认字体:", self.font_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 300)
        self.dpi_spin.setValue(get_setting("chart_dpi", CHART_DPI))
        general_layout.addRow("图表DPI:", self.dpi_spin)

        self.animations_check = QCheckBox("界面动画效果 (淡入/数字滚动)")
        self.animations_check.setChecked(get_setting("animations_enabled", True))
        general_layout.addRow("动画:", self.animations_check)

        tabs.addTab(general_tab, "通用")

        rules_tab = QWidget()
        rules_layout = QFormLayout(rules_tab)

        self.nelson_check = QCheckBox("启用Nelson判异规则")
        self.nelson_check.setChecked(get_setting("nelson_rules_enabled", True))
        rules_layout.addRow(self.nelson_check)

        tabs.addTab(rules_tab, "判异规则")

        msa_tab = QWidget()
        msa_layout = QFormLayout(msa_tab)

        self.grr_accept = QDoubleSpinBox()
        self.grr_accept.setRange(0, 0.5)
        self.grr_accept.setValue(get_setting("msa_grr_acceptable", MSA_GRR_ACCEPTABLE))
        self.grr_accept.setSingleStep(0.01)
        msa_layout.addRow("%GRR 可接受阈值:", self.grr_accept)

        self.ndc_spin = QSpinBox()
        self.ndc_spin.setRange(1, 10)
        self.ndc_spin.setValue(get_setting("msa_ndc_threshold", MSA_NDC_THRESHOLD))
        msa_layout.addRow("NDC 阈值:", self.ndc_spin)

        tabs.addTab(msa_tab, "MSA")

        alert_tab = QWidget()
        alert_layout = QFormLayout(alert_tab)

        self.alert_min_spin = QSpinBox()
        self.alert_min_spin.setRange(0, 100)
        self.alert_min_spin.setValue(get_setting("alert_min_violations", 1))
        self.alert_min_spin.setToolTip("判异点数达到该阈值才触发告警")
        alert_layout.addRow("最小判异点数:", self.alert_min_spin)

        self.alert_popup_check = QCheckBox("弹窗告警")
        self.alert_popup_check.setChecked(get_setting("alert_popup_enabled", True))
        alert_layout.addRow(self.alert_popup_check)

        self.alert_sound_check = QCheckBox("声音提醒")
        self.alert_sound_check.setChecked(get_setting("alert_sound_enabled", True))
        alert_layout.addRow(self.alert_sound_check)

        self.alert_log_check = QCheckBox("告警日志")
        self.alert_log_check.setChecked(get_setting("alert_log_enabled", True))
        alert_layout.addRow(self.alert_log_check)

        tabs.addTab(alert_tab, "告警")

        tabs.addTab(self._build_agent_tab(tc), "QAM Harness")
        tabs.addTab(self._build_plugins_tab(tc), "插件")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------ QAM Harness
    def _build_plugins_tab(self, tc) -> QWidget:
        """插件接口 v2 管理页 — 状态列表 + 信任 + 插件设置页。"""
        from core.plugin_api import PLUGIN_API_VERSION
        from core.plugin_manager import PluginManager

        manager = PluginManager()
        manager.discover()

        tab = QWidget()
        layout = QVBoxLayout(tab)
        hint = QLabel(
            f"插件接口 v{PLUGIN_API_VERSION}：外部插件可贡献 Tab / Agent 工具 / "
            "设置页。随包插件默认信任；用户目录与 pip 插件首次需信任，"
            "信任后重新打开设置或重启应用生效。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        layout.addWidget(hint)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["插件", "版本", "来源", "状态", "操作"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setMinimumHeight(180)
        for record in manager.records():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(record.name))
            table.setItem(row, 1, QTableWidgetItem(record.version))
            table.setItem(row, 2, QTableWidgetItem({
                "bundled": "随包", "user": "用户目录",
                "entry_point": "pip 包"}.get(record.source, record.source)))
            if not record.trusted:
                status = "待信任"
            elif record.available:
                status = "可用" + (f"（{record.reason}）" if record.reason else "")
            else:
                status = f"不可用：{record.reason or record.error or '未知原因'}"
            table.setItem(row, 3, QTableWidgetItem(status))
            if not record.trusted:
                btn = QPushButton("信任")
                btn.setFixedWidth(64)
                btn.clicked.connect(
                    lambda _, pid=record.id: self._trust_plugin(pid))
                table.setCellWidget(row, 4, btn)
        layout.addWidget(table)

        for record in manager.settings_plugins():
            page = manager.create_settings_page(record, manager.host, tab)
            if page is None:
                continue
            box = QGroupBox(f"{record.name} 设置")
            box_layout = QVBoxLayout(box)
            box_layout.addWidget(page)
            layout.addWidget(box)
        layout.addStretch()
        return tab

    def _trust_plugin(self, plugin_id: str):
        from core.plugin_manager import PluginManager

        PluginManager().trust(plugin_id)
        QMessageBox.information(
            self, "插件已信任",
            f"已信任插件 {plugin_id}。重新打开设置或重启应用后加载。")

    def _build_agent_tab(self, tc) -> QWidget:
        """QAM Harness（BYOK）配置页 — 供应商/模型/密钥/连通性/隐私授权。"""
        from core.agent.privacy import consent_status, revoke_consent
        from core.agent.providers import (
            PROVIDERS, get_provider, masked_key, models_for,
        )

        tab = QWidget()
        form = QFormLayout(tab)
        self._agent_ctx = {"tc": tc}
        active = str(get_setting("llm_active_provider", "ollama") or "ollama")

        self.provider_combo = QComboBox()
        for pid, spec in PROVIDERS.items():
            self.provider_combo.addItem(spec.label, pid)
        idx = self.provider_combo.findData(active)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        form.addRow("供应商:", self.provider_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        form.addRow("模型:", self.model_combo)

        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(6)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("API Key（保存后加密存储，不再回显）")
        key_layout.addWidget(self.api_key_edit, 1)
        self.show_key_check = QCheckBox("显示")
        self.show_key_check.toggled.connect(
            lambda on: self.api_key_edit.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password))
        key_layout.addWidget(self.show_key_check)
        self.clear_key_btn = QPushButton("清除")
        self.clear_key_btn.setFixedWidth(56)
        self.clear_key_btn.clicked.connect(self._clear_api_key)
        key_layout.addWidget(self.clear_key_btn)
        form.addRow("API Key:", key_row)

        self.api_base_edit = QLineEdit()
        form.addRow("接口地址:", self.api_base_edit)

        self.key_state_label = QLabel("")
        self.key_state_label.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        form.addRow("状态:", self.key_state_label)

        test_row = QWidget()
        test_layout = QHBoxLayout(test_row)
        test_layout.setContentsMargins(0, 0, 0, 0)
        test_layout.setSpacing(6)
        self.test_btn = QPushButton("连通性测试")
        self.test_btn.clicked.connect(self._on_test_connection)
        test_layout.addWidget(self.test_btn)
        self.test_result = QLabel("未测试")
        self.test_result.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        self.test_result.setWordWrap(True)
        test_layout.addWidget(self.test_result, 1)
        form.addRow("", test_row)

        self.consent_label = QLabel("")
        self.consent_label.setWordWrap(True)
        self.consent_label.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 9pt;")
        form.addRow("隐私授权:", self.consent_label)

        consent_row = QWidget()
        consent_layout = QHBoxLayout(consent_row)
        consent_layout.setContentsMargins(0, 0, 0, 0)
        self.revoke_btn = QPushButton("撤销云调用授权")
        self.revoke_btn.clicked.connect(lambda: self._on_revoke_consent(revoke_consent))
        consent_layout.addWidget(self.revoke_btn)
        consent_layout.addStretch()
        form.addRow("", consent_row)

        self.cloud_check = QCheckBox("允许调用云 API（关闭时 QAM Harness 只用本地工具）")
        self.cloud_check.setChecked(bool(get_setting("llm_cloud_enabled", False)))
        form.addRow("云调用:", self.cloud_check)

        hint = QLabel("密钥仅以加密形式保存在本机（Windows DPAPI / Linux·macOS keyring）；"
                      "首次调用某家云 API 会弹出隐私确认，确认后按供应商记忆，可在此撤销。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        form.addRow("", hint)

        self._provider_models = {pid: list(models_for(pid)) for pid in PROVIDERS}
        self._masked = masked_key
        self._get_provider = get_provider
        self._consent_status = consent_status
        self._on_provider_changed()
        return tab

    def _current_provider(self) -> str:
        return str(self.provider_combo.currentData() or "ollama")

    def _on_provider_changed(self):
        from config.settings import get_secret
        pid = self._current_provider()
        spec = self._get_provider(pid)
        saved_model = str(get_setting(f"llm_{pid}_model", "") or "")
        self.model_combo.clear()
        for name in self._provider_models.get(pid) or [spec.default_model()]:
            self.model_combo.addItem(name)
        if saved_model:
            self.model_combo.setCurrentText(saved_model)
        self.api_base_edit.setPlaceholderText(f"默认: {spec.base_url}")
        self.api_base_edit.setText(str(get_setting(f"llm_{pid}_api_base", "") or ""))
        stored = get_secret(f"llm_{pid}_api_key", "")
        self.api_key_edit.clear()
        self.api_key_edit.setEnabled(True)
        self._key_cleared = False
        hint = f"已配置: {self._masked(stored)}" if stored else \
            (f"未配置（{spec.key_hint}）" if spec.requires_key else "无需密钥")
        if spec.note:
            hint += f"　·　{spec.note}"
        self.key_state_label.setText(hint)
        self.test_result.setText("未测试")
        self.consent_label.setText(self._consent_status(
            pid, self.api_base_edit.text() or spec.base_url))

    def _clear_api_key(self):
        self._key_cleared = True
        self.api_key_edit.clear()
        self.api_key_edit.setEnabled(False)
        self.key_state_label.setText("将在保存后清除本机密钥")

    def _build_test_client(self):
        from core.llm_client import LLMClient
        pid = self._current_provider()
        base = self.api_base_edit.text().strip() or None
        key = self.api_key_edit.text().strip()
        if not key and not self._key_cleared:
            from config.settings import get_secret
            key = get_secret(f"llm_{pid}_api_key", "")
        return LLMClient(model=self.model_combo.currentText().strip(),
                         provider=pid, api_key=key or "", api_base=base)

    def _on_test_connection(self):
        self.test_btn.setEnabled(False)
        self.test_result.setText("测试中…")
        client = self._build_test_client()

        class _Worker(QThread):
            done = Signal(object)

            def run(self_inner):
                self_inner.done.emit(client.test_connection())

        self._test_worker = _Worker(self)

        def _finish(result):
            self.test_btn.setEnabled(True)
            color = "#27ae60" if result.ok else "#e74c3c"
            models = f"（模型 {len(result.models)} 个）" if result.models else ""
            self.test_result.setText(
                f"<span style='color:{color}'>{'✓' if result.ok else '✗'} "
                f"{result.message}{models} · {result.latency_ms:.0f} ms</span>")

        self._test_worker.done.connect(_finish)
        self._test_worker.start()

    def _on_revoke_consent(self, revoke_fn):
        pid = self._current_provider()
        revoke_fn(pid)
        self.consent_label.setText("已撤销（下次云调用会重新弹出确认）")

    def agent_values(self) -> dict:
        """QAM Harness 相关配置（密钥键名以 `_api_key` 结尾 → 自动加密）。"""
        pid = self._current_provider()
        values = {
            "llm_active_provider": pid,
            f"llm_{pid}_model": self.model_combo.currentText().strip(),
            f"llm_{pid}_api_base": self.api_base_edit.text().strip(),
            "llm_cloud_enabled": self.cloud_check.isChecked(),
        }
        if getattr(self, "_key_cleared", False):
            # None = 删除该键（含 <key>_enc），否则旧加密值会被 get_secret 读回
            values[f"llm_{pid}_api_key"] = None
        elif self.api_key_edit.text().strip():
            values[f"llm_{pid}_api_key"] = self.api_key_edit.text().strip()
        return values

    def closeEvent(self, event):
        """关闭前等待连通性测试线程结束，避免 QThread 运行中被销毁。"""
        self._stop_test_worker()
        super().closeEvent(event)

    def done(self, result):
        """OK/Cancel 也走这里（accept/reject 不触发 closeEvent）。"""
        self._stop_test_worker()
        super().done(result)

    def _stop_test_worker(self):
        worker = getattr(self, "_test_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(3000)

    def get_values(self) -> dict:
        """返回所有用户设置值"""
        values = {
            "font_family": self.font_combo.currentText(),
            "chart_dpi": self.dpi_spin.value(),
            "animations_enabled": self.animations_check.isChecked(),
            "nelson_rules_enabled": self.nelson_check.isChecked(),
            "msa_grr_acceptable": self.grr_accept.value(),
            "msa_ndc_threshold": self.ndc_spin.value(),
            "alert_min_violations": self.alert_min_spin.value(),
            "alert_popup_enabled": self.alert_popup_check.isChecked(),
            "alert_sound_enabled": self.alert_sound_check.isChecked(),
            "alert_log_enabled": self.alert_log_check.isChecked(),
        }
        values.update(self.agent_values())
        return values
