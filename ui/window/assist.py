"""指南、模板、诊断、设置和数据清洗入口。"""

import os

from PySide6.QtWidgets import (
    QMessageBox, QFileDialog,
)
from PySide6.QtCore import (
    Qt, QUrl,
)
from PySide6.QtGui import QDesktopServices

from core.i18n import i18n
from core.audit import audit

from ui.dialogs.settings_dialog import SettingsDialog
from ui.main_window_helpers import (
    _resolve_llm_client,
)

from ui.main_window_constants import (
    project_path,
)


class AssistMixin:
    def _on_llm_assist(self):
        """打开 QAM Harness（质量工程 AI Agent）对话窗口。"""
        client = _resolve_llm_client(self)
        if client is None:
            return
        from ui.dialogs.llm_dialog import QAMHarnessDialog
        dlg = getattr(self, "_agent_dialog", None)
        if dlg is not None and dlg.isVisible():
            if dlg.isMinimized():
                dlg.showNormal()
            dlg.raise_()
            dlg.activateWindow()
            return
        dlg = QAMHarnessDialog(self, engine=None, llm=client)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.destroyed.connect(lambda *_: setattr(self, "_agent_dialog", None))
        self._agent_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_one_click_analysis(self):
        """一键智能分析 — 画像 → 推荐 → 执行 → 报告"""
        raw_data = self.current_data.get("raw_data", {})
        if not raw_data:
            QMessageBox.warning(self, "无数据", "请先导入数据文件后再运行一键分析")
            return
        from ui.dialogs.one_click_dialog import OneClickDialog
        dlg = OneClickDialog(raw_data, self)
        dlg.exec()

    def _on_template_dialog(self):
        from ui.dialogs.template_dialog import TemplateDialog
        dlg = TemplateDialog(self, analyses=self.analyses)
        dlg.exec()

    def _on_html_export(self):
        if not self.analyses:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 HTML 报告", "akia_report.html", "HTML 报告 (*.html)")
        if not path:
            return
        try:
            from output.html_export import export_html
            charts = self._collect_charts(list(self.analyses.keys()))
            export_html(list(self.analyses.values()), charts=charts, output_path=path)
            audit("export", "user", f"HTML 报告 {os.path.basename(path)}")
            self._record_report_exported("html", path,
                                         analyses=list(self.analyses.values()))
            self.status_label.setText("HTML 报告已导出")
            QMessageBox.information(self, "导出完成", "HTML 报告已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_template_help(self):
        from ui.dialogs.template_help_dialog import TemplateHelpDialog
        dlg = TemplateHelpDialog(self)
        dlg.exec()

    def _on_open_guide(self):
        """在系统默认浏览器中打开使用指南 (config/help/guide.html)"""
        guide = project_path("config", "help", "guide.html")
        if os.path.exists(guide):
            QDesktopServices.openUrl(QUrl.fromLocalFile(guide))
        else:
            QMessageBox.warning(self, i18n.tr("menu.guide"),
                                "未找到使用指南文件:\nconfig/help/guide.html")

    def _on_diagnose(self):
        if not self.profile_result or not self.profile_result.get("sheets"):
            QMessageBox.information(self, "智能诊断", "请先导入数据文件，系统将自动分析数据特征")
            return
        from ui.dialogs.diagnosis_dialog import DiagnosisDialog
        dlg = DiagnosisDialog(self.profile_result, self)
        dlg.apply_clicked.connect(self._apply_diagnosis)
        dlg.exec()

    def _apply_diagnosis(self, recommendation: dict):
        tab_idx = recommendation.get("tab_index", 1)
        params = recommendation.get("params", {})
        self._switch_tab(tab_idx)
        tabs = self._get_tabs()
        tab = tabs.get(tab_idx)
        if tab is None:
            return

        col = params.get("column") or params.get("response") or params.get("col1")
        if col and tab_idx == 1:
            combo = getattr(tab, 'col_combo', None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            if params.get("subgroup_size") and hasattr(tab, 'subgroup_spin'):
                tab.subgroup_spin.setValue(int(params["subgroup_size"]))
            if params.get("usl") and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(params["usl"]))
            if params.get("lsl") and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(params["lsl"]))
            method = recommendation.get("method", "")
            if method and hasattr(tab, 'chart_type_combo'):
                mi = tab.chart_type_combo.findText(method)
                if mi >= 0:
                    tab.chart_type_combo.setCurrentIndex(mi)
        elif col and tab_idx == 2:
            combo = getattr(tab, 'col_combo', None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            if params.get("usl") and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(params["usl"]))
            if params.get("lsl") and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(params["lsl"]))
        elif col and tab_idx in (3, 4, 5, 6):
            combo_attrs = {3: 'measure_col', 4: 'col1_combo', 5: 'response_combo', 6: 'response_combo'}
            combo = getattr(tab, combo_attrs.get(tab_idx, ''), None)
            if combo:
                idx = combo.findText(col)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

        self.status_label.setText(f"依诊断推荐已配置 '{recommendation.get('tab_name', '')}', 可运行分析")

    def _on_batch_scheduler(self):
        from ui.dialogs.batch_dialog import BatchDialog
        dlg = BatchDialog(self)
        dlg.exec()

    def _on_settings(self):
        from config.settings import save_config
        dialog = SettingsDialog(self)
        if dialog.exec():
            save_config(dialog.get_values())
            from output.chart_engine import setup_chinese_font
            setup_chinese_font()
            self.statusBar().showMessage("设置已保存", 3000)

    def _on_data_cleaner(self):
        idx = self.stack.currentIndex()
        tabs = self._get_tabs()
        current_tab = tabs.get(idx)
        if current_tab is None or getattr(current_tab, 'df', None) is None or len(current_tab.df) == 0:
            QMessageBox.warning(self, "无数据", "请先导入数据文件并选择一个分析模块")
            return
        from ui.dialogs.data_cleaner import DataCleaner
        dialog = DataCleaner(current_tab.df, self)
        if dialog.exec():
            cleaned = dialog.get_cleaned_df()
            if cleaned is not None:
                current_df_id = id(current_tab.df)
                updated = set()
                for ti, tab in tabs.items():
                    df = getattr(tab, 'df', None)
                    if df is not None and id(df) == current_df_id:
                        info = getattr(tab, 'parsed_info', None)
                        if info:
                            # 清洗后重算列类型/数值列（DataLoader 全列 dtype=str,
                            # 不能用 select_dtypes 判定数值列 — 结果恒为空）
                            try:
                                info = self.data_parser.refresh_info(cleaned, info)
                            except Exception:
                                info = dict(info)
                        tab.set_data(cleaned.copy(), info or {})
                        self._update_tab_empty_state(ti)
                        updated.add(ti)
                self.statusBar().showMessage(
                    f"数据清洗已完成，已更新 {len(updated)} 个分析模块", 5000
                )
                self._ledger_append(
                    "data_edited", object_refs=[f"tab:{idx}"],
                    payload={"action": "data_cleaner", "updated_tabs": len(updated)})

    def _on_data_clean_wizard(self):
        if not self.current_data:
            QMessageBox.information(self, "提示", "请先导入数据文件")
            return
        raw = self.current_data.get("raw_data", {})
        first_key = next(iter(raw.keys()), None)
        if first_key is None:
            return
        df = raw[first_key]
        from ui.dialogs.data_clean_wizard import DataCleanWizard
        wiz = DataCleanWizard(df, self)
        if wiz.exec() == DataCleanWizard.Accepted:
            cleaned = wiz.get_result()
            raw[first_key] = cleaned
            self.current_data["raw_data"] = raw
            self._route_sheets_to_tabs(raw, worksheet_mode=False)
            audit("data_clean", "user",
                  f"清洗 {first_key}")
            self._ledger_append(
                "data_edited", object_refs=[str(first_key)],
                payload={"action": "data_clean_wizard", "sheet": str(first_key)})
            self.statusBar().showMessage("数据清洗向导完成", 5000)
