"""抽样透明化收口测试（v4.4.0 B6）——统一抽样决定 + 三类入口标注。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

from core.sampling_note import (
    SamplingNote,
    seeded_sample_indices,
    thin_indices,
)


class TestSamplingNoteContract:
    def test_validation(self):
        with pytest.raises(ValueError, match="未知抽样层"):
            SamplingNote(layer="magic", method="none", source_count=1,
                         sampled_count=1)
        with pytest.raises(ValueError, match="未知抽样方法"):
            SamplingNote(layer="chart", method="magic", source_count=1,
                         sampled_count=1)
        with pytest.raises(ValueError, match="不能超过"):
            SamplingNote(layer="chart", method="systematic", source_count=1,
                         sampled_count=2)

    def test_label_texts(self):
        assert SamplingNote(layer="chart", method="none", source_count=10,
                            sampled_count=10).label() == ""
        stride = SamplingNote(layer="trend", method="stride", source_count=5000,
                              sampled_count=1000, kept_count=4,
                              detail="趋势图等距抽稀")
        label = stride.label()
        assert "原始 5000 点" in label and "抽样至 1000 点" in label
        assert "强制保留 4 点" in label and "可复现" in label
        seeded = SamplingNote(layer="profiler", method="seeded_random",
                              source_count=10000, sampled_count=5000, seed=42)
        assert "种子 42（可复现）" in seeded.label()

    def test_roundtrip_and_unknown_schema(self):
        note = SamplingNote(layer="chart", method="systematic",
                            source_count=100, sampled_count=30, kept_count=2)
        assert SamplingNote.from_dict(note.to_dict()) == note
        payload = note.to_dict()
        payload["schema_version"] = "9"
        with pytest.raises(ValueError, match="schema"):
            SamplingNote.from_dict(payload)


class TestThinIndices:
    def test_no_thin_when_under_limit(self):
        indices, note = thin_indices(100, 300)
        assert indices == list(range(100))
        assert note.method == "none" and note.label() == ""

    def test_thinning_deterministic_and_keeps_violations(self):
        first, note = thin_indices(1000, 300, keep=(17, 512, 999),
                                   layer="chart", detail="图表智能系统抽样")
        second, _ = thin_indices(1000, 300, keep=(17, 512, 999),
                                 layer="chart", detail="图表智能系统抽样")
        assert first == second
        assert len(first) <= 300
        assert {17, 512, 999} <= set(first)
        assert note.kept_count == 3
        assert note.source_count == 1000
        label = note.label()
        assert "判异" not in label  # 具体措辞在 detail 中
        assert "强制保留 3 点" in label and "可复现" in label

    def test_plain_stride_has_no_kept(self):
        indices, note = thin_indices(5000, 1000, layer="trend",
                                     method="stride")
        assert note.kept_count == 0
        assert len(indices) == 1000


class TestSeededSampleIndices:
    def test_deterministic_and_seed_sensitive(self):
        first, note = seeded_sample_indices(10000, 5000, seed=42,
                                            detail="大样本正态检验抽样")
        second, _ = seeded_sample_indices(10000, 5000, seed=42)
        other, _ = seeded_sample_indices(10000, 5000, seed=7)
        assert first == second
        assert first != other
        assert len(first) == 5000
        assert note.method == "seeded_random" and note.seed == 42
        assert "种子 42（可复现）" in note.label()

    def test_full_when_under_size(self):
        indices, note = seeded_sample_indices(100, 5000, seed=1)
        assert indices == list(range(100)) and note.method == "none"


class TestChartThinning:
    def test_smart_thin_note_and_kept_points(self):
        from output.chart_engine import _smart_thin

        data = list(np.linspace(0, 1, 1000))
        violations = [{"point": 50, "rule": 1}, {"point": 800, "rule": 2}]
        thinned, _labels, was_thinned, note = _smart_thin(data, violations)
        assert was_thinned is True
        assert len(thinned) <= 300
        assert data[49] in thinned and data[799] in thinned
        assert "强制保留 2 点" in note and "可复现" in note
        again, _, _, note2 = _smart_thin(data, violations)
        assert again == thinned and note2 == note

    def test_small_series_not_thinned(self):
        from output.chart_engine import _smart_thin

        data = list(range(100))
        thinned, _labels, was_thinned, note = _smart_thin(data, [])
        assert was_thinned is False and note == ""
        assert thinned == data


class TestProfilerSampling:
    def test_head_sample_is_labeled(self):
        from core.data_profiler import DataProfiler

        frame = pd.DataFrame({"x": np.arange(12000.0)})
        result = DataProfiler().profile({"S": frame})
        sheet = result["sheets"]["S"]
        assert "画像预览抽样" in sheet["sampling_note"]
        assert "可复现" in sheet["sampling_note"]
        assert sheet["sampling_decision"]["method"] == "head"
        assert sheet["sampling_decision"]["source_count"] == 12000

    def test_normality_sampling_seeded_and_reproducible(self):
        from core.data_profiler import (
            NORMALITY_SAMPLE_MAX,
            NORMALITY_SAMPLE_SEED,
            DataProfiler,
        )

        rng = np.random.default_rng(3)
        frame = pd.DataFrame({"x": rng.normal(0, 1, NORMALITY_SAMPLE_MAX + 2000)})
        profiler = DataProfiler(sample_size=NORMALITY_SAMPLE_MAX + 5000)
        first = profiler.profile({"S": frame})["sheets"]["S"]
        second = profiler.profile({"S": frame})["sheets"]["S"]
        column_first = first["columns"][0]
        column_second = second["columns"][0]
        assert column_first["normality_sample"]["seed"] == NORMALITY_SAMPLE_SEED
        assert column_first["normality_sample"]["n"] == NORMALITY_SAMPLE_MAX
        assert "种子" in column_first["normality_sample_note"]
        assert column_first["normality_pvalue"] == \
            column_second["normality_pvalue"]  # 固定种子 → 可复现

    def test_small_column_has_no_normality_note(self):
        from core.data_profiler import DataProfiler

        frame = pd.DataFrame({"x": np.arange(500.0)})
        sheet = DataProfiler().profile({"S": frame})["sheets"]["S"]
        column = sheet["columns"][0]
        assert not column.get("normality_sample_note")


class TestTrendTabNote:
    def test_trend_title_carries_sampling_note(self):
        pytest.importorskip("PySide6")
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        from ui.tabs.trend_tab import TrendTab

        tab = TrendTab()
        try:
            frame = pd.DataFrame({
                "t": pd.date_range("2026-01-01", periods=2500, freq="min"),
                "v": np.arange(2500.0),
            })
            tab.set_data(frame)
            index = tab.date_combo.findText("t")
            tab.date_combo.setCurrentIndex(index)
            for i in range(tab.val_list.count()):
                if tab.val_list.item(i).text() == "v":
                    tab.val_list.item(i).setSelected(True)
            tab._run()
            app.processEvents()
            title = tab.current_figure.axes[0].get_title()
            assert "抽样至" in title and "可复现" in title
            assert "原始 2500 点" in title
        finally:
            tab.close()
