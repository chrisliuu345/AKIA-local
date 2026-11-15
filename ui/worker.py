"""把耗时计算移出界面线程，完成后再回到界面线程。

``run_in_worker`` 在后台线程执行函数。调用方停在一个局部事件循环里，
所以窗口仍能重绘，但函数本身不在界面线程上跑。函数返回后，调用才返回，
因此现有「调用结束即完成」的用法保持不变。

后台函数不得读写 Qt 控件。控件取值要在调用前完成，结果刷新要在返回后进行。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QEventLoop, QObject, Qt, QThread, Signal
from PySide6.QtWidgets import QApplication


class _FnWorker(QThread):
    done = Signal(object)
    failed = Signal(object)

    def __init__(self, fn: Callable[..., Any], args: tuple, kwargs: dict):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            self.done.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:
            self.failed.emit(exc)


class _Bridge(QObject):
    def __init__(self, loop: QEventLoop, holder: dict):
        super().__init__()
        self._loop = loop
        self._holder = holder

    def ok(self, value: object) -> None:
        self._holder["value"] = value
        self._loop.quit()

    def bad(self, exc: object) -> None:
        self._holder["error"] = exc
        self._loop.quit()


def run_in_worker(owner: QObject, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    """在后台线程执行 ``fn`` 并返回其结果。异常在调用方线程重新抛出。"""
    app = QApplication.instance()
    if app is not None and QThread.currentThread() is not app.thread():
        return fn(*args, **kwargs)

    holder: dict[str, Any] = {}
    loop = QEventLoop()
    bridge = _Bridge(loop, holder)
    worker = _FnWorker(fn, args, kwargs)
    worker.done.connect(bridge.ok, Qt.ConnectionType.QueuedConnection)
    worker.failed.connect(bridge.bad, Qt.ConnectionType.QueuedConnection)
    worker.start()
    loop.exec()
    worker.wait()
    worker.deleteLater()
    bridge.deleteLater()
    if app is not None:
        app.processEvents()
    if "error" in holder:
        raise holder["error"]
    return holder.get("value")
