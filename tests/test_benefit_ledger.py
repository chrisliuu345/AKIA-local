"""收益账本与 COPQ 契约测试（v4.4.0 B0）。"""

import pytest

from core.benefit_ledger import (
    BENEFIT_CATEGORIES,
    BenefitLedger,
    BenefitRecord,
    double_count_key,
)


def _record(**kwargs):
    params = {
        "case_id": "CASE-1", "month": "2026-10",
        "ledger_kind": "improvement", "category": "改善收益",
        "basis": {"baseline_value": 32.0, "new_value": 30.0, "quantity": 1000,
                  "unit_cost": 0.5, "standard_ref": "STD-1",
                  "standard_as_of": "2026-09-01T00:00:00+08:00", "unit": "s"},
        "confidence": "A",
    }
    params.update(kwargs)
    return BenefitRecord(**params)


class TestRecordValidation:
    def test_valid_and_roundtrip(self):
        record = _record()
        restored = BenefitRecord.from_dict(record.to_dict())
        assert restored == record
        assert record.double_count_key == double_count_key(
            "CASE-1", "2026-10", record.basis, "改善收益", "improvement")
        assert record.category in BENEFIT_CATEGORIES

    def test_month_format(self):
        with pytest.raises(ValueError, match="YYYY-MM"):
            _record(month="2026/10")
        with pytest.raises(ValueError, match="YYYY-MM"):
            _record(month="2026-13")

    def test_enums(self):
        with pytest.raises(ValueError, match="非法账本分区"):
            _record(ledger_kind="other")
        with pytest.raises(ValueError, match="非法收益类别"):
            _record(category="其他")
        with pytest.raises(ValueError, match="非法置信分级"):
            _record(confidence="D")
        with pytest.raises(ValueError, match="非法收益来源"):
            _record(source="magic")

    def test_missing_case_and_bad_key(self):
        with pytest.raises(ValueError, match="case_id"):
            _record(case_id=" ")
        with pytest.raises(ValueError, match="double_count_key"):
            _record(double_count_key="deadbeef")

    def test_unknown_schema_rejected(self):
        payload = _record().to_dict()
        payload["schema_version"] = "2"
        with pytest.raises(ValueError, match="schema"):
            BenefitRecord.from_dict(payload)


class TestAmountAndConfidence:
    def test_improvement_amount(self):
        # (32 − 30) × 1000 × 0.5 = 1000
        assert _record().amount == pytest.approx(1000.0)

    def test_improvement_negative_keeps_sign(self):
        record = _record(basis={"baseline_value": 30.0, "new_value": 32.0,
                                "quantity": 10, "unit_cost": 2.0})
        assert record.amount == pytest.approx(-40.0)

    def test_copq_amount(self):
        record = _record(ledger_kind="cost_of_quality", category="内部失败",
                         basis={"quantity": 30, "unit_cost": 5.0})
        assert record.amount == pytest.approx(150.0)

    def test_confidence_gate(self):
        assert _record(confidence="A").admits_to_summary is True
        assert _record(confidence="A-").admits_to_summary is True
        assert _record(confidence="B").admits_to_summary is True
        assert _record(confidence="C").admits_to_summary is False


class TestLedger:
    def test_double_count_rejected(self):
        ledger = BenefitLedger([_record()])
        with pytest.raises(ValueError, match="重复计入"):
            ledger.add(_record(record_id="BEN-OTHER"))
        # 同一口径下"数量变化"仍视为重复（防重复计入的核心语义）
        with pytest.raises(ValueError, match="重复计入"):
            ledger.add(_record(basis={"baseline_value": 32.0, "new_value": 30.0,
                                      "quantity": 500, "unit_cost": 0.5,
                                      "standard_ref": "STD-1",
                                      "standard_as_of":
                                          "2026-09-01T00:00:00+08:00",
                                      "unit": "s"}))
        # 换月份 → 允许
        ledger.add(_record(month="2026-11"))
        assert len(ledger) == 2

    def test_summary_partitions_and_confidence(self):
        ledger = BenefitLedger([
            _record(),
            _record(ledger_kind="cost_of_quality", category="鉴定",
                    basis={"quantity": 200, "unit_cost": 1.0}),
            _record(confidence="C", basis={"baseline_value": 32.0,
                                           "new_value": 29.0,
                                           "quantity": 999, "unit_cost": 1.0}),
        ])
        summary = ledger.summary()
        assert summary["improvement_total"] == pytest.approx(1000.0)
        assert summary["copq_total"] == pytest.approx(200.0)
        assert summary["roi"] == pytest.approx(5.0)
        assert len(summary["pending_records"]) == 1

    def test_roi_none_without_copq(self):
        summary = BenefitLedger([_record()]).summary()
        assert summary["roi"] is None

    def test_month_filter_and_roundtrip(self):
        ledger = BenefitLedger([_record(), _record(month="2026-11",
                                                   basis={"quantity": 1,
                                                          "unit_cost": 1,
                                                          "baseline_value": 1,
                                                          "new_value": 0})])
        assert len(ledger.for_month("2026-11")) == 1
        assert len(ledger.for_case("CASE-1")) == 2
        restored = BenefitLedger.from_dict(ledger.to_dict())
        assert [r.to_dict() for r in restored] == ledger.to_dicts()

    def test_from_dict_none_and_unknown_schema(self):
        assert len(BenefitLedger.from_dict(None)) == 0
        with pytest.raises(ValueError, match="schema"):
            BenefitLedger.from_dict({"schema_version": "9", "records": []})
