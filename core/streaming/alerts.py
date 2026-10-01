"""实时告警引擎 — OOC/OOS 事件采集 → 去抖 → 通道分发（邮件/webhook/桌面弹窗）。

- 规则: 设备+通道+规格限, 经 LiveSPC 实时检测
- 去抖: 同一 (设备,通道,类型) 在 cooldown 秒内只通知一次; 且要求连续 N 点违规
- 等级: 预告(info) / 警告(warning) / 严重(critical) — 规则可覆盖, 缺省按类型判定
- 通道: journal(留存+确认) / email / webhook / desktop(Signal) / action(停机指令)
"""
import json
import logging
import smtplib
import subprocess
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import formataddr

from PySide6.QtCore import QObject, Signal

from core.streaming.alert_journal import (
    SEVERITY_CRITICAL, SEVERITY_INFO, SEVERITY_WARNING, JournalEntry,
    severity_rank,
)
from core.streaming.live_spc import LiveSPC

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    device: str
    channel: str
    usl: float | None = None
    lsl: float | None = None
    debounce_n: int = 1       # 连续 N 点违规才触发
    cooldown_s: float = 60.0  # 同键冷却
    window: int = 30
    severity: str | None = None  # None → 自动（oos=严重, 判异=警告）
    actions: list[str] = None    # 联动动作（停机/命令），需显式开启才执行


@dataclass
class AlertEvent:
    device: str
    channel: str
    kind: str          # nelson / ooc / oos
    desc: str
    value: float
    ts: float
    severity: str = SEVERITY_WARNING
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]


def classify_severity(kind: str, rule: "AlertRule | None" = None,
                      value: float | None = None) -> str:
    """告警等级判定 — 规则显式配置优先, 其次按事件类型, 最后看超限幅度。

    - 规则 severity 显式设置 → 直接采用（预告/警告/严重）
    - 超规格(oos) → 严重；控制限判异(nelson/ooc) → 警告
    - 超出规格限 3 倍容差（或未配置规格限时的极端偏移）→ 严重
    """
    if rule is not None and rule.severity:
        return str(rule.severity)
    if kind == "oos":
        if rule is not None and value is not None:
            usl, lsl = rule.usl, rule.lsl
            if usl is not None or lsl is not None:
                width = None
                if usl is not None and lsl is not None:
                    width = float(usl) - float(lsl)
                if width and width > 0:
                    over = 0.0
                    if usl is not None and value > usl:
                        over = (value - float(usl)) / width
                    elif lsl is not None and value < lsl:
                        over = (float(lsl) - value) / width
                    if over >= 1.0:
                        return SEVERITY_CRITICAL
        return SEVERITY_CRITICAL
    if kind in ("nelson", "ooc"):
        return SEVERITY_WARNING
    return SEVERITY_INFO


class DesktopHandler(QObject):
    """线程安全桌面通知 — 信号排队到主线程。"""
    alert = Signal(str, str)  # title, message

    def notify(self, e: AlertEvent):
        from core.streaming.alert_journal import severity_label

        self.alert.emit(
            f"[AKIA·{severity_label(e.severity)}] {e.device}/{e.channel} 异常",
            f"{e.desc} · 当前值 {e.value:.3f}")


class AlertEngine:
    def __init__(self, bus, rules: list[AlertRule], handlers: list | None = None):
        self.bus = bus
        self.rules = rules
        self.handlers = handlers or []
        self._spc_by_key: dict[tuple[str, str], LiveSPC] = {}
        self._last_fire: dict[tuple[str, str, str], float] = {}
        self._last_event: dict[tuple[str, str, str], tuple[int, float]] = {}
        self._unsubs: list = []
        self.debounce: bool = True
        self.last_event: AlertEvent | None = None
        self.journal = None            # AlertJournal | None（留存 + 确认）
        # 通知通道(邮件/webhook)可能阻塞 — 脱离采集线程
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._pending: list = []

    def start(self) -> int:
        """订阅规则涉及的设备。返回订阅数。"""
        for rule in self.rules:
            key = (rule.device, rule.channel)
            spc = LiveSPC(rule.channel, mode="imr", window=rule.window,
                          usl=rule.usl, lsl=rule.lsl)
            self._spc_by_key[key] = spc
            self._unsubs.append(self.bus.subscribe(rule.device, self._make_cb(spc)))
        return len(self._unsubs)

    def stop(self):
        for unsub in self._unsubs:
            unsub()
        self._unsubs = []
        self.wait_pending()
        self._executor.shutdown(wait=False)

    def _make_cb(self, spc: LiveSPC):
        def cb(samples):
            values = [s.value for s in samples if s.channel == spc.channel]
            frame = spc.feed(values)
            device = next((d for (d, _c), s in self._spc_by_key.items() if s is spc), "")
            for ev in frame.events:
                self._handle(device, spc.channel, ev)
        return cb

    def _handle(self, device: str, channel: str, ev) -> None:
        rule = next((r for r in self.rules
                     if r.device == device and r.channel == channel), None)
        n_streak = rule.debounce_n if rule else 1
        cooldown = rule.cooldown_s if rule else 60.0
        key = (device, channel, ev.kind)
        count, _last = self._last_event.get(key, (0, 0.0))
        self._last_event[key] = (count + 1, time.time())
        if count + 1 < n_streak:
            return
        last_fire = self._last_fire.get(key, 0.0)
        if self.debounce and time.time() - last_fire < cooldown:
            return
        self._last_fire[key] = time.time()
        event = AlertEvent(
            device, channel, ev.kind, ev.desc, ev.value, time.time(),
            severity=classify_severity(ev.kind, rule, ev.value),
        )
        self.last_event = event
        for h in self.handlers:
            try:
                self._pending.append(self._executor.submit(self._dispatch, h, event))
            except Exception:
                logger.exception("alert handler dispatch failed: %s", h)

    @staticmethod
    def _dispatch(handler, event):
        """兼容两种处理器形态: 带 notify() 的对象（桌面/自定义）与普通函数
        （邮件/webhook/journal/action 工厂产物）。

        v3.7.0 遗留缺陷: 工厂返回的函数此前被按 h.notify 调用，导致
        email/webhook 通道在引擎路径下始终抛 AttributeError 且被吞掉。
        """
        notify = getattr(handler, "notify", None)
        if callable(notify):
            return notify(event)
        return handler(event)

    def wait_pending(self, timeout: float = 10.0):
        """测试/退出用: 等待在途通知完成。"""
        pending = [f for f in self._pending if not f.done()]
        if pending:
            wait(pending, timeout=timeout)
        self._pending = [f for f in self._pending if not f.done()]


def make_email_handler(host: str, port: int, user: str, password: str,
                       to: str, from_addr: str | None = None, timeout: float = 10.0,
                       use_tls: bool = False):
    def notify(e: AlertEvent):
        msg = MIMEText(
            f"{e.device}/{e.channel} {e.desc}\n"
            f"值: {e.value:.3f}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.ts))}")
        msg["Subject"] = f"AKIA 告警 {e.device}/{e.channel}"
        msg["From"] = formataddr(("AKIA", from_addr or user))
        msg["To"] = to
        with smtplib.SMTP(host, port, timeout=timeout) as s:
            if use_tls:
                s.starttls()
            if user:
                s.login(user, password)
            s.send_message(msg)
    return notify


def make_webhook_handler(url: str, timeout: float = 5.0):
    def notify(e: AlertEvent):
        payload = json.dumps({
            "event": "akia-alert", "device": e.device, "channel": e.channel,
            "kind": e.kind, "desc": e.desc, "value": e.value, "ts": e.ts,
            "severity": e.severity, "id": e.id,
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    return notify


def make_journal_handler(journal, min_severity: str = SEVERITY_INFO):
    """告警留存处理器 — 追加 JSONL + 审计（v3.8.0-③）。

    等级过滤: 低于 min_severity 的事件只记录不派发（返回 False 供调用方判断）。
    """
    from core.audit import audit

    def notify(e: AlertEvent) -> bool:
        if severity_rank(e.severity) < severity_rank(min_severity):
            return False
        journal.record(JournalEntry(
            id=e.id, ts=e.ts, device=e.device, channel=e.channel, kind=e.kind,
            severity=e.severity, desc=e.desc, value=float(e.value),
        ))
        audit("alert_fired", "system",
              f"{e.severity} {e.device}/{e.channel} {e.kind} {e.desc} 值={e.value:.3f} id={e.id}")
        return True
    return notify


def make_action_handler(actions: dict[str, list[str]] | None = None,
                        enabled: bool = False, timeout: float = 5.0,
                        runner=None):
    """联动动作处理器 — 命中设备映射时执行停机/复位等外部命令。

    安全默认: enabled=False 时只记录不执行（日志 WARNING），避免误触发产线动作；
    需在 user_config 显式开启 `alert_actions_enabled`。
    """
    actions = actions or {}

    def notify(e: AlertEvent) -> bool:
        command = actions.get(e.device) or actions.get(f"{e.device}/{e.channel}")
        if not command:
            return False
        if not enabled:
            logger.warning("联动动作被禁用(alert_actions_enabled=false)，忽略: %s -> %s",
                           e.device, command)
            return False
        try:
            if runner is not None:
                runner(command, e)
            else:
                subprocess.run(list(command), timeout=timeout, check=False)
            logger.info("联动动作已执行: %s -> %s", e.device, command)
            from core.audit import audit
            audit("alert_action", "system",
                  f"{e.device}/{e.channel} {e.kind} -> {' '.join(command)}")
            return True
        except Exception:
            logger.exception("联动动作执行失败: %s", command)
            return False
    return notify


def rules_from_plant(plant) -> list[AlertRule]:
    """产线配置 → 告警规则（每工位通道一条; 规格限缺省时仍对 Nelson 判异打开）。"""
    rules = []
    for line in plant.lines:
        for st in line.stations:
            for ch in st.channels:
                rules.append(AlertRule(device=st.device, channel=ch,
                                       usl=st.usl, lsl=st.lsl))
    return rules


def build_default_handlers(settings: dict | None = None) -> list:
    """按 user_config 设置组装可选通道（webhook/邮件）; 未配置的跳过。"""
    s = settings or {}
    handlers: list = []
    journal = s.get("alert_journal")
    if journal is not None:
        handlers.append(make_journal_handler(
            journal, min_severity=s.get("alert_min_severity", SEVERITY_INFO)))
    url = s.get("alert_webhook_url", "")
    if url:
        handlers.append(make_webhook_handler(url))
    actions = s.get("alert_actions") or {}
    if actions:
        handlers.append(make_action_handler(
            actions, enabled=bool(s.get("alert_actions_enabled", False))))
    smtp_host = s.get("alert_smtp_host", "")
    if smtp_host:
        handlers.append(make_email_handler(
            smtp_host, int(s.get("alert_smtp_port", 25)),
            s.get("alert_smtp_user", ""), s.get("alert_smtp_password", ""),
            s.get("alert_email_to", ""),
            use_tls=bool(s.get("alert_smtp_starttls", False))))
    return handlers
