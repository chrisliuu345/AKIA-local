"""质量、IE、数据库和模板导入。"""

import contextlib
import os
import pandas as pd

from PySide6.QtWidgets import (
    QMessageBox, QFileDialog,
)

from core.i18n import i18n
from ui.worker import run_in_worker
from core.audit import audit

from ui._tab_registry import TAB_INDEX
from ui.dialogs.import_dialog import ImportDialog

from ui.main_window_constants import (
    _IE_IMPORT_TAB_INDICES,
    _IE_TAB_INDICES,
)


class ImportMixin:
    def _import_cp_from_fmea(self, cp_rows: list) -> bool:
        """FMEA → 控制计划：追加行 → 切换 Tab → 写入项目上下文。

        返回是否成功；失败时由调用方给出提示（不再静默丢弃）。
        """
        cp_idx = TAB_INDEX["control_plan"]
        cp_tab = self._lazy_load_tab(cp_idx)
        if cp_tab is None or not hasattr(cp_tab, 'append_rows'):
            return False

        cp_tab.set_project_context(self.project_context)
        cp_tab.append_rows(cp_rows)
        self._switch_tab(cp_idx)
        return True

    def _import_spc_from_cp(self, spc_items: list) -> bool:
        """控制计划 → SPC：注入监控清单 → 切换 Tab → 写入项目上下文。

        返回是否成功。注意必须先懒加载再取实例（原实现在 Tab 未打开时取到 None）。
        """
        self._spc_monitoring_list = spc_items
        self.project_context.set_analysis_snapshot(
            "spc_monitoring", {"items": spc_items, "source": "control_plan"})

        spc_idx = TAB_INDEX["spc"]
        spc_tab = self._lazy_load_tab(spc_idx)
        if spc_tab is None or not hasattr(spc_tab, 'import_from_cp'):
            return False

        spc_tab.import_from_cp(spc_items)
        self._switch_tab(spc_idx)
        return True

    def _on_import_quality(self):
        dialog = ImportDialog(self, mode="quality")
        if dialog.exec():
            file_path, _sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                loader = self.data_loader

                def _load_quality():
                    raw = loader.load(file_path)
                    return raw, dict(loader.metadata or {})

                raw_data, metadata = run_in_worker(self, _load_quality)
                self.data_loader.metadata = metadata
                audit("import_data", "user",
                      f"质量数据 {os.path.basename(file_path)}")
                self._record_data_imported(file_path, raw_data, kind="quality")
                self.current_data = {
                    "file_path": file_path,
                    "raw_data": raw_data,
                    "metadata": self.data_loader.metadata,
                }
                self.session_manager.create_session(file_path=file_path)
                try:
                    self._route_sheets_to_tabs(raw_data, worksheet_mode=True)
                except Exception as re:
                    import logging
                    logging.getLogger(__name__).exception("Sheet 分发失败")
                    QMessageBox.critical(self, "路由失败", f"Sheet 分发异常:\n{re!s}")
                self.data_label.setText(f" {os.path.basename(file_path)} [{len(raw_data)} sheets]")

                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}

                tabs = self._get_tabs()
                all_warnings = 0
                for idx, tab in tabs.items():
                    if idx > 6:
                        continue
                    df = getattr(tab, 'df', None)
                    if df is None or len(df) == 0:
                        continue
                    num_cols = []
                    for i, c in enumerate(df.columns):
                        try:
                            s = pd.to_numeric(df.iloc[:, i], errors="coerce").dropna()
                            if len(s) > 0:
                                num_cols.append(c)
                        except (ValueError, TypeError):  # 非数值列：不参与校验
                            pass
                    num_cols = num_cols[:20]
                    if num_cols:
                        v = self.data_validator.validate(df, num_cols)
                        all_warnings += v.get("warning_count", 0)

                if all_warnings > 0:
                    self.statusBar().showMessage(
                        f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} 个工作表  |  数据校验: {all_warnings} 个警告",
                        8000,
                    )
                else:
                    self.status_label.setText(f"{i18n.tr('status.loaded')}: {len(self.data_loader.metadata['sheet_names'])} 个工作表")
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception("导入工作表失败")
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), f"{i18n.tr('msg.cannot_load')}\n{e!s}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_ie(self):
        dialog = ImportDialog(self, mode="ie")
        if dialog.exec():
            file_path, _sheet_names = dialog.get_selection()
            try:
                self.status_label.setText(f"{i18n.tr('status.loading')}{file_path}...")
                loader = self.data_loader

                def _load_ie():
                    raw = loader.load(file_path)
                    ie = loader.load_ie_data()
                    return raw, ie, dict(loader.metadata or {})

                raw_data, ie_data, metadata = run_in_worker(self, _load_ie)
                self.data_loader.metadata = metadata
                audit("import_data", "user",
                      f"IE 数据 {os.path.basename(file_path)}")
                self._record_data_imported(file_path, raw_data, kind="ie")

                if not ie_data:
                    from core.ie_parser import IEDataParser
                    QMessageBox.warning(self, "格式不匹配", IEDataParser.format_help())
                    self.status_label.setText(i18n.tr("status.ready"))
                    return

                self.current_data = {
                    "file_path": file_path,
                    "raw_data": raw_data,
                    "metadata": self.data_loader.metadata,
                    "ie_data": ie_data,
                }
                self.data_label.setText(f" {os.path.basename(file_path)} [{len(raw_data)} sheets]")

                if ie_data.get("TimeObservation"):
                    ts_tab = self._lazy_load_tab(7)
                    if ts_tab and hasattr(ts_tab, 'set_ie_data'):
                        ts_tab.set_ie_data(ie_data["TimeObservation"])
                if ie_data.get("Process"):
                    for tab_idx in (9, 11):
                        t = self._lazy_load_tab(tab_idx)
                        if t is None:
                            continue
                        if tab_idx == 9:
                            t.set_ie_data(ie_data["Process"])
                        else:
                            t.set_ie_data(processes=ie_data["Process"])
                if ie_data.get("MaterialFlow"):
                    t = self._lazy_load_tab(11)
                    if t is not None:
                        t.set_ie_data(flows=ie_data["MaterialFlow"])
                if ie_data.get("Resource"):
                    t = self._lazy_load_tab(10)
                    if t is not None:
                        t.set_ie_data(ie_data["Resource"])
                for idx in _IE_IMPORT_TAB_INDICES:
                    self._update_tab_empty_state(idx)

                parts = []
                for obj_type, objects in ie_data.items():
                    type_labels = {
                        "Process": "工序表", "TimeObservation": "时间观测",
                        "QualityRecord": "质量记录", "MaterialFlow": "物流", "Resource": "资源",
                    }
                    parts.append(f"{type_labels.get(obj_type, obj_type)}: {len(objects)} 条")
                self.status_label.setText(f"已加载 IE 数据: {' | '.join(parts)}")
                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"无法加载 IE 数据:\n{e!s}")
                self.status_label.setText(i18n.tr("status.failed"))

    def _on_import_db(self):
        # 延迟导入：数据库驱动（sqlalchemy）不进入冷启动路径
        from core.sql_loader import SqlLoader
        from ui.dialogs.db_connection_dialog import DbConnectionDialog
        dialog = DbConnectionDialog(self)
        if dialog.exec():
            config, table_names = dialog.get_selection()
            if not config or not table_names:
                return
            try:
                self.status_label.setText(f"正在从数据库加载 {len(table_names)} 个表...")

                def _load_db():
                    db = SqlLoader()
                    try:
                        db.connect(config)
                        tables = db.load(table_names)
                        meta = dict(db.metadata or {})
                    finally:
                        with contextlib.suppress(Exception):
                            db.disconnect()
                    return tables, meta

                raw_data, metadata = run_in_worker(self, _load_db)
                loader = SqlLoader()
                loader.metadata = metadata
                audit("import_db", "user",
                      f"数据库 {config.get('database', '')} 表数={len(raw_data)}")
                self._record_data_imported(
                    f"db:{config.get('database', '')}", raw_data, kind="database")

                self.current_data = {
                    "source": "database",
                    "db_config": config,
                    "raw_data": raw_data,
                    "metadata": loader.metadata,
                }
                self.data_loader.raw_data = raw_data
                self.data_loader.metadata = loader.metadata

                self._route_sheets_to_tabs(raw_data, worksheet_mode=False)
                db_label = f"{config.get('database', 'DB')}"
                self.data_label.setText(f" DB: {db_label} [{len(raw_data)} tables]")

                try:
                    self.profile_result = self.data_profiler.profile(raw_data)
                except Exception:
                    self.profile_result = {}

                self.status_label.setText(
                    f"数据库加载完成: {len(table_names)} 个表, "
                    f"{loader.metadata.get('total_rows', 0)} 行"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "数据库导入失败",
                    f"从数据库加载数据失败:\n{e!s}"
                )
                self.status_label.setText("数据库导入失败")

    def _on_import_data(self):
        """兼容旧调用 — 默认质量导入"""
        self._on_import_quality()

    def _route_sheets_to_tabs(self, raw_data: dict[str, pd.DataFrame], worksheet_mode: bool = False):
        """将导入的 Sheet 分配到各分析 Tab。
        worksheet_mode=True: 分配到除 IE 工具(7-11,21-22)外的所有 Tab。
        worksheet_mode=False: 分配到所有 Tab（含 IE）。"""
        sheet_map = {
            1:  ["spc", "控制图", "control chart"],
            2:  ["能力", "capability", "cpk", "ppk"],
            3:  ["msa", "gage", "量具", "r&r", "grr"],
            4:  ["假设", "hypothesis", "t_test", "anova", "检验"],
            5:  ["doe", "因子", "实验设计", "design"],
            6:  ["regression", "回归", "reg"],
            12: ["chart", "图表", "chart_tab", "可视化"],
            13: ["reliability", "可靠性", "weibull", "mtbf", "寿命"],
            14: ["fishbone", "鱼骨", "因果", "ishikawa"],
            15: ["pareto", "帕累托", "柏拉图", "abc"],
            16: ["fmea", "失效", "fmea"],
            17: ["control_plan", "控制计划", "cp"],
            18: ["cap_comparison", "能力对比", "comparison"],
            19: ["trend", "趋势", "trend"],
            20: ["summary", "摘要", "汇总", "summary_panel"],
            23: ["merge", "合并", "sheet_merge"],
            24: ["split", "拆分", "sheet_split"],
            25: ["layered", "lpa", "分层", "审核"],
            26: ["sampling", "抽样", "aql", "采样"],
            27: ["dashboard", "仪表盘", "dashboard", "汇总报告"],
            28: ["data_tools", "数据工具", "生成", "转换"],
            36: ["时间序列", "时序", "time series", "timeseries"],
            37: ["预测", "predict", "机器学习", "建模"],
        }

        all_indices = set(sheet_map.keys())
        for idx in all_indices:
            if worksheet_mode and idx in _IE_TAB_INDICES:
                continue
            tab = self._lazy_load_tab(idx)
            if tab and hasattr(tab, 'set_raw_data'):
                tab.set_raw_data(raw_data, self.data_parser)
                self._update_tab_empty_state(idx)

        assigned = set()
        for tab_idx, keywords in sheet_map.items():
            if worksheet_mode and tab_idx in _IE_TAB_INDICES:
                continue
            tab = self._lazy_load_tab(tab_idx)
            if not tab or not hasattr(tab, 'sheet_combo'):
                continue
            for sname in raw_data:
                if sname in assigned:
                    continue
                if any(kw in sname.lower() for kw in keywords):
                    pos = tab.sheet_combo.findText(sname)
                    if pos >= 0:
                        tab.sheet_combo.setCurrentIndex(pos)
                        assigned.add(sname)
                        break

        sheets_info = ", ".join(f"{s} ({len(raw_data[s])}r)" for s in assigned)
        if sheets_info:
            self.status_label.setText(f"Sheet 已自动匹配: {sheets_info}")

    def _on_import_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("menu.import_template"), "",
            "Excel/JSON (*.xlsx *.xls *.xlsm *.json);;All (*.*)",
        )
        if file_path:
            try:
                self.template_parser.load(file_path)
                analyses_list = self.template_parser.get_analysis_list()
                if not analyses_list:
                    QMessageBox.warning(self, "模板为空", "未解析到有效的分析配置")
                    return

                atype_to_tab = {
                    "xbar_r": 1, "xbar_s": 1, "imr": 1,
                    "p_chart": 1, "np_chart": 1, "c_chart": 1, "u_chart": 1,
                    "cusum": 1, "ewma": 1,
                    "normal_capability": 2, "non_normal_capability": 2,
                    "between_within_capability": 2,
                    "gage_rr_crossed": 3, "gage_rr_nested": 3,
                    "linearity_bias": 3, "attribute_agreement": 3,
                    "t_test_1sample": 4, "t_test_2sample": 4, "t_test_paired": 4,
                    "anova_oneway": 4, "anova_twoway": 4,
                    "normality_test": 4, "variance_test": 4,
                    "factorial_design": 5, "response_surface": 5, "doe_analysis": 5,
                    "box_behnken": 5,
                    "linear_regression": 6, "correlation_heatmap": 6,
                }
                tabs = self._get_tabs()
                applied = 0

                for analysis in analyses_list:
                    atype = analysis.get("analysis_type", "").lower().strip()
                    tab_idx = atype_to_tab.get(atype)
                    if tab_idx is None:
                        continue
                    tab = tabs.get(tab_idx)
                    if tab is None:
                        continue

                    col = analysis.get("measurement_column", "")
                    usl = analysis.get("usl")
                    lsl = analysis.get("lsl")
                    subgroup = analysis.get("subgroup_size")

                    self._apply_template_to_tab(tab, tab_idx, atype, col, usl, lsl, subgroup, analysis)
                    applied += 1

                self.statusBar().showMessage(f"模板已应用: {applied}/{len(analyses_list)} 项", 5000)
                if applied > 0:
                    QMessageBox.information(
                        self, "模板应用完成",
                        f"成功应用 {applied} 个分析配置到对应模块\n\n"
                        + "\n".join(f" - {a.get('analysis_type', '?')}"
                                    for a in analyses_list[:10])
                    )
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.template_failed"), str(e))

    def _apply_template_to_tab(self, tab, tab_idx: int, atype: str,
                                 col: str, usl, lsl, subgroup, analysis: dict):
        method_maps = {
            1: {"xbar_r": "XBar-R", "xbar_s": "XBar-S", "imr": "I-MR",
                "p_chart": "P Chart", "np_chart": "NP Chart",
                "c_chart": "C Chart", "u_chart": "U Chart"},
            2: {"normal_capability": "正态过程能力",
                "non_normal_capability": "非正态 (Box-Cox)",
                "between_within_capability": "组间/组内能力"},
            3: {"gage_rr_crossed": "Gage R&R (交叉)",
                "gage_rr_nested": "Gage R&R (嵌套)",
                "linearity_bias": "线性与偏倚",
                "attribute_agreement": "属性一致性"},
            4: {"t_test_1sample": "单样本 t检验",
                "t_test_2sample": "双样本 t检验",
                "t_test_paired": "配对 t检验",
                "anova_oneway": "单因素 ANOVA",
                "anova_twoway": "双因素 ANOVA",
                "normality_test": "正态性检验",
                "variance_test": "方差齐性检验"},
             5: {"factorial_design": "因子设计分析",
                 "response_surface": "响应曲面分析 (CCD)",
                 "doe_analysis": "DOE 分析",
                 "box_behnken": "Box-Behnken 设计"},
             6: {"linear_regression": "回归分析",
                 "correlation_heatmap": "相关性热力图"},
        }

        method_name = method_maps.get(tab_idx, {}).get(atype, "")

        if tab_idx == 1:
            col_combo = getattr(tab, 'col_combo', None)
            if col_combo and col:
                idx = col_combo.findText(col)
                if idx >= 0:
                    col_combo.setCurrentIndex(idx)
            if method_name:
                chart_combo = getattr(tab, 'chart_type_combo', None)
                if chart_combo:
                    idx = chart_combo.findText(method_name)
                    if idx >= 0:
                        chart_combo.setCurrentIndex(idx)
            if subgroup and hasattr(tab, 'subgroup_spin'):
                tab.subgroup_spin.setValue(int(subgroup))
            if usl is not None and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(usl))
            if lsl is not None and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(lsl))

        elif tab_idx == 2:
            col_combo = getattr(tab, 'col_combo', None)
            if col_combo and col:
                idx = col_combo.findText(col)
                if idx >= 0:
                    col_combo.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)
            if usl is not None and hasattr(tab, 'usl_spin'):
                tab.usl_spin.setValue(float(usl))
            if lsl is not None and hasattr(tab, 'lsl_spin'):
                tab.lsl_spin.setValue(float(lsl))
            target = analysis.get("target")
            if target is not None and hasattr(tab, 'target_spin'):
                tab.target_spin.setValue(float(target))

        elif tab_idx == 3:
            measure_col = getattr(tab, 'measure_col', None)
            if measure_col and col:
                idx = measure_col.findText(col)
                if idx >= 0:
                    measure_col.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)

        elif tab_idx == 4:
            col1 = getattr(tab, 'col1_combo', None)
            if col1 and col:
                idx = col1.findText(col)
                if idx >= 0:
                    col1.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)
            confidence = analysis.get("confidence_level")
            if confidence is not None and hasattr(tab, 'confidence_spin'):
                tab.confidence_spin.setValue(float(confidence))

        elif tab_idx == 5:
            response = getattr(tab, 'response_combo', None)
            if response and col:
                idx = response.findText(col)
                if idx >= 0:
                    response.setCurrentIndex(idx)
            if method_name:
                method_combo = getattr(tab, 'method_combo', None)
                if method_combo:
                    idx = method_combo.findText(method_name)
                    if idx >= 0:
                        method_combo.setCurrentIndex(idx)

        elif tab_idx == 6:
            response = getattr(tab, 'response_combo', None)
            if response and col:
                idx = response.findText(col)
                if idx >= 0:
                    response.setCurrentIndex(idx)
            factor1 = analysis.get("factor1")
            factor2 = analysis.get("factor2")
            factor3 = analysis.get("factor3")
            for i, fc in enumerate([factor1, factor2, factor3], 1):
                if fc:
                    combo = getattr(tab, f'factor{i}_combo', None)
                    if combo:
                        idx = combo.findText(fc)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)

    def _on_import_data_asset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入本地数据资产", "", "AKIA 数据资产 (*.qap *.qda);;All (*.*)")
        if not path:
            return
        try:
            from core.data_asset import load_data_asset, migrate_project_to_asset
            if path.lower().endswith(".qap"):
                # 旧项目通过同一迁移契约进入，避免维护第二套导入流程。
                import tempfile
                with tempfile.TemporaryDirectory() as directory:
                    migrated = migrate_project_to_asset(
                        path, os.path.join(directory, "migration.qda"))
                    project = load_data_asset(migrated["path"])
            else:
                project = load_data_asset(path)
            self._apply_loaded_project(
                project, path,
                status_msg=f"数据资产已导入: {project['manifest'].get('sheet_count', 0)} sheets",
                success_msg=f"已导入 {project['manifest'].get('asset_counts', {})}")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
