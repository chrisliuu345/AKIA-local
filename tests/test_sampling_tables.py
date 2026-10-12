"""GB/T 2828.1 抽样表正确性回归（v4.4.0 B0 重建）。

背景：v4.3.0 及以前的 `_NORMAL_TABLE` 与标准原表不符（A~H 行数字格错位、
J/K 行完全相同、箭头与检验水平未实现、加严/放宽表缺失）。本文件固化重建后的
交叉验证结果：知识库节选逐格一致、Re=Ac+1、接收数梯单调、R5 带心带宽、
箭头解析、检验水平与转移规则确定性。
"""

import math

import numpy as np
import pytest

from core.sampling_engine import (
    _ARROW_DOWN,
    _ARROW_UP,
    _AQL_VALS,
    _LOT_RANGES,
    _NORMAL_CELLS,
    _REDUCED_CELLS,
    _REDUCED_SAMPLE_SIZE,
    _SAMPLE_SIZES,
    _TIGHTENED_CELLS,
    SamplingEngine,
)
from core.sampling_plan import LotRecord

#: 随包知识库《AQL 正常检验抽样表（一般检验水平 II，节选）》的字码→批量代表值
LOT_FOR_CODE = {"A": 5, "B": 12, "C": 20, "D": 30, "E": 70, "F": 120,
                "G": 200, "H": 400, "J": 600, "K": 2000, "L": 5000,
                "M": 20000, "N": 100000, "P": 300000, "Q": 700000}

#: 知识库节选（11 行 × 5 个 AQL 的 Ac/Re）
KB_EXCERPT = {
    "A": {"0.65": "0/1", "1.0": "0/1", "1.5": "0/1", "2.5": "0/1", "4.0": "0/1"},
    "B": {"0.65": "0/1", "1.0": "0/1", "1.5": "0/1", "2.5": "0/1", "4.0": "0/1"},
    "C": {"0.65": "0/1", "1.0": "0/1", "1.5": "0/1", "2.5": "0/1", "4.0": "0/1"},
    "D": {"0.65": "0/1", "1.0": "0/1", "1.5": "0/1", "2.5": "0/1", "4.0": "1/2"},
    "E": {"0.65": "0/1", "1.0": "0/1", "1.5": "0/1", "2.5": "1/2", "4.0": "1/2"},
    "F": {"0.65": "0/1", "1.0": "0/1", "1.5": "1/2", "2.5": "1/2", "4.0": "2/3"},
    "G": {"0.65": "0/1", "1.0": "1/2", "1.5": "1/2", "2.5": "2/3", "4.0": "3/4"},
    "H": {"0.65": "1/2", "1.0": "1/2", "1.5": "2/3", "2.5": "3/4", "4.0": "5/6"},
    "J": {"0.65": "1/2", "1.0": "2/3", "1.5": "3/4", "2.5": "5/6", "4.0": "7/8"},
    "K": {"0.65": "2/3", "1.0": "3/4", "1.5": "5/6", "2.5": "7/8", "4.0": "10/11"},
    "L": {"0.65": "3/4", "1.0": "5/6", "1.5": "7/8", "2.5": "10/11", "4.0": "14/15"},
}

_LADDER = [1, 2, 3, 5, 7, 10, 14, 21, 30, 44, 60, 80, 100, 120, 150, 200,
           250, 315, 400, 500, 650, 800, 1000]
_CENTERS = [0.5, 0.8, 1.25, 2, 3.15, 5, 8, 12.5, 20, 31.5, 50, 80, 125,
            200, 315, 500, 800, 1250, 2000, 3150, 5000, 8000, 12500]


def _center(ac: int) -> float:
    """接收数 → n·AQL 带心（R5 序列，对数插值）。"""
    if ac <= 0:
        return 0.125
    return float(np.exp(np.interp(math.log(ac), np.log(_LADDER),
                                  np.log(_CENTERS))))


class TestKnowledgeBaseExcerpt:
    def test_all_excerpt_cells_match(self):
        """随包知识库节选 55 格（含箭头解析后的 Ac/Re）逐格一致。"""
        checked = 0
        for code, cells in KB_EXCERPT.items():
            for aql, expected in cells.items():
                result = SamplingEngine.aql_lookup(
                    LOT_FOR_CODE[code], float(aql), "II")
                got = f"{result['accept']}/{result['reject']}"
                assert got == expected, (
                    f"{code}@AQL{aql}: 期望 {expected} 实际 {got}")
                checked += 1
        assert checked == 55


class TestTableStructure:
    def test_re_equals_ac_plus_one(self):
        for name, table in (("正常", _NORMAL_CELLS), ("加严", _TIGHTENED_CELLS),
                            ("放宽", _REDUCED_CELLS)):
            for code, row in table.items():
                for cell in row:
                    if isinstance(cell, tuple):
                        assert cell[1] == cell[0] + 1, f"{name} {code} {cell}"

    def test_rows_cover_full_aql_axis(self):
        for table in (_NORMAL_CELLS, _TIGHTENED_CELLS, _REDUCED_CELLS):
            for row in table.values():
                assert len(row) == len(_AQL_VALS)
                assert all(cell in (_ARROW_DOWN, _ARROW_UP)
                           or isinstance(cell, tuple) for cell in row)

    def test_acceptance_ladder_non_decreasing_along_aql(self):
        for code, row in _NORMAL_CELLS.items():
            numbers = [cell[0] for cell in row if isinstance(cell, tuple)]
            assert numbers == sorted(numbers), f"{code} 行接收数梯不单调"

    def test_resolved_acceptance_non_decreasing_with_lot_size(self):
        """同一 AQL 下，批量越大（字码越靠后）接收数不应变小。"""
        order = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L",
                 "M", "N", "P", "Q"]
        for aql in (1.0, 2.5):
            values = [SamplingEngine.aql_lookup(LOT_FOR_CODE[code], aql,
                                                "II")["accept"]
                      for code in order]
            assert values == sorted(values), f"AQL{aql} 非单调: {values}"

    def test_band_rule_all_numeric_cells(self):
        """表 2-A 全部数字格：n·AQL 落在接收数对应 R5 带心带宽内。"""
        ratios = []
        for code, row in _NORMAL_CELLS.items():
            n = _SAMPLE_SIZES[code]
            for idx, cell in enumerate(row):
                if not isinstance(cell, tuple):
                    continue
                lam = n * _AQL_VALS[idx] / 100.0
                ratios.append(lam / _center(cell[0]))
        assert min(ratios) > 0.7, f"带心比过低: {min(ratios):.3f}"
        assert max(ratios) < 1.45, f"带心比过高: {max(ratios):.3f}"
        assert abs(float(np.median(ratios)) - 1.0) < 0.02


class TestArrowResolution:
    def test_down_arrow_uses_plan_below(self):
        # 批量 26~50（字码 D）@AQL4.0 为 ↓，应采用 E 行（n=13）的 1/2
        result = SamplingEngine.aql_lookup(30, 4.0)
        assert result["via_arrow"] is True
        assert result["plan_code"] == "E"
        assert result["sample_size"] == 13
        assert (result["accept"], result["reject"]) == (1, 2)

    def test_up_arrow_uses_plan_above(self):
        # 批量 26~50（字码 D）@AQL2.5 为 ↑，应采用 C 行（n=5）的 0/1
        result = SamplingEngine.aql_lookup(30, 2.5)
        assert result["via_arrow"] is True
        assert result["plan_code"] == "C"
        assert result["sample_size"] == 5
        assert (result["accept"], result["reject"]) == (0, 1)

    def test_resolution_is_deterministic(self):
        first = SamplingEngine.aql_lookup(700000, 0.01)
        second = SamplingEngine.aql_lookup(700000, 0.01)
        assert first == second


class TestInspectionModesAndLevels:
    def test_level_codes_table_one(self):
        assert SamplingEngine.get_code(500, "I") == "F"
        assert SamplingEngine.get_code(500, "II") == "H"
        assert SamplingEngine.get_code(500, "III") == "J"
        assert SamplingEngine.get_code(500, "S-1") == "B"
        with pytest.raises(ValueError, match="未知检验水平"):
            SamplingEngine.get_code(500, "IV")
        assert SamplingEngine.get_code(1) == "A"  # 批量 <2 按 2 处理

    def test_level_ii_matches_legacy_mapping(self):
        """水平 II 的字码与 v4.3.0 的固定映射一致（仅验证兼容性）。"""
        legacy = {5: "A", 12: "B", 20: "C", 30: "D", 70: "E", 120: "F",
                  200: "G", 400: "H", 600: "J", 2000: "K"}
        for lot, code in legacy.items():
            assert SamplingEngine.get_code(lot) == code

    def test_tightened_plan(self):
        result = SamplingEngine.aql_lookup(2000, 1.0, inspection="tightened")
        assert result["inspection"] == "tightened"
        assert (result["sample_size"], result["accept"], result["reject"]) == \
            (125, 2, 3)

    def test_reduced_plan_uses_reduced_sample_size(self):
        # 行业确认值（AQL2.5）：K → 5/6（n_red=50）、L → 6/7（n_red=80）
        k = SamplingEngine.aql_lookup(2000, 2.5, inspection="reduced")
        l = SamplingEngine.aql_lookup(5000, 2.5, inspection="reduced")
        assert (k["sample_size"], k["accept"], k["reject"]) == (50, 5, 6)
        assert (l["sample_size"], l["accept"], l["reject"]) == (80, 6, 7)
        assert _REDUCED_SAMPLE_SIZE["K"] == 50
        assert _REDUCED_SAMPLE_SIZE["L"] == 80

    def test_unknown_inspection_rejected(self):
        with pytest.raises(ValueError, match="未知检验严格度"):
            SamplingEngine.aql_lookup(1000, 1.0, inspection="strict")

    def test_lot_ranges_cover_table_one(self):
        assert _LOT_RANGES[0][0] == 2 and _LOT_RANGES[-1][1] is None
        for _, _, codes in _LOT_RANGES:
            assert len(codes) == 7


def _lot(decision: str, lot_id: str, serious: bool = False) -> LotRecord:
    return LotRecord(lot_id=lot_id, qty=100, inspected=20,
                     defects=0 if decision == "accept" else 3,
                     decision=decision, serious=serious)


class TestTransferRuleBook:
    def test_normal_to_tightened_two_consecutive_rejects(self):
        decision = SamplingEngine.evaluate_transfer(
            "normal", [_lot("reject", "L1"), _lot("reject", "L2")])
        assert decision.to_state == "tightened"
        assert decision.rule == "two_consecutive_rejects"
        assert decision.triggering_lots == ["L1", "L2"]

    def test_single_reject_keeps_normal(self):
        decision = SamplingEngine.evaluate_transfer("normal", [_lot("reject", "L1")])
        assert decision.to_state == "normal"
        assert decision.changed is False

    def test_serious_nonconformity_immediate_tightened(self):
        decision = SamplingEngine.evaluate_transfer(
            "normal", [_lot("accept", "L1"), _lot("reject", "L2", serious=True)])
        assert decision.to_state == "tightened"
        assert decision.rule == "serious_nonconformity"

    def test_tightened_to_normal_five_accepts(self):
        lots = [_lot("accept", f"L{i}") for i in range(5)]
        decision = SamplingEngine.evaluate_transfer("tightened", lots)
        assert decision.to_state == "normal"
        assert decision.rule == "five_consecutive_accepts"
        interrupted = [_lot("accept", f"L{i}") for i in range(4)] + [_lot("reject", "L5")]
        assert SamplingEngine.evaluate_transfer(
            "tightened", interrupted).changed is False

    def test_reduced_disabled_by_default(self):
        lots = [_lot("accept", f"L{i}") for i in range(10)]
        default = SamplingEngine.evaluate_transfer("normal", lots)
        enabled = SamplingEngine.evaluate_transfer(
            "normal", lots, reduced_enabled=True)
        assert default.changed is False
        assert enabled.to_state == "reduced"
        assert enabled.rule == "ten_consecutive_accepts"
        unstable = SamplingEngine.evaluate_transfer(
            "normal", lots, reduced_enabled=True, production_stable=False)
        assert unstable.changed is False

    def test_reduced_back_to_normal(self):
        by_reject = SamplingEngine.evaluate_transfer(
            "reduced", [_lot("accept", "L1"), _lot("reject", "L2")])
        assert by_reject.to_state == "normal"
        assert by_reject.rule == "lot_rejected"
        by_unstable = SamplingEngine.evaluate_transfer(
            "reduced", [_lot("accept", "L1")], production_stable=False)
        assert by_unstable.to_state == "normal"
        assert by_unstable.rule == "production_unstable"

    def test_deterministic_trajectory(self):
        """同一事故序列重放，状态轨迹逐点一致（确定性）。"""
        sequence = [
            ("accept", False), ("reject", False), ("reject", False),
            ("accept", False), ("accept", False), ("accept", False),
            ("accept", False), ("accept", False),
        ]
        lots = [_lot(d, f"L{i}", serious) for i, (d, serious) in enumerate(sequence)]

        def replay():
            state = "normal"
            trajectory = [state]
            for idx in range(1, len(lots) + 1):
                decision = SamplingEngine.evaluate_transfer(
                    state, lots[:idx], reduced_enabled=True)
                state = decision.to_state
                trajectory.append(state)
            return trajectory

        assert replay() == replay()

    def test_invalid_state_rejected(self):
        with pytest.raises(ValueError, match="非法检验状态"):
            SamplingEngine.evaluate_transfer("panic", [])

    def test_non_lot_items_ignored(self):
        decision = SamplingEngine.evaluate_transfer(
            "normal", [{"decision": "reject"}, None])
        assert decision.changed is False
