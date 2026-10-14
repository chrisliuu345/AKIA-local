"""时间语义守卫测试（v4.3.0 B0-5）。

1. 新增双时态契约模块禁止无时区时间构造（`datetime.now()` 必须接 `.astimezone()`）；
2. 新契约写出的时间戳必须全部带时区偏移。
"""

import ast
import re
from datetime import datetime
from pathlib import Path

from core.evidence_ledger import EvidenceLedger
from core.measurement_event import MeasurementEvent
from core.standard_record import StandardRecord

ROOT = Path(__file__).resolve().parent.parent
GUARDED = [
    ROOT / "core" / "time_utils.py",
    ROOT / "core" / "measurement_event.py",
    ROOT / "core" / "measurement_store.py",
    ROOT / "core" / "evidence_ledger.py",
    ROOT / "core" / "evidence_pack.py",
    ROOT / "core" / "share_pack.py",
    ROOT / "core" / "standard_record.py",
    ROOT / "core" / "case_workflow.py",
    ROOT / "core" / "sampling_plan.py",
    ROOT / "core" / "gauge_study.py",
    ROOT / "core" / "benefit_ledger.py",
    ROOT / "core" / "skill_matrix.py",
    ROOT / "core" / "sampling_note.py",
]

#: datetime.now() 后必须紧跟 .astimezone(...)；utcnow/today 属于无时区构造
_NAIVE_PATTERNS = (
    re.compile(r"datetime\.utcnow\s*\("),
    re.compile(r"datetime\.today\s*\("),
    re.compile(r"datetime\.now\s*\(\s*\)(?!\s*\.astimezone\s*\()"),
)


def test_no_naive_datetime_construction():
    problems = []
    for path in GUARDED:
        text = path.read_text(encoding="utf-8")
        for pattern in _NAIVE_PATTERNS:
            for match in pattern.finditer(text):
                line = text[:match.start()].count("\n") + 1
                problems.append(f"{path.name}:{line} {match.group(0)}")
    assert not problems, "双时态模块禁止无时区时间构造: " + "；".join(problems)


def test_new_contract_timestamps_are_aware():
    event = MeasurementEvent.from_manual(1.0)
    record = StandardRecord(
        record_id="S1", object_type="spec_limit", object_ref="QC-1",
        payload={"usl": 1.0}, valid_from=event.recorded_at,
        change_reason="测试")
    ledger = EvidenceLedger()
    ledger_event = ledger.append("case_created", payload={"title": "t"})
    for text in (event.ts_start, event.ts_end, event.recorded_at,
                 record.valid_from, record.recorded_at, ledger_event.at):
        assert datetime.fromisoformat(text).tzinfo is not None, text


def test_ast_guard_can_see_datetime_now_calls():
    """守卫规则自身的正则自检：确保能命中 `datetime.now().isoformat()`。"""
    tree = ast.parse("x = datetime.now().isoformat()\n")
    assert any(isinstance(node, ast.Call) for node in ast.walk(tree))
    assert _NAIVE_PATTERNS[2].search("x = datetime.now().isoformat()")
    assert not _NAIVE_PATTERNS[2].search("x = datetime.now().astimezone().isoformat()")
