"""测量在线域契约测试（v4.4.0 B0）。"""

from datetime import datetime, timedelta

import pytest

from core.gauge_study import (
    GAUGE_STATES,
    GaugeRollingState,
    GaugeStudyPolicy,
    compute_bias,
    compute_repeatability,
)


class TestPolicy:
    def test_valid_and_roundtrip(self):
        policy = GaugeStudyPolicy(
            gauge_id="caliper-1:value", standard_ref="STD-1",
            expected_value=10.0, window_n=10,
            drift_rule={"bias_limit": 0.05})
        restored = GaugeStudyPolicy.from_dict(policy.to_dict())
        assert restored == policy

    def test_validation(self):
        with pytest.raises(ValueError, match="gauge_id"):
            GaugeStudyPolicy(gauge_id=" ")
        with pytest.raises(ValueError, match="窗口"):
            GaugeStudyPolicy(gauge_id="g", window_n=1)
        with pytest.raises(ValueError, match="未知漂移规则键"):
            GaugeStudyPolicy(gauge_id="g", drift_rule={"magic": 1})
        with pytest.raises(ValueError, match="成对"):
            GaugeStudyPolicy(gauge_id="g", drift_rule={"ucl": 1.0})

    def test_unknown_schema_rejected(self):
        payload = GaugeStudyPolicy(gauge_id="g").to_dict()
        payload["schema_version"] = "9"
        with pytest.raises(ValueError, match="schema"):
            GaugeStudyPolicy.from_dict(payload)


class TestRollingState:
    def test_valid_and_roundtrip(self):
        state = GaugeRollingState(
            gauge_id="g", n=12, repeatability_sigma=0.01, bias=0.002,
            bias_history=[{"at": "2026-10-12T10:00:00+08:00", "bias": 0.002}],
            health_score=92.5, state="watch")
        restored = GaugeRollingState.from_dict(state.to_dict())
        assert restored == state
        assert state.state in GAUGE_STATES

    def test_validation(self):
        with pytest.raises(ValueError, match="健康分"):
            GaugeRollingState(gauge_id="g", health_score=101)
        with pytest.raises(ValueError, match="非法量具状态"):
            GaugeRollingState(gauge_id="g", state="broken")
        with pytest.raises(ValueError, match="有限数"):
            GaugeRollingState(gauge_id="g", bias=float("nan"))

    def test_prompt_cooldown(self):
        now = datetime.now().astimezone()
        recent = GaugeRollingState(
            gauge_id="g",
            last_prompt_at=(now - timedelta(seconds=30)).isoformat(timespec="seconds"))
        old = GaugeRollingState(
            gauge_id="g",
            last_prompt_at=(now - timedelta(hours=2)).isoformat(timespec="seconds"))
        assert recent.prompt_cooldown_active(600, now=now) is True
        assert old.prompt_cooldown_active(600, now=now) is False
        assert GaugeRollingState(gauge_id="g").prompt_cooldown_active(600) is False


class TestPureHelpers:
    def test_repeatability(self):
        assert compute_repeatability([10.0, 10.0, 10.0]) == 0.0
        value = compute_repeatability([10.0, 11.0])
        assert value == pytest.approx(0.7071, abs=1e-4)
        assert compute_repeatability([1.0]) == 0.0
        assert compute_repeatability([]) == 0.0

    def test_bias(self):
        assert compute_bias([10.1, 10.3], 10.0) == pytest.approx(0.2)
        assert compute_bias([], 10.0) == 0.0
        assert compute_bias([10.0, None, float("nan")], 10.0) == 0.0
