"""SPC 已知值 — PELT 变点检测（v4.2.0 P2-3）

来源: Killick, Fearnhead & Eckley (2012), JASA 107(500):1590-1598

覆盖:
1. 与暴力 DP 全局最优解一致（K=0 剪枝时 PELT 精确）—— 独立实现对照
2. 已知均值漂移/方差漂移位置可检出
3. 在纯噪声上不误报（默认 BIC 罚项）
"""

import numpy as np
import pandas as pd
import pytest

from analysis.spc.change_point import detect
from tests.known_values import KnownValueCase, assert_close

_OPTIMAL_CASE = KnownValueCase.with_preset(
    "pelt-vs-dp-optimal-cost", "Killick et al. (2012) 目标函数",
    preset="closed_form",
    reference="PELT 总代价 = 暴力 DP 全局最优代价（同为 SSE + β per segment）",
    notes="SSE 代价 C(a,b) = Σy² − (Σy)²/n，β = σ̂²·log(n)",
)

_DETECT_CASE = KnownValueCase(
    case_id="pelt-mean-shift-location",
    source="合成数据（固定种子）",
    reference="60 点 N(0,1) + 60 点 N(5,1) ⇒ 变点位于索引 60（±2）",
    rel_tol=1e-9, abs_tol=2.0,
    notes="位置容差 ±2 点",
)


def _dp_optimal_cost(y: np.ndarray, pen: float, min_size: int) -> float:
    """测试内独立实现的 O(n²) 全局最优分割代价（与 PELT 同一目标函数）。"""
    n = y.size
    cusum = np.concatenate(([0.0], np.cumsum(y)))
    cusum_sq = np.concatenate(([0.0], np.cumsum(y * y)))

    def cost(a: int, b: int) -> float:
        k = b - a
        total = cusum[b] - cusum[a]
        return max(cusum_sq[b] - cusum_sq[a] - total * total / k, 0.0)

    f = np.full(n + 1, np.inf)
    f[0] = -pen
    for t in range(1, n + 1):
        best = np.inf
        for s in range(t - min_size + 1):
            best = min(best, f[s] + cost(s, t) + pen)
        f[t] = best
    return float(f[n])


class TestPeltOptimality:
    def test_matches_brute_force_optimal_cost(self):
        rng = np.random.default_rng(2)
        y = np.concatenate([rng.normal(0, 1, 30), rng.normal(3, 1, 25),
                            rng.normal(-2, 1, 20)])
        result = detect(y, model="mean", penalty=6.0)
        expected = _dp_optimal_cost(y, 6.0, min_size=2)
        assert_close(result["cost"], expected, _OPTIMAL_CASE, context="总代价")

    def test_matches_brute_force_on_multiple_penalties(self):
        rng = np.random.default_rng(3)
        y = np.concatenate([rng.normal(0, 1, 20), rng.normal(2, 1, 20),
                            rng.normal(0, 1, 20)])
        for pen in (1.0, 4.0, 25.0):
            result = detect(y, model="mean", penalty=pen)
            expected = _dp_optimal_cost(y, pen, min_size=2)
            assert_close(result["cost"], expected, _OPTIMAL_CASE,
                         context=f"β={pen}")


class TestPeltDetection:
    def test_mean_shift_location(self):
        rng = np.random.default_rng(42)
        y = np.concatenate([rng.normal(0, 1, 60), rng.normal(5, 1, 60)])
        result = detect(y)
        assert result["num_changes"] == 1, f"5σ 漂移应只检出 1 个变点: {result['changepoints']}"
        assert abs(result["changepoints"][0] - 60) <= 2
        means = [segment["mean"] for segment in result["segments"]]
        assert means[0] == pytest.approx(0.0, abs=0.6)
        assert means[-1] == pytest.approx(5.0, abs=0.6)
        assert result["changepoints"] == pd.Series(result["changepoints"]).sort_values().tolist()

    def test_variance_shift_detected_with_meanvar_model(self):
        rng = np.random.default_rng(5)
        y = np.concatenate([rng.normal(0, 1, 80), rng.normal(0, 6, 80)])
        result = detect(y, model="meanvar")
        assert result["num_changes"] >= 1
        assert any(abs(cp - 80) <= 3 for cp in result["changepoints"])

    def test_no_false_positives_on_pure_noise(self):
        total_changes = 0
        for seed in range(20):
            rng = np.random.default_rng(seed)
            total_changes += detect(rng.normal(size=150))["num_changes"]
        assert total_changes <= 3, f"纯噪声误报过多: {total_changes} 个变点/20 序列"

    def test_constant_series_reports_no_change(self):
        result = detect(np.full(50, 3.14))
        assert result["num_changes"] == 0
        assert "常量" in result["reason"]

    def test_short_series_returns_empty_result(self):
        result = detect([1.0, 2.0, 3.0], min_size=5)
        assert result["num_changes"] == 0
        assert result["cost"] is None

    def test_validation_errors(self):
        with pytest.raises(ValueError):
            detect(np.zeros(10), model="bogus")
        with pytest.raises(ValueError):
            detect(np.array([]))
        with pytest.raises(ValueError):
            detect(np.arange(10.0), min_size=0)
        with pytest.raises(ValueError):
            detect(np.arange(10.0), penalty=-1.0)
