"""数值列缓存与 Excel 读取的边界：返回值隔离、异常类型保持。"""

import pandas as pd
import pytest

from core.excel_utils import read_excel_auto
from core.numeric_cache import cached_numeric, clear_numeric_cache


def test_caller_mutation_does_not_leak_into_cache():
    df = pd.DataFrame({"a": ["1", "2", "3", "4"]})
    first = cached_numeric(df, "a")
    first.iloc[0] = 999.0
    assert cached_numeric(df, "a").iloc[0] == 1.0


def test_clear_after_in_place_edit_returns_fresh_values():
    df = pd.DataFrame({"a": ["1", "2", "3", "4"]})
    assert cached_numeric(df, "a").tolist() == [1, 2, 3, 4]
    df.loc[0, "a"] = "100"
    clear_numeric_cache(df)
    assert cached_numeric(df, "a").tolist() == [100, 2, 3, 4]


def test_replaced_column_is_recomputed():
    df = pd.DataFrame({"a": ["1", "2", "3", "4"]})
    cached_numeric(df, "a")
    df["a"] = ["10", "20", "30", "40"]
    assert cached_numeric(df, "a").tolist() == [10, 20, 30, 40]


@pytest.mark.parametrize("suffix", [".xlsx", ".xlsm", ".xls"])
def test_missing_file_keeps_file_not_found(tmp_path, suffix):
    with pytest.raises(FileNotFoundError):
        read_excel_auto(str(tmp_path / f"missing{suffix}"))
