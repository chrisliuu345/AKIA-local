"""实时数据流总线 — 发布/订阅，内存环形缓冲。

单进程内的线程安全总线：采集线程 publish，图表/服务 subscriber 收回调，
`recent()` 供新订阅方拿最近窗口（回填补齐）。
"""
import threading
from collections import deque
from collections.abc import Callable

from core.devices.driver import Sample


class StreamBus:
    def __init__(self, maxlen: int = 5000):
        self._maxlen = maxlen
        self._buf: dict[str, deque[Sample]] = {}
        self._subs: dict[str, list[Callable[[list[Sample]], None]]] = {}
        self._wild: list[Callable[[list[Sample]], None]] = []
        self._lock = threading.Lock()

    def publish(self, topic: str, samples: list[Sample]) -> None:
        with self._lock:
            buf = self._buf.setdefault(topic, deque(maxlen=self._maxlen))
            buf.extend(samples)
            subs = list(self._subs.get(topic, ())) + self._wild
        for cb in subs:
            try:
                cb(samples)
            except Exception:
                pass

    def subscribe(self, topic: str | None, callback: Callable[[list[Sample]], None]) -> Callable[[], bool]:
        """返回 unsubscribe 函数。topic=None 表示订阅全部主题。"""
        with self._lock:
            if topic is None:
                self._wild.append(callback)
            else:
                self._subs.setdefault(topic, []).append(callback)

        def unsubscribe() -> bool:
            with self._lock:
                if topic is None:
                    try:
                        self._wild.remove(callback)
                        return True
                    except ValueError:
                        return False
                try:
                    self._subs[topic].remove(callback)
                    return True
                except ValueError:
                    return False
        return unsubscribe

    def recent(self, topic: str, n: int = 100) -> list[Sample]:
        with self._lock:
            buf = self._buf.get(topic)
            if not buf:
                return []
            return list(buf)[-n:]

    def topics(self) -> list[str]:
        with self._lock:
            return sorted(self._buf)
