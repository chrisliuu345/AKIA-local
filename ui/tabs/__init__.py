"""QA-Tool 分析 Tab 统一入口"""
from ui.tabs.spc_tab import SPCTab
from ui.tabs.capability_tab import CapabilityTab
from ui.tabs.msa_tab import MSATab
from ui.tabs.hypothesis_tab import HypothesisTab
from ui.tabs.doe_tab import DOETab
from ui.tabs.regression_tab import RegressionTab
from ui.tabs.time_study_tab import TimeStudyTab
from ui.tabs.work_sampling_tab import WorkSamplingTab
from ui.tabs.line_balance_tab import LineBalanceTab
from ui.tabs.oee_tab import OEETab
from ui.tabs.vsm_tab import VSMTab
from ui.tabs.chart_tab import ChartTab
from ui.tabs.reliability_tab import ReliabilityTab
from ui.tabs.fishbone_tab import FishboneTab
from ui.tabs.pareto_tab import ParetoTab
from ui.tabs.fmea_tab import FMEATab
from ui.tabs.control_plan_tab import ControlPlanTab
from ui.tabs.cap_comparison_tab import CapComparisonTab
from ui.tabs.trend_tab import TrendTab
from ui.tabs.summaries_panel_tab import SummaryPanelTab
from ui.tabs.worker_machine_tab import WorkerMachineTab
from ui.tabs.std_work_combo_tab import StdWorkComboTab
from ui.tabs.sheet_merge_tab import SheetMergeTab
from ui.tabs.sheet_split_tab import SheetSplitTab
from ui.tabs.layered_form_tab import LayeredFormTab
from ui.tabs.sampling_tab import SamplingTab
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.data_tools_tab import DataToolsTab
from ui.tabs.smed_tab import SMEDTab
from ui.tabs.eight_d_tab import EightDTab
from ui.tabs.tpm_tab import TPMTab
from ui.tabs.ppap_tab import PPAPTab
from ui.tabs.monitor_tab import MonitorTab
from ui.tabs.multi_plant_tab import MultiPlantTab

__all__ = [
    "SPCTab", "CapabilityTab", "MSATab", "HypothesisTab",
    "DOETab", "RegressionTab",
    "TimeStudyTab", "WorkSamplingTab", "LineBalanceTab",
    "OEETab", "VSMTab", "ChartTab", "ReliabilityTab",
    "FishboneTab", "ParetoTab", "FMEATab", "ControlPlanTab",
    "CapComparisonTab", "TrendTab", "SummaryPanelTab",
    "WorkerMachineTab", "StdWorkComboTab",
    "SheetMergeTab", "SheetSplitTab", "LayeredFormTab",
    "SamplingTab", "DashboardTab", "DataToolsTab",
    "SMEDTab", "EightDTab", "TPMTab", "PPAPTab", "MonitorTab",
    "MultiPlantTab",
]
