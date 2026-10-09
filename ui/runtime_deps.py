"""可选用运行期依赖探测（不 import 重依赖，仅用 importlib.util.find_spec）。

图表链路依赖 matplotlib / seaborn。缺失时主程序仍应正常启动（数据、分析、
案例、证据等核心功能可用），只在打开图表类 Tab 时给出明确安装提示。
"""

from __future__ import annotations

import importlib.util

CHART_DEPENDENCIES = ("matplotlib", "seaborn")
CHART_INSTALL_HINT = "pip install matplotlib seaborn"


def _spec_missing(name: str) -> bool:
    """find_spec 探测；探测本身抛错（父包损坏等）也按缺失处理。"""
    try:
        return importlib.util.find_spec(name) is None
    except (ImportError, ValueError):
        return True


def missing_chart_dependencies() -> list[str]:
    """返回缺失的图表依赖包名（全部可用时为空列表）。"""
    return [name for name in CHART_DEPENDENCIES if _spec_missing(name)]


def broken_chart_dependencies() -> list[str]:
    """find_spec 正常但 import 失败（安装损坏）的图表依赖。

    仅在 Tab 加载失败路径调用，避免启动期真实导入重依赖。
    """
    broken: list[str] = []
    for name in CHART_DEPENDENCIES:
        if _spec_missing(name):
            continue
        try:
            importlib.import_module(name)
        except Exception:  # 安装损坏/ABI 不匹配等一律视为不可用
            broken.append(name)
    return broken


def chart_dependency_hint(missing: list[str] | None = None) -> str:
    """缺失图表依赖时的用户提示；依赖齐全返回空串。"""
    names = missing_chart_dependencies() if missing is None else list(missing)
    if not names:
        return ""
    return (f"缺少图表依赖: {', '.join(names)}\n"
            f"图表类功能不可用；安装后可恢复：\n  {CHART_INSTALL_HINT}")
