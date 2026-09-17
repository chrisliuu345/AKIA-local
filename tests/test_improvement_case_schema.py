"""test_improvement_case_schema.py — P0 改善案例 schema v0 契约测试"""

import pytest

from core.improvement_case import (
    CASE_PHASES,
    CASE_SCHEMA_VERSION,
    ImprovementCase,
)


class TestImprovementCase:
    def test_create_defaults(self):
        case = ImprovementCase(id="CASE-001", title="节拍改善")
        assert case.status == "active"
        assert case.schema_version == CASE_SCHEMA_VERSION
        assert case.created_at and case.updated_at
        assert case.baseline_refs == []
        assert case.steps == []

    def test_add_step_records_phase_and_timestamp(self):
        case = ImprovementCase(id="CASE-002")
        step = case.add_step("baseline", ref="sheet:工时", note="改善前")
        assert step["phase"] == "baseline"
        assert step["ref"] == "sheet:工时"
        assert step["at"] == case.updated_at
        assert len(case.steps) == 1
        assert CASE_PHASES[0] == "baseline"

    def test_add_step_rejects_empty_phase(self):
        case = ImprovementCase(id="CASE-003")
        with pytest.raises(ValueError):
            case.add_step("")

    def test_roundtrip(self):
        case = ImprovementCase(id="CASE-004", title="换型改善",
                               baseline_refs=["sheet:baseline"],
                               conclusion_refs=["cred:1"], standard_draft="ST-1")
        case.add_step("improve", ref="smed:plan")
        restored = ImprovementCase.from_dict(case.to_dict())
        assert restored.to_dict() == case.to_dict()

    def test_from_dict_ignores_unknown_keys(self):
        data = ImprovementCase(id="CASE-005").to_dict()
        data["future_field"] = {"ignored": True}
        assert ImprovementCase.from_dict(data).id == "CASE-005"

    def test_rejects_invalid_fields(self):
        with pytest.raises(ValueError):
            ImprovementCase(id="")
        with pytest.raises(ValueError):
            ImprovementCase(id="CASE-006", status="unknown")
        with pytest.raises(ValueError):
            ImprovementCase(id="CASE-007", baseline_refs=[1, 2])
        with pytest.raises(ValueError):
            ImprovementCase(id="CASE-008", schema_version="99")

    def test_from_dict_requires_id(self):
        with pytest.raises(ValueError):
            ImprovementCase.from_dict({"title": "no id"})

    def test_from_dict_rejects_unknown_schema(self):
        with pytest.raises(ValueError):
            ImprovementCase.from_dict({"id": "CASE-009", "schema_version": "99"})
