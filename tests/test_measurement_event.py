"""MeasurementEvent v1 契约测试（v4.3.0 B0-1）。"""

import math
from datetime import datetime

import pandas as pd
import pytest

from core.devices.driver import Sample
from core.evidence import fingerprint_dataframe
from core.measurement_event import (
    CLOCK_SKEW_TOLERANCE_S,
    INLINE_VALUE_LIMIT,
    MeasurementEvent,
    fingerprint_values,
    summarize_values,
    timeseries_ref,
)


class TestSummary:
    def test_statistics(self):
        summary = summarize_values([1.0, 2.0, 3.0, 4.0])
        assert summary["n"] == 4
        assert summary["mean"] == pytest.approx(2.5)
        assert summary["std"] == pytest.approx(1.2909944487358056)
        assert summary["min"] == 1.0
        assert summary["max"] == 4.0

    def test_single_value_std_is_zero(self):
        assert summarize_values([5.0])["std"] == 0.0

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="空序列"):
            summarize_values([])

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_rejected(self, bad):
        with pytest.raises(ValueError, match="NaN/Inf"):
            summarize_values([1.0, bad])

    def test_fingerprint_is_stable_and_value_sensitive(self):
        left = fingerprint_values([1.0, 2.0])
        assert left == fingerprint_values([1.0, 2.0])
        assert left.startswith("pd-hash-v1:")
        assert left != fingerprint_values([1.0, 2.1])


class TestManualEvent:
    def test_defaults_and_raw_ref(self):
        event = MeasurementEvent.from_manual(10.0, characteristic_id="QC-001")
        assert event.source_kind == "manual"
        assert event.summary["n"] == 1
        assert event.values == [10.0]
        assert event.fingerprint.startswith("pd-hash-v1:")
        assert event.raw_ref == f"manual://{event.event_id}"
        assert event.validity == "valid"
        assert event.clock_skew_s == 0.0

    def test_recorded_at_is_timezone_aware(self):
        event = MeasurementEvent.from_manual(1.0)
        assert datetime.fromisoformat(event.recorded_at).tzinfo is not None

    def test_roundtrip_and_unknown_keys(self):
        event = MeasurementEvent.from_manual(3.5, characteristic_id="QC-2")
        data = event.to_dict()
        data["future_field"] = {"ignored": True}
        restored = MeasurementEvent.from_dict(data)
        assert restored.to_dict() == event.to_dict()
        assert restored.characteristic_id == "QC-2"

    def test_to_dataframe_inline(self):
        frame = MeasurementEvent.from_manual(2.0).to_dataframe()
        assert list(frame.columns) == ["device", "channel", "ts", "value"]
        assert frame["value"].tolist() == [2.0]


class TestSampleAdapter:
    @staticmethod
    def _samples(n=5, device="dev-1", channel="CH0"):
        return [Sample(device, channel, float(i), 1_700_000_000.0 + i) for i in range(n)]

    def test_single_channel_batch(self):
        event = MeasurementEvent.from_samples(self._samples())
        assert event.source_kind == "connector"
        assert (event.device, event.channel) == ("dev-1", "CH0")
        assert event.summary["n"] == 5
        assert len(event.values) == 5
        assert event.raw_ref.startswith("timeseries://dev-1/CH0?since=")
        assert datetime.fromisoformat(event.ts_start).tzinfo is not None

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="不能为空"):
            MeasurementEvent.from_samples([])

    def test_mixed_channels_rejected_by_single_adapter(self):
        samples = self._samples(2) + self._samples(2, channel="CH1")
        with pytest.raises(ValueError, match="多通道"):
            MeasurementEvent.from_samples(samples)

    def test_multi_channel_split(self):
        samples = self._samples(2) + self._samples(3, channel="CH1")
        events = MeasurementEvent.events_from_samples(samples)
        assert len(events) == 2
        assert sorted(e.channel for e in events) == ["CH0", "CH1"]
        assert sorted(e.summary["n"] for e in events) == [2, 3]

    def test_large_batch_keeps_summary_only(self):
        count = INLINE_VALUE_LIMIT + 1
        samples = [Sample("dev", "CH0", float(i), 1_700_000_000.0 + i)
                   for i in range(count)]
        event = MeasurementEvent.from_samples(samples)
        assert event.summary["n"] == count
        assert event.values == []
        assert event.fingerprint == ""
        with pytest.raises(ValueError, match="raw_ref"):
            event.to_dataframe()

    def test_from_timeseries_sets_window_ref(self):
        event = MeasurementEvent.from_timeseries(
            self._samples(3), device="dev-1", channel="CH0",
            since_ts=1_700_000_000.0, until_ts=1_700_000_002.0)
        assert event.raw_ref == timeseries_ref(
            "dev-1", "CH0", 1_700_000_000.0, 1_700_000_002.0)


class TestDataFrameAdapter:
    @staticmethod
    def _frame():
        return pd.DataFrame({
            "x": [1.0, 2.0, None, 4.0],
            "label": ["a", "b", "c", "d"],
            "t": ["2026-10-01T10:00:00+08:00", "2026-10-01T10:01:00+08:00",
                  "2026-10-01T10:02:00+08:00", "2026-10-01T10:03:00+08:00"],
        })

    def test_explicit_column_and_time_range(self):
        event = MeasurementEvent.from_dataframe(
            self._frame(), column="x", ts_column="t", source_id="line.xlsx")
        assert event.summary["n"] == 3
        assert event.summary["dropped_invalid"] == 1
        assert event.ts_start == "2026-10-01T10:00:00+08:00"
        assert event.ts_end == "2026-10-01T10:03:00+08:00"
        assert event.fingerprint == fingerprint_dataframe(self._frame())
        assert event.raw_ref.startswith("dataframe://")

    def test_auto_picks_numeric_column(self):
        event = MeasurementEvent.from_dataframe(self._frame().drop(columns="t"))
        assert event.channel == "x"
        assert event.summary["n"] == 3

    def test_empty_and_missing_column_rejected(self):
        with pytest.raises(ValueError, match="为空"):
            MeasurementEvent.from_dataframe(pd.DataFrame())
        with pytest.raises(ValueError, match="列不存在"):
            MeasurementEvent.from_dataframe(self._frame(), column="missing")

    def test_no_numeric_column_rejected(self):
        frame = pd.DataFrame({"a": ["x", "y"]})
        with pytest.raises(ValueError, match="数值列"):
            MeasurementEvent.from_dataframe(frame)

    def test_missing_value_column_rejected(self):
        frame = pd.DataFrame({"x": pd.Series([None, None], dtype="float64")})
        with pytest.raises(ValueError, match="有效数值"):
            MeasurementEvent.from_dataframe(frame)

    def test_large_column_not_inlined(self):
        frame = pd.DataFrame({"x": [float(i) for i in range(INLINE_VALUE_LIMIT + 1)]})
        event = MeasurementEvent.from_dataframe(frame)
        assert event.values == []
        assert event.summary["n"] == INLINE_VALUE_LIMIT + 1
        assert event.fingerprint.startswith("pd-hash-v1:")


class TestTimeValidation:
    def test_naive_timestamp_rejected(self):
        with pytest.raises(ValueError, match="时区"):
            MeasurementEvent(source_kind="manual", ts_start="2026-10-01T10:00:00",
                             ts_end="2026-10-01T10:00:00", summary={"n": 1})

    def test_end_before_start_rejected(self):
        with pytest.raises(ValueError, match="不能早于"):
            MeasurementEvent(source_kind="manual",
                             ts_start="2026-10-01T10:00:00+08:00",
                             ts_end="2026-10-01T09:00:00+08:00")

    def test_recorded_too_early_rejected(self):
        with pytest.raises(ValueError, match="偏差容差"):
            MeasurementEvent(
                source_kind="manual",
                ts_start="2026-10-01T10:00:00+08:00",
                ts_end="2026-10-01T10:00:00+08:00",
                recorded_at="2026-10-01T09:00:00+08:00",
                summary={"n": 1})

    def test_small_clock_skew_marked(self):
        event = MeasurementEvent(
            source_kind="manual",
            ts_start="2026-10-01T10:00:00+08:00",
            ts_end="2026-10-01T10:00:10+08:00",
            recorded_at="2026-10-01T10:00:00+08:00",
            summary={"n": 1})
        assert event.clock_skew_s == pytest.approx(10.0)
        assert event.clock_skew_s <= CLOCK_SKEW_TOLERANCE_S


class TestValidation:
    def test_unknown_source_kind_rejected(self):
        with pytest.raises(ValueError, match="来源"):
            MeasurementEvent(source_kind="magic", summary={"n": 1})

    def test_unknown_confidence_rejected(self):
        with pytest.raises(ValueError, match="confidence"):
            MeasurementEvent(source_kind="manual", confidence="certain",
                             summary={"n": 1})

    def test_suspect_requires_reason(self):
        with pytest.raises(ValueError, match="validity_reason"):
            MeasurementEvent(source_kind="manual", validity="suspect",
                             summary={"n": 1})

    def test_invalid_event_without_values_allowed(self):
        event = MeasurementEvent(source_kind="connector", validity="invalid",
                                 validity_reason="传感器断线")
        assert event.summary == {}
        assert event.fingerprint == ""

    def test_summary_unknown_field_rejected(self):
        with pytest.raises(ValueError, match="未知字段"):
            MeasurementEvent(source_kind="manual", summary={"n": 1, "median": 1.0})

    def test_unknown_schema_rejected(self):
        with pytest.raises(ValueError, match="schema"):
            MeasurementEvent(source_kind="manual", summary={"n": 1},
                             schema_version="99")
        data = MeasurementEvent.from_manual(1.0).to_dict()
        data["schema_version"] = "99"
        with pytest.raises(ValueError, match="schema"):
            MeasurementEvent.from_dict(data)

    def test_parent_ids_are_strings(self):
        event = MeasurementEvent(source_kind="manual", summary={"n": 1},
                                 parent_event_ids=["a", "", "b"])
        assert event.parent_event_ids == ["a", "b"]

    def test_content_hash_changes_with_payload(self):
        left = MeasurementEvent.from_manual(1.0)
        right = MeasurementEvent.from_manual(2.0)
        assert left.content_hash() != right.content_hash()
        assert left.content_hash() == MeasurementEvent.from_dict(left.to_dict()).content_hash()

    def test_nan_values_rejected(self):
        with pytest.raises(ValueError, match="NaN/Inf"):
            MeasurementEvent(source_kind="manual", values=[math.nan])
