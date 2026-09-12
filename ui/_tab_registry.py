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
    (1,  "sidebar.spc",              "SPCTab",              "ui.tabs.spc_tab",              "sidebar.quality_tools"),
    (2,  "sidebar.capability",       "CapabilityTab",       "ui.tabs.capability_tab",       "sidebar.quality_tools"),
    (3,  "sidebar.msa",              "MSATab",              "ui.tabs.msa_tab",              "sidebar.quality_tools"),
    (4,  "sidebar.hypothesis",       "HypothesisTab",       "ui.tabs.hypothesis_tab",       "sidebar.quality_tools"),
    (5,  "sidebar.doe",              "DOETab",              "ui.tabs.doe_tab",              "sidebar.quality_tools"),
    (6,  "sidebar.regression",       "RegressionTab",       "ui.tabs.regression_tab",       "sidebar.quality_tools"),
    (7,  "sidebar.time_study",       "TimeStudyTab",        "ui.tabs.time_study_tab",       "sidebar.ie_tools"),
    (8,  "sidebar.work_sampling",    "WorkSamplingTab",     "ui.tabs.work_sampling_tab",    "sidebar.ie_tools"),
    (9,  "sidebar.line_balance",     "LineBalanceTab",      "ui.tabs.line_balance_tab",     "sidebar.ie_tools"),
    (10, "sidebar.oee",              "OEETab",              "ui.tabs.oee_tab",              "sidebar.ie_tools"),
    (11, "sidebar.vsm",              "VSMTab",              "ui.tabs.vsm_tab",              "sidebar.ie_tools"),
    (21, "sidebar.worker_machine",   "WorkerMachineTab",    "ui.tabs.worker_machine_tab",   "sidebar.ie_tools"),
    (22, "sidebar.std_work_combo",   "StdWorkComboTab",     "ui.tabs.std_work_combo_tab",   "sidebar.ie_tools"),
    (12, "sidebar.chart_tab",        "ChartTab",            "ui.tabs.chart_tab",            "sidebar.chart_tools"),
    (18, "sidebar.cap_comparison",   "CapComparisonTab",    "ui.tabs.cap_comparison_tab",   "sidebar.chart_tools"),
    (19, "sidebar.trend",            "TrendTab",            "ui.tabs.trend_tab",            "sidebar.chart_tools"),
    (20, "sidebar.summary_panel",    "SummaryPanelTab",     "ui.tabs.summaries_panel_tab",  "sidebar.chart_tools"),
    (13, "sidebar.reliability",      "ReliabilityTab",      "ui.tabs.reliability_tab",      "sidebar.engineering_tools"),
    (14, "sidebar.fishbone",         "FishboneTab",         "ui.tabs.fishbone_tab",         "sidebar.engineering_tools"),
    (15, "sidebar.pareto",           "ParetoTab",           "ui.tabs.pareto_tab",           "sidebar.engineering_tools"),
    (16, "sidebar.fmea",             "FMEATab",             "ui.tabs.fmea_tab",             "sidebar.engineering_tools"),
    (17, "sidebar.control_plan",     "ControlPlanTab",      "ui.tabs.control_plan_tab",     "sidebar.engineering_tools"),
    (23, "sidebar.sheet_merge",      "SheetMergeTab",       "ui.tabs.sheet_merge_tab",      "sidebar.sheet_tools"),
    (24, "sidebar.sheet_split",      "SheetSplitTab",       "ui.tabs.sheet_split_tab",      "sidebar.sheet_tools"),
    (25, "sidebar.layered_form",     "LayeredFormTab",      "ui.tabs.layered_form_tab",     "sidebar.sheet_tools"),
    (26, "sidebar.sampling",         "SamplingTab",         "ui.tabs.sampling_tab",         "sidebar.sampling_tools"),
    (27, "sidebar.dashboard",        "DashboardTab",        "ui.tabs.dashboard_tab",        "sidebar.report"),
    (28, "sidebar.data_tools_tab",   "DataToolsTab",        "ui.tabs.data_tools_tab",       "sidebar.data_tools"),
    (29, "sidebar.smed",             "SMEDTab",             "ui.tabs.smed_tab",             "sidebar.ie_tools"),
    (30, "sidebar.8d",               "EightDTab",           "ui.tabs.eight_d_tab",          "sidebar.engineering_tools"),
    (31, "sidebar.tpm",              "TPMTab",              "ui.tabs.tpm_tab",              "sidebar.ie_tools"),
    (32, "sidebar.ppap",             "PPAPTab",             "ui.tabs.ppap_tab",             "sidebar.engineering_tools"),
    (33, "sidebar.monitor",          "MonitorTab",          "ui.tabs.monitor_tab",          "sidebar.monitoring"),
    (34, "sidebar.multi_plant",      "MultiPlantTab",       "ui.tabs.multi_plant_tab",      "sidebar.monitoring"),
    (35, "sidebar.device",           "DeviceTab",           "ui.tabs.device_tab",           "sidebar.monitoring"),
    (36, "sidebar.time_series",      "TimeSeriesTab",       "ui.tabs.time_series_tab",      "sidebar.quality_tools"),
]

INDEX_MAP = {entry[0]: entry for entry in TAB_REGISTRY}
TAB_COUNT = len(TAB_REGISTRY)

# 命名索引 — 跨 Tab 链路（五链贯通）与程序化跳转统一使用，
# 避免散落各处的魔法数字与对 i18n 文案的隐式依赖
TAB_INDEX = {
    "home": 0,
    "spc": 1,
    "capability": 2,
    "msa": 3,
    "hypothesis": 4,
    "doe": 5,
    "regression": 6,
    "reliability": 13,
    "fishbone": 14,
    "pareto": 15,
    "fmea": 16,
    "control_plan": 17,
    "eight_d": 30,
    "ppap": 32,
}

# 五链贯通涉及的 Tab（FMEA → CP → SPC → PPAP → 8D）
CHAIN_TABS = ("fmea", "control_plan", "spc", "ppap", "eight_d")
