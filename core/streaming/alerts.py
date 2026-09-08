"""实时告警引擎 — OOC/OOS 事件采集 → 去抖 → 通道分发（邮件/webhook/桌面弹窗）。

- 规则: 设备+通道+规格限, 经 LiveSPC 实时检测
- 去抖: 同一 (设备,通道,类型) 在 cooldown 秒内只通知一次; 且要求连续 N 点违规
- 通道: email / webhook / desktop(Signal, 线程安全排队到主线程)
"""
import json
import logging
import smtplib
import time
import urllib.request
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import formataddr

from PySide6.QtCore import QObject, Signal

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


@dataclass
class AlertEvent:
    device: str
    channel: str
    kind: str          # nelson / ooc / oos
    desc: str
    value: float
    ts: float


class DesktopHandler(QObject):
    """线程安全桌面通知 — 信号排队到主线程。"""
    alert = Signal(str, str)  # title, message

    def notify(self, e: AlertEvent):
        self.alert.emit(f"[QA-Tool] {e.device}/{e.channel} 异常",
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
        event = AlertEvent(device, channel, ev.kind, ev.desc, ev.value, time.time())
        for h in self.handlers:
            try:
                h.notify(event)
            except Exception:
                logger.exception("alert handler failed: %s", h)


def make_email_handler(host: str, port: int, user: str, password: str,
                       to: str, from_addr: str | None = None, timeout: float = 10.0):
    def notify(e: AlertEvent):
        msg = MIMEText(
            f"{e.device}/{e.channel} {e.desc}\n"
            f"值: {e.value:.3f}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.ts))}")
        msg["Subject"] = f"QA-Tool 告警 {e.device}/{e.channel}"
        msg["From"] = formataddr(("QA-Tool", from_addr or user))
        msg["To"] = to
        with smtplib.SMTP(host, port, timeout=timeout) as s:
            s.starttls() if hasattr(s, "starttls") else None
            if user:
                s.login(user, password)
            s.send_message(msg)
    return notify


def make_webhook_handler(url: str, timeout: float = 5.0):
    def notify(e: AlertEvent):
        payload = json.dumps({
            "event": "qa-tool-alert", "device": e.device, "channel": e.channel,
            "kind": e.kind, "desc": e.desc, "value": e.value, "ts": e.ts,
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
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
    url = s.get("alert_webhook_url", "")
    if url:
        handlers.append(make_webhook_handler(url))
    smtp_host = s.get("alert_smtp_host", "")
    if smtp_host:
        handlers.append(make_email_handler(
            smtp_host, int(s.get("alert_smtp_port", 25)),
            s.get("alert_smtp_user", ""), s.get("alert_smtp_password", ""),
            s.get("alert_email_to", "")))
    return handlers
