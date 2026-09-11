"""v3.8.0-③ 告警补全 — 等级判定 / 留存与确认 / 联动动作 / 告警中心。
"""
import json
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.devices.driver import Sample
from core.streaming.alert_journal import (
    SEVERITY_CRITICAL, SEVERITY_INFO, SEVERITY_WARNING, AlertJournal,
    JournalEntry, severity_rank,
)
from core.streaming.alerts import (
    AlertEngine, AlertRule, classify_severity, make_action_handler,
    make_journal_handler,
)
from core.streaming.bus import StreamBus


def _entry(eid="e1", severity=SEVERITY_WARNING, device="dev-a", ack=False):
    return JournalEntry(id=eid, ts=time.time(), device=device, channel="CH0",
                        kind="oos", severity=severity, desc="超规格上界",
                        value=131.0, ack=ack)


# ---------- 等级判定 ----------

def test_classify_severity_by_kind():
    rule = AlertRule(device="d", channel="CH0", usl=110.0, lsl=90.0)
    assert classify_severity("oos", rule, 111.0) == SEVERITY_CRITICAL
    assert classify_severity("oos", rule, 300.0) == SEVERITY_CRITICAL
    assert classify_severity("nelson", rule, 100.0) == SEVERITY_WARNING
    assert classify_severity("ooc", rule, 100.0) == SEVERITY_WARNING
    assert classify_severity("heartbeat", rule, 100.0) == SEVERITY_INFO


def test_rule_severity_override_wins():
    rule = AlertRule(device="d", channel="CH0", usl=110.0, severity=SEVERITY_INFO)
    assert classify_severity("oos", rule, 999.0) == SEVERITY_INFO
    assert severity_rank(SEVERITY_CRITICAL) > severity_rank(SEVERITY_WARNING)
    assert severity_rank(SEVERITY_WARNING) > severity_rank(SEVERITY_INFO)


# ---------- 留存 / 确认 ----------

def test_journal_records_and_filters(tmp_path):
    j = AlertJournal(tmp_path / "alerts.jsonl")
    j.record(_entry("a", SEVERITY_INFO))
    j.record(_entry("b", SEVERITY_WARNING))
    j.record(_entry("c", SEVERITY_CRITICAL))
    assert [e.id for e in j.entries()] == ["c", "b", "a"]      # 最新在前
    assert [e.id for e in j.entries(severity=SEVERITY_WARNING)] == ["c", "b"]
    assert j.unacked_count() == 3
    assert j.get("b").severity == SEVERITY_WARNING
    assert j.get("missing") is None


def test_journal_ack_persists_across_reload(tmp_path):
    path = tmp_path / "alerts.jsonl"
    j = AlertJournal(path)
    j.record(_entry("a"))
    j.record(_entry("b"))
    assert j.ack("a", "tester", note="已换刀") is True
    assert j.ack("a", "tester") is False          # 重复确认不生效
    assert j.ack("nope", "tester") is False
    assert j.unacked_count() == 1
    assert j.entries(unacked_only=True)[0].id == "b"

    reloaded = AlertJournal(path)
    acked = reloaded.get("a")
    assert acked.ack and acked.ack_by == "tester" and acked.note == "已换刀"
    assert reloaded.unacked_count() == 1


def test_journal_ack_all_and_clear(tmp_path):
    j = AlertJournal(tmp_path / "alerts.jsonl")
    for i in range(4):
        sev = SEVERITY_CRITICAL if i % 2 else SEVERITY_INFO
        j.record(_entry(f"e{i}", sev))
    assert j.ack_all("user", severity=SEVERITY_CRITICAL) == 2
    assert j.unacked_count() == 2
    assert j.ack_all("user") == 2
    assert j.unacked_count() == 0
    j.clear()
    assert j.entries() == []


def test_journal_tolerates_corrupt_lines_and_caps(tmp_path):
    path = tmp_path / "alerts.jsonl"
    path.write_text("not-json\n" + _entry("ok").to_json() + "\n",
                    encoding="utf-8")
    j = AlertJournal(path, max_entries=5)
    assert [e.id for e in j.entries()] == ["ok"]
    for i in range(8):
        j.record(_entry(f"n{i}"))
    assert len(j.entries()) == 5
    raw = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(raw) >= 5 and json.loads(raw[-1])["id"].startswith("n7")


# ---------- 处理器 ----------

def test_journal_handler_records_and_filters_severity(tmp_path):
    j = AlertJournal(tmp_path / "alerts.jsonl")
    handler = make_journal_handler(j, min_severity=SEVERITY_WARNING)

    class E:
        id, ts, device, channel = "h1", time.time(), "d", "CH0"
        kind, desc, value, severity = "nelson", "连续9点同侧", 1.0, SEVERITY_INFO

    assert handler(E()) is False          # 低于门槛 → 只忽略
    assert j.entries() == []

    class E2(E):
        severity = SEVERITY_CRITICAL
        id = "h2"
    assert handler(E2()) is True
    assert [e.id for e in j.entries()] == ["h2"]


def test_action_handler_disabled_by_default():
    calls = []
    handler = make_action_handler({"dev-a": ["stop", "line1"]},
                                  enabled=False,
                                  runner=lambda cmd, e: calls.append(cmd))

    class E:
        device, channel, kind, severity = "dev-a", "CH0", "oos", SEVERITY_CRITICAL
        desc, value, ts, id = "超规格", 131.0, 0.0, "x"

    assert handler(E()) is False
    assert calls == []                    # 未开启 → 绝不执行


def test_action_handler_enabled_runs_matching_command():
    calls = []
    handler = make_action_handler(
        {"dev-a": ["stop-line1"], "dev-b/CH1": ["reset"]},
        enabled=True, runner=lambda cmd, e: calls.append((tuple(cmd), e.device)))

    class E:
        device, channel, kind, severity = "dev-a", "CH0", "oos", SEVERITY_CRITICAL
        desc, value, ts, id = "超规格", 131.0, 0.0, "x"

    class E2(E):
        device, channel = "dev-b", "CH1"

    class E3(E):
        device = "dev-z"

    assert handler(E()) is True and calls[-1][0] == ("stop-line1",)
    assert handler(E2()) is True and calls[-1][0] == ("reset",)
    assert handler(E3()) is False


# ---------- 引擎集成 ----------

def test_engine_attaches_severity_and_journal(tmp_path):
    bus = StreamBus()
    journal = AlertJournal(tmp_path / "alerts.jsonl")
    engine = AlertEngine(
        bus,
        [AlertRule(device="dev-a", channel="CH0", usl=110.0, lsl=90.0,
                   cooldown_s=0.0)],
        [make_journal_handler(journal)],
    )
    engine.start()
    try:
        engine._handle("dev-a", "CH0", type("Ev", (), {
            "kind": "oos", "desc": "超规格上界 110.0", "value": 131.0})())
        engine.wait_pending()
    finally:
        engine.stop()
    entries = journal.entries()
    assert len(entries) == 1
    assert entries[0].severity == SEVERITY_CRITICAL
    assert entries[0].device == "dev-a" and entries[0].id
    assert engine.last_event is not None and engine.last_event.id == entries[0].id


def test_engine_end_to_end_from_bus(tmp_path):
    bus = StreamBus()
    journal = AlertJournal(tmp_path / "alerts.jsonl")
    engine = AlertEngine(bus, [AlertRule(device="dev-a", channel="CH0",
                                         usl=110.0, lsl=90.0, cooldown_s=0.0)],
                         [make_journal_handler(journal)])
    engine.start()
    try:
        now = time.time()
        bus.publish("dev-a", [Sample("dev-a", "CH0", 100.0, now - 1),
                              Sample("dev-a", "CH0", 140.0, now)])
        engine.wait_pending()
    finally:
        engine.stop()
    assert journal.entries() and journal.entries()[0].severity == SEVERITY_CRITICAL


# ---------- 告警中心 UI ----------

def test_alert_center_dialog_filters_and_ack(tmp_path):
    from ui.dialogs.alert_center_dialog import AlertCenterDialog

    journal = AlertJournal(tmp_path / "alerts.jsonl")
    journal.record(_entry("i1", SEVERITY_INFO))
    journal.record(_entry("w1", SEVERITY_WARNING))
    journal.record(_entry("c1", SEVERITY_CRITICAL))

    dlg = AlertCenterDialog(journal, auto_refresh_ms=0)
    assert dlg.table.rowCount() == 3              # 默认仅未确认 → 全部
    dlg.unacked_only.setChecked(False)
    dlg.severity_combo.setCurrentIndex(1)         # 严重
    assert dlg.table.rowCount() == 1
    assert dlg.table.item(0, 1).text() == "严重"

    journal.ack("c1", "tester")
    dlg.unacked_only.setChecked(True)
    dlg.refresh()
    assert dlg.table.rowCount() == 0              # 已确认 + 仅等级严重 → 空

    dlg.severity_combo.setCurrentIndex(0)
    dlg.refresh()
    assert dlg.table.rowCount() == 2              # c1 已确认被过滤
    dlg.deleteLater()
