#!/usr/bin/env python3
"""性能基准（v4.1.0 B4）— 冷启动 / 百万行导入 / 图表渲染 / 模型训练。

用法:
    python tools/benchmark.py                  # 与 tools/perf_baseline.json 比较
    python tools/benchmark.py --update-baseline  # 用本次结果更新基线
    python tools/benchmark.py --json           # 机器可读输出
    python tools/benchmark.py --tolerance 4    # 放宽回归判定倍数

判定: 实测值 > max(基线 × tolerance, 基线 + 0.5s) 视为回归，退出码 1。
基线在开发机测得，CI 用较宽 tolerance 捕获数量级劣化（而非抖动）。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplcache")

BASELINE_PATH = Path(__file__).resolve().parent / "perf_baseline.json"
METRIC_KEYS = ("cold_start_s", "import_1m_rows_s", "chart_render_5k_s",
               "ml_train_5k_s")
DEFAULT_TOLERANCE = 3.0


def _timed(fn):
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def measure_cold_start() -> float:
    """Qt 应用 + 主窗口构建耗时（离屏）。"""
    def _run():
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        from ui.main_window import MainWindow

        window = MainWindow()
        window.close()
        window.deleteLater()
        app.processEvents()

    return _timed(_run)


def _big_frame(rows: int = 1_000_000):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "测量值": rng.normal(10, 0.2, rows),
        "温度": rng.normal(60, 3, rows),
        "压力": rng.normal(5, 0.4, rows),
        "产线": rng.choice(["L1", "L2", "L3"], rows),
        "班次": rng.choice(["早", "晚"], rows),
        "子组": (np.arange(rows) % 5).astype(str),
    })


def measure_import_1m_rows() -> float:
    """百万行数据体检 + 数值列识别（DataParser / DataProfiler 路径）。"""
    def _run():
        from core.data_parser import DataParser

        frame = _big_frame()
        parser = DataParser()
        cleaned, info = parser.prepare(frame)
        parser.refresh_info(cleaned, info)

    return _timed(_run)


def measure_chart_render_5k() -> float:
    """5000 点控制图渲染 + PNG 编码（含智能抽样）。"""
    def _run():
        import numpy as np

        from output.chart_engine import create_control_chart, figure_to_bytes

        rng = np.random.default_rng(11)
        data = list(rng.normal(10, 0.1, 5000))
        chart_data = {"chart_type": "I-MR",
                      "i_chart": {"data": data, "cl": 10.0,
                                  "ucl": 10.3, "lcl": 9.7, "violations": []},
                      "mr_chart": {"data": data[1:], "cl": 0.1,
                                   "ucl": 0.4, "lcl": 0.0, "violations": []}}
        figure_to_bytes(create_control_chart(chart_data, title="bench"))

    return _timed(_run)


def measure_ml_train_5k() -> float:
    """5000 行 × 5 特征的 CART 训练 + 指标（见 analysis/ml）。"""
    def _run():
        import numpy as np
        import pandas as pd

        from analysis.ml import train

        rng = np.random.default_rng(13)
        n = 5000
        frame = pd.DataFrame({f"x{i}": rng.normal(size=n) for i in range(5)})
        frame["y"] = (2 * frame["x0"] - frame["x1"] + rng.normal(0, 0.3, n))
        train.fit_pipeline(frame, "y", [f"x{i}" for i in range(5)],
                           model="tree", cv=3, test_size=0.2)

    return _timed(_run)


MEASURES = {
    "cold_start_s": measure_cold_start,
    "import_1m_rows_s": measure_import_1m_rows,
    "chart_render_5k_s": measure_chart_render_5k,
    "ml_train_5k_s": measure_ml_train_5k,
}


def run_one(key: str) -> float:
    return round(float(MEASURES[key]()), 3)


def run_all(only=None, *, isolate: bool = True) -> dict:
    """逐项测量；默认每项独立子进程（隔离内存与字体/Qt 状态）。"""
    keys = [k for k in METRIC_KEYS if not only or k in only]
    if not isolate:
        return {key: run_one(key) for key in keys}
    results = {}
    for key in keys:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--run-one", key],
            capture_output=True, text=True, timeout=900,
            check=False,
            env={**os.environ, "MPLCONFIGDIR": "/tmp/mplcache",
                 "QT_QPA_PLATFORM": "offscreen"})
        if proc.returncode != 0:
            raise SystemExit(f"[benchmark] {key} 执行失败:\n{proc.stderr[-1500:]}")
        results.update(json.loads(proc.stdout.strip().splitlines()[-1]))
    return results


def load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def compare(results: dict, baseline: dict, tolerance: float) -> list:
    regressions = []
    for key, value in results.items():
        limit = baseline.get(key)
        if limit is None:
            continue
        allowed = max(float(limit) * float(tolerance), float(limit) + 0.5)
        if value > allowed:
            regressions.append((key, value, limit, allowed))
    return regressions


def main() -> int:
    parser = argparse.ArgumentParser(description="QA-Tool 性能基准")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--only", default="")
    parser.add_argument("--run-one", default="")
    parser.add_argument("--in-process", action="store_true",
                        help="同一进程内测量（调试用，可能受内存状态影响）")
    args = parser.parse_args()

    if args.run_one:
        if args.run_one not in MEASURES:
            raise SystemExit(f"未知指标: {args.run_one}")
        print(json.dumps({args.run_one: run_one(args.run_one)}, ensure_ascii=False))
        return 0

    only = {k.strip() for k in args.only.split(",") if k.strip()}
    results = run_all(only or None, isolate=not args.in_process)

    if args.update_baseline:
        BASELINE_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                 encoding="utf-8")

    if args.json:
        print(json.dumps(results, ensure_ascii=False))
    else:
        print("性能基准结果（秒）:")
        for key, value in results.items():
            print(f"  {key:22s} {value:8.3f}")

    baseline = load_baseline() if not args.update_baseline else results
    regressions = compare(results, baseline, args.tolerance)
    if regressions:
        print("\n性能回归:")
        for key, value, limit, allowed in regressions:
            print(f"  {key}: {value:.3f}s > 允许 {allowed:.3f}s（基线 {limit:.3f}s）")
        return 1
    if baseline:
        print(f"\n性能基线检查通过（tolerance ×{args.tolerance}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
