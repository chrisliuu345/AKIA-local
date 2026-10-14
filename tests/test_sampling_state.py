"""抽样状态编排测试（v4.4.0 B3）——转移轨迹 / 留痕 / 持久化。"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from core.evidence_ledger import EvidenceLedger
from core.sampling_state import SAMPLING_STATE_SCHEMA_VERSION, SamplingStateManager
from core.standard_record import StandardRegistry

TZ = timezone(timedelta(hours=8))
BASE = datetime(2026, 10, 14, 9, 0, 0, tzinfo=TZ)


class _Clock:
    def __init__(self, start=BASE):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds=1):
        self.now = self.now + timedelta(seconds=seconds)


def _setup(*, reduced=False):
    ledger = EvidenceLedger()
    registry = StandardRegistry()
    clock = _Clock()
    manager = SamplingStateManager(ledger=ledger, standards=registry,
                                   clock=clock, reduced_enabled=reduced)
    return manager, ledger, registry, clock


def _lot(manager, key, decision, *, defects=0, serious=False, qty=500,
         inspected=50):
    clock = manager._clock  # 测试内直取，保持时间单调
    clock.advance()
    return manager.record_lot(scope_key=key, qty=qty, inspected=inspected,
                              defects=defects, decision=decision,
                              serious=serious, at=clock().isoformat())


class TestPlanSelection:
    def test_normal_plan_and_ledger(self):
        manager, ledger, registry, _clock = _setup()
        result = manager.select_plan("供应商A|P100", lot_size=2000, aql=1.0,
                                     method="random", seed=7)
        assert result["state"] == "normal"
        assert result["plan"]["sample_size"] == 125
        assert (result["plan"]["accept"], result["plan"]["reject"]) == (3, 4)
        assert result["plan_ref"]
        events = [e for e in ledger.events
                  if e.event_type == "sampling_plan_selected"]
        assert len(events) == 1
        payload = events[0].payload
        assert payload["stage"] == "plan_selected"
        assert payload["decision"]["seed"] == 7
        assert payload["plan"]["inspection"] == "normal"
        assert "scope:供应商A|P100" in events[0].object_refs
        # 标准注册表登记 sampling_plan 版本（可 as-of）
        records = [r for r in registry.records if r.object_type == "sampling_plan"]
        assert len(records) == 1
        assert records[0].object_ref == "供应商A|P100"

    def test_plan_ref_idempotent_for_same_plan(self):
        manager, _ledger, registry, _clock = _setup()
        first = manager.select_plan("A|P", lot_size=500, aql=1.0)
        second = manager.select_plan("A|P", lot_size=500, aql=1.0)
        assert first["plan_ref"] == second["plan_ref"]
        assert len([r for r in registry.records
                    if r.object_type == "sampling_plan"]) == 1

    def test_tightened_plan_after_transfer(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        manager.select_plan(key, lot_size=2000, aql=1.0)
        _lot(manager, key, "reject", defects=1)
        _lot(manager, key, "reject", defects=2)
        result = manager.select_plan(key, lot_size=2000, aql=1.0)
        assert result["state"] == "tightened"
        assert (result["plan"]["accept"], result["plan"]["reject"]) == (2, 3)

    def test_missing_scope_rejected(self):
        manager, _ledger, _registry, _clock = _setup()
        with pytest.raises(ValueError, match="scope_key"):
            manager.select_plan("", lot_size=100)


class TestSampling:
    def test_sample_backfills_fingerprint(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        result = manager.select_plan(key, lot_size=2000, aql=1.0, seed=9)
        frame = pd.DataFrame({"x": range(500)})
        sampled, decision = manager.sample(frame, key, method="systematic",
                                           n=50, seed=9)
        assert len(sampled) == 50
        assert decision is result["decision"]
        assert decision.row_fingerprint.startswith("pd-hash-v1:")
        lot_result = _lot(manager, key, "accept")
        lot_events = [e for e in manager.ledger.events
                      if e.event_type == "lot_inspected"]
        assert lot_events[-1].payload["row_fingerprint"] == \
            decision.row_fingerprint
        assert lot_events[-1].payload["decision_id"] == decision.decision_id
        assert lot_result["lot"].plan_ref == result["plan_ref"]

    def test_sample_without_plan_requires_n(self):
        manager, _ledger, _registry, _clock = _setup()
        with pytest.raises(ValueError, match="样本量"):
            manager.sample(pd.DataFrame({"x": [1]}), "A|P")
        with pytest.raises(ValueError, match="为空"):
            manager.sample(pd.DataFrame(), "A|P", n=5)


class TestTransferTrajectory:
    def test_two_rejects_then_five_accepts(self):
        manager, ledger, _registry, _clock = _setup()
        key = "A|P"
        _lot(manager, key, "reject", defects=1)
        second = _lot(manager, key, "reject", defects=2)
        assert second["state"] == "tightened"
        assert second["transfer"].rule == "two_consecutive_rejects"
        for _ in range(5):
            last = _lot(manager, key, "accept")
        assert last["state"] == "normal"
        assert last["transfer"].rule == "five_consecutive_accepts"
        types = [e.event_type for e in ledger.events]
        assert types.count("sampling_transfer_changed") == 2

    def test_serious_nonconformity_immediate(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        _lot(manager, key, "accept")
        result = _lot(manager, key, "reject", defects=10, serious=True)
        assert result["state"] == "tightened"
        assert result["transfer"].rule == "serious_nonconformity"

    def test_isolated_reject_does_not_trigger(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        _lot(manager, key, "reject", defects=1)
        result = _lot(manager, key, "accept")
        assert result["state"] == "normal"

    def test_reduced_disabled_by_default_and_enabled(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        for _ in range(10):
            last = _lot(manager, key, "accept")
        assert last["state"] == "normal"
        manager2, _l2, _r2, _c2 = _setup(reduced=True)
        for _ in range(10):
            last2 = _lot(manager2, key, "accept")
        assert last2["state"] == "reduced"
        rejected = _lot(manager2, key, "reject", defects=1)
        assert rejected["state"] == "normal"
        assert rejected["transfer"].rule == "lot_rejected"

    def test_trajectory_deterministic_across_managers(self):
        sequence = ["accept", "reject", "reject", "accept", "accept",
                    "accept", "accept", "accept"]
        trajectories = []
        for _ in range(2):
            manager, _ledger, _registry, _clock = _setup()
            key = "A|P"
            for decision in sequence:
                _lot(manager, key, decision,
                     defects=1 if decision == "reject" else 0)
            state = manager.state_for(key)
            trajectories.append([(e["from"], e["to"], e["rule"])
                                 for e in state.history])
        assert trajectories[0] == trajectories[1]

    def test_scopes_are_isolated(self):
        manager, _ledger, _registry, _clock = _setup()
        _lot(manager, "A|P1", "reject", defects=1)
        _lot(manager, "A|P1", "reject", defects=1)
        result_other = _lot(manager, "A|P2", "reject", defects=1)
        assert result_other["state"] == "normal"
        assert manager.state_for("A|P1").state == "tightened"


class TestManualOverride:
    def test_requires_reason_and_records(self):
        manager, ledger, _registry, _clock = _setup()
        key = "A|P"
        with pytest.raises(ValueError, match="原因"):
            manager.manual_override(key, "tightened", " ")
        with pytest.raises(ValueError, match="一致"):
            manager.manual_override(key, "normal", "无变化")
        state = manager.manual_override(key, "reduced", "客户特批放宽（附评审记录）")
        assert state.state == "reduced"
        assert state.override_reason == "客户特批放宽（附评审记录）"
        events = [e for e in ledger.events
                  if e.event_type == "sampling_transfer_changed"]
        assert events[-1].payload["rule"] == "manual_override"
        assert events[-1].payload["reason"] == "客户特批放宽（附评审记录）"


class TestTimelineAndSnapshot:
    def test_timeline_kinds_and_order(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        manager.select_plan(key, lot_size=500, aql=1.0, seed=1)
        _lot(manager, key, "reject", defects=1)
        result = _lot(manager, key, "reject", defects=1)
        assert result["changed"] is True
        rows = manager.timeline(key)
        kinds = {row["kind"] for row in rows}
        assert {"plan", "lot", "transfer"} <= kinds
        assert rows[0]["kind"] == "transfer"  # 最新事件在顶部
        transfer_row = next(row for row in rows if row["kind"] == "transfer")
        assert "连续 2 批拒收" in transfer_row["text"]
        assert "规则 two_consecutive_rejects" in transfer_row["text"]

    def test_snapshot_fields(self):
        manager, _ledger, _registry, _clock = _setup()
        key = "A|P"
        _lot(manager, key, "accept")
        snap = manager.snapshot(key)
        assert snap["state"] == "normal"
        assert snap["lots_total"] == 1
        assert snap["reduced_enabled"] is False


class TestPersistence:
    def test_roundtrip_continues_trajectory(self):
        manager, ledger, registry, clock = _setup()
        key = "A|P"
        manager.select_plan(key, lot_size=2000, aql=1.0, seed=3)
        _lot(manager, key, "reject", defects=1)
        payload = manager.to_dict()
        assert payload["schema_version"] == SAMPLING_STATE_SCHEMA_VERSION
        restored = SamplingStateManager.from_dict(
            payload, ledger=ledger, standards=registry, clock=clock)
        assert len(restored.lots) == 1
        assert restored.decision_for(key) is not None
        # 重载后继续：第二批判 reject → 加严（轨迹延续）
        result = _lot(restored, key, "reject", defects=1)
        assert result["state"] == "tightened"

    def test_from_dict_validation(self):
        assert len(SamplingStateManager.from_dict(None).lots) == 0
        with pytest.raises(ValueError, match="schema"):
            SamplingStateManager.from_dict({"schema_version": "9"})
        with pytest.raises(ValueError, match="必须为列表"):
            SamplingStateManager.from_dict({"schema_version": "1", "lots": {}})

    def test_supplier_product_key_parsing(self):
        manager, _ledger, _registry, _clock = _setup()
        result = manager.record_lot(supplier="供应商B", product="P200",
                                    qty=100, inspected=10, defects=0,
                                    decision="accept")
        key = "供应商B|P200"
        assert result["lot"].supplier == "供应商B"
        assert manager.lots_for(key) == [result["lot"]]


class TestEvidencePackIntegration:
    def test_sampling_trail_verifies_independently(self, tmp_path):
        """抽样事件随证据包导出并可独立校验（为何加严可还原）。"""
        from core.evidence_pack import export_evidence_pack, read_evidence_pack

        manager, ledger, _registry, _clock = _setup()
        key = "A|P"
        manager.select_plan(key, lot_size=500, aql=1.0, seed=5)
        _lot(manager, key, "reject", defects=1)
        _lot(manager, key, "reject", defects=1)
        result = export_evidence_pack(str(tmp_path / "pack.zip"), ledger=ledger)
        assert result["verify"]["ok"] is True
        payload = read_evidence_pack(result["path"])
        events_text = payload["events.jsonl"]
        assert "sampling_transfer_changed" in events_text
        assert "two_consecutive_rejects" in events_text
        assert "sampling_plan_selected" in events_text
