"""主窗口与拆出模块共用的页签范围和安装路径。

这些值原先写在 ``ui/main_window.py`` 模块顶层。拆分后仍从这里取值，
避免各模块互相导入。
"""

from __future__ import annotations

import os

from ui._tab_registry import CHAIN_TABS, INDEX_MAP, TAB_INDEX

_PLUGIN_TAB_START = max(INDEX_MAP.keys()) + 1

#: 五链贯通涉及的 Tab 索引（FMEA → CP → SPC → PPAP → 8D），需要注入项目上下文
_CONTEXT_TAB_INDICES = {TAB_INDEX[key] for key in (
    *CHAIN_TABS, "capability", "time_study", "std_work_combo")}

#: IE 工具 Tab — 工作表导入时分发跳过（IE 数据走「导入 IE 数据」）
_IE_TAB_INDICES = frozenset({7, 8, 9, 10, 11, 21, 22})
#: 消费 IE 数据对象（TimeObservation/Process/Resource/MaterialFlow）的 Tab
_IE_IMPORT_TAB_INDICES = frozenset({7, 9, 10, 11})

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_path(*parts: str) -> str:
    """安装根目录下的路径。本文件位于 ``ui/``，根目录是其上一级。"""
    return os.path.join(_PROJECT_DIR, *parts)
