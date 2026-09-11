"""工时研究引擎测试 — 计时列取值（observation_time 优先 / cycle 回退）与标准工时。"""
import pandas as pd

from analysis.ie.time_study import TimeStudyEngine
from core.data_objects import TimeObservation


def _obs(process="P1", operator="OP1", cycle=1, seconds=10.0):
    return TimeObservation(process, operator, cycle, seconds)


def test_observation_time_preferred_over_cycle():
    """V0 修复：旧实现误用 cycle 列，3 次观测 11/12/13 秒会算成均值 2。"""
    result = TimeStudyEngine.analyze(
        [_obs(cycle=1, seconds=11.0), _obs(cycle=2, seconds=12.0),
         _obs(cycle=3, seconds=13.0)])
    stats = result["results"][0]
    assert stats["avg_time"] == 12.0
    assert stats["stats"]["n"] == 3
    assert result["summary"]["overall_stats"]["mean"] == 12.0


def test_fallback_to_cycle_when_no_observation_time():
    """旧数据只有 cycle 计时列（observation_time=0）时保持向后兼容。"""
    result = TimeStudyEngine.analyze(
        [_obs(cycle=8.0, seconds=0.0), _obs(cycle=9.0, seconds=0.0),
         _obs(cycle=10.0, seconds=0.0)])
    assert result["results"][0]["avg_time"] == 9.0


def test_mixed_rows_fall_back_per_row():
    result = TimeStudyEngine.analyze([
        _obs(cycle=2.0, seconds=0.0),      # 回退 cycle=2
        _obs(cycle=99.0, seconds=20.0),    # 用 observation_time=20（cycle 为序号）
    ])
    assert result["results"][0]["avg_time"] == 11.0


def test_grouping_by_process_and_operator():
    result = TimeStudyEngine.analyze([
        _obs("P1", "OP1", 1, 10.0), _obs("P1", "OP1", 2, 12.0),
        _obs("P1", "OP2", 1, 20.0),
        _obs("P2", "OP1", 1, 30.0),
    ])
    keys = {(r["process_id"], r["operator"]) for r in result["results"]}
    assert keys == {("P1", "OP1"), ("P1", "OP2"), ("P2", "OP1")}


def test_standard_time_formula():
    result = TimeStudyEngine.analyze(
        [_obs(seconds=10.0), _obs(seconds=20.0)], rating=1.1, allowance_pct=10.0)
    row = result["results"][0]
    assert row["avg_time"] == 15.0
    assert row["normal_time"] == 16.5
    assert row["standard_time"] == 18.15


def test_outliers_removed_before_stats():
    times = pd.Series([10.0, 10.1, 10.2, 10.0, 10.1, 99.0])
    clean, outliers = TimeStudyEngine.remove_outliers(times)
    assert 5 in outliers
    assert len(clean) == 5
    assert clean.max() < 11.0


def test_capability_uses_observation_time():
    result = TimeStudyEngine.analyze(
        [_obs(cycle=i, seconds=40.0 + i) for i in range(1, 6)],
        takt_time=50.0)
    cap = result["results"][0]["capability"]
    assert cap["available"] is True
    assert cap["mean"] == 43.0
    assert cap["takt_time"] == 50.0
    assert cap["can_meet_takt"] is True


def test_empty_input_returns_invalid():
    result = TimeStudyEngine.analyze([])
    assert result["valid"] is False
