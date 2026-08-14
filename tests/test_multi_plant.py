"""多工厂对比测试 — 单厂汇总/对比汇总/Tab 交互 (v2.4 E2)"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from core.plant_compare import summarize_plant, build_comparison
from ui.tabs.multi_plant_tab import MultiPlantTab, MULTI_PLANT_ANALYSIS_TYPE


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _df(n=30, with_spec=False):
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"测量值": rng.normal(10.0, 0.5, n)})
    if with_spec:
        df["USL"] = 11.5
        df["LSL"] = 8.5
    return df


class TestSummarizePlant:
    def test_basic_metrics_no_spec(self, tmp_path):
        path = tmp_path / "plant_a.xlsx"
        _df().to_excel(path, index=False)
        out = summarize_plant(str(path))
        assert not out["error"]
        assert out["sample_size"] == 30
        assert out["column"] == "测量值"
        assert out["mean"] is not None and out["std"] is not None
        assert out["cpk"] is None          # 无规格限列
        assert out["violations"] >= 0

    def test_cpk_with_spec_columns(self, tmp_path):
        path = tmp_path / "plant_b.xlsx"
        _df(with_spec=True).to_excel(path, index=False)
        out = summarize_plant(str(path))
        assert not out["error"]
        assert out["cpk"] is not None
        assert out["usl"] == 11.5 and out["lsl"] == 8.5

    def test_missing_file(self, tmp_path):
        out = summarize_plant(str(tmp_path / "nope.xlsx"))
        assert out["error"] == "文件不存在"


class TestBuildComparison:
    def test_aggregates(self):
        plants = [
            {"name": "A", "error": None, "cpk": 1.6, "violations": 1,
             "mean": 10.0, "std": 0.4, "sample_size": 30},
            {"name": "B", "error": None, "cpk": 1.2, "violations": 3,
             "mean": 11.0, "std": 0.6, "sample_size": 30},
            {"name": "C", "error": "文件不存在", "cpk": None, "violations": 0,
             "mean": None, "std": None, "sample_size": 0},
        ]
        comp = build_comparison(plants)
        assert comp["plant_count"] == 3
        assert comp["ok_count"] == 2
        assert comp["best_cpk"] == 1.6
        assert comp["worst_cpk"] == 1.2
        assert comp["has_cpk"] is True
        assert comp["total_violations"] == 4

    def test_no_cpk(self):
        plants = [{"name": "A", "error": None, "cpk": None, "violations": 0}]
        comp = build_comparison(plants)
        assert comp["has_cpk"] is False
        assert comp["best_cpk"] is None


class TestMultiPlantTab:
    def _make_tab(self):
        tab = MultiPlantTab()
        return tab

    def test_run_produces_result_and_chart(self, app, tmp_path):
        path1 = tmp_path / "p1.xlsx"
        path2 = tmp_path / "p2.xlsx"
        _df().to_excel(path1, index=False)
        _df(with_spec=True).to_excel(path2, index=False)

        tab = self._make_tab()
        emitted = []
        tab.analysis_completed.connect(lambda: emitted.append(1))

        tab._plants = [str(path1), str(path2)]
        tab.file_list.addItem("p1.xlsx")
        tab.file_list.addItem("p2.xlsx")
        tab._on_run()

        assert len(emitted) == 1
        assert tab.current_result["analysis_type"] == MULTI_PLANT_ANALYSIS_TYPE
        result = tab.current_result["result"]
        assert result["plant_count"] == 2
        assert result["ok_count"] == 2
        assert tab.table.rowCount() == 2
        assert tab.canvas is not None
        assert tab.current_figure is not None
        tab.close()
        tab.deleteLater()

    def test_run_without_files_shows_error(self, app):
        tab = self._make_tab()
        emitted = []
        tab.analysis_completed.connect(lambda: emitted.append(1))
        tab._on_run()
        assert not emitted
        assert tab.current_result == {}
        assert tab.canvas is None
        tab.close()
        tab.deleteLater()

    def test_error_plant_shown_in_table(self, app, tmp_path):
        path = tmp_path / "p1.xlsx"
        _df().to_excel(path, index=False)
        bad = str(tmp_path / "missing.xlsx")

        tab = self._make_tab()
        tab._plants = [path, bad]
        tab.file_list.addItem("p1.xlsx")
        tab.file_list.addItem("missing.xlsx")
        tab._on_run()

        assert tab.table.rowCount() == 2
        assert tab.table.item(1, 1).text() == "文件不存在"
        tab.close()
        tab.deleteLater()
