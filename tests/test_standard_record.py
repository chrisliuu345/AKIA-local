"""StandardRecord v1 + StandardRegistry 契约测试（v4.3.0 B0-2）。"""

from datetime import datetime

import pytest

from core.standard_record import (
    OBJECT_TYPES,
    STANDARD_SCHEMA_VERSION,
    StandardRecord,
    StandardRegistry,
    migrate_legacy_context,
)

T1 = "2026-10-01T00:00:00+08:00"
T2 = "2026-10-02T00:00:00+08:00"
T3 = "2026-10-03T00:00:00+08:00"


def _record(record_id="S1", ref="QC-001", payload=None, valid_from=T1,
            valid_to=None, reason="初始版本", origin="manual", **kwargs):
    return StandardRecord(
        record_id=record_id, object_type=kwargs.pop("object_type", "spec_limit"),
        object_ref=ref, payload={"usl": 10.1, "lsl": 9.9} if payload is None else payload,
        valid_from=valid_from, valid_to=valid_to, change_reason=reason,
        origin=origin, **kwargs)


class TestRecordValidation:
    def test_valid_record_and_fingerprint(self):
        record = _record()
        assert record.schema_version == STANDARD_SCHEMA_VERSION
        assert record.valid_to is None
        assert record.is_open()
        assert record.fingerprint.startswith("std-hash-v1:")
        assert record.recorded_at

    def test_fingerprint_changes_with_payload(self):
        left = _record(payload={"usl": 10.1})
        right = _record(payload={"usl": 10.2})
        assert left.fingerprint != right.fingerprint

    def test_missing_reason_rejected_for_manual(self):
        with pytest.raises(ValueError, match="change_reason"):
            _record(reason="")

    def test_migration_defaults_reason(self):
        record = _record(reason="", origin="migration")
        assert record.change_reason == "历史数据迁移"

    def test_empty_required_fields_rejected(self):
        with pytest.raises(ValueError, match="record_id"):
            _record(record_id="")
        with pytest.raises(ValueError, match="object_ref"):
            _record(ref="")
        with pytest.raises(ValueError, match="payload"):
            _record(payload={})

    def test_unknown_type_and_origin_rejected(self):
        with pytest.raises(ValueError, match="对象类型"):
            _record(object_type="magic")
        with pytest.raises(ValueError, match="origin"):
            _record(origin="magic")

    def test_naive_valid_from_rejected(self):
        with pytest.raises(ValueError, match="时区"):
            _record(valid_from="2026-10-01T00:00:00")

    def test_valid_to_must_be_after_valid_from(self):
        with pytest.raises(ValueError, match="valid_to"):
            _record(valid_to=T1)

    def test_roundtrip_and_unknown_keys(self):
        record = _record(payload={"usl": 10.1, "lsl": 9.9, "unit": "mm"})
        data = record.to_dict()
        data["future"] = 1
        restored = StandardRecord.from_dict(data)
        assert restored.to_dict() == record.to_dict()

    def test_unknown_schema_rejected(self):
        data = _record().to_dict()
        data["schema_version"] = "99"
        with pytest.raises(ValueError, match="schema"):
            StandardRecord.from_dict(data)

    def test_expected_object_types_declared(self):
        assert set(OBJECT_TYPES) == {
            "spec_limit", "control_limit", "standard_time",
            "work_combination", "control_plan_row"}


class TestRegistryAppend:
    def test_append_auto_closes_previous(self):
        registry = StandardRegistry()
        first = registry.append(_record("S1"))
        second = registry.append(_record("S2", payload={"usl": 10.2}, valid_from=T2))
        assert datetime.fromisoformat(first.valid_to) == datetime.fromisoformat(T2)
        assert second.supersedes == "S1"
        assert registry.current("QC-001").record_id == "S2"
        assert len(registry) == 2

    def test_backdated_overlap_rejected(self):
        registry = StandardRegistry()
        registry.append(_record("S1"))
        with pytest.raises(ValueError, match="重叠|早于|晚于"):
            registry.append(_record("S2", valid_from="2026-09-30T00:00:00+08:00"))

    def test_explicit_closed_gap_accepted(self):
        registry = StandardRegistry()
        registry.append(_record("S1", valid_to="2026-10-01T12:00:00+08:00"))
        registry.append(_record("S2", valid_from=T2))
        assert registry.current("QC-001").record_id == "S2"

    def test_type_conflict_rejected(self):
        registry = StandardRegistry()
        registry.append(_record("S1"))
        with pytest.raises(ValueError, match="类型"):
            registry.append(_record("S2", object_type="control_limit", valid_from=T2))

    def test_duplicate_id_rejected(self):
        registry = StandardRegistry()
        first = registry.append(_record("S1"))
        with pytest.raises(ValueError, match="重复"):
            registry.append(_record("S1", ref="QC-002"))
        # 追加失败必须原子：现行版本保持开放，不出现"已关闭且无新版"的损坏状态
        assert first.is_open() is True
        assert registry.current("QC-001") is first

    def test_registry_rejects_non_record(self):
        with pytest.raises(TypeError):
            StandardRegistry().append({"record_id": "S1"})


class TestRegistryQuery:
    @staticmethod
    def _registry():
        registry = StandardRegistry()
        registry.append(_record("S1", payload={"usl": 10.1}))
        registry.append(_record("S2", payload={"usl": 10.2}, valid_from=T2))
        return registry

    def test_as_of_boundaries(self):
        registry = self._registry()
        assert registry.as_of("QC-001", T1).record_id == "S1"
        assert registry.as_of("QC-001", "2026-10-01T23:59:59+08:00").record_id == "S1"
        assert registry.as_of("QC-001", T2).record_id == "S2"
        assert registry.as_of("QC-001", "2026-09-30T00:00:00+08:00") is None

    def test_current_and_history(self):
        registry = self._registry()
        assert registry.current("QC-001").record_id == "S2"
        assert [r.record_id for r in registry.history("QC-001")] == ["S1", "S2"]
        assert registry.current("missing") is None
        assert registry.as_of("missing", T1) is None

    def test_diff_reports_payload_changes(self):
        registry = self._registry()
        first, second = registry.history("QC-001")
        changes = StandardRegistry.diff(first, second)
        assert changes["payload"]["usl"] == {"old": 10.1, "new": 10.2}
        assert datetime.fromisoformat(changes["valid_from"]["old"]) == datetime.fromisoformat(T1)
        assert datetime.fromisoformat(changes["valid_from"]["new"]) == datetime.fromisoformat(T2)

    def test_diff_identical_is_empty(self):
        first = _record("S1")
        assert StandardRegistry.diff(first, StandardRecord.from_dict(first.to_dict())) == {}

    def test_diff_rejects_non_records(self):
        with pytest.raises(TypeError):
            StandardRegistry.diff(_record(), {"record_id": "x"})

    def test_refs(self):
        registry = self._registry()
        registry.append(_record("S3", ref="QC-002"))
        assert registry.refs() == ["QC-001", "QC-002"]


class TestRegistrySerialization:
    def test_roundtrip(self):
        registry = TestRegistryQuery._registry()
        restored = StandardRegistry.from_dict(registry.to_dict())
        assert [r.to_dict() for r in restored.records] == [r.to_dict() for r in registry.records]
        assert restored.as_of("QC-001", T1).record_id == "S1"

    def test_none_and_empty(self):
        assert len(StandardRegistry.from_dict(None)) == 0
        assert len(StandardRegistry.from_dict({"schema_version": "1", "records": []})) == 0

    def test_unknown_schema_rejected(self):
        with pytest.raises(ValueError, match="schema"):
            StandardRegistry.from_dict({"schema_version": "99", "records": []})

    def test_overlap_on_load_rejected(self):
        payload = {
            "schema_version": "1",
            "records": [
                _record("S1", valid_to=T3).to_dict(),
                _record("S2", valid_from=T2, valid_to=T3).to_dict(),
            ],
        }
        with pytest.raises(ValueError, match="重叠"):
            StandardRegistry.from_dict(payload)


class TestLegacyMigration:
    @staticmethod
    def _context():
        return {
            "created_at": "2026-09-01T08:00:00",
            "characteristics": [
                {"id": "QC-001", "name": "轴径", "process": "车削",
                 "usl": 10.02, "lsl": 9.98, "target": 10.0, "unit": "mm"},
                {"id": "QC-002", "name": "外观", "usl": None, "lsl": None, "target": None},
            ],
        }

    def test_migration_creates_spec_limit_records(self):
        registry = migrate_legacy_context(self._context())
        assert len(registry) == 1
        record = registry.current("QC-001")
        assert record.origin == "migration"
        assert record.change_reason == "历史数据迁移"
        assert record.payload["usl"] == 10.02
        assert record.valid_from.startswith("2026-09-01T08:00:00")
        assert "QC-002" not in registry.refs()

    def test_migration_handles_naive_and_invalid_created_at(self):
        context = self._context()
        context["created_at"] = "not-a-time"
        registry = migrate_legacy_context(context, recorded_at="2026-10-03T09:00:00+08:00")
        assert registry.current("QC-001").valid_from.startswith("2026-10-03T09:00:00")

    def test_migration_empty_context(self):
        assert len(migrate_legacy_context({})) == 0
        assert len(migrate_legacy_context(None)) == 0
