"""项目、会话、共享包和报告导出。"""

import os

from PySide6.QtWidgets import (
    QMessageBox, QFileDialog,
)
from PySide6.QtGui import QAction

from core.i18n import i18n
from core.project_manager import ProjectManager
from ui.worker import run_in_worker
from core.project_context import ProjectContext
from core.benefit_ledger import (
    BenefitLedger,
)
from core.gauge_study import GaugeMonitor
from core.skill_matrix import SkillMatrix
from core.sampling_state import SamplingStateManager
from core.audit import audit

from ui._tab_registry import TAB_INDEX

from ui.main_window_constants import (
    _CONTEXT_TAB_INDICES,
)


class ProjectMixin:
    def _on_export_single(self, idx: int, fmt: str = "docx"):
        result = self.analyses.get(idx)
        if not result:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)",
                "pdf": "PDF (*.pdf)", "pptx": "PowerPoint (*.pptx)"}
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", f"分析报告.{fmt}", filters.get(fmt, "")
        )

        if file_path:
            try:
                self.status_label.setText(f"{i18n.tr('status.exporting')} {fmt.upper()}...")
                charts = {} if fmt == "xlsx" else self._collect_charts([idx])

                def _export_one():
                    if fmt == "xlsx":
                        from output.excel_report import ExcelReport
                        ExcelReport().generate([result], file_path)
                    elif fmt == "docx":
                        from output.word_report import WordReport
                        WordReport().generate([result], file_path, charts=charts)
                    elif fmt == "pdf":
                        from output.pdf_report import generate_pdf_report
                        generate_pdf_report([result], file_path, charts=charts)
                    elif fmt == "pptx":
                        from output.pptx_report import PptxReport
                        PptxReport().generate([result], file_path, charts=charts)

                run_in_worker(self, _export_one)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"单Tab导出 {fmt} {os.path.basename(file_path)}")
                self._record_report_exported(fmt, file_path, analyses=[result])
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
                QMessageBox.information(self, i18n.tr("msg.export_complete"), f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_export_all(self, fmt: str = "docx"):
        if not self.analyses:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return

        filters = {"xlsx": "Excel (*.xlsx)", "docx": "Word (*.docx)",
                "pdf": "PDF (*.pdf)", "pptx": "PowerPoint (*.pptx)"}
        file_path, _ = QFileDialog.getSaveFileName(
            self, "汇总导出", f"Quality_Report.{fmt}", filters.get(fmt, "")
        )

        if file_path:
            try:
                self.status_label.setText(f"{i18n.tr('status.exporting')} {fmt.upper()}...")
                analyses_list = list(self.analyses.values())
                charts = ({} if fmt == "xlsx"
                          else self._collect_charts(list(self.analyses.keys())))

                def _export_all():
                    if fmt == "xlsx":
                        from output.excel_report import ExcelReport
                        ExcelReport().generate(analyses_list, file_path)
                    elif fmt == "docx":
                        from output.word_report import WordReport
                        WordReport().generate(analyses_list, file_path, charts=charts)
                    elif fmt == "pptx":
                        from output.pptx_report import PptxReport
                        PptxReport().generate(analyses_list, file_path, charts=charts)
                    elif fmt == "pdf":
                        from output.pdf_report import generate_pdf_report
                        generate_pdf_report(analyses_list, file_path, charts=charts)

                run_in_worker(self, _export_all)
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"汇总导出 {fmt} {os.path.basename(file_path)}")
                self._record_report_exported(fmt, file_path, analyses=analyses_list)
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
                QMessageBox.information(self, i18n.tr("msg.export_complete"), f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _on_export_compliance(self, template_id: str):
        if not self.analyses:
            QMessageBox.warning(self, i18n.tr("msg.no_results"), i18n.tr("msg.run_first"))
            return
        from output.compliance_report import ComplianceReportGenerator
        t = ComplianceReportGenerator.load_template(template_id)
        fmt = t.get("format", "docx")
        filters = {"docx": "Word (*.docx)", "pdf": "PDF (*.pdf)"}
        ext = "docx" if fmt != "pdf" else "pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出合规报告", f"Compliance_Report.{ext}", filters.get(fmt, ""),
        )
        if file_path:
            try:
                self.status_label.setText("正在导出合规报告...")
                charts = self._collect_charts(list(self.analyses.keys()))
                ComplianceReportGenerator.generate(
                    template_id, list(self.analyses.values()),
                    file_path, charts=charts,
                )
                self.status_label.setText(f"{i18n.tr('status.exported')}{file_path}")
                audit("export", "user",
                      f"合规报告 {template_id} {os.path.basename(file_path)}")
                self._record_report_exported(
                    fmt, file_path, analyses=list(self.analyses.values()))
                self._show_toast(f"已导出：{os.path.basename(file_path)}", "success")
                QMessageBox.information(self, i18n.tr("msg.export_complete"),
                                        f"{i18n.tr('msg.export_saved')}\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.export_failed"), str(e))

    def _flush_tab_edits(self) -> None:
        """保存路径统一入口：冲刷各 Tab 节流窗口内的挂起编辑（若有）。

        Tab 侧以 ``flush_pending_edits()`` 暴露冲刷能力（当前：控制计划逐格
        编辑 1.5s 节流）；单个 Tab 冲刷失败不影响保存主链路。
        """
        import logging

        for tab in list(self._tab_cache.values()):
            flush = getattr(tab, "flush_pending_edits", None)
            if not callable(flush):
                continue
            try:
                flush()
            except Exception:
                logging.getLogger(__name__).exception("刷新 Tab 挂起编辑失败")

    def _on_save_project(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "AKIA_Project.qap", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            # 冲刷节流窗口内的挂起编辑（如控制计划 1.5s 合并），否则刚编辑的
            # 内容可能不落盘（2026-10-15 审查实测）
            self._flush_tab_edits()
            self.status_label.setText("正在保存项目...")
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            payload = {
                "path": path, "raw": raw, "analyses": self.analyses, "charts": charts,
                "project_context": self.project_context.to_dict() if self.project_context else None,
                "cases": [workflow.to_dict() for workflow in self.case_workflows],
                "standards": (self.project_context.standards.to_dict()
                              if self.project_context else None),
                "measurements": self.measurement_store.to_dicts(),
                "evidence_events": self.ledger,
                "gauge_studies": self.gauge_monitor.to_dict(),
                "sampling": self.sampling_manager.to_dict(),
                "benefits": self.benefit_ledger.to_dict(),
                "skills": self.skill_matrix.to_dict(),
            }

            def _save_project():
                ProjectManager.save_project(
                    payload["path"], payload["raw"], payload["analyses"],
                    payload["charts"], "",
                    project_context=payload["project_context"],
                    cases=payload["cases"], standards=payload["standards"],
                    measurements=payload["measurements"],
                    evidence_events=payload["evidence_events"],
                    gauge_studies=payload["gauge_studies"],
                    sampling=payload["sampling"], benefits=payload["benefits"],
                    skills=payload["skills"])
                return ProjectManager.recent_projects()

            recent = run_in_worker(self, _save_project)
            self.status_label.setText(f"项目已保存: {path}")
            self._rebuild_recent_menu(recent)
            recent_items = [(r["name"], r["path"]) for r in recent]
            self.welcome_page.set_recent_projects(recent_items)
            QMessageBox.information(self, "保存完成", f"项目已保存到:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_export_data_asset(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据或打开项目")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出本地数据资产", "AKIA_Assets.qda", "AKIA 数据资产 (*.qda)")
        if not path:
            return
        try:
            from core.data_asset import export_data_asset
            self._flush_tab_edits()
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            result = export_data_asset(
                path, raw_data=raw, analyses=self.analyses, chart_bytes=charts,
                project_context=self.project_context,
                cases=[workflow.to_dict() for workflow in self.case_workflows],
                standards=self.project_context.standards,
                evidence_events=self.ledger,
                measurements=self.measurement_store,
                sampling=self.sampling_manager,
                gauge_studies=self.gauge_monitor,
                benefits=self.benefit_ledger,
                skills=self.skill_matrix,
            )
            if not result["verify"].get("ok"):
                raise ValueError("数据资产导出后校验失败")
            audit("export", "user", f"本地数据资产 {os.path.basename(result['path'])}")
            self.status_label.setText(f"数据资产已导出: {result['path']}")
            QMessageBox.information(self, "导出完成", f"数据资产已保存到:\n{result['path']}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _apply_loaded_project(self, project: dict, path: str,
                              status_msg: str | None = None,
                              data_label_suffix: bool = True,
                              success_msg: str | None = None):
        """应用已加载的 .qap 项目: 恢复数据/分析结果/最近菜单并刷新 Dashboard"""
        raw_data = project["raw_data"]
        self.current_data = {
            "file_path": path,
            "raw_data": raw_data,
            "metadata": {"sheet_names": list(raw_data.keys()), "total_rows": sum(len(df) for df in raw_data.values())},
        }
        self.data_loader.raw_data = raw_data
        self.data_loader.metadata = self.current_data["metadata"]
        self._route_sheets_to_tabs(raw_data)
        self.analyses = project["analyses"]

        ctx_dict = project.get("project_context")
        if ctx_dict:
            from core.project_context import ProjectContext as PC
            self.project_context = PC.from_dict(ctx_dict)
        else:
            self.project_context = ProjectContext()
        self.project_context.event_sink = self._on_standard_event
        standards_payload = project.get("standards")
        if standards_payload and not len(self.project_context.standards):
            from core.standard_record import StandardRegistry
            self.project_context.standards = StandardRegistry.from_dict(standards_payload)
        self._restore_ledger(project.get("evidence_events") or [],
                             project.get("evidence_errors") or [])
        # 告警自动立案编排器持有 context/ledger 引用（v4.4.0 B1）：项目加载
        # 会替换这两个对象，必须显式重绑——否则立案快照/8D 草稿/账本事件会
        # 写入已被丢弃的旧对象（不落盘、不可见；2026-10-15 审查实测）。
        self.alert_case_orchestrator.context = self.project_context
        self.alert_case_orchestrator.ledger = self.ledger
        self._restore_case_workflows(project.get("cases") or [])
        self._restore_measurement_store(project.get("measurements") or [])
        self.gauge_monitor = GaugeMonitor.from_dict(project.get("gauge_studies"))
        self._last_gauge_outcome = {}
        msa_tab = self._tab_cache.get(TAB_INDEX["msa"])
        if msa_tab is not None and hasattr(msa_tab, "set_gauge_context"):
            msa_tab.set_gauge_context(self.gauge_monitor,
                                      self._submit_gauge_measurement)
        self.sampling_manager = SamplingStateManager.from_dict(
            project.get("sampling"), ledger=self.ledger,
            standards=self.project_context.standards)
        self.benefit_ledger = BenefitLedger.from_dict(project.get("benefits"))
        self.skill_matrix = SkillMatrix.from_dict(project.get("skills"))
        line_tab = self._tab_cache.get(TAB_INDEX["line_balance"])
        if line_tab is not None and hasattr(line_tab, "set_skill_context"):
            line_tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                       self.record_skill_balance_step)
        if line_tab is not None and hasattr(line_tab, "set_balance_context"):
            line_tab.set_balance_context(self.project_context,
                                         self.record_line_balance_step)
        sampling_tab = self._tab_cache.get(TAB_INDEX["sampling"])
        if sampling_tab is not None and hasattr(sampling_tab, "set_sampling_context"):
            sampling_tab.set_sampling_context(self.sampling_manager)
        evidence_errors = project.get("evidence_errors") or []
        measurement_errors = project.get("measurement_errors") or []
        if evidence_errors or measurement_errors:
            self.statusBar().showMessage(
                f"项目加载警告：账本 {len(evidence_errors)} 条 / 测量 "
                f"{len(measurement_errors)} 条记录解析失败（已跳过并留痕）", 20000)
        for idx in _CONTEXT_TAB_INDICES:
            tab = self._tab_cache.get(idx)
            if tab and hasattr(tab, 'set_project_context'):
                tab.set_project_context(self.project_context)
                if hasattr(tab, 'load_from_context'):
                    tab.load_from_context()

        info = project["manifest"]
        suffix = f" [{info.get('sheet_count', 0)} sheets]" if data_label_suffix else ""
        self.data_label.setText(f" {os.path.basename(path)}{suffix}")
        recent = ProjectManager.recent_projects()
        self._rebuild_recent_menu(recent)
        recent_items = [(r["name"], r["path"]) for r in recent]
        self.welcome_page.set_recent_projects(recent_items)
        self.status_label.setText(
            status_msg or f"项目已加载: {info.get('analysis_count', 0)} 个分析"
        )
        self._notify_dashboard()
        if success_msg:
            QMessageBox.information(self, "加载完成", success_msg)

    def _on_load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            self.status_label.setText("正在加载项目...")
            project = run_in_worker(self, ProjectManager.load_project, path)
            self._apply_loaded_project(
                project, path,
                success_msg=(
                    f"已恢复 {len(project['raw_data'])} 个数据表、"
                    f"{len(self.analyses)} 个分析结果、"
                    f"{len(self.case_workflows)} 个改善案例"),
            )
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _load_project_by_path(self, path: str):
        """通过路径直接加载项目（供欢迎页最近项目使用）"""
        try:
            self.status_label.setText("正在加载项目...")
            project = run_in_worker(self, ProjectManager.load_project, path)
            self._apply_loaded_project(project, path)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _rebuild_recent_menu(self, recent: list):
        if not hasattr(self, 'recent_menu'):
            return
        self.recent_menu.clear()
        for r in recent:
            name = r.get("name", "?")[:50]
            action = QAction(name, self)
            p = r["path"]
            action.triggered.connect(lambda checked, path=p: self._on_load_recent(path))
            self.recent_menu.addAction(action)

    def _on_load_recent(self, path: str):
        if os.path.exists(path):
            try:
                self.status_label.setText("正在加载项目...")
                project = run_in_worker(self, ProjectManager.load_project, path)
                self._apply_loaded_project(
                    project, path,
                    status_msg=f"项目已加载: {len(project['raw_data'])} sheets",
                    data_label_suffix=False,
                    success_msg=f"已恢复 {len(project['analyses'])} 个分析",
                )
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))
        else:
            QMessageBox.warning(self, "文件不存在", f"项目文件已移动或删除:\n{path}")

    def _on_save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("menu.save_session"), "session.json", "JSON (*.json)"
        )
        if file_path:
            tabs = self._get_tabs()
            self.session_manager.current_session["tab_params"] = {}
            for idx, tab in tabs.items():
                params = {}
                if idx == 1:
                    if hasattr(tab, 'col_combo'):
                        params["column"] = tab.col_combo.currentText()
                    if hasattr(tab, 'chart_type_combo'):
                        params["chart_type"] = tab.chart_type_combo.currentText()
                    if hasattr(tab, 'subgroup_spin'):
                        params["subgroup_size"] = tab.subgroup_spin.value()
                    if hasattr(tab, 'usl_spin'):
                        params["usl"] = tab.usl_spin.value()
                    if hasattr(tab, 'lsl_spin'):
                        params["lsl"] = tab.lsl_spin.value()
                elif idx == 2:
                    if hasattr(tab, 'col_combo'):
                        params["column"] = tab.col_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                    if hasattr(tab, 'usl_spin'):
                        params["usl"] = tab.usl_spin.value()
                    if hasattr(tab, 'lsl_spin'):
                        params["lsl"] = tab.lsl_spin.value()
                elif idx == 3:
                    if hasattr(tab, 'measure_col'):
                        params["column"] = tab.measure_col.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 4:
                    if hasattr(tab, 'col1_combo'):
                        params["col1"] = tab.col1_combo.currentText()
                    if hasattr(tab, 'col2_combo'):
                        params["col2"] = tab.col2_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 5:
                    if hasattr(tab, 'response_combo'):
                        params["response"] = tab.response_combo.currentText()
                    if hasattr(tab, 'method_combo'):
                        params["method"] = tab.method_combo.currentText()
                elif idx == 6:
                    if hasattr(tab, 'response_combo'):
                        params["response"] = tab.response_combo.currentText()
                    if hasattr(tab, 'factor1_combo'):
                        params["factor1"] = tab.factor1_combo.currentText()
                    if hasattr(tab, 'factor2_combo'):
                        params["factor2"] = tab.factor2_combo.currentText()
                    if hasattr(tab, 'factor3_combo'):
                        params["factor3"] = tab.factor3_combo.currentText()
                if params:
                    self.session_manager.current_session["tab_params"][str(idx)] = params

            self.session_manager.set_analyses(self.analyses)

            path = self.session_manager.save(file_path)
            self.status_label.setText(f"{i18n.tr('status.session_saved')}{path}")

    def _on_load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, i18n.tr("menu.load_session"), "", "JSON (*.json)"
        )
        if file_path:
            try:
                data = self.session_manager.load(file_path)
                src_file = data.get("file_path", "")
                if src_file and os.path.exists(src_file):
                    loader = self.data_loader

                    def _load_session_file():
                        raw = loader.load(src_file)
                        return raw, dict(loader.metadata or {})

                    raw_data, metadata = run_in_worker(self, _load_session_file)
                    self.data_loader.metadata = metadata
                    self.current_data = {
                        "file_path": src_file,
                        "raw_data": raw_data,
                        "metadata": self.data_loader.metadata,
                    }
                    self._route_sheets_to_tabs(raw_data)
                    self.data_label.setText(f" {os.path.basename(src_file)}")

                tab_params = data.get("tab_params", {})
                tabs = self._get_tabs()
                for idx_str, params in tab_params.items():
                    idx = int(idx_str)
                    tab = tabs.get(idx)
                    if tab is None:
                        continue
                    col = params.get("column") or params.get("col1") or params.get("response")
                    if col:
                        combo_attrs = {
                            1: "col_combo", 2: "col_combo",
                            3: "measure_col", 4: "col1_combo", 5: "response_combo",
                            6: "response_combo",
                        }
                        combo = getattr(tab, combo_attrs.get(idx, ""), None)
                        if combo:
                            ci = combo.findText(col)
                            if ci >= 0:
                                combo.setCurrentIndex(ci)

                    method = params.get("method") or params.get("chart_type")
                    if method and hasattr(tab, 'method_combo'):
                        mi = tab.method_combo.findText(method)
                        if mi >= 0:
                            tab.method_combo.setCurrentIndex(mi)
                    if method and idx == 1 and hasattr(tab, 'chart_type_combo'):
                        mi = tab.chart_type_combo.findText(method)
                        if mi >= 0:
                            tab.chart_type_combo.setCurrentIndex(mi)

                    usl = params.get("usl")
                    if usl is not None and hasattr(tab, 'usl_spin'):
                        tab.usl_spin.setValue(float(usl))
                    lsl = params.get("lsl")
                    if lsl is not None and hasattr(tab, 'lsl_spin'):
                        tab.lsl_spin.setValue(float(lsl))
                    subgroup = params.get("subgroup_size")
                    if subgroup is not None and hasattr(tab, 'subgroup_spin'):
                        tab.subgroup_spin.setValue(int(subgroup))

                self.analyses = self.session_manager.get_analyses()
                self._notify_dashboard()
                count = len(self.analyses)
                self.statusBar().showMessage(
                    f"会话已加载: {data.get('name', '')} ({count} 个分析)", 5000
                )
            except Exception as e:
                QMessageBox.critical(self, i18n.tr("msg.import_failed"), str(e))

    def _on_save_shared(self):
        if not self.current_data:
            QMessageBox.warning(self, "无数据", "请先导入数据并运行分析")
            return
        from core.project_manager import SharedProjectManager
        dept = "公共"
        path, _ = QFileDialog.getSaveFileName(
            self, "保存到共享目录", "AKIA_Shared.qap", "AKIA 项目 (*.qap)"
        )
        if not path:
            return
        try:
            # 同 _on_save_project：共享保存前冲刷节流窗口内的挂起编辑
            self._flush_tab_edits()
            raw = self.current_data.get("raw_data", {})
            charts = {}
            for label, buf in self._collect_charts(list(self.analyses.keys())).items():
                charts[label] = buf.getvalue() if hasattr(buf, 'getvalue') else buf
            SharedProjectManager.save_shared(
                path, raw, self.analyses, charts, dept,
                project_context=(self.project_context.to_dict()
                                 if self.project_context else None),
                cases=[workflow.to_dict() for workflow in self.case_workflows],
                standards=(self.project_context.standards.to_dict()
                           if self.project_context else None),
                measurements=self.measurement_store.to_dicts(),
                evidence_events=self.ledger,
                gauge_studies=self.gauge_monitor.to_dict(),
                sampling=self.sampling_manager.to_dict(),
                benefits=self.benefit_ledger.to_dict(),
                skills=self.skill_matrix.to_dict())
            audit("share_project", "user",
                  f"保存 {os.path.basename(path)}")
            self.status_label.setText("共享项目已保存")
            QMessageBox.information(self, "保存完成", f"项目已共享到部门: {dept}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_load_shared(self):
        from core.project_manager import SharedProjectManager
        dept = ""
        role = ""
        projects = SharedProjectManager.list_shared(department=dept, role=role)
        if not projects:
            QMessageBox.information(self, "共享项目", "共享目录中没有可用的项目")
            return
        from PySide6.QtWidgets import QInputDialog
        names = [f"{p['name']} ({p['department']})" for p in projects]
        name, ok = QInputDialog.getItem(self, "打开共享项目", "选择项目:", names, 0, False)
        if ok and name:
            idx = names.index(name)
            proj = projects[idx]
            try:
                loaded = SharedProjectManager.load_shared(proj['path'])
                self._apply_loaded_project(
                    loaded, proj['path'],
                    status_msg=f"共享项目已加载: {len(loaded['raw_data'])} sheets")
            except Exception as e:
                QMessageBox.critical(self, "加载失败", str(e))
