"""平台感知的 CJK 字体解析 — 单一数据源（core 层，无 Qt 依赖）

Windows: Microsoft YaHei → SimHei
macOS:   PingFang SC → Heiti SC
Linux:   Noto Sans CJK SC → WenQuanYi Micro Hei → Source Han Sans SC

v3.7.1 由 ui/font_config.py 下沉至此：config/core/output 层原先反向依赖 ui，
破坏了分层；ui/font_config.py 保留为兼容转发模块。
"""

import sys
import subprocess
import logging
from functools import lru_cache

logger = logging.getLogger("QA-Tool.FontConfig")


@lru_cache(maxsize=1)
def get_ui_font() -> str:
    """返回 UI 主字体（Qt 字体族名称）"""
    if sys.platform == "win32":
        return "Microsoft YaHei"
    elif sys.platform == "darwin":
        return "PingFang SC"
    else:
        return _detect_linux_ui_font()


@lru_cache(maxsize=1)
def get_mono_font() -> str:
    """返回等宽字体名称"""
    if sys.platform == "win32":
        return "Consolas"
    elif sys.platform == "darwin":
        return "Menlo"
    else:
        return "DejaVu Sans Mono"


def _detect_linux_ui_font() -> str:
    """通过 fc-list 检测 Linux 上已安装的最佳 CJK 字体"""
    candidates = [
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Source Han Sans SC",
        "AR PL UMing CN",
        "Droid Sans Fallback",
    ]
    try:
        result = subprocess.run(
            ["fc-list", ":lang=zh", "-f", "%{family}\n"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            installed = result.stdout.lower()
            for font in candidates:
                if font.lower() in installed:
                    logger.debug(f"Linux CJK font detected: {font}")
                    return font
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("fc-list not available, using fallback")
    return "sans-serif"


def get_pdf_font_paths() -> list:
    """返回 PDF 导出的 CJK 字体搜索路径（按优先级排序）"""
    if sys.platform == "win32":
        return ["C:/Windows/Fonts"]
    elif sys.platform == "darwin":
        return [
            "/Library/Fonts/",
            "/System/Library/Fonts/",
            "/usr/local/share/fonts/",
        ]
    else:
        return [
            "/usr/share/fonts/truetype/noto/",
            "/usr/share/fonts/opentype/noto/",
            "/usr/share/fonts/truetype/wqy/",
            "/usr/share/fonts/truetype/",
            "/usr/share/fonts/",
            "/usr/local/share/fonts/",
            "/usr/local/share/fonts/truetype/",
        ]


def get_pdf_font_candidates() -> list:
    """返回 PDF 导出的 CJK 字体文件候选列表（按优先级排序）"""
    if sys.platform == "win32":
        return [
            "msyh.ttc",
            "msyhbd.ttf",
            "simhei.ttf",
            "simsun.ttc",
            "NotoSansSC-Regular.ttf",
            "NotoSansSC-VF.ttf",
        ]
    elif sys.platform == "darwin":
        return [
            "PingFang.ttc",
            "STHeiti Medium.ttc",
            "Hiragino Sans GB.ttc",
            "NotoSansSC-Regular.otf",
        ]
    else:
        return [
            "NotoSansCJK-Regular.ttc",
            "NotoSansSC-Regular.otf",
            "NotoSansSC-Regular.ttf",
            "wqy-microhei.ttc",
            "wqy-zenhei.ttc",
            "NotoSansCJKsc-Regular.otf",
            "SourceHanSansSC-Regular.otf",
        ]
