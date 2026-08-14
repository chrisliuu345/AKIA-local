"""告警通知引擎 (v2.4 E3) — 判异状态机 + 渠道规则 + 告警日志 (Qt-free)

- AlertTracker: 违反数变化状态机 (NONE/NEW/ONGOING/CLEARED)，
  仅在 NEW/CLEARED 跳变时产生告警事件 (天然去重，避免每次轮询重复弹窗)
- AlertRules: 可配置规则 (最小判异数 / 弹窗 / 声音 / 日志开关)，
  经 config.settings.get_setting 读取 user_config.json 覆盖值
- AlertLog: 内存环形日志 (供 UI 面板展示历史告警)
"""

from collections import deque
from datetime import datetime
from enum import Enum

from config.settings import get_setting
from core.i18n import i18n


class AlertState(Enum):
    """判异状态 — NONE 无 / NEW 新增 / ONGOING 持续 / CLEARED 解除"""

    NONE = "none"
    NEW = "new"
    ONGOING = "ongoing"
    CLEARED = "cleared"


class AlertRules:
    """告警规则 — 全部经 get_setting 支持 user_config.json 覆盖"""

    @staticmethod
    def min_violations() -> int:
        return int(get_setting("alert_min_violations", 1))

    @staticmethod
    def popup_enabled() -> bool:
        return bool(get_setting("alert_popup_enabled", True))

    @staticmethod
    def sound_enabled() -> bool:
        return bool(get_setting("alert_sound_enabled", True))

    @staticmethod
    def log_enabled() -> bool:
        return bool(get_setting("alert_log_enabled", True))


class AlertTracker:
    """判异状态机 — 只在状态跳变时产生事件，天然去重"""

    def __init__(self):
        self._prev = 0
        self.state = AlertState.NONE

    def update(self, violations: int) -> AlertState:
        v = max(0, int(violations or 0))
        if v > 0 and self._prev == 0:
            self.state = AlertState.NEW
        elif v > 0:
            self.state = AlertState.ONGOING
        elif v == 0 and self._prev > 0:
            self.state = AlertState.CLEARED
        else:
            self.state = AlertState.NONE
        self._prev = v
        return self.state

    def reset(self):
        self._prev = 0
        self.state = AlertState.NONE


class AlertLog:
    """内存环形告警日志 — 最新在前"""

    def __init__(self, max_entries: int = 200):
        self._entries = deque(maxlen=max_entries)

    def add(self, message: str):
        self._entries.appendleft((datetime.now(), message))

    def entries(self):
        return list(self._entries)

    def clear(self):
        self._entries.clear()

    def __len__(self):
        return len(self._entries)


def format_alert_message(state: AlertState, violations: int, file_name: str) -> str:
    """按状态生成本地化告警文案"""
    if state == AlertState.NEW:
        return i18n.tr("alert.new").format(n=violations, file=file_name)
    if state == AlertState.CLEARED:
        return i18n.tr("alert.cleared").format(file=file_name)
    return ""
