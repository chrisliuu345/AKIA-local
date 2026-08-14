import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd

from ui.main_window import _tab_has_data


class _FakeTab:
    def __init__(self, df):
        self.df = df


class _NoDfTab:
    pass


def test_none_df_returns_false():
    assert _tab_has_data(_NoDfTab()) is False


def test_empty_dataframe_returns_false():
    assert _tab_has_data(_FakeTab(pd.DataFrame())) is False


def test_nonempty_dataframe_returns_true():
    assert _tab_has_data(_FakeTab(pd.DataFrame({"a": [1, 2, 3]}))) is True


def test_len_based_object_returns_true():
    assert _tab_has_data(_FakeTab([1, 2])) is True
