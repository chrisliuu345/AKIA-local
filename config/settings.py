"""
IE Quality Analyzer - 全局配置
"""

import json
import os

# ── 应用信息 ──────────────────────────────────────────
APP_NAME = "QA-Tool"
APP_VERSION = "2.8.0"
ORGANIZATION = "QA-Tool"

# ── 统计常量 ──────────────────────────────────────────
NELSON_RULES = {
    1: "一点超出3σ控制限",
    2: "连续9点在中心线同一侧",
    3: "连续6点递增或递减",
    4: "连续14点交替上下",
    5: "连续3点中有2点超出2σ",
    6: "连续5点中有4点超出1σ",
    7: "连续15点在中心线±1σ内",
    8: "连续8点在中心线±1σ外（两侧）",
}

WECO_RULES_DESC = {
    1: "一点超出3σ控制限",
    2: "连续2/3点超出2σ（同侧）",
    3: "连续4/5点超出1σ（同侧）",
    4: "连续8点在中心线同侧",
}

# 控制图常数 (子组大小 n=2~25)
# A2, D3, D4 用于 XBar-R; A3, B3, B4 用于 XBar-S; d2, c4 用于能力分析
CONTROL_CHART_CONSTANTS = {
    2:  {"A2": 1.880, "D3": 0.000, "D4": 3.267, "A3": 2.659, "B3": 0.000, "B4": 3.267, "d2": 1.128, "c4": 0.7979},
    3:  {"A2": 1.023, "D3": 0.000, "D4": 2.574, "A3": 1.954, "B3": 0.000, "B4": 2.568, "d2": 1.693, "c4": 0.8862},
    4:  {"A2": 0.729, "D3": 0.000, "D4": 2.282, "A3": 1.628, "B3": 0.000, "B4": 2.266, "d2": 2.059, "c4": 0.9213},
    5:  {"A2": 0.577, "D3": 0.000, "D4": 2.114, "A3": 1.427, "B3": 0.000, "B4": 2.089, "d2": 2.326, "c4": 0.9400},
    6:  {"A2": 0.483, "D3": 0.000, "D4": 2.004, "A3": 1.287, "B3": 0.030, "B4": 1.970, "d2": 2.534, "c4": 0.9515},
    7:  {"A2": 0.419, "D3": 0.076, "D4": 1.924, "A3": 1.182, "B3": 0.118, "B4": 1.882, "d2": 2.704, "c4": 0.9594},
    8:  {"A2": 0.373, "D3": 0.136, "D4": 1.864, "A3": 1.099, "B3": 0.185, "B4": 1.815, "d2": 2.847, "c4": 0.9650},
    9:  {"A2": 0.337, "D3": 0.184, "D4": 1.816, "A3": 1.032, "B3": 0.239, "B4": 1.761, "d2": 2.970, "c4": 0.9693},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "A3": 0.975, "B3": 0.284, "B4": 1.716, "d2": 3.078, "c4": 0.9727},
    11: {"A2": 0.285, "D3": 0.256, "D4": 1.744, "A3": 0.927, "B3": 0.321, "B4": 1.679, "d2": 3.173, "c4": 0.9754},
    12: {"A2": 0.266, "D3": 0.283, "D4": 1.717, "A3": 0.886, "B3": 0.354, "B4": 1.646, "d2": 3.258, "c4": 0.9776},
    13: {"A2": 0.249, "D3": 0.307, "D4": 1.693, "A3": 0.850, "B3": 0.382, "B4": 1.618, "d2": 3.336, "c4": 0.9794},
    14: {"A2": 0.235, "D3": 0.328, "D4": 1.672, "A3": 0.817, "B3": 0.406, "B4": 1.594, "d2": 3.407, "c4": 0.9810},
    15: {"A2": 0.223, "D3": 0.347, "D4": 1.653, "A3": 0.789, "B3": 0.428, "B4": 1.572, "d2": 3.472, "c4": 0.9823},
    16: {"A2": 0.212, "D3": 0.363, "D4": 1.637, "A3": 0.763, "B3": 0.448, "B4": 1.552, "d2": 3.532, "c4": 0.9835},
    17: {"A2": 0.203, "D3": 0.378, "D4": 1.622, "A3": 0.739, "B3": 0.466, "B4": 1.534, "d2": 3.588, "c4": 0.9845},
    18: {"A2": 0.194, "D3": 0.391, "D4": 1.608, "A3": 0.718, "B3": 0.482, "B4": 1.518, "d2": 3.640, "c4": 0.9854},
    19: {"A2": 0.187, "D3": 0.403, "D4": 1.597, "A3": 0.698, "B3": 0.497, "B4": 1.503, "d2": 3.689, "c4": 0.9862},
    20: {"A2": 0.180, "D3": 0.415, "D4": 1.585, "A3": 0.680, "B3": 0.510, "B4": 1.490, "d2": 3.735, "c4": 0.9869},
    21: {"A2": 0.173, "D3": 0.425, "D4": 1.575, "A3": 0.663, "B3": 0.523, "B4": 1.477, "d2": 3.778, "c4": 0.9876},
    22: {"A2": 0.167, "D3": 0.434, "D4": 1.566, "A3": 0.647, "B3": 0.534, "B4": 1.466, "d2": 3.819, "c4": 0.9882},
    23: {"A2": 0.162, "D3": 0.443, "D4": 1.557, "A3": 0.633, "B3": 0.545, "B4": 1.455, "d2": 3.858, "c4": 0.9887},
    24: {"A2": 0.157, "D3": 0.451, "D4": 1.548, "A3": 0.619, "B3": 0.555, "B4": 1.445, "d2": 3.895, "c4": 0.9892},
    25: {"A2": 0.153, "D3": 0.459, "D4": 1.541, "A3": 0.606, "B3": 0.565, "B4": 1.435, "d2": 3.931, "c4": 0.9896},
}

# ── 图表样式 ──────────────────────────────────────────
CHART_COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "warning": "#d62728",
    "ucl_lcl": "#d62728",
    "center_line": "#2ca02c",
    "data_points": "#1f77b4",
    "violation": "#d62728",
    "grid": "#e0e0e0",
    "background": "#ffffff",
}

CHART_DPI = 120
CHART_FIGSIZE = (10, 6)

# ── 中文支持 ──────────────────────────────────────────
FONT_FAMILY = ["Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei", "sans-serif"]
FONT_SIZE_TITLE = 14
FONT_SIZE_LABEL = 11
FONT_SIZE_TICK = 9

# ── 过程能力分级 ──────────────────────────────────────
CAPABILITY_GRADES = {
    "A+": (1.67, float("inf"), "特优"),
    "A":  (1.33, 1.67, "优"),
    "B":  (1.00, 1.33, "良好"),
    "C":  (0.67, 1.00, "一般"),
    "D":  (0.00, 0.67, "差"),
}

# ── 文件配置 ──────────────────────────────────────────
SUPPORTED_EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm")
SUPPORTED_TEMPLATE_EXTENSIONS = (".xlsx", ".json")
MAX_PREVIEW_ROWS = 100
CHUNK_SIZE = 10000  # 大文件分块读取大小

# ── MSA 判定标准 ──────────────────────────────────────
MSA_NDC_THRESHOLD = 5
MSA_GRR_ACCEPTABLE = 0.10   # %GRR < 10% 可接受
MSA_GRR_MARGINAL = 0.30     # %GRR 10%~30% 条件接受
MSA_GRR_UNACCEPTABLE = 0.30 # %GRR > 30% 不可接受

# ── MSA d2* 因子表 (AIAG MSA Manual, d2* = 1/d2 for AV/PV) ──
# AV 用 K2 倒数, PV 用 K3 倒数; n=2~25
# 参考: AIAG MSA 4th Edition, Table 2
MSA_D2_STAR = {
    2:  1.41,   # K2=0.7086 → d2*=1.41
    3:  1.91,   # K2=0.5231 → d2*=1.91
    4:  2.24,   # K2=0.4467 → d2*=2.24
    5:  2.48,   # K2=0.4030 → d2*=2.48
    6:  2.67,   # K2=0.3746 → d2*=2.67
    7:  2.83,   # K2=0.3534 → d2*=2.83
    8:  2.96,   # K2=0.3375 → d2*=2.96
    9:  3.08,   # K2=0.3249 → d2*=3.08
    10: 3.18,   # K2=0.3146 → d2*=3.18
    11: 3.27,   # K2=0.3060 → d2*=3.27
    12: 3.35,   # K2=0.2987 → d2*=3.35
    13: 3.42,   # K2=0.2924 → d2*=3.42
    14: 3.49,   # K2=0.2868 → d2*=3.49
    15: 3.55,   # K2=0.2820 → d2*=3.55
    16: 3.61,   # K2=0.2776 → d2*=3.61
    17: 3.66,   # K2=0.2738 → d2*=3.66
    18: 3.71,   # K2=0.2703 → d2*=3.71
    19: 3.76,   # K2=0.2671 → d2*=3.76
    20: 3.80,   # K2=0.2643 → d2*=3.80
    21: 3.84,   # K2=0.2618 → d2*=3.84
    22: 3.88,   # K2=0.2594 → d2*=3.88
    23: 3.92,   # K2=0.2573 → d2*=3.92
    24: 3.95,   # K2=0.2553 → d2*=3.95
    25: 3.99,   # K2=0.2535 → d2*=3.99
}

# ── OEE 分级阈值 ──────────────────────────────────────
OEE_WORLD_CLASS = 0.85
OEE_GOOD = 0.65
OEE_FAIR = 0.40

# ── FMEA RPN 阈值 ──────────────────────────────────────
RPN_CRITICAL = 200   # RPN >= 200: 停线整改
RPN_HIGH = 100       # RPN >= 100: 高风险，需生成控制计划
RPN_MEDIUM = 50      # RPN >= 50: 中等风险

# ── 统计显著性 ──────────────────────────────────────────
SIGNIFICANCE_LEVEL = 0.05

# ── 根因分析权重 (SHAP三路融合) ────────────────────────
ROOT_CAUSE_W_IMPORTANCE = 0.4
ROOT_CAUSE_W_CORRELATION = 0.3
ROOT_CAUSE_W_LINKAGE = 0.3

# ── 用户配置持久化 ────────────────────────────────────
_USER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "user_config.json")

_user_overrides = {}



def load_config() -> dict:
    """加载用户配置，返回可合并的 dict，并同步全局变量"""
    global _user_overrides, CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_GRR_MARGINAL, MSA_NDC_THRESHOLD
    if os.path.exists(_USER_CONFIG_PATH):
        try:
            with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                _user_overrides = json.load(f)
        except Exception:
            _user_overrides = {}
    if "chart_dpi" in _user_overrides:
        CHART_DPI = _user_overrides["chart_dpi"]
    if "msa_grr_acceptable" in _user_overrides:
        MSA_GRR_ACCEPTABLE = _user_overrides["msa_grr_acceptable"]
        MSA_GRR_MARGINAL = max(_user_overrides["msa_grr_acceptable"], MSA_GRR_MARGINAL)
    if "msa_ndc_threshold" in _user_overrides:
        MSA_NDC_THRESHOLD = _user_overrides["msa_ndc_threshold"]
    return dict(_user_overrides)


def save_config(values: dict) -> None:
    """保存用户配置到 JSON 文件"""
    global _user_overrides, CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_GRR_MARGINAL, MSA_NDC_THRESHOLD
    _user_overrides.update(values)
    if "chart_dpi" in values:
        CHART_DPI = values["chart_dpi"]
    if "msa_grr_acceptable" in values:
        MSA_GRR_ACCEPTABLE = values["msa_grr_acceptable"]
        MSA_GRR_MARGINAL = max(values["msa_grr_acceptable"], MSA_GRR_MARGINAL)
    if "msa_ndc_threshold" in values:
        MSA_NDC_THRESHOLD = values["msa_ndc_threshold"]
    with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_user_overrides, f, indent=2, ensure_ascii=False)


def get_setting(key: str, default=None):
    """读取设置，优先用户配置，回退到默认值"""
    return _user_overrides.get(key, default)


def get_effective(key: str, module_default):
    """获取最终生效值（用户配置覆盖模块默认）"""
    return _user_overrides.get(key, module_default)


# ── ESP-32 硬件拓展安装门控 ────────────────────────────
ESP32_DEVICE_TAB_INDEX = 35


def esp32_extension_enabled() -> bool:
    """ESP-32 硬件拓展是否启用（默认启用，可由 user_config.json 的 esp32_extension 关闭）"""
    return bool(_user_overrides.get("esp32_extension", True))


def tab_allowed(idx: int) -> bool:
    """Tab 是否允许加载 — 用于安装器可选组件门控"""
    if idx == ESP32_DEVICE_TAB_INDEX:
        return esp32_extension_enabled()
    return True


# --- org constants ---
DEPARTMENTS = ['质量部', '生产部', 'IE部', '研发部', '供应链', '其他']
TEAMS = ['一组', '二组', '三组', '白班', '夜班', 'A班', 'B班', 'C班']


load_config()
