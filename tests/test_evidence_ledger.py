"""EvidenceEvent v1 + 哈希链账本契约测试（v4.3.0 B0-3）。"""

import json

import pytest

from core.evidence_ledger import (
    EVIDENCE_SCHEMA_VERSION,
    EVENT_TYPES,
    GENESIS_HASH,
    EvidenceEvent,
    EvidenceLedger,
    canonical_json,
    file_sha256,
    verify_chain,
)


def _ledger(path=""):
    ledger = EvidenceLedger(path=path)
    ledger.append("case_created", actor="alice", object_refs=["case:C1"],
                  payload={"title": "节拍改善"})
    ledger.append("case_step", actor="alice", object_refs=["case:C1"],
                  payload={"phase": "baseline", "fingerprint": "pd-hash-v1:abc"})
    ledger.append("measurement_recorded", actor="system", object_refs=["MEV-1"],
                  payload={"case": "case:C1"})
    return ledger


class TestChain:
    def test_first_event_links_to_genesis(self):
        ledger = EvidenceLedger()
        event = ledger.append("case_created", payload={"title": "x"})
        assert event.seq == 1
        assert event.prev_hash == GENESIS_HASH
        assert len(event.event_hash) == 64

    def test_events_are_linked(self):
        ledger = _ledger()
        assert ledger.events[1].prev_hash == ledger.events[0].event_hash
        assert ledger.events[2].prev_hash == ledger.events[1].event_hash
        result = ledger.verify()
        assert result["ok"] is True
        assert result["count"] == 3
        assert result["broken_at"] is None

    def test_tamper_payload_detected(self):
        ledger = _ledger()
        ledger.events[1].payload["phase"] = "improvement"
        result = ledger.verify()
        assert result["ok"] is False
        assert result["broken_at"] == 2
        assert "篡改" in result["reason"]

    def test_tamper_prev_hash_detected(self):
        ledger = _ledger()
        ledger.events[1].prev_hash = "f" * 64
        result = ledger.verify()
        assert result["ok"] is False
        assert result["broken_at"] == 2

    def test_dropped_event_detected_as_sequence_gap(self):
        ledger = _ledger()
        del ledger.events[1]
        result = verify_chain(ledger.events)
        assert result["ok"] is False
        assert result["broken_at"] == 3
        assert "序号" in result["reason"]

    def test_verify_accepts_dicts(self):
        ledger = _ledger()
        assert verify_chain([e.to_dict() for e in ledger.events])["ok"] is True

    def test_verify_reports_unparseable_item(self):
        result = verify_chain([{"seq": 1}])
        assert result["ok"] is False
        assert result["broken_at"] == 1


class TestEventValidation:
    def test_unknown_type_rejected(self):
        with pytest.raises(ValueError, match="事件类型"):
            EvidenceEvent(seq=1, event_type="magic")

    def test_seq_starts_at_one(self):
        with pytest.raises(ValueError, match="seq"):
            EvidenceEvent(seq=0, event_type="case_created")

    def test_naive_at_rejected(self):
        with pytest.raises(ValueError, match="时区"):
            EvidenceEvent(seq=1, event_type="case_created", at="2026-10-03T10:00:00")

    def test_roundtrip_and_unknown_keys(self):
        event = EvidenceEvent(seq=1, event_type="case_created", actor="bob",
                              object_refs=["case:C1"], payload={"n": 1})
        data = event.to_dict()
        data["future"] = True
        restored = EvidenceEvent.from_dict(data)
        assert restored.to_dict() == event.to_dict()

    def test_unknown_schema_rejected(self):
        data = EvidenceEvent(seq=1, event_type="case_created").to_dict()
        data["schema_version"] = "99"
        with pytest.raises(ValueError, match="schema"):
            EvidenceEvent.from_dict(data)

    def test_expected_types_declared(self):
        for name in ("data_imported", "measurement_recorded", "standard_changed",
                     "analysis_run", "case_created", "case_step", "case_closed",
                     "case_reopened", "report_exported", "alert_ack",
                     "data_edited", "share_pack_exported"):
            assert name in EVENT_TYPES

    def test_custom_event_id_and_at(self):
        event = EvidenceEvent(seq=1, event_type="case_created", event_id="EVT-X",
                              at="2026-10-03T10:00:00+08:00")
        assert event.event_id == "EVT-X"
        assert event.at == "2026-10-03T10:00:00+08:00"


class TestSerialization:
    def test_jsonl_roundtrip(self):
        ledger = _ledger()
        restored = EvidenceLedger.from_jsonl(ledger.to_jsonl())
        assert [e.to_dict() for e in restored.events] == [e.to_dict() for e in ledger.events]
        assert restored.verify()["ok"] is True

    def test_from_events_accepts_dicts(self):
        ledger = _ledger()
        restored = EvidenceLedger.from_events([e.to_dict() for e in ledger.events])
        assert len(restored) == 3
        assert restored.verify()["ok"] is True

    def test_canonical_json_is_order_independent(self):
        assert canonical_json({"b": 1, "a": [2, {"d": 4, "c": 3}]}) == \
            canonical_json({"a": [2, {"c": 3, "d": 4}], "b": 1})

    def test_bytes_roundtrip(self):
        ledger = _ledger()
        restored = EvidenceLedger.from_bytes(ledger.to_bytes())
        assert restored.verify()["ok"] is True

    def test_file_sha256(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("hello", encoding="utf-8")
        assert file_sha256(target) == file_sha256(target)


class TestRecovery:
    def test_truncated_tail_recovered(self):
        ledger = _ledger()
        text = ledger.to_jsonl() + '{"seq":4,"type":"case_'
        restored = EvidenceLedger.from_jsonl(text)
        assert restored.recovered_truncation is True
        assert len(restored) == 3
        assert restored.verify()["ok"] is True

    def test_load_file_rewrites_clean_tail(self, tmp_path):
        path = tmp_path / "events.jsonl"
        _ledger(path=str(path))
        with open(path, "a", encoding="utf-8") as handle:
            handle.write('{"seq":4,"type":"case_')
        loaded = EvidenceLedger.load_file(path)
        assert loaded.recovered_truncation is True
        assert loaded.verify()["ok"] is True
        assert not path.read_text(encoding="utf-8").endswith('"case_')
        assert len(loaded) == 3

    def test_malformed_middle_line_blocks_append(self, tmp_path):
        path = tmp_path / "events.jsonl"
        _ledger(path=str(path))
        lines = path.read_text(encoding="utf-8").splitlines()
        lines.insert(1, "{bad-json")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        loaded = EvidenceLedger.load_file(path)
        assert loaded.load_errors
        assert loaded.verify()["ok"] is False
        with pytest.raises(RuntimeError, match="拒绝追加"):
            loaded.append("case_step")

    def test_file_mode_appends_lines(self, tmp_path):
        path = tmp_path / "events.jsonl"
        _ledger(path=str(path))
        assert len(path.read_text(encoding="utf-8").splitlines()) == 3
        reloaded = EvidenceLedger.load_file(path)
        assert reloaded.verify()["ok"] is True
        assert len(reloaded) == 3

    def test_save_file(self, tmp_path):
        ledger = _ledger()
        target = tmp_path / "sub" / "events.jsonl"
        ledger.save_file(target)
        assert target.exists()
        assert EvidenceLedger.load_file(target).verify()["ok"] is True


class TestQueriesAndManifest:
    def test_events_for_ref_and_payload(self):
        ledger = _ledger()
        # 两条显式 object_refs + 一条 payload 引用（measurement_recorded）
        assert len(ledger.events_for("case:C1")) == 3
        assert len(ledger.events_for("MEV-1")) == 1
        assert ledger.events_for("") == []
        assert ledger.events_for("missing") == []

    def test_export_manifest(self):
        manifest = _ledger().export_manifest()
        assert manifest["schema_version"] == EVIDENCE_SCHEMA_VERSION
        assert manifest["event_count"] == 3
        assert manifest["chain_ok"] is True
        assert manifest["types"]["case_created"] == 1
        assert manifest["first_at"] and manifest["last_at"]
        assert manifest["last_hash"] != GENESIS_HASH

    def test_json_line_is_valid_json(self):
        line = _ledger().to_jsonl().splitlines()[0]
        payload = json.loads(line)
        assert payload["seq"] == 1
        assert payload["type"] == "case_created"
