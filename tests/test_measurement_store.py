"""MeasurementStore v1 契约测试（v4.3.0 B2）。"""

import json

import pytest

from core.measurement_event import MeasurementEvent
from core.measurement_store import MeasurementStore


def _event(value=1.0, characteristic="QC-1"):
    return MeasurementEvent.from_manual(value, characteristic_id=characteristic)


class TestStoreBasics:
    def test_add_get_and_len(self):
        store = MeasurementStore()
        event = store.add(_event())
        assert len(store) == 1
        assert store.get(event.event_id) is event
        assert store.get("missing") is None
        assert list(store) == [event]

    def test_idempotent_by_event_id(self):
        store = MeasurementStore()
        first = _event(1.0)
        store.add(first)
        replacement = MeasurementEvent.from_manual(2.0, event_id=first.event_id)
        store.add(replacement)
        assert len(store) == 1
        assert store.get(first.event_id).summary["mean"] == 2.0

    def test_extend_and_by_ids(self):
        store = MeasurementStore()
        events = store.extend([_event(1.0), _event(2.0), _event(3.0)])
        wanted = [events[2].event_id, events[0].event_id, "missing"]
        assert [e.event_id for e in store.by_ids(wanted)] == [
            events[2].event_id, events[0].event_id]
        assert store.by_ids([]) == []

    def test_fifo_trim(self):
        store = MeasurementStore(max_events=2)
        store.extend([_event(1.0), _event(2.0), _event(3.0)])
        assert len(store) == 2
        assert [e.summary["mean"] for e in store] == [2.0, 3.0]

    def test_clear(self):
        store = MeasurementStore([_event()])
        store.clear()
        assert len(store) == 0

    def test_invalid_event_rejected(self):
        with pytest.raises(ValueError):
            MeasurementStore().add({"schema_version": "1"})


class TestSerialization:
    def test_dicts_jsonl_bytes_roundtrip(self):
        store = MeasurementStore([_event(1.0), _event(2.0)])
        assert len(store.to_dicts()) == 2
        for restored in (MeasurementStore.from_jsonl(store.to_jsonl()),
                         MeasurementStore.from_bytes(store.to_bytes())):
            assert [e.to_dict() for e in restored] == store.to_dicts()
            assert restored.load_errors == []

    def test_truncated_tail_recovered(self):
        store = MeasurementStore([_event(1.0)])
        text = store.to_jsonl() + '{"schema_version":"1","event_id":"MEV-x'
        restored = MeasurementStore.from_jsonl(text)
        assert restored.recovered_truncation is True
        assert len(restored) == 1

    def test_complete_jsonl_without_trailing_newline_keeps_events(self):
        """完整 JSONL 仅缺尾随换行时不得丢尾行。"""
        store = MeasurementStore([_event(1.0)])
        text = store.to_jsonl().rstrip("\n")
        restored = MeasurementStore.from_jsonl(text)
        assert restored.recovered_truncation is False
        assert len(restored) == 1

    def test_malformed_line_recorded(self):
        store = MeasurementStore([_event(1.0)])
        lines = store.to_jsonl().splitlines()
        lines.insert(0, "{bad-json")
        restored = MeasurementStore.from_jsonl("\n".join(lines) + "\n")
        assert restored.load_errors
        assert len(restored) == 1

    def test_save_and_load_file_rewrites_tail(self, tmp_path):
        path = tmp_path / "measurements.jsonl"
        store = MeasurementStore([_event(1.0)])
        store.save_file(path)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write('{"schema_version":"1","event_id":"MEV-half')
        loaded = MeasurementStore.load_file(path)
        assert loaded.recovered_truncation is True
        assert len(loaded) == 1
        assert not path.read_text(encoding="utf-8").endswith("MEV-half")
        assert json.loads(path.read_text(encoding="utf-8").splitlines()[0])["event_id"]

    def test_load_missing_file(self, tmp_path):
        assert len(MeasurementStore.load_file(tmp_path / "missing.jsonl")) == 0
