"""量具滚动监控测试（v4.4.0 B2）。"""

from datetime import datetime, timedelta, timezone

import pytest

from core.gauge_study import (
    GaugeMonitor,
    GaugeRollingState,
    GaugeStudyPolicy,
    compute_health,
    compute_repeatability,
)
from core.measurement_event import MeasurementEvent

TZ = timezone(timedelta(hours=8))
BASE = datetime(2026, 10, 13, 9, 0, 0, tzinfo=TZ)


class _Clock:
    def __init__(self, start=BASE):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds=0):
        self.now = self.now + timedelta(seconds=seconds)


def _policy(gauge_id="caliper:value", expected=10.0, window=5,
            drift_rule=None, enabled=True):
    rule = {"bias_limit": 0.1} if drift_rule is None else dict(drift_rule)
    return GaugeStudyPolicy(gauge_id=gauge_id, expected_value=expected,
                            window_n=window, drift_rule=rule,
                            enabled=enabled)


def _monitor(**kwargs):
    clock = kwargs.pop("clock", _Clock())
    monitor = GaugeMonitor(clock=clock, **kwargs)
    return monitor, clock


class TestRollingStats:
    def test_window_slides_and_stats(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        outcome = monitor.ingest_values("caliper:value",
                                        [10.0, 10.02, 10.04, 10.06, 10.08])
        assert outcome.n == 5
        state = monitor.states["caliper:value"]
        assert state.repeatability_sigma == pytest.approx(
            round(compute_repeatability([10.0, 10.02, 10.04, 10.06, 10.08]), 8))
        first_bias = state.bias
        monitor.ingest_values("caliper:value", [10.1])
        assert monitor.states["caliper:value"].n == 5  # 窗口滑动
        assert monitor.states["caliper:value"].bias != first_bias
        assert len(monitor.states["caliper:value"].bias_history) == 2

    def test_invalid_inputs(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        with pytest.raises(ValueError, match="未知量具策略"):
            monitor.ingest_values("missing", [1.0])
        with pytest.raises(ValueError, match="不能为空"):
            monitor.ingest_values("caliper:value", [])
        monitor.set_policy(_policy(gauge_id="off", enabled=False))
        with pytest.raises(ValueError, match="已禁用"):
            monitor.ingest_values("off", [1.0])


class TestDriftDetection:
    def test_bias_limit_triggers_drift_and_prompt(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        outcome = monitor.ingest_values("caliper:value", [10.3])
        assert outcome.state == "drift"
        assert any("偏倚" in reason for reason in outcome.drift_reasons)
        assert outcome.prompt is True

    def test_prompt_cooldown(self):
        monitor, clock = _monitor()
        monitor.set_policy(_policy())
        first = monitor.ingest_values("caliper:value", [10.3])
        assert first.prompt is True
        monitor.note_prompted("caliper:value")
        second = monitor.ingest_values("caliper:value", [10.3])
        assert second.state == "drift"
        assert second.prompt is False
        clock.advance(seconds=7200)
        third = monitor.ingest_values("caliper:value", [10.3])
        assert third.prompt is True

    def test_watch_zone(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        outcome = monitor.ingest_values("caliper:value", [10.08])
        assert outcome.state == "watch"
        assert outcome.prompt is False

    def test_mpc_chart_detects_shift(self):
        """基线 12 个小抖动偏倚后注入 3σ+ 跳变 → MPC 判异 → drift。"""
        monitor, _ = _monitor()
        monitor.set_policy(_policy(expected=10.0, window=50, drift_rule={}))
        for value in [10.000, 10.001] * 6:
            monitor.ingest_values("caliper:value", [value])
        outcome = monitor.ingest_values("caliper:value", [12.0])
        assert outcome.state == "drift"
        assert any(reason.startswith("MPC") for reason in outcome.drift_reasons)
        frame = monitor.frame_for("caliper:value")
        assert frame is not None and frame.point_index == 13

    def test_mpc_gated_before_warmup(self):
        """预热不足（<10 点）不因控制图触发漂移。"""
        monitor, _ = _monitor()
        monitor.set_policy(_policy(expected=10.0, window=50, drift_rule={}))
        outcome = monitor.ingest_values("caliper:value", [12.0])
        assert outcome.state != "drift"


class TestHealthScore:
    def test_full_health_cold_start(self):
        score = compute_health(n=10, window_n=10, bias=0.0, sigma=0.0,
                               bias_history=[], bias_limit=None)
        assert score == 100.0

    def test_coverage_penalty(self):
        low = compute_health(n=2, window_n=10, bias=0.0, sigma=0.0,
                             bias_history=[], bias_limit=None)
        assert low == pytest.approx(100 * (0.2 * 0.2 + 0.5 + 0.3), abs=0.1)

    def test_bias_penalty(self):
        score = compute_health(n=10, window_n=10, bias=0.3, sigma=0.0,
                               bias_history=[], bias_limit=0.1)
        assert score < 100
        extreme = compute_health(n=10, window_n=10, bias=10.0, sigma=0.0,
                                 bias_history=[], bias_limit=0.1)
        assert extreme == pytest.approx(0.2 * 100 + 0.3 * 100, abs=0.1)

    def test_stability_penalty(self):
        history = [{"bias": 0.0}] * 6 + [{"bias": 0.5}]
        score = compute_health(n=7, window_n=10, bias=0.5, sigma=0.01,
                               bias_history=history, bias_limit=None)
        assert score < 100


class TestPersistence:
    def test_roundtrip_replays_mpc_history(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy(expected=10.0, window=50, drift_rule={}))
        for value in [10.000, 10.001] * 6:
            monitor.ingest_values("caliper:value", [value], event_id="MEV-1")
        payload = monitor.to_dict()
        assert payload["schema_version"] == "1"
        restored = GaugeMonitor.from_dict(payload)
        state = restored.states["caliper:value"]
        assert state.n == 12
        frame = restored.frame_for("caliper:value")
        assert frame is not None and frame.point_index == 12
        # 重载后续报仍能触发 MPC 判异（判定链延续）
        outcome = restored.ingest_values("caliper:value", [12.0])
        assert outcome.state == "drift"
        assert any(reason.startswith("MPC") for reason in outcome.drift_reasons)

    def test_from_dict_defaults_and_validation(self):
        assert len(GaugeMonitor.from_dict(None).policies) == 0
        with pytest.raises(ValueError, match="schema"):
            GaugeMonitor.from_dict({"schema_version": "9"})
        with pytest.raises(ValueError, match="必须为列表"):
            GaugeMonitor.from_dict({"schema_version": "1", "studies": {}})

    def test_state_without_policy_still_restores(self):
        state = GaugeRollingState(gauge_id="orphan", n=3, bias=0.01,
                                  bias_history=[{"at": "2026-10-13T09:00:00+08:00",
                                                 "bias": 0.01, "sigma": 0.0,
                                                 "n": 3}])
        monitor = GaugeMonitor(states=[state])
        assert monitor.states["orphan"].bias == 0.01
        assert monitor.frame_for("orphan") is not None


class TestEventIngestion:
    def test_match_by_characteristic_and_device_channel(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy(gauge_id="caliper:value"))
        by_char = MeasurementEvent.from_manual(10.0, characteristic_id="caliper:value")
        outcome = monitor.ingest_event(by_char)
        assert outcome is not None and outcome.gauge_id == "caliper:value"
        monitor.set_policy(_policy(gauge_id="line1:size"))
        by_channel = MeasurementEvent.from_manual(
            10.0, device="line1", channel="size")
        outcome = monitor.ingest_event(by_channel)
        assert outcome is not None and outcome.gauge_id == "line1:size"
        assert monitor.event_ids_for("line1:size") == [by_channel.event_id]

    def test_unmatched_and_invalid_events_skipped(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        unmatched = MeasurementEvent.from_manual(1.0, characteristic_id="other")
        assert monitor.ingest_event(unmatched) is None
        invalid = MeasurementEvent.from_manual(
            1.0, characteristic_id="caliper:value", validity="invalid",
            validity_reason="量具异常")
        assert monitor.ingest_event(invalid) is None


class TestConfig:
    def test_remove_policy_and_snapshot(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy())
        monitor.ingest_values("caliper:value", [10.0])
        assert monitor.remove_policy("caliper:value") is True
        assert "caliper:value" not in monitor.policies
        assert "caliper:value" not in monitor.states
        assert monitor.snapshot() == []

    def test_snapshot_fields(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy(drift_rule={"bias_limit": 0.1, "ucl": 0.5,
                                               "lcl": -0.5}))
        monitor.ingest_values("caliper:value", [10.01])
        row = monitor.snapshot()[0]
        assert row["gauge_id"] == "caliper:value"
        assert row["n"] == 1 and row["state"] in ("ok", "watch", "drift")
        assert row["spec_ucl"] == 0.5 and row["spec_lcl"] == -0.5
        assert row["bias_limit"] == 0.1

    def test_policy_window_change_reslices_buffer(self):
        monitor, _ = _monitor()
        monitor.set_policy(_policy(window=5))
        for value in range(5):
            monitor.ingest_values("caliper:value", [10.0 + value * 0.01])
        monitor.set_policy(_policy(window=3))
        outcome = monitor.ingest_values("caliper:value", [10.1])
        assert outcome.n == 3
