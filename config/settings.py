"""
AKIA（AKIM IE/Quality analyzer-local）— 全局配置
"""

import json
import logging
import os
import shutil
import sys

from core.fonts import get_ui_font

APP_NAME = "AKIA"
APP_FULL_NAME = "AKIM IE/Quality analyzer-local"
APP_SLUG = "akia"
APP_VERSION = "4.4.0"
ORGANIZATION = "AKIA"

# 旧品牌标识（仅用于一次性数据迁移，勿在新代码中引用）
LEGACY_APP_NAME = "QA-Tool"
LEGACY_APP_SLUG = "qa-tool"

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

FONT_FAMILY = [get_ui_font(), "Microsoft YaHei", "SimHei", "Noto Sans SC", "WenQuanYi Micro Hei", "sans-serif"]
FONT_SIZE_TITLE = 14
FONT_SIZE_LABEL = 11
FONT_SIZE_TICK = 9

CAPABILITY_GRADES = {
    "A+": (1.67, float("inf"), "特优"),
    "A":  (1.33, 1.67, "优"),
    "B":  (1.00, 1.33, "良好"),
    "C":  (0.67, 1.00, "一般"),
    "D":  (0.00, 0.67, "差"),
}

SUPPORTED_EXCEL_EXTENSIONS = (".xlsx", ".xls", ".xlsm")
SUPPORTED_TEMPLATE_EXTENSIONS = (".xlsx", ".json")
MAX_PREVIEW_ROWS = 100
CHUNK_SIZE = 10000

MSA_NDC_THRESHOLD = 5
MSA_GRR_ACCEPTABLE = 0.10
MSA_GRR_MARGINAL = 0.30
MSA_GRR_UNACCEPTABLE = 0.30

MSA_D2_STAR = {
    2:  1.41,
    3:  1.91,
    4:  2.24,
    5:  2.48,
    6:  2.67,
    7:  2.83,
    8:  2.96,
    9:  3.08,
    10: 3.18,
    11: 3.27,
    12: 3.35,
    13: 3.42,
    14: 3.49,
    15: 3.55,
    16: 3.61,
    17: 3.66,
    18: 3.71,
    19: 3.76,
    20: 3.80,
    21: 3.84,
    22: 3.88,
    23: 3.92,
    24: 3.95,
    25: 3.99,
}

OEE_WORLD_CLASS = 0.85
OEE_GOOD = 0.65
OEE_FAIR = 0.40

RPN_CRITICAL = 200
RPN_HIGH = 100
RPN_MEDIUM = 50

SIGNIFICANCE_LEVEL = 0.05

ROOT_CAUSE_W_IMPORTANCE = 0.4
ROOT_CAUSE_W_CORRELATION = 0.3
ROOT_CAUSE_W_LINKAGE = 0.3

FRACTIONAL_FRACTIONS = ["1/2", "1/4", "1/8"]
FRACTIONAL_MAX_K = 15
FRACTIONAL_MAX_P = 5

RESOLUTION_DESCRIPTIONS = {
    3: "Resolution III: main effects aliased with 2FI",
    4: "Resolution IV: main effects clear, 2FI aliased with 2FI",
    5: "Resolution V: main effects and 2FI clear",
    6: "Resolution VI: 2FI clear of 3FI",
}

_MIN_ABERRATION_TABLE = {
    (3, 1): {"generators": ["AB"], "resolution": 3, "defining_relation": "I=ABC"},
    (4, 1): {"generators": ["ABC"], "resolution": 4, "defining_relation": "I=ABCD"},
    (4, 2): {"generators": ["AB", "AC"], "resolution": 3, "defining_relation": "I=ABC=ABD=BCD"},
    (5, 1): {"generators": ["ABCD"], "resolution": 5, "defining_relation": "I=ABCDE"},
    (5, 2): {"generators": ["AB", "AC"], "resolution": 3, "defining_relation": "I=ABD=ACE=BCDE"},
    (6, 1): {"generators": ["ABCDE"], "resolution": 6, "defining_relation": "I=ABCDEF"},
    (6, 2): {"generators": ["ABC", "ADE"], "resolution": 4, "defining_relation": "I=ABCE=ADEF=BCDF"},
    (6, 3): {"generators": ["AB", "AC", "BC"], "resolution": 3, "defining_relation": "I=ABD=ACE=BCF=ABCDEF"},
    (7, 2): {"generators": ["ABCDE", "ABCDG"], "resolution": 5, "defining_relation": "I=ABCDE=ABCDG=DEFG"},
    (7, 3): {"generators": ["ABC", "ABD", "ACD"], "resolution": 4, "defining_relation": "I=ABCE=ABDF=ACDG"},
    (7, 4): {"generators": ["AB", "AC", "AD", "AE"], "resolution": 3, "defining_relation": "I=ABD=ACE=BCF"},
    (8, 3): {"generators": ["ABCD", "ABCE", "ABDE"], "resolution": 4, "defining_relation": "I=ABCD=ABCE=ABDE"},
    (8, 4): {"generators": ["AB", "AC", "AD", "AE"], "resolution": 3, "defining_relation": "I=ABD=ACE=BCF"},
}

MIXTURE_DESIGN_TYPES = ["simplex_lattice", "simplex_centroid", "extreme_vertices"]
MIXTURE_MODELS = ["linear", "quadratic", "special_cubic"]
MIXTURE_MAX_COMPONENTS = 10


_CONFIG_DIR = os.path.dirname(__file__)
# 随安装包分发的公共默认值（无 secrets / 无本机设备列表）
_DEFAULT_CONFIG_PATH = os.path.join(_CONFIG_DIR, "..", "user_config.default.json")


def _default_user_config_path() -> str:
    """用户本机配置路径（不入库、不打包）。

    - 源码运行: 仓库根 ``user_config.json``（保持既有行为与测试隔离方式）
    - 打包运行: 平台用户目录 —— AppImage 只读挂载 / Program Files 无写权限，
      安装目录不可写，必须落到用户可写位置
    - ``AKIA_USER_CONFIG`` 环境变量优先（便携版/多实例），
      旧 ``QA_TOOL_USER_CONFIG`` 作为回退继续生效
    """
    override = (os.environ.get("AKIA_USER_CONFIG")
                or os.environ.get("QA_TOOL_USER_CONFIG"))
    if override:
        return override
    if not getattr(sys, "frozen", False):
        return os.path.abspath(os.path.join(_CONFIG_DIR, "..", "user_config.json"))
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME, "user_config.json")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_NAME, "user_config.json")


_USER_CONFIG_PATH = _default_user_config_path()


def _migrate_legacy_user_config(target: str) -> None:
    """打包版首次启动时，把旧版（QA-Tool）用户配置迁移到 AKIA 目录。

    迁移源按优先级:
      1. 旧版安装目录内的 user_config.json
      2. 旧品牌平台目录 ``~/.config/QA-Tool`` / ``%APPDATA%\\QA-Tool``
    """
    if os.path.exists(target):
        return
    legacy_candidates = [
        os.path.abspath(os.path.join(_CONFIG_DIR, "..", "user_config.json")),
    ]
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
            os.path.expanduser("~"), ".config")
    legacy_candidates.append(os.path.join(base, LEGACY_APP_NAME, "user_config.json"))

    for legacy in legacy_candidates:
        if os.path.abspath(target) == legacy or not os.path.exists(legacy):
            continue
        try:
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.copy2(legacy, target)
            logging.getLogger(f"{APP_NAME}.Settings").info(
                "已把旧版用户配置迁移到 %s（源: %s）", target, legacy)
        except OSError as e:  # 迁移失败不影响启动，但用户会丢旧配置，必须留痕
            logging.getLogger(f"{APP_NAME}.Settings").warning(
                "旧版 user_config.json 迁移失败（%s → %s）: %s", legacy, target, e)
        return

_defaults = {}
_user_overrides = {}

# 敏感键后缀 — 保存时自动改存 <key>_enc（DPAPI / keyring 加密）
_SECRET_SUFFIXES = ("_password", "_secret", "_token", "_api_key")


def is_secret_key(key: str) -> bool:
    """键名是否为敏感配置（密码/密钥/令牌）"""
    k = str(key).lower()
    return any(k.endswith(suffix) for suffix in _SECRET_SUFFIXES)


def _read_json(path: str) -> dict:
    """读取 JSON 配置，失败返回空 dict（损坏文件不阻塞启动）"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_config() -> dict:
    """加载配置：默认文件 + 用户文件叠加，并同步全局变量"""
    global _defaults, _user_overrides
    global CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_GRR_MARGINAL, MSA_NDC_THRESHOLD
    if getattr(sys, "frozen", False):
        # 仅打包版需要迁移（源码运行时 legacy 路径本身就是用户配置路径）
        _migrate_legacy_user_config(_USER_CONFIG_PATH)
    _defaults = _read_json(_DEFAULT_CONFIG_PATH)
    _user_overrides = _read_json(_USER_CONFIG_PATH)
    merged = {**_defaults, **_user_overrides}
    if "chart_dpi" in merged:
        CHART_DPI = merged["chart_dpi"]
    if "msa_grr_acceptable" in merged:
        MSA_GRR_ACCEPTABLE = merged["msa_grr_acceptable"]
        MSA_GRR_MARGINAL = max(merged["msa_grr_acceptable"], MSA_GRR_MARGINAL)
    if "msa_ndc_threshold" in merged:
        MSA_NDC_THRESHOLD = merged["msa_ndc_threshold"]
    return dict(merged)


def save_config(values: dict) -> None:
    """保存用户配置到本机 JSON 文件（敏感键自动加密为 <key>_enc）。

    值为 None 表示**删除该键**（连同 `<key>_enc`）——用于"清除 API Key"等场景，
    避免旧的加密值残留导致 get_secret 仍能读回已清除的密钥。
    """
    global CHART_DPI, MSA_GRR_ACCEPTABLE, MSA_GRR_MARGINAL, MSA_NDC_THRESHOLD
    removals = [k for k, v in values.items() if v is None]
    for key in removals:
        _user_overrides.pop(key, None)
        _user_overrides.pop(f"{key}_enc", None)
    protected = _protect_secrets({k: v for k, v in values.items() if v is not None})
    _user_overrides.update(protected)
    # 迁移清理：加密成功后移除旧版明文键，避免同一密钥以两种形态共存
    for key in values:
        if is_secret_key(key) and (f"{key}_enc" in protected or key in removals):
            _user_overrides.pop(key, None)
    if "chart_dpi" in values:
        CHART_DPI = values["chart_dpi"]
    if "msa_grr_acceptable" in values:
        MSA_GRR_ACCEPTABLE = values["msa_grr_acceptable"]
        MSA_GRR_MARGINAL = max(values["msa_grr_acceptable"], MSA_GRR_MARGINAL)
    if "msa_ndc_threshold" in values:
        MSA_NDC_THRESHOLD = values["msa_ndc_threshold"]
    parent = os.path.dirname(_USER_CONFIG_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_user_overrides, f, indent=2, ensure_ascii=False)


def _protect_secrets(values: dict) -> dict:
    """敏感明文 → 加密存储（<key>_enc）。加密不可用时保留明文并告警，
    避免用户配置被静默丢弃。"""
    out = {}
    for key, value in values.items():
        if is_secret_key(key) and isinstance(value, str) and value:
            try:
                from core.secret_store import encrypt_secret
                encrypted = encrypt_secret(value)
                if encrypted:
                    out[f"{key}_enc"] = encrypted
                    continue
            except Exception as e:  # noqa: BLE001 - 加密失败：告警后退回明文保存（不阻断）
                logging.getLogger("AKIA.Settings").warning(
                    "敏感配置 %s 加密失败，按明文保存: %s", key, e)
        out[key] = value
    return out


def get_setting(key: str, default=None):
    """读取设置：用户配置 → 随包默认值 → 调用方默认值"""
    if key in _user_overrides:
        return _user_overrides[key]
    return _defaults.get(key, default)


def get_effective(key: str, module_default):
    """获取最终生效值（用户配置 → 随包默认 → 模块默认）"""
    if key in _user_overrides:
        return _user_overrides[key]
    return _defaults.get(key, module_default)


def get_secret(key: str, default: str = "") -> str:
    """读取敏感配置：优先解密 <key>_enc，回退旧版明文（向后兼容）"""
    encrypted = _user_overrides.get(f"{key}_enc") or _defaults.get(f"{key}_enc")
    if encrypted:
        try:
            from core.secret_store import decrypt_secret
            value = decrypt_secret(encrypted)
            if value:
                return value
        except Exception:  # noqa: BLE001 - 加密失败：告警后退回明文保存（不阻断）
            pass
    return get_setting(key, default)


ESP32_DEVICE_TAB_INDEX = 35


def esp32_extension_enabled() -> bool:
    """ESP-32 硬件拓展是否启用（默认启用，可由 user_config.json 的 esp32_extension 关闭）"""
    return bool(get_setting("esp32_extension", True))


def tab_allowed(idx: int) -> bool:
    """Tab 是否允许加载 — 用于安装器可选组件门控"""
    if idx == ESP32_DEVICE_TAB_INDEX:
        return esp32_extension_enabled()
    return True


DEPARTMENTS = ['质量部', '生产部', 'IE部', '研发部', '供应链', '其他']
TEAMS = ['一组', '二组', '三组', '白班', '夜班', 'A班', 'B班', 'C班']


load_config()
