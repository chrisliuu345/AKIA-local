"""技能域契约测试（v4.4.0 B0）。"""

import pytest

from core.skill_matrix import SchedulePlan, SkillMatrix


def _matrix():
    return SkillMatrix(entries=[
        {"operator": "张三", "process_id": "OP10", "level": 4},
        {"operator": "张三", "process_id": "OP20", "level": 3},
        {"operator": "李四", "process_id": "OP10", "level": 2},
        {"operator": "王五", "process_id": "OP20", "level": 5},
    ])


class TestSkillMatrix:
    def test_valid_and_roundtrip(self):
        matrix = _matrix()
        restored = SkillMatrix.from_dict(matrix.to_dict())
        assert restored == matrix
        assert len(matrix) == 4

    def test_duplicate_pair_rejected(self):
        with pytest.raises(ValueError, match="重复"):
            SkillMatrix(entries=[
                {"operator": "张三", "process_id": "OP10", "level": 3},
                {"operator": "张三", "process_id": "OP10", "level": 4},
            ])

    def test_level_range_and_missing_fields(self):
        with pytest.raises(ValueError, match="技能等级"):
            SkillMatrix(entries=[{"operator": "张三", "process_id": "OP10",
                                  "level": 6}])
        with pytest.raises(ValueError, match="缺少"):
            SkillMatrix(entries=[{"operator": "", "process_id": "OP10",
                                  "level": 3}])

    def test_queries(self):
        matrix = _matrix()
        assert matrix.level_of("张三", "OP10") == 4
        assert matrix.level_of("赵六", "OP10") is None
        assert matrix.operators_for("OP10") == ["张三", "李四"]
        assert matrix.operators_for("OP10", min_level=3) == ["张三"]
        assert matrix.processes_for("张三") == ["OP10", "OP20"]

    def test_unknown_schema_rejected(self):
        payload = _matrix().to_dict()
        payload["schema_version"] = "3"
        with pytest.raises(ValueError, match="schema"):
            SkillMatrix.from_dict(payload)


class TestSchedulePlan:
    def test_valid_and_roundtrip(self):
        plan = SchedulePlan(
            assignments=[{"process_id": "OP10", "operator": "张三",
                          "start_s": 0.0, "end_s": 30.0}],
            constraints={"takt_s": 32.0, "headcount": 3},
            balance_rate_before=0.72, balance_rate_after=0.88,
            plan_ref="STD-1")
        restored = SchedulePlan.from_dict(plan.to_dict())
        assert restored == plan
        assert plan.feasible is True

    def test_invalid_assignments(self):
        with pytest.raises(ValueError, match="缺少"):
            SchedulePlan(assignments=[{"process_id": "OP10"}])
        with pytest.raises(ValueError, match="早于"):
            SchedulePlan(assignments=[{"process_id": "OP10", "operator": "张三",
                                       "start_s": 10, "end_s": 5}])

    def test_unmet_marks_infeasible(self):
        plan = SchedulePlan(unmet=["OP30 无满足技能等级的人员"])
        assert plan.feasible is False
        assert SchedulePlan.from_dict(None) is None

    def test_unknown_schema_rejected(self):
        payload = SchedulePlan().to_dict()
        payload["schema_version"] = "9"
        with pytest.raises(ValueError, match="schema"):
            SchedulePlan.from_dict(payload)
