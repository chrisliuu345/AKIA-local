"""Vision 基准脚本测试 — 标注解析 / 混淆评估 / 合成自检准确率。"""
import pytest

pytest.importorskip("cv2")

from analysis.vision.action import ActionSegment, ActionState
from tools.vision_benchmark import (
    LabelInterval,
    evaluate,
    load_labels,
    run_demo_benchmark,
)


def test_evaluate_perfect_and_partial():
    segments = [ActionSegment(0, 1000, ActionState.WORKING),
                ActionSegment(1000, 2000, ActionState.WALKING)]
    labels = [LabelInterval(0, 1000, ActionState.WORKING),
              LabelInterval(1000, 2000, ActionState.WALKING)]
    perfect = evaluate(labels, segments)
    assert perfect["accuracy"] == 1.0
    assert perfect["per_state"]["working"]["accuracy"] == 1.0

    shifted = [ActionSegment(0, 500, ActionState.WORKING),
               ActionSegment(500, 2000, ActionState.IDLE)]
    partial = evaluate(labels, shifted)
    assert partial["accuracy"] == pytest.approx(0.25, abs=0.01)
    assert partial["confusion_s"]


def test_load_labels_csv(tmp_path):
    path = tmp_path / "labels.csv"
    path.write_text("start_ms,end_ms,state\n0,1000,working\n1000,2000,走动\n",
                    encoding="utf-8")
    labels = load_labels(path)
    assert [lab.state for lab in labels] == [ActionState.WORKING,
                                             ActionState.WALKING]
    assert labels[1].duration_s == 1.0


def test_load_labels_rejects_unknown_state(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("start_ms,end_ms,state\n0,1000,running\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_labels(path)


def test_demo_benchmark_meets_acceptance():
    report = run_demo_benchmark(sample_fps=10.0)
    assert report["accuracy"] >= 0.85, report
    assert report["per_state"]["working"]["accuracy"] > 0.8
    assert report["per_state"]["walking"]["accuracy"] > 0.8
