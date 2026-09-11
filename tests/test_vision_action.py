"""动作分类测试 — 规则判定 / 迟滞 / 状态段与占比（无 OpenCV 依赖）。"""
from analysis.vision.action import (
    ACTION_LABELS,
    ActionClassifier,
    ActionConfig,
    ActionState,
    classify_pose,
    duration_by_state,
    ratio_by_state,
)
from analysis.vision.pose import PoseFrame


def _pose(ts, *, present=True, speed=0.0, energy=0.0, activity=0.0, arm_swing=0.0,
          wrists_low=False, landmarks=False):
    return PoseFrame(ts_ms=ts, person_present=present, backend="test",
                     landmarks=[(0.5, 0.5, 0.0, 1.0)] if landmarks else [],
                     motion_energy=energy, activity_energy=activity,
                     speed_px_s=speed,
                     arm_swing=arm_swing, wrists_low=wrists_low)


def test_rule_classification_states():
    cfg = ActionConfig()
    assert classify_pose(_pose(0, present=False), cfg) == ActionState.AWAY
    assert classify_pose(_pose(0, speed=80), cfg) == ActionState.WALKING
    assert classify_pose(_pose(0, speed=80, landmarks=True, wrists_low=True,
                               arm_swing=0.02), cfg) == ActionState.CARRYING
    assert classify_pose(_pose(0, energy=0.05), cfg) == ActionState.WORKING
    assert classify_pose(_pose(0, activity=0.004), cfg) == ActionState.WORKING
    assert classify_pose(_pose(0, arm_swing=0.2), cfg) == ActionState.WORKING
    assert classify_pose(_pose(0, energy=0.001), cfg) == ActionState.IDLE


def test_hysteresis_ignores_brief_blip():
    classifier = ActionClassifier(ActionConfig(min_dwell_ms=500))
    ts = 0.0
    for _ in range(10):                       # 工作 1s
        classifier.update(_pose(ts, energy=0.05))
        ts += 100
    for _ in range(2):                        # 走动 0.2s（短于迟滞）
        classifier.update(_pose(ts, speed=120))
        ts += 100
    for _ in range(10):                       # 回到工作
        classifier.update(_pose(ts, energy=0.05))
        ts += 100
    classifier.finish(ts)
    states = [seg.state for seg in classifier.segments()]
    assert states == [ActionState.WORKING]


def test_sustained_transition_creates_segments():
    classifier = ActionClassifier(ActionConfig(min_dwell_ms=300))
    ts = 0.0
    for _ in range(10):                       # 工作 1s
        classifier.update(_pose(ts, energy=0.05))
        ts += 100
    for _ in range(10):                       # 走动 1s
        classifier.update(_pose(ts, speed=120))
        ts += 100
    classifier.finish(ts)
    segments = classifier.segments()
    assert [s.state for s in segments] == [ActionState.WORKING, ActionState.WALKING]
    # 迟滞窗口归入新状态：候选首次出现 1.0s 处切换，1.0s 后确认
    assert segments[0].duration_s == 1.0
    assert segments[1].duration_s == 1.0
    durations = duration_by_state(segments)
    assert durations["working"] == 1.0
    ratios = ratio_by_state(segments)
    assert sum(ratios.values()) == 100.0
    assert ratios["walking"] == 50.0
    assert ACTION_LABELS[ActionState.WORKING] == "工作"


def test_empty_and_finish_are_safe():
    classifier = ActionClassifier()
    assert classifier.segments() == []
    classifier.finish()
    assert ratio_by_state([]) == {}
    assert duration_by_state([]) == {}
