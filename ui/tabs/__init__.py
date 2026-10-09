"""AKIA 分析 Tab 统一入口（惰性导出）。

Python 在导入 ``ui.tabs.<模块>`` 前会先执行本包 ``__init__``。此前这里在包
初始化时一次性 import 全部 34 个 Tab 模块，等于绕过了主窗口的按需懒加载：
任意一个 Tab 的首次打开都会连带加载 spc_tab / chart_tab 等图表依赖模块，
在缺少 matplotlib 的环境里直接导致所有 Tab 加载失败。

现在改为 PEP 562 惰性导出：``from ui.tabs import SPCTab`` 仍可用，但只有真正
访问该名字时才导入对应子模块，``import ui.tabs.fmea_tab`` 这样的子模块导入
也不再触发其余 Tab 的连带加载。
"""

from __future__ import annotations

import importlib

#: 导出名 -> 子模块路径
_EXPORTS: dict[str, str] = {
    "SPCTab": "ui.tabs.spc_tab",
    "CapabilityTab": "ui.tabs.capability_tab",
    "MSATab": "ui.tabs.msa_tab",
    "HypothesisTab": "ui.tabs.hypothesis_tab",
    "DOETab": "ui.tabs.doe_tab",
    "RegressionTab": "ui.tabs.regression_tab",
    "TimeStudyTab": "ui.tabs.time_study_tab",
    "WorkSamplingTab": "ui.tabs.work_sampling_tab",
    "LineBalanceTab": "ui.tabs.line_balance_tab",
    "OEETab": "ui.tabs.oee_tab",
    "VSMTab": "ui.tabs.vsm_tab",
    "ChartTab": "ui.tabs.chart_tab",
    "ReliabilityTab": "ui.tabs.reliability_tab",
    "FishboneTab": "ui.tabs.fishbone_tab",
    "ParetoTab": "ui.tabs.pareto_tab",
    "FMEATab": "ui.tabs.fmea_tab",
    "ControlPlanTab": "ui.tabs.control_plan_tab",
    "CapComparisonTab": "ui.tabs.cap_comparison_tab",
    "TrendTab": "ui.tabs.trend_tab",
    "SummaryPanelTab": "ui.tabs.summaries_panel_tab",
    "WorkerMachineTab": "ui.tabs.worker_machine_tab",
    "StdWorkComboTab": "ui.tabs.std_work_combo_tab",
    "SheetMergeTab": "ui.tabs.sheet_merge_tab",
    "SheetSplitTab": "ui.tabs.sheet_split_tab",
    "LayeredFormTab": "ui.tabs.layered_form_tab",
    "SamplingTab": "ui.tabs.sampling_tab",
    "DashboardTab": "ui.tabs.dashboard_tab",
    "DataToolsTab": "ui.tabs.data_tools_tab",
    "SMEDTab": "ui.tabs.smed_tab",
    "EightDTab": "ui.tabs.eight_d_tab",
    "TPMTab": "ui.tabs.tpm_tab",
    "PPAPTab": "ui.tabs.ppap_tab",
    "MonitorTab": "ui.tabs.monitor_tab",
    "MultiPlantTab": "ui.tabs.multi_plant_tab",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value  # 缓存，后续访问不再走 __getattr__
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
