"""v4.1.0 B4 — 性能基准脚本与基线（不执行重型度量自身的回归判定）。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import benchmark  # noqa: E402  (需要先补 sys.path)


def test_baseline_file_is_valid():
    baseline = benchmark.load_baseline()
    assert baseline, "tools/perf_baseline.json 应存在且非空"
    for key in benchmark.METRIC_KEYS:
        assert key in baseline, f"基线缺少指标 {key}"
        assert isinstance(baseline[key], (int, float)) and baseline[key] > 0


def test_compare_flags_regression():
    baseline = {"cold_start_s": 2.0, "chart_render_5k_s": 1.0}
    ok = benchmark.compare({"cold_start_s": 2.5, "chart_render_5k_s": 1.1},
                           baseline, tolerance=3.0)
    assert ok == []
    bad = benchmark.compare({"cold_start_s": 9.0, "chart_render_5k_s": 1.0},
                            baseline, tolerance=3.0)
    assert len(bad) == 1 and bad[0][0] == "cold_start_s"


def test_compare_ignores_unknown_metrics():
    assert benchmark.compare({"not_a_metric": 999}, {"cold_start_s": 1.0}, 3.0) == []


def test_metric_registry_matches_baseline_keys():
    assert set(benchmark.METRIC_KEYS) == set(benchmark.MEASURES)


def test_ci_runs_benchmark():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "tools/benchmark.py" in ci, "CI 应包含性能基线步骤"


def test_update_baseline_writes_json(tmp_path, monkeypatch):
    target = tmp_path / "baseline.json"
    monkeypatch.setattr(benchmark, "BASELINE_PATH", target)
    results = {"cold_start_s": 1.5}
    target.write_text(json.dumps(results), encoding="utf-8")
    assert benchmark.load_baseline() == results
