"""兼容转发 — 字体解析已下沉至 core/fonts.py（v3.7.1）

保留本模块避免既有 UI 代码大面积改 import；新代码请直接使用 core.fonts。
"""

from core.fonts import (  # noqa: F401
    get_ui_font,
    get_mono_font,
    get_pdf_font_paths,
    get_pdf_font_candidates,
)

__all__ = [
    "get_ui_font",
    "get_mono_font",
    "get_pdf_font_paths",
    "get_pdf_font_candidates",
]
