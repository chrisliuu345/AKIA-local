"""技能约束排班测试（v4.4.0 B5）——LPT 不受破坏 + 约束求解与不可行明细。"""

import pytest

from analysis.ie.line_balance import LineBalanceEngine
from core.data_objects import Process
from core.skill_matrix import ProcessSkillReq, SkillMatrix


def _processes(count: int = 4, ct: float = 10.0) -> list[Process]:
    return [Process(process_id=f"P{i}", process_name=f"工序{i}", cycle_time=ct)
            for i in range(1, count + 1)]


def _full_matrix(level: int = 3, operators=("张三", "李四"),
                 requirements=None) -> SkillMatrix:
    entries = []
    for operator in operators:
        for i in range(1, 5):
            entries.append({"operator": operator, "process_id": f"P{i}",
                            "level": level})
    return SkillMatrix(entries=entries,
                       requirements=list(requirements or []))


class TestScheduleBasics:
    def test_feasible_roster(self):
        plan = LineBalanceEngine.schedule_with_skills(
            _processes(), 20.0, _full_matrix())
        assert plan.feasible is True
        assert len(plan.assignments) == 4  # 2 工位 × 2 工序
        operators = {item["operator"] for item in plan.assignments}
        assert operators == {"张三", "李四"}  # 一人一工位
        assert plan.balance_rate_before == plan.balance_rate_after == 1.0
        assert plan.plan_ref.startswith("skill-hash-v1:")
        for item in plan.assignments:
            assert item["start_s"] == 0.0 and item["end_s"] == 20.0

    def test_original_lpt_untouched(self):
        base = LineBalanceEngine().analyze(_processes(), 20.0)
        assert base["error"] is None
        assert base["balanced"]["station_count"] == 2

    def test_deterministic_output(self):
        first = LineBalanceEngine.schedule_with_skills(
            _processes(), 20.0, _full_matrix()).to_dict()
        second = LineBalanceEngine.schedule_with_skills(
            _processes(), 20.0, _full_matrix()).to_dict()
        assert first == second

    def test_invalid_processes_raise(self):
        with pytest.raises(ValueError, match="有效工序不足"):
            LineBalanceEngine.schedule_with_skills(
                [Process(process_id="P1", process_name="a", cycle_time=0.0)],
                10.0, _full_matrix())


class TestConstraints:
    def test_skill_gap_partial_assignment(self):
        matrix = SkillMatrix(
            entries=[{"operator": operator, "process_id": f"P{i}", "level": 2}
                     for operator in ("王五", "赵六") for i in range(1, 5)],
            requirements=[ProcessSkillReq("P3", min_level=4).to_dict()])
        plan = LineBalanceEngine.schedule_with_skills(_processes(), 20.0, matrix)
        assert plan.feasible is False
        assert plan.balance_rate_after is None
        assert any("技能不满足" in reason for reason in plan.unmet)
        assert plan.assignments  # 可行工位照常指派（不静默降级为全空）

    def test_requirement_level_enforced(self):
        matrix = _full_matrix(level=2,
                              requirements=[ProcessSkillReq("P3", 3).to_dict()])
        plan = LineBalanceEngine.schedule_with_skills(_processes(), 20.0, matrix)
        assert plan.feasible is False
        # P3 所在工位不可派，其余工位仍指派
        assigned = {item["process_id"] for item in plan.assignments}
        assert "P3" not in assigned and assigned

    def test_unlisted_process_counts_unqualified(self):
        matrix = SkillMatrix(entries=[
            {"operator": "甲", "process_id": "P1", "level": 5},
            {"operator": "乙", "process_id": "P2", "level": 5}])
        plan = LineBalanceEngine.schedule_with_skills(
            _processes(2), 20.0, matrix)
        assert plan.feasible is False
        assert any("技能不满足" in reason for reason in plan.unmet)

    def test_headcount_shortage(self):
        plan = LineBalanceEngine.schedule_with_skills(
            _processes(), 20.0, _full_matrix(), headcount=1)
        assert plan.feasible is False
        assert any("可用人数不足" in reason for reason in plan.unmet)
        assert any("无剩余人员可派" in reason for reason in plan.unmet)

    def test_equipment_parallel_capacity(self):
        processes = [
            Process(process_id="P1", process_name="a", cycle_time=10.0,
                    equipment="车床"),
            Process(process_id="P2", process_name="b", cycle_time=10.0,
                    equipment="车床"),
        ]
        plan = LineBalanceEngine.schedule_with_skills(
            processes, 10.0, _full_matrix(), equipment_parallel={"车床": 1})
        assert plan.feasible is False
        assert any("并发需求 2 超出上限 1" in reason for reason in plan.unmet)
        assert plan.constraints["equipment_concurrent"] == {"车床": 2}
        ok = LineBalanceEngine.schedule_with_skills(
            processes, 10.0, _full_matrix(), equipment_parallel={"车床": 2})
        assert ok.feasible is True

    def test_empty_matrix_reports_unmet(self):
        plan = LineBalanceEngine.schedule_with_skills(_processes(), 20.0,
                                                      SkillMatrix())
        assert plan.feasible is False
        assert plan.assignments == []
        assert any("技能矩阵为空" in reason for reason in plan.unmet)


class TestMatrixExtensions:
    def test_requirements_roundtrip_and_min_level(self):
        matrix = _full_matrix(requirements=[
            ProcessSkillReq("P1", 2).to_dict(),
            ProcessSkillReq("P3", 4).to_dict()])
        assert matrix.min_level_for("P3") == 4
        assert matrix.min_level_for("P9") is None
        restored = SkillMatrix.from_dict(matrix.to_dict())
        assert restored == matrix
        assert restored.min_level_for("P1") == 2

    def test_invalid_requirement_rejected(self):
        with pytest.raises(ValueError, match="最低技能等级"):
            ProcessSkillReq("P1", 6)
        with pytest.raises(ValueError, match="process_id"):
            ProcessSkillReq("  ", 2)
        with pytest.raises(ValueError, match="重复"):
            SkillMatrix(requirements=[{"process_id": "P1", "min_level": 2},
                                      {"process_id": "P1", "min_level": 3}])

    def test_fingerprint_stable_and_sensitive(self):
        left = _full_matrix()
        right = SkillMatrix.from_dict(left.to_dict())
        assert left.fingerprint() == right.fingerprint()
        assert left.fingerprint().startswith("skill-hash-v1:")
        changed = _full_matrix(level=4)
        assert changed.fingerprint() != left.fingerprint()
        with_req = _full_matrix(requirements=[
            ProcessSkillReq("P1", 2).to_dict()])
        assert with_req.fingerprint() != left.fingerprint()
