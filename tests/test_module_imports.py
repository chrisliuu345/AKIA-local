"""
模块导入冒烟 — 防止重构/新增模块造成 import 断链
仅验证可导入性，不做实例化
"""

import importlib


_CORE_MODULES = [
    # 图表体系
    "analysis.charts.chart_options",
    "analysis.charts.chart_generator",
    "analysis.charts.heatmap",
    "analysis.charts.faceting",
    "output.chart_engine",
    "output.pptx_report",
    "output.word_report",
    "output.excel_report",
    "output.pdf_report",
    "output.html_export",
    "ui.widgets.chart_editor",
    "ui.widgets.chart_gallery",
    "ui.tabs.base_tab",
    "ui.tabs.chart_tab",
    "ui.tabs.spc_tab",
    "ui.tabs.capability_tab",
    "ui.tabs.hypothesis_tab",
    "ui.tabs.msa_tab",
    "ui.tabs.time_series_tab",
    "ui.tabs.regression_tab",
    "ui.tabs.summaries_panel_tab",
    "ui.tabs.dashboard_tab",
    # 工程上下文
    "core.project_context",
    "core.project_manager",
    "core.archive_safety",
    "core.plugin_check",
    "core.rule_pack",
    "core.i18n",
    "config.settings",
    "akia_sdk",
    "akia_sdk.client",
    "akia_sdk.cli",
    "ui.main_window",
]


class TestModuleImports:
    def test_core_modules_importable(self):
        for name in _CORE_MODULES:
            module = importlib.import_module(name)
            assert module is not None, name
