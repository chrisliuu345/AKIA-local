"""标准版本 as-of 复判与凭证追溯测试（v4.3.0 B3-1/B3-5）。"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from analysis.capability import normal_cap
from core.evidence import credential_trace_code, make_credential
from core.project_context import ProjectContext, QualityCharacteristic
from core.project_manager import ProjectManager
from core.standard_record import (
    StandardRecord,
    StandardRegistry,
    resolve_standard_context,
)

T1 = "2026-10-01T00:00:00+08:00"
T2 = "2026-10-02T00:00:00+08:00"
T3 = "2026-10-03T00:00:00+08:00"


def _record(record_id, payload, valid_from, valid_to=None, reason="变更"):
    return StandardRecord(
        record_id=record_id, object_type="spec_limit", object_ref="轴径",
        payload=payload, valid_from=valid_from, valid_to=valid_to,
        change_reason=reason, changed_by="tester")


class TestRegistryRecordChange:
    def test_record_change_creates_and_closes_versions(self):
        registry = StandardRegistry()
        first = registry.record_change("spec_limit", "轴径",
                                       {"usl": 10.1, "lsl": 9.9},
                                       change_reason="初始版本", changed_by="张三")
        second = registry.record_change("spec_limit", "轴径",
                                        {"usl": 10.2, "lsl": 9.8},
                                        change_reason="客户放宽公差")
        assert first.valid_to == second.valid_from
        assert second.supersedes == first.record_id
        assert first.record_id.startswith("STD-")
        assert registry.current("轴径") is second
        assert [r.record_id for r in registry.history("轴径")] == [
            first.record_id, second.record_id]

    def test_identical_payload_is_noop(self):
        registry = StandardRegistry()
        first = registry.record_change("spec_limit", "轴径",
                                       {"usl": 10.1, "lsl": 9.9},
                                       change_reason="初始版本")
        again = registry.record_change("spec_limit", "轴径",
                                       {"usl": 10.1, "lsl": 9.9},
                                       change_reason="重复保存")
        assert again.record_id == first.record_id
        assert len(registry) == 1

    def test_missing_reason_rejected(self):
        with pytest.raises(ValueError, match="change_reason"):
            StandardRegistry().record_change(
                "spec_limit", "轴径", {"usl": 1, "lsl": 0}, change_reason=" ")


class TestProjectContextStandards:
    def test_record_specification_updates_characteristic(self):
        ctx = ProjectContext(project_name="P1")
        ctx.add_characteristic(QualityCharacteristic(id="QC-001", name="轴径"))
        first = ctx.record_specification("QC-001", usl=10.1, lsl=9.9,
                                         target=10.0, change_reason="初始版本")
        qc = ctx.get_characteristic("QC-001")
        assert qc.usl == 10.1 and qc.lsl == 9.9 and qc.target == 10.0
        second = ctx.record_specification("QC-001", usl=10.2, lsl=9.8,
                                          target=10.0, change_reason="放宽")
        assert ctx.standards.current("QC-001") is second
        assert first.valid_to == second.valid_from
        assert ctx.standard_as_of("QC-001", first.valid_from) is first

    def test_control_plan_versions_by_row(self):
        ctx = ProjectContext(project_name="P1")
        row = ["OP10", "车削", "轴径", "10±0.05", "卡尺", "5", "每批", "SPC", "隔离"]
        ctx.set_control_plan([row], change_reason="初始控制计划")
        key = "OP10|轴径"
        assert ctx.standards.current(key).payload["row"] == row
        changed = list(row)
        changed[3] = "10±0.08"
        ctx.set_control_plan([changed], change_reason="公差放宽")
        history = ctx.standards.history(key)
        assert len(history) == 2
        assert history[0].payload["row"][3] == "10±0.05"
        assert history[1].payload["row"][3] == "10±0.08"
        ctx.set_control_plan([], change_reason="移除条目")
        assert ctx.standards.current(key).payload["removed"] is True

    def test_roundtrip_and_legacy_migration(self):
        ctx = ProjectContext(project_name="P1")
        ctx.add_characteristic(QualityCharacteristic(
            id="QC-001", name="轴径", usl=10.1, lsl=9.9, target=10.0))
        ctx.record_specification("QC-001", usl=10.1, lsl=9.9, target=10.0,
                                 change_reason="初始版本")
        restored = ProjectContext.from_dict(ctx.to_dict())
        assert len(restored.standards) == 1
        assert restored.standards.current("QC-001").payload["usl"] == 10.1

        legacy = ctx.to_dict()
        legacy.pop("standards")
        migrated = ProjectContext.from_dict(legacy)
        assert len(migrated.standards) == 1
        record = migrated.standards.current("QC-001")
        assert record.origin == "migration"
        assert record.payload["lsl"] == 9.9


class TestResolveAndCredentials:
    def test_resolve_current_and_as_of(self):
        registry = StandardRegistry([
            _record("S1", {"usl": 10.1, "lsl": 9.9}, T1, T2),
            _record("S2", {"usl": 10.2, "lsl": 9.8}, T2),
        ])
        current = resolve_standard_context(registry, ["轴径"])
        assert current["standard_ref"] == "S2"
        historical = resolve_standard_context(registry, ["轴径"], ts="2026-10-01T12:00:00+08:00")
        assert historical["standard_ref"] == "S1"
        by_id = resolve_standard_context(registry, ["S1"])
        assert by_id["standard_ref"] == "S1"
        assert by_id["standard_object_ref"] == "轴径"
        assert resolve_standard_context(registry, ["不存在"]) == {}
        assert resolve_standard_context(None, ["轴径"]) == {}

    def test_trace_code_changes_with_standard_version(self):
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        v1 = make_credential("capability@1", {"standard_ref": "S1"}, df=frame)
        v2 = make_credential("capability@1", {"standard_ref": "S2"}, df=frame)
        assert credential_trace_code([v1]) != credential_trace_code([v2])

    def test_same_data_different_standard_changes_verdict(self):
        rng = np.random.default_rng(7)
        data = pd.Series(rng.normal(10.0, 0.03, 60))
        narrow = _record("S1", {"usl": 10.05, "lsl": 9.95}, T1, T2)
        wide = _record("S2", {"usl": 10.30, "lsl": 9.70}, T2)
        registry = StandardRegistry([narrow, wide])

        old = registry.as_of("轴径", "2026-10-01T12:00:00+08:00")
        new = registry.as_of("轴径", T3)
        result_old = normal_cap.analyze(data, old.payload["usl"], old.payload["lsl"], 10.0)
        result_new = normal_cap.analyze(data, new.payload["usl"], new.payload["lsl"], 10.0)
        assert result_old["capability"]["cpk"] < result_new["capability"]["cpk"]
        assert result_new["capability"]["cpk"] > 1.0


class TestQapStandards:
    def test_standards_section_roundtrip(self):
        registry = StandardRegistry([
            _record("S1", {"usl": 10.1, "lsl": 9.9}, T1, T2),
            _record("S2", {"usl": 10.2, "lsl": 9.8}, T2),
        ])
        with tempfile.NamedTemporaryFile(suffix=".qap", delete=False) as handle:
            path = handle.name
        try:
            ProjectManager.save_project(
                path, {"S": pd.DataFrame({"x": [1]})}, {}, {},
                standards=registry.to_dict())
            project = ProjectManager.load_project(path)
            assert project["manifest"]["standard_count"] == 2
            assert project["manifest"]["has_standards"] is True
            restored = StandardRegistry.from_dict(project["standards"])
            assert restored.as_of(
                "轴径", "2026-10-01T12:00:00+08:00").record_id == "S1"
            assert restored.current("轴径").record_id == "S2"
        finally:
            os.unlink(path)
