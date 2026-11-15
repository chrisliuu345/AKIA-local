"""主窗口菜单。"""


from PySide6.QtGui import QAction

from core.i18n import i18n
from core.project_manager import ProjectManager


class MenuMixin:
    def _setup_menu(self):
        menubar = self.menuBar()

        def _pin(menu):
            self._menu_refs.append(menu)
            return menu

        file_menu = _pin(menubar.addMenu(i18n.tr("menu.file")))

        import_quality_action = QAction(i18n.tr("sidebar.import_quality"), self)
        import_quality_action.setShortcut("Ctrl+O")
        import_quality_action.triggered.connect(self._on_import_quality)
        file_menu.addAction(import_quality_action)

        import_ie_action = QAction(i18n.tr("sidebar.import_ie"), self)
        import_ie_action.triggered.connect(self._on_import_ie)
        file_menu.addAction(import_ie_action)

        import_db_action = QAction(i18n.tr("sidebar.import_db"), self)
        import_db_action.triggered.connect(self._on_import_db)
        file_menu.addAction(import_db_action)

        file_menu.addSeparator()

        template_action = QAction(i18n.tr("menu.import_template"), self)
        template_action.triggered.connect(self._on_import_template)
        file_menu.addAction(template_action)

        file_menu.addSeparator()

        recent = ProjectManager.recent_projects()
        if recent:
            self.recent_menu = _pin(file_menu.addMenu(i18n.tr("menu.recent")))
            self._rebuild_recent_menu(recent)
            recent_items = [(r["name"], r["path"]) for r in recent]
            self.welcome_page.set_recent_projects(recent_items)

        save_session = QAction(i18n.tr("menu.save_session"), self)
        save_session.setShortcut("Ctrl+S")
        save_session.triggered.connect(self._on_save_session)
        file_menu.addAction(save_session)
        load_session = QAction(i18n.tr("menu.load_session"), self)
        load_session.triggered.connect(self._on_load_session)
        file_menu.addAction(load_session)

        save_project_action = QAction(i18n.tr("menu.save_project"), self)
        save_project_action.setShortcut("Ctrl+Shift+S")
        save_project_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_project_action)
        open_project_action = QAction(i18n.tr("menu.open_project"), self)
        open_project_action.setShortcut("Ctrl+Shift+O")
        open_project_action.triggered.connect(self._on_load_project)
        file_menu.addAction(open_project_action)
        export_asset_action = QAction("导出本地数据资产 (.qda)", self)
        export_asset_action.setObjectName("exportDataAssetAction")
        export_asset_action.triggered.connect(self._on_export_data_asset)
        file_menu.addAction(export_asset_action)
        import_asset_action = QAction("导入本地数据资产 (.qda)", self)
        import_asset_action.setObjectName("importDataAssetAction")
        import_asset_action.triggered.connect(self._on_import_data_asset)
        file_menu.addAction(import_asset_action)
        save_shared_action = QAction(i18n.tr("menu.save_shared"), self)
        save_shared_action.triggered.connect(self._on_save_shared)
        file_menu.addAction(save_shared_action)
        load_shared_action = QAction(i18n.tr("menu.load_shared"), self)
        load_shared_action.triggered.connect(self._on_load_shared)
        file_menu.addAction(load_shared_action)

        file_menu.addSeparator()

        export_menu = _pin(file_menu.addMenu(i18n.tr("menu.export")))
        export_xlsx = QAction(i18n.tr("menu.export_xlsx"), self)
        export_xlsx.triggered.connect(lambda: self._on_export_all("xlsx"))
        export_menu.addAction(export_xlsx)
        export_docx = QAction(i18n.tr("menu.export_docx"), self)
        export_docx.triggered.connect(lambda: self._on_export_all("docx"))
        export_menu.addAction(export_docx)
        export_pdf = QAction(i18n.tr("menu.export_pdf"), self)
        export_pdf.triggered.connect(lambda: self._on_export_all("pdf"))
        export_menu.addAction(export_pdf)
        export_pptx = QAction(i18n.tr("menu.export_pptx"), self)
        export_pptx.triggered.connect(lambda: self._on_export_all("pptx"))
        export_menu.addAction(export_pptx)
        export_html = QAction(i18n.tr("menu.html_export"), self)
        export_html.triggered.connect(self._on_html_export)
        export_menu.addAction(export_html)

        try:
            from output.compliance_report import ComplianceReportGenerator
            templates = ComplianceReportGenerator.list_templates()
            if templates:
                export_menu.addSeparator()
                comply_menu = _pin(export_menu.addMenu(i18n.tr("menu.compliance")))
                for t in templates:
                    ac = comply_menu.addAction(f"{t['name']} ({t['standard']})")
                    ac.setData(t["id"])
                    ac.triggered.connect(lambda checked, tid=t["id"]: self._on_export_compliance(tid))
        except Exception:  # 合规报告模板不可用：菜单少一项，不影响其余菜单
            pass

        file_menu.addSeparator()

        exit_action = QAction(i18n.tr("menu.exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = _pin(menubar.addMenu(i18n.tr("menu.view")))
        self.toggle_sidebar_action = QAction(i18n.tr("menu.toggle_sidebar"), self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.setShortcut("Ctrl+B")
        self.toggle_sidebar_action.triggered.connect(
            lambda checked: self._toggle_sidebar(not checked)
        )
        view_menu.addAction(self.toggle_sidebar_action)
        palette_action = QAction("命令面板", self)
        palette_action.setShortcuts(["Ctrl+K", "Ctrl+P"])
        palette_action.setToolTip("快速跳转模块 / 执行操作")
        palette_action.triggered.connect(self._open_command_palette)
        view_menu.addAction(palette_action)
        display_mode_action = QAction(i18n.tr("menu.display_mode"), self)
        display_mode_action.setShortcut("F11")
        display_mode_action.triggered.connect(self._open_display_mode)
        view_menu.addAction(display_mode_action)

        analysis_menu = _pin(menubar.addMenu(i18n.tr("menu.analysis")))
        quality_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.quality_tools")))
        for idx, key in [(1, "sidebar.spc"), (2, "sidebar.capability"), (3, "sidebar.msa"),
                         (4, "sidebar.hypothesis"), (5, "sidebar.doe"), (6, "sidebar.regression"),
                         (36, "sidebar.time_series"), (37, "sidebar.predictive")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            quality_sub.addAction(a)
        ie_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.ie_tools")))
        for idx, key in [(7, "sidebar.time_study"), (8, "sidebar.work_sampling"),
                         (9, "sidebar.line_balance"), (10, "sidebar.oee"),
                         (11, "menu.vsm"), (21, "sidebar.worker_machine"),
                         (22, "sidebar.std_work_combo"), (29, "sidebar.smed"), (31, "sidebar.tpm")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            ie_sub.addAction(a)
        chart_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.chart_tools")))
        for idx, key in [(12, "sidebar.chart_tab"), (18, "sidebar.cap_comparison"),
                         (19, "sidebar.trend"), (20, "sidebar.summary_panel")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            chart_sub.addAction(a)
        eng_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.engineering_tools")))
        for idx, key in [(13, "sidebar.reliability"), (14, "sidebar.fishbone"),
                         (15, "sidebar.pareto"), (16, "sidebar.fmea"),
                         (17, "sidebar.control_plan"), (30, "sidebar.8d"), (32, "sidebar.ppap")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            eng_sub.addAction(a)
        sheet_sub = _pin(analysis_menu.addMenu(i18n.tr("sidebar.sheet_tools")))
        for idx, key in [(23, "sidebar.sheet_merge"), (24, "sidebar.sheet_split"),
                         (25, "sidebar.layered_form")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            sheet_sub.addAction(a)
        analysis_menu.addSeparator()
        for idx, key in [(26, "sidebar.sampling"), (28, "sidebar.data_tools_tab"),
                         (27, "sidebar.dashboard"), (33, "sidebar.monitor"),
                         (34, "sidebar.multi_plant"), (35, "sidebar.device")]:
            a = QAction(i18n.tr(key), self)
            a.triggered.connect(lambda _, i=idx: self._switch_tab(i))
            analysis_menu.addAction(a)
        analysis_menu.addSeparator()
        run_all = QAction(i18n.tr("menu.run"), self)
        run_all.setShortcut("F5")
        run_all.triggered.connect(self._on_run_all_analyses)
        run_all.setShortcut("Ctrl+Shift+B")
        analysis_menu.addAction(run_all)

        ai_menu = _pin(menubar.addMenu(i18n.tr("menu.ai")))
        ai_chat = QAction(i18n.tr("sidebar.llm"), self)
        ai_chat.triggered.connect(self._on_llm_assist)
        ai_menu.addAction(ai_chat)
        one_click = QAction(i18n.tr("menu.one_click"), self)
        one_click.triggered.connect(self._on_one_click_analysis)
        ai_menu.addAction(one_click)

        tools_menu = _pin(menubar.addMenu(i18n.tr("menu.tools")))
        settings_act = QAction(i18n.tr("menu.settings"), self, triggered=self._on_settings)
        tools_menu.addAction(settings_act)
        batch_act = QAction(i18n.tr("menu.batch"), self, triggered=self._on_batch_scheduler)
        tools_menu.addAction(batch_act)
        self.case_workbench_act = QAction("改善案例工作台", self,
                                          triggered=self._on_case_workbench)
        tools_menu.addAction(self.case_workbench_act)
        self.case_center_act = QAction("改善案例中心", self,
                                       triggered=self._on_case_center)
        tools_menu.addAction(self.case_center_act)
        self.standard_history_act = QAction("标准版本记录", self,
                                            triggered=self._on_standard_history)
        tools_menu.addAction(self.standard_history_act)
        self.benefit_ledger_act = QAction("收益账本", self,
                                          triggered=self._on_benefit_ledger)
        self.benefit_ledger_act.setToolTip("改善收益 / COPQ 四类 / ROI / 月度复算（v4.4.0 B4）")
        tools_menu.addAction(self.benefit_ledger_act)
        self.evidence_view_act = QAction("证据视图", self,
                                         triggered=self._on_evidence_view)
        tools_menu.addAction(self.evidence_view_act)
        tools_menu.addSeparator()
        clean_act = QAction(i18n.tr("sidebar.data_clean"), self, triggered=self._on_data_cleaner)
        tools_menu.addAction(clean_act)
        clean_wiz_act = QAction(i18n.tr("menu.data_clean_wizard"), self, triggered=self._on_data_clean_wizard)
        tools_menu.addAction(clean_wiz_act)
        tools_menu.addAction(QAction(i18n.tr("sidebar.diagnose"), self,
                                     triggered=self._on_diagnose))
        tools_menu.addSeparator()
        template_act = QAction(i18n.tr("menu.template"), self)
        template_act.triggered.connect(self._on_template_dialog)
        tools_menu.addAction(template_act)
        tools_menu.addSeparator()
        plant_cfg_act = QAction(i18n.tr("menu.plant_config"), self,
                                triggered=self._on_plant_config)
        tools_menu.addAction(plant_cfg_act)
        tools_menu.addAction(QAction(i18n.tr("menu.alert_center"), self,
                                     triggered=self._on_alert_center))
        tools_menu.addAction(QAction(i18n.tr("menu.connector_health"), self,
                                     triggered=self._on_connector_health))
        self.live_dash_act = QAction(i18n.tr("menu.live_dashboard"), self,
                                     checkable=True, triggered=self._on_live_dashboard)
        tools_menu.addAction(self.live_dash_act)

        help_menu = _pin(menubar.addMenu(i18n.tr("menu.help")))
        guide_action = QAction(i18n.tr("menu.guide"), self)
        guide_action.setShortcut("F1")
        guide_action.triggered.connect(self._on_open_guide)
        help_menu.addAction(guide_action)
        help_menu.addAction(QAction(i18n.tr("sidebar.template_help_tip"), self,
                                    triggered=self._on_template_help))
        help_menu.addSeparator()
        about_action = QAction(i18n.tr("menu.about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
