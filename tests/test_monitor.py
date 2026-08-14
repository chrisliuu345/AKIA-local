"""实时SPC监控测试 — auto_spc 分派 / FileMonitor 轮询 / MonitorTab 更新 (v2.4 E1)"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from core.file_watcher import pick_numeric_column, auto_spc, FileMonitor
from ui.tabs.monitor_tab import MonitorTab


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _df(values=None, n=30):
    if values is None:
        import numpy as np
        rng = np.random.default_rng(42)
        values = rng.normal(10.0, 1.0, n)
    return pd.DataFrame({"测量值": values, "批次": list(range(1, len(values) + 1))})


# ── auto_spc ─────────────────────────────────────────────
class TestAutoSpc:
    def test_pick_numeric_column(self):
        df = _df()
        assert pick_numeric_column(df) == "测量值"

    def test_imr_when_subgroup_1(self):
        df = _df()
        out = auto_spc(df, "测量值", subgroup_size=1)
        assert out["result"]["chart_type"] == "I-MR"
        assert out["num_points"] == len(df)

    def test_xbar_r_when_subgroup_gt_1(self):
        df = _df(n=40)
        out = auto_spc(df, "测量值", subgroup_size=5)
        assert out["result"]["chart_type"] == "XBar-R"

    def test_no_numeric_column_raises(self):
        df = pd.DataFrame({"名称": ["a"] * 10})
        with pytest.raises(ValueError):
            pick_numeric_column(df)


# ── FileMonitor ──────────────────────────────────────────
class TestFileMonitor:
    def _make_xlsx(self, tmp_path):
        path = tmp_path / "data.xlsx"
        _df(n=30).to_excel(path, index=False)
        return str(path)

    def test_check_once_parses_file(self, tmp_path):
        path = self._make_xlsx(tmp_path)
        payloads = []
        m = FileMonitor(path, payloads.append, interval=0.2)
        payload = m.check_once()
        assert payload["error"] is None
        assert payload["spc"] is not None
        assert payload["num_points"] == 30
        assert payload["column"] == "测量值"

    def test_check_once_missing_file(self, tmp_path):
        m = FileMonitor(str(tmp_path / "nope.xlsx"), lambda p: None)
        payload = m.check_once()
        assert payload["error"] == "文件不存在"
        assert payload["spc"] is None

    def test_start_stop_fast(self, tmp_path):
        path = self._make_xlsx(tmp_path)
        m = FileMonitor(path, lambda p: None, interval=0.2)
        m.start()
        m.stop(timeout=5.0)
        assert not m.is_alive()

    def test_detects_change(self, tmp_path):
        path = self._make_xlsx(tmp_path)
        payloads = []
        m = FileMonitor(path, payloads.append, interval=0.2)
        m.start()
        m.check_once()
        # 修改文件触发一轮轮询
        _df(n=30).to_excel(path, index=False)
        m._last_state = None  # 强制下一轮认为有变化
        import time
        time.sleep(0.6)
        m.stop(timeout=5.0)
        assert len(payloads) >= 1


# ── MonitorTab ───────────────────────────────────────────
class TestMonitorTab:
    def test_toggle_without_file_does_not_start(self, app):
        tab = MonitorTab()
        tab._on_toggle()
        assert tab._monitor is None

    def test_on_update_sets_result_and_emits(self, app):
        import numpy as np
        from analysis.spc.imr import analyze as imr_analyze
        rng = np.random.default_rng(7)
        data = pd.Series(rng.normal(10.0, 1.0, 30))
        spc = imr_analyze(data)

        tab = MonitorTab()
        emitted = []
        tab.analysis_completed.connect(lambda: emitted.append(True))
        payload = {
            "file_path": "demo.xlsx",
            "updated_at": "12:00:00",
            "sheet": "Sheet1",
            "column": "测量值",
            "num_points": 30,
            "violations": 0,
            "spc": spc,
            "error": None,
        }
        tab._on_update(payload)
        assert emitted, "analysis_completed 未发射"
        assert tab.current_result["analysis_type"] == "实时SPC监控"
        assert tab.current_result["result"]["chart_type"] == "I-MR"
        assert tab.canvas is not None

    def test_on_update_error_keeps_old_chart(self, app):
        tab = MonitorTab()
        tab._on_update({"error": "文件不存在"})
        assert tab.current_result == {}
        assert tab.canvas is None
