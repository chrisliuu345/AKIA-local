"""收益账本复算与案例入账测试（v4.4.0 B4）。"""

from types import SimpleNamespace

import pytest

from core.benefit_ledger import (
    BenefitLedger,
    BenefitRecord,
    double_count_key,
    month_bounds,
    record_case_benefit,
    resolve_standard_basis,
)
from core.standard_record import StandardRegistry


def _registry():
    registry = StandardRegistry()
    first = registry.record_change(
        "standard_time", "OP10", {"standard_time_s": 30.0},
        change_reason="初始标准工时", changed_by="user")
    return registry, first


class TestMonthBounds:
    def test_normal_and_leap(self):
        start, end = month_bounds("2026-02")
        assert start.day == 1 and end.day == 28 and end.hour == 23
        start, end = month_bounds("2028-02")  # 闰年
        assert end.day == 29
        start, end = month_bounds("2026-12")
        assert start.month == 12 and end.day == 31

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="YYYY-MM"):
            month_bounds("2026/02")
        with pytest.raises(ValueError, match="YYYY-MM"):
            month_bounds("")


class TestResolveStandardBasis:
    def test_by_object_ref_and_record_id(self):
        registry, first = _registry()
        by_ref = resolve_standard_basis(registry, ["OP10"])
        assert by_ref["standard_ref"] == first.record_id
        assert by_ref["standard_as_of"] == first.valid_from
        assert by_ref["standard_object_ref"] == "OP10"
        by_id = resolve_standard_basis(registry, [first.record_id])
        assert by_id["standard_ref"] == first.record_id

    def test_empty_inputs(self):
        registry, _ = _registry()
        assert resolve_standard_basis(None, ["OP10"]) == {}
        assert resolve_standard_basis(registry, []) == {}
        assert resolve_standard_basis(registry, ["不存在"]) == {}


class TestRecordCaseBenefit:
    def test_amount_basis_and_event(self):
        registry, first = _registry()
        ledger = BenefitLedger()
        events = []
        case = SimpleNamespace(id="CASE-1", standard_refs=["OP10"])
        record = record_case_benefit(
            ledger, case, month="2026-10", baseline_value=32.0,
            new_value=30.0, quantity=1000, unit_cost=0.5, unit="s",
            currency="CNY", confidence="A", standards=registry,
            event_sink=lambda *args: events.append(args))
        assert record.amount == pytest.approx(1000.0)
        assert record.basis["standard_ref"] == first.record_id
        assert record.basis["currency"] == "CNY"
        assert events[0][0] == "benefit_recorded"
        assert events[0][2]["amount"] == pytest.approx(1000.0)
        assert events[0][1][0] == "case:CASE-1"

    def test_missing_case_id_rejected(self):
        with pytest.raises(ValueError, match="无法入账"):
            record_case_benefit(BenefitLedger(), SimpleNamespace(id=""),
                                month="2026-10")

    def test_standard_upgrade_does_not_open_second_booking(self):
        registry, _ = _registry()
        ledger = BenefitLedger()
        case = SimpleNamespace(id="CASE-1", standard_refs=["OP10"])
        record_case_benefit(ledger, case, month="2026-10",
                            baseline_value=32.0, new_value=30.0,
                            quantity=1000, unit_cost=0.5, standards=registry)
        registry.record_change("standard_time", "OP10",
                               {"standard_time_s": 28.0},
                               change_reason="改善后标准", changed_by="user")
        with pytest.raises(ValueError, match="重复计入"):
            record_case_benefit(ledger, case, month="2026-10",
                                baseline_value=32.0, new_value=29.0,
                                quantity=1000, unit_cost=0.5,
                                standards=registry)

    def test_key_ignores_standard_version(self):
        basis_a = {"unit": "s", "unit_cost": 0.5,
                   "standard_ref": "STD-A", "standard_as_of": "2026-10-01"}
        basis_b = {"unit": "s", "unit_cost": 0.5,
                   "standard_ref": "STD-B", "standard_as_of": "2026-10-10"}
        assert double_count_key("C1", "2026-10", basis_a, "改善收益",
                                "improvement") == \
            double_count_key("C1", "2026-10", basis_b, "改善收益",
                             "improvement")


class TestRecompute:
    def _seed(self, registry, month: str, ledger: BenefitLedger,
              case_id: str = "CASE-1") -> BenefitRecord:
        case = SimpleNamespace(id=case_id, standard_refs=["OP10"])
        return record_case_benefit(
            ledger, case, month=month, baseline_value=32.0, new_value=30.0,
            quantity=100, unit_cost=1.0, confidence="A", standards=registry)

    def test_historical_month_frozen(self):
        registry, first = _registry()
        ledger = BenefitLedger()
        record = self._seed(registry, "2026-09", ledger)
        registry.record_change("standard_time", "OP10",
                               {"standard_time_s": 28.0},
                               change_reason="改善后标准", changed_by="user")
        events = []
        result = ledger.recompute_month(
            "2026-09", standards=registry,
            now="2026-10-14T12:00:00+08:00",
            event_sink=lambda *args: events.append(args))
        assert result["frozen"] is True
        assert result["updates"] == []
        assert record.basis["standard_as_of"] == first.valid_from
        assert events == []  # 历史月复算不产生事件

    def test_current_month_advances_standard_version(self):
        registry, first = _registry()
        ledger = BenefitLedger()
        record = self._seed(registry, "2026-10", ledger)
        second = registry.record_change("standard_time", "OP10",
                                        {"standard_time_s": 28.0},
                                        change_reason="改善后标准",
                                        changed_by="user")
        amount_before = record.amount
        events = []
        result = ledger.recompute_month(
            "2026-10", standards=registry,
            now="2026-10-14T12:00:00+08:00",
            event_sink=lambda *args: events.append(args))
        assert result["frozen"] is False
        assert len(result["updates"]) == 1
        update = result["updates"][0]
        assert update["old_as_of"] == first.valid_from
        assert update["new_as_of"] == second.valid_from
        assert record.basis["standard_ref"] == second.record_id
        assert record.amount == amount_before  # 金额仍按案例测量口径
        assert events and events[0][0] == "benefit_recomputed"
        assert events[0][2]["new_as_of"] == second.valid_from

    def test_recompute_without_standards_is_noop(self):
        registry, _ = _registry()
        ledger = BenefitLedger()
        self._seed(registry, "2026-10", ledger)
        result = ledger.recompute_month("2026-10",
                                        now="2026-10-14T12:00:00+08:00")
        assert result["updates"] == []
        assert result["frozen"] is False


class TestSummaryAndBreakdown:
    def _ledger_with_mix(self) -> BenefitLedger:
        ledger = BenefitLedger()
        ledger.add(BenefitRecord(
            case_id="C1", month="2026-10", ledger_kind="improvement",
            category="改善收益", confidence="A",
            basis={"baseline_value": 10, "new_value": 8, "quantity": 100,
                   "unit_cost": 1}))
        ledger.add(BenefitRecord(
            case_id="C2", month="2026-10", ledger_kind="cost_of_quality",
            category="内部失败", confidence="B",
            basis={"quantity": 50, "unit_cost": 2}))
        ledger.add(BenefitRecord(
            case_id="C3", month="2026-10", ledger_kind="cost_of_quality",
            category="鉴定", confidence="C",
            basis={"quantity": 30, "unit_cost": 1}))
        ledger.add(BenefitRecord(
            case_id="C4", month="2026-09", ledger_kind="cost_of_quality",
            category="预防", confidence="B",
            basis={"quantity": 10, "unit_cost": 3}))
        return ledger

    def test_month_filter_and_pending(self):
        ledger = self._ledger_with_mix()
        summary = ledger.summary("2026-10")
        assert summary["improvement_total"] == pytest.approx(200.0)
        assert summary["copq_total"] == pytest.approx(100.0)  # C 级(30)不计
        assert summary["roi"] == pytest.approx(2.0)
        assert summary["pending_count"] == 1
        assert summary["count"] == 3
        assert summary["copq_breakdown"]["内部失败"] == pytest.approx(100.0)
        assert summary["copq_breakdown"]["鉴定"] == 0.0  # C 级排除

    def test_breakdown_all_months(self):
        ledger = self._ledger_with_mix()
        breakdown = ledger.cost_breakdown()
        assert breakdown["预防"] == pytest.approx(30.0)
        assert breakdown["内部失败"] == pytest.approx(100.0)
