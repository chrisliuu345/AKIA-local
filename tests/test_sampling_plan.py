"""抽样域契约测试（v4.4.0 B0）。"""

import pandas as pd
import pytest

from core.sampling_plan import (
    LOT_DECISIONS,
    SAMPLING_METHODS,
    TRANSFER_STATES,
    LotRecord,
    SamplingDecision,
    TransferDecision,
    TransferState,
    fingerprint_from_frames,
    scope_key_for,
)


def _lot(**kwargs):
    params = {"lot_id": "LOT-1", "qty": 100, "inspected": 20, "defects": 1,
              "decision": "accept"}
    params.update(kwargs)
    return LotRecord(**params)


class TestLotRecord:
    def test_valid_and_roundtrip(self):
        lot = _lot(supplier="供应商A", product="P100", serious=False)
        restored = LotRecord.from_dict(lot.to_dict())
        assert restored == lot
        assert lot.decision in LOT_DECISIONS

    def test_quantity_constraints(self):
        with pytest.raises(ValueError, match="不能超过批量"):
            _lot(qty=10, inspected=20)
        with pytest.raises(ValueError, match="不能超过检验数"):
            _lot(inspected=10, defects=11)
        with pytest.raises(ValueError, match="不能为负"):
            _lot(defects=-1)

    def test_invalid_decision_and_schema(self):
        with pytest.raises(ValueError, match="非法检验批判定"):
            _lot(decision="maybe")
        with pytest.raises(ValueError, match="schema"):
            _lot(schema_version="99")

    def test_empty_lot_id_rejected(self):
        with pytest.raises(ValueError, match="lot_id"):
            _lot(lot_id="  ")


class TestSamplingDecision:
    def test_valid_and_roundtrip(self):
        decision = SamplingDecision(
            scope_key="供应商A|P100", method="systematic", seed=7, n=50,
            aql=1.0, level="II", row_fingerprint="pd-hash-v1:abc",
            note="按转移状态正常检验")
        restored = SamplingDecision.from_dict(decision.to_dict())
        assert restored == decision
        assert decision.method in SAMPLING_METHODS

    def test_invalid_method_and_sample_size(self):
        with pytest.raises(ValueError, match="非法抽样方法"):
            SamplingDecision(method="magic", n=10)
        with pytest.raises(ValueError, match="样本量"):
            SamplingDecision(method="random", n=0)

    def test_unknown_schema_rejected(self):
        payload = SamplingDecision(n=5).to_dict()
        payload["schema_version"] = "2"
        with pytest.raises(ValueError, match="schema"):
            SamplingDecision.from_dict(payload)


class TestTransferContracts:
    def test_state_validation_and_roundtrip(self):
        state = TransferState(scope_key="供应商A|P100", state="tightened")
        restored = TransferState.from_dict(state.to_dict())
        assert restored == state
        with pytest.raises(ValueError, match="scope_key"):
            TransferState(scope_key=" ")
        with pytest.raises(ValueError, match="非法检验状态"):
            TransferState(scope_key="A|B", state="panic")

    def test_decision_changed_flag(self):
        moved = TransferDecision(scope_key="A|B", from_state="normal",
                                 to_state="tightened", rule="r")
        stayed = TransferDecision(scope_key="A|B", from_state="normal",
                                  to_state="normal")
        assert moved.changed is True
        assert stayed.changed is False
        assert stayed.to_dict()["rule"] == ""
        assert set(TRANSFER_STATES) == {"normal", "tightened", "reduced"}

    def test_decision_rejects_invalid_state(self):
        with pytest.raises(ValueError, match="非法转移状态"):
            TransferDecision(scope_key="A", from_state="normal", to_state="?" )


class TestHelpers:
    def test_scope_key_normalizes_empty(self):
        assert scope_key_for("厂商A", "P1") == "厂商A|P1"
        assert scope_key_for("", "") == "-|-"

    def test_fingerprint_single_and_group(self):
        frame = pd.DataFrame({"x": [1.0, 2.0]})
        single = fingerprint_from_frames(frame)
        assert single.startswith("pd-hash-v1:")
        group = fingerprint_from_frames([frame, frame])
        assert group.startswith("pd-hash-v1-group:")
        # 确定性：同输入同输出
        assert fingerprint_from_frames([frame, frame]) == group
        assert fingerprint_from_frames([]) == ""
