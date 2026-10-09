"""测量四通道适配器测试（v4.3.0 B2-1/B2-2）。"""

import time

import pandas as pd
import pytest

from core.devices.driver import Sample
from core.evidence import make_credential
from core.measurement_event import (
    INLINE_VALUE_LIMIT,
    MeasurementEvent,
    parse_timeseries_ref,
    timeseries_ref,
)
from core.storage.timeseries import TimeseriesStore
from core.streaming.bus import StreamBus
from core.streaming.collector import IngestRunner


class _StubStore:
    def __init__(self):
        self.rows: list[Sample] = []

    def insert_samples(self, samples):
        self.rows.extend(samples)
        return len(samples)


class _OnceDriver:
    name = "mock-1"

    def __init__(self, samples):
        self._samples = list(samples)

    def open(self):
        pass

    def close(self):
        pass

    def poll(self):
        samples, self._samples = self._samples, []
        return samples


class TestTimeseriesRef:
    def test_roundtrip(self):
        ref = timeseries_ref("dev-1", "CH0", 1.5, 2.5)
        assert ref == "timeseries://dev-1/CH0?since=1.500&until=2.500"
        parsed = parse_timeseries_ref(ref)
        assert parsed == {"device": "dev-1", "channel": "CH0",
                          "since_ts": 1.5, "until_ts": 2.5}

    def test_dash_means_empty(self):
        parsed = parse_timeseries_ref("timeseries://-/-")
        assert parsed["device"] == "" and parsed["channel"] == ""
        assert parsed["since_ts"] is None and parsed["until_ts"] is None

    @pytest.mark.parametrize("bad", [
        "", "http://dev/CH0", "timeseries://dev/CH0?bad=1",
        "timeseries://dev/CH0?since=abc"])
    def test_invalid_ref_rejected(self, bad):
        with pytest.raises(ValueError):
            parse_timeseries_ref(bad)

    def test_query_ref_reads_window(self, tmp_path):
        store = TimeseriesStore(tmp_path / "ts.db")
        try:
            samples = [Sample("dev-1", "CH0", float(i), 1000.0 + i)
                       for i in range(5)]
            store.insert_samples(samples)
            event = MeasurementEvent.from_samples(samples)
            restored = store.query_ref(event.raw_ref)
            assert [s.value for s in restored] == [0.0, 1.0, 2.0, 3.0, 4.0]
            partial = store.query_ref(MeasurementEvent.from_samples(samples[:2]).raw_ref)
            assert len(partial) == 2
        finally:
            store.close()


class TestFileAdapter:
    def test_events_from_raw_data_skips_non_numeric(self):
        raw = {
            "尺寸": pd.DataFrame({"x": [1.0, 2.0, 3.0]}),
            "备注": pd.DataFrame({"note": ["a", "b"]}),
        }
        events = MeasurementEvent.events_from_raw_data(raw, source_id="line.xlsx",
                                                       source_name="line.xlsx")
        assert len(events) == 1
        event = events[0]
        assert event.source_kind == "file"
        assert event.channel == "尺寸"
        assert event.raw_ref == "sheet://尺寸"
        assert event.summary["n"] == 3

    def test_file_event_fingerprint_matches_credential(self):
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        event = MeasurementEvent.from_dataframe(frame, source_id="f.xlsx")
        credential = make_credential("capability@1", {"usl": 10}, df=frame)
        assert event.fingerprint == credential.data_fingerprint

    def test_file_and_manual_share_contract(self):
        frame = pd.DataFrame({"x": [1.0, 2.0]})
        file_event = MeasurementEvent.from_dataframe(frame)
        manual_event = MeasurementEvent.from_manual(1.0)
        assert set(file_event.to_dict()) == set(manual_event.to_dict())
        assert MeasurementEvent.from_dict(file_event.to_dict()).to_dict() == file_event.to_dict()


class TestCollectorAdapter:
    @staticmethod
    def _runner(sink, driver=None):
        return IngestRunner(StreamBus(), _StubStore(), [driver or _OnceDriver([])],
                            poll_interval=0.01, event_sink=sink)

    def test_one_batch_one_event_with_summary_only(self):
        captured = []
        runner = self._runner(captured.append)
        samples = [Sample("mock-1", "CH0", float(i), 2000.0 + i)
                   for i in range(INLINE_VALUE_LIMIT + 5)]
        runner._emit_measurement_events(_OnceDriver([]), samples)
        assert len(captured) == 1
        assert len(captured[0]) == 1
        event = captured[0][0]
        assert event.source_kind == "connector"
        assert event.source_id == "mock-1"
        assert event.summary["n"] == INLINE_VALUE_LIMIT + 5
        assert event.values == []
        assert event.raw_ref.startswith("timeseries://mock-1/CH0?since=")

    def test_multi_channel_batch_splits_events(self):
        captured = []
        runner = self._runner(captured.append)
        samples = ([Sample("mock-1", "CH0", 1.0, 1.0),
                    Sample("mock-1", "CH1", 2.0, 2.0)])
        runner._emit_measurement_events(_OnceDriver([]), samples)
        assert sorted(event.channel for event in captured[0]) == ["CH0", "CH1"]

    def test_sink_failure_is_isolated(self):
        def _boom(_events):
            raise RuntimeError("sink down")

        runner = self._runner(_boom)
        runner._emit_measurement_events(
            _OnceDriver([]), [Sample("mock-1", "CH0", 1.0, 1.0)])

    def test_no_sink_is_noop(self):
        runner = self._runner(None)
        runner._emit_measurement_events(
            _OnceDriver([]), [Sample("mock-1", "CH0", 1.0, 1.0)])

    def test_loop_wires_sink_and_store(self):
        samples = [Sample("mock-1", "CH0", 1.0, 100.0),
                   Sample("mock-1", "CH0", 2.0, 101.0)]
        driver = _OnceDriver(samples)
        captured = []
        store = _StubStore()
        runner = IngestRunner(StreamBus(), store, [driver],
                              poll_interval=0.01, event_sink=captured.append)
        runner.start()
        try:
            deadline = time.time() + 3
            while not captured and time.time() < deadline:
                time.sleep(0.01)
        finally:
            runner.stop()
        assert len(store.rows) == 2
        assert len(captured) == 1
        assert captured[0][0].summary["n"] == 2
