import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd

from ui.main_window import _tab_has_data, _tab_is_runnable


class _FakeTab:
    def __init__(self, df):
        self.df = df


class _NoDfTab:
    pass


class _RunnableTab:
    def __init__(self, df):
        self.df = df

    def run_and_display(self):
        pass


def test_none_df_returns_false():
    assert _tab_has_data(_NoDfTab()) is False


def test_empty_dataframe_returns_false():
    assert _tab_has_data(_FakeTab(pd.DataFrame())) is False


def test_nonempty_dataframe_returns_true():
    assert _tab_has_data(_FakeTab(pd.DataFrame({"a": [1, 2, 3]}))) is True


def test_len_based_object_returns_true():
    assert _tab_has_data(_FakeTab([1, 2])) is True


def test_data_without_run_and_display_not_runnable():
    assert _tab_is_runnable(_FakeTab(pd.DataFrame({"a": [1]}))) is False


def test_runnable_with_data_returns_true():
    assert _tab_is_runnable(_RunnableTab(pd.DataFrame({"a": [1]}))) is True


def test_runnable_without_data_returns_false():
    assert _tab_is_runnable(_RunnableTab(pd.DataFrame())) is False


# ── 退出清理（v3.7.1: 告警引擎/看板线程/实时订阅不得残留）──

def test_close_stops_alert_engine(_qt_application):
    import pytest

    from ui.main_window import MainWindow

    window = MainWindow()
    engine = getattr(window, "_alert_engine", None)

    window.close()

    assert window._alert_engine is None
    assert window._dash_thread is None
    if engine is not None:
        assert engine._unsubs == [], "告警引擎订阅应已解绑"
        with pytest.raises(RuntimeError):
            engine._executor.submit(lambda: None)  # 线程池应已关闭


def test_close_shuts_down_spc_live_stream(_qt_application):
    from ui._tab_registry import TAB_INDEX
    from ui.main_window import MainWindow

    window = MainWindow()
    spc = window._lazy_load_tab(TAB_INDEX["spc"])
    assert getattr(spc, "_bus", None) is window.stream_bus

    window.close()

    assert spc._live_unsub is None
    assert spc._live_timer.isActive() is False
