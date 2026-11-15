"""各分析页共用的「校验 → 后台计算 → 展示」入口。

页签在界面线程读取控件，并返回一个零参数计算函数。计算本身经
``run_in_worker`` 离开界面线程。成功后刷新结果，并发出 ``analysis_completed``。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.i18n import i18n
from ui.worker import run_in_worker

_ERROR_STYLE = "color: #E00000; "


def _show_error(tab, text: str) -> None:
    tab._clear_canvas()
    tab.result_text.setStyleSheet(_ERROR_STYLE)
    tab.result_text.setText(text)


def present_analysis(
    tab,
    prepare: Callable[[], Callable[..., Any]],
    *,
    on_invalid: Callable[[str], str] | None = None,
    on_failed: Callable[[BaseException], str] | None = None,
    finish: Callable[[Any], Any] | None = None,
) -> Any:
    """校验参数、后台执行 ``prepare()`` 返回的函数，再展示结果。

    ``prepare`` 在界面线程调用，只读取控件并返回后台函数。
    ``finish`` 在界面线程接收后台结果；返回 ``None`` 表示失败已经在页签内处理。
    未提供 ``finish`` 时，后台返回值会写入 ``current_result`` 并直接展示。
    """
    valid, msg = tab.validate_params()
    if not valid:
        text = on_invalid(msg) if on_invalid else f"▎{i18n.tr('val.param_failed')}\n{msg}"
        _show_error(tab, text)
        return None
    tab.result_text.setStyleSheet("")
    try:
        produced = run_in_worker(tab, prepare())
    except Exception as exc:
        # 引擎失败留在结果区，避免打断已经打开的分析页。
        text = on_failed(exc) if on_failed else f"▎{i18n.tr('val.analysis_failed')}\n{exc!s}"
        _show_error(tab, text)
        return None
    if finish is None:
        tab.current_result = produced
        shown = produced
    else:
        shown = finish(produced)
        if shown is None:
            return None
    tab.display_result(shown)
    tab.analysis_completed.emit()
    return shown
