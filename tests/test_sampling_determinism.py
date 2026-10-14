"""确定性抽样测试（v4.4.0 B3）——同参数重跑样本逐行一致。"""

import numpy as np
import pandas as pd
import pytest

from core.sampling_engine import SamplingEngine
from core.sampling_plan import fingerprint_from_frames


def _frame(rows: int = 1000, groups=("A", "B", "C", "D")) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.DataFrame({
        "value": rng.normal(10, 1, rows),
        "group": rng.choice(groups, rows),
    })


class TestSeededDeterminism:
    @pytest.mark.parametrize("method", ["random", "stratified", "systematic"])
    def test_same_params_identical_rows(self, method):
        frame = _frame()
        kwargs = {"column": "group"} if method == "stratified" else {}
        first = SamplingEngine.sample_frame(
            frame, method=method, n=60, seed=42, **kwargs)
        second = SamplingEngine.sample_frame(
            frame, method=method, n=60, seed=42, **kwargs)
        assert first.equals(second)
        assert fingerprint_from_frames(first) == fingerprint_from_frames(second)

    def test_different_seed_changes_systematic_start(self):
        frame = _frame()
        results = {fingerprint_from_frames(SamplingEngine.sample_frame(
            frame, method="systematic", n=10, seed=seed))
            for seed in range(6)}
        assert len(results) > 1  # 不同种子覆盖不同起点（至少出现两种）

    def test_fingerprint_changes_with_data(self):
        frame = _frame()
        left = SamplingEngine.sample_frame(frame, method="random", n=20, seed=1)
        changed = frame.copy()
        changed["value"] = changed["value"] + 1.0  # 整列偏移：任一抽中行必不同
        right = SamplingEngine.sample_frame(changed, method="random", n=20, seed=1)
        assert fingerprint_from_frames(left) != fingerprint_from_frames(right)

    def test_stratified_group_seeds_are_derived(self):
        frame = _frame()
        base = SamplingEngine.stratified_sample(frame, "group", 40, seed=7)
        shifted = SamplingEngine.stratified_sample(frame, "group", 40, seed=8)
        assert base.equals(SamplingEngine.stratified_sample(
            frame, "group", 40, seed=7))
        assert not base.equals(shifted)  # 派生种子：不同种子的组内样本不同


class TestSampleFrameDispatch:
    def test_method_case_insensitive(self):
        frame = _frame()
        assert SamplingEngine.sample_frame(
            frame, method="SYSTEMATIC", n=10, seed=3).equals(
            SamplingEngine.sample_frame(frame, method="systematic", n=10, seed=3))

    def test_unknown_method_rejected(self):
        with pytest.raises(ValueError, match="不支持的表格抽样方法"):
            SamplingEngine.sample_frame(_frame(), method="magic", n=10)

    def test_stratified_requires_column(self):
        with pytest.raises(ValueError, match="分层列"):
            SamplingEngine.sample_frame(_frame(), method="stratified", n=10)
        with pytest.raises(ValueError, match="不存在"):
            SamplingEngine.stratified_sample(_frame(), "missing", 10)

    def test_sample_size_guards(self):
        frame = _frame(rows=50)
        with pytest.raises(ValueError, match="≥ 1"):
            SamplingEngine.random_sample(frame, 0)
        with pytest.raises(ValueError, match="≥ 1"):
            SamplingEngine.systematic_sample(frame, -3)
        full = SamplingEngine.random_sample(frame, 50)
        assert len(full) == 50
        assert full.equals(frame.reset_index(drop=True))

    def test_systematic_non_divisible_rows(self):
        frame = _frame(rows=97)
        sampled = SamplingEngine.systematic_sample(frame, 10, seed=5)
        assert len(sampled) <= 10
        assert len(sampled) >= 9  # 97/9 ≈ 每 9 行取一，接近目标
