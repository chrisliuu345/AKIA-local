"""
Tab 注册表 — 单一数据源，替代 main_window 中三处平行 tab 结构

每个条目: (index, i18n_key, class_name, module_path, category_key)
- index: stack widget 索引
- i18n_key: 侧栏/国际化键名
- class_name: Tab 类名
- module_path: Python 模块路径 (相对于项目根)
- category_key: 侧栏分类键名
"""

TAB_REGISTRY = [
    # ── 质量分析 (1-6) ──
    (1,  "sidebar.spc",              "SPCTab",              "ui.tabs.spc_tab",              "sidebar.quality_tools"),
    (2,  "sidebar.capability",       "CapabilityTab",       "ui.tabs.capability_tab",       "sidebar.quality_tools"),
    (3,  "sidebar.msa",              "MSATab",              "ui.tabs.msa_tab",              "sidebar.quality_tools"),
    (4,  "sidebar.hypothesis",       "HypothesisTab",       "ui.tabs.hypothesis_tab",       "sidebar.quality_tools"),
    (5,  "sidebar.doe",              "DOETab",              "ui.tabs.doe_tab",              "sidebar.quality_tools"),
    (6,  "sidebar.regression",       "RegressionTab",       "ui.tabs.regression_tab",       "sidebar.quality_tools"),
    # ── IE 工具 (7-11, 21-22) ──
    (7,  "sidebar.time_study",       "TimeStudyTab",        "ui.tabs.time_study_tab",       "sidebar.ie_tools"),
    (8,  "sidebar.work_sampling",    "WorkSamplingTab",     "ui.tabs.work_sampling_tab",    "sidebar.ie_tools"),
    (9,  "sidebar.line_balance",     "LineBalanceTab",      "ui.tabs.line_balance_tab",     "sidebar.ie_tools"),
    (10, "sidebar.oee",              "OEETab",              "ui.tabs.oee_tab",              "sidebar.ie_tools"),
    (11, "sidebar.vsm",              "VSMTab",              "ui.tabs.vsm_tab",              "sidebar.ie_tools"),
    (21, "sidebar.worker_machine",   "WorkerMachineTab",    "ui.tabs.worker_machine_tab",   "sidebar.ie_tools"),
    (22, "sidebar.std_work_combo",   "StdWorkComboTab",     "ui.tabs.std_work_combo_tab",   "sidebar.ie_tools"),
    # ── 图表工具 (12, 18-20) ──
    (12, "sidebar.chart_tab",        "ChartTab",            "ui.tabs.chart_tab",            "sidebar.chart_tools"),
    (18, "sidebar.cap_comparison",   "CapComparisonTab",    "ui.tabs.cap_comparison_tab",   "sidebar.chart_tools"),
    (19, "sidebar.trend",            "TrendTab",            "ui.tabs.trend_tab",            "sidebar.chart_tools"),
    (20, "sidebar.summary_panel",    "SummaryPanelTab",     "ui.tabs.summaries_panel_tab",  "sidebar.chart_tools"),
    # ── 工程工具 (13-17) ──
    (13, "sidebar.reliability",      "ReliabilityTab",      "ui.tabs.reliability_tab",      "sidebar.engineering_tools"),
    (14, "sidebar.fishbone",         "FishboneTab",         "ui.tabs.fishbone_tab",         "sidebar.engineering_tools"),
    (15, "sidebar.pareto",           "ParetoTab",           "ui.tabs.pareto_tab",           "sidebar.engineering_tools"),
    (16, "sidebar.fmea",             "FMEATab",             "ui.tabs.fmea_tab",             "sidebar.engineering_tools"),
    (17, "sidebar.control_plan",     "ControlPlanTab",      "ui.tabs.control_plan_tab",     "sidebar.engineering_tools"),
    # ── 工作表 (23-25) ──
    (23, "sidebar.sheet_merge",      "SheetMergeTab",       "ui.tabs.sheet_merge_tab",      "sidebar.sheet_tools"),
    (24, "sidebar.sheet_split",      "SheetSplitTab",       "ui.tabs.sheet_split_tab",      "sidebar.sheet_tools"),
    (25, "sidebar.layered_form",     "LayeredFormTab",      "ui.tabs.layered_form_tab",     "sidebar.sheet_tools"),
    # ── 抽样检验 (26) ──
    (26, "sidebar.sampling",         "SamplingTab",         "ui.tabs.sampling_tab",         "sidebar.sampling_tools"),
    # ── 报告 (27) ──
    (27, "sidebar.dashboard",        "DashboardTab",        "ui.tabs.dashboard_tab",        "sidebar.report"),
    # ── 数据工具 (28) ──
    (28, "sidebar.data_tools_tab",   "DataToolsTab",        "ui.tabs.data_tools_tab",       "sidebar.data_tools"),
    # ── v2.2 工程工具扩展 (29-32) ──
    (29, "sidebar.smed",             "SMEDTab",             "ui.tabs.smed_tab",             "sidebar.ie_tools"),
    (30, "sidebar.8d",               "EightDTab",           "ui.tabs.eight_d_tab",          "sidebar.engineering_tools"),
    (31, "sidebar.tpm",              "TPMTab",              "ui.tabs.tpm_tab",              "sidebar.ie_tools"),
    (32, "sidebar.ppap",             "PPAPTab",             "ui.tabs.ppap_tab",             "sidebar.engineering_tools"),
    # ── v2.4 实时监控 (33-34) ──
    (33, "sidebar.monitor",          "MonitorTab",          "ui.tabs.monitor_tab",          "sidebar.monitoring"),
    (34, "sidebar.multi_plant",      "MultiPlantTab",       "ui.tabs.multi_plant_tab",      "sidebar.monitoring"),
    # ── v2.5 硬件拓展 (35) ──
    (35, "sidebar.device",           "DeviceTab",           "ui.tabs.device_tab",           "sidebar.monitoring"),
]

# 构建快速索引: index → registry entry
INDEX_MAP = {entry[0]: entry for entry in TAB_REGISTRY}
# 构建快速索引: module_path → class_name (用于 import)
TAB_COUNT = len(TAB_REGISTRY)
