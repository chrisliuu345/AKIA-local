"""test_data_parser_duplicate_columns.py — 表头重名列回归。

真实场景：公司报表 `CO401-20220930.xls` 的「导出信息」表头含两个"二维码"，
旧实现直接把表头行设为列名，`df[col]` 返回 DataFrame →
`pd.to_numeric` 抛 TypeError（Sheet 分发失败）。
"""

import pandas as pd

from core.data_parser import DataParser


def _report_like_frame() -> pd.DataFrame:
    return pd.DataFrame([
        ["统计报表", None, None],
        ["直径", "直径", "编号"],
        ["10.1", "10.2", "A1"],
        ["10.3", "10.4", "A2"],
        ["10.5", "10.6", "A3"],
    ])


class TestDuplicateHeaderColumns:
    def test_apply_header_dedupes_and_identifies_types(self):
        parser = DataParser()
        cleaned = parser._apply_header(_report_like_frame(), 1)
        info = parser._analyze_frame(cleaned)

        assert cleaned.columns.tolist() == ["直径", "直径.1", "编号"]
        assert cleaned.columns.is_unique
        assert info["duplicate_columns"] == [
            {"original": "直径", "renamed": "直径.1"},
        ]
        assert {"直径", "直径.1"} <= set(info["numeric_columns"])

    def test_prepare_survives_duplicate_header(self, monkeypatch):
        parser = DataParser()
        monkeypatch.setattr(parser, "_detect_header_row", lambda df: 1)
        cleaned, info = parser.prepare(_report_like_frame())

        assert cleaned.columns.is_unique
        assert cleaned.columns.tolist() == ["直径", "直径.1", "编号"]
        assert info["duplicate_columns"][0]["renamed"] == "直径.1"
        assert {"直径", "直径.1"} <= set(info["numeric_columns"])

    def test_three_duplicates_get_numbered_suffixes(self):
        parser = DataParser()
        df = pd.DataFrame([[1, 2, 3]], columns=["a", "a", "a"])
        parser._dedupe_columns(df)
        assert df.columns.tolist() == ["a", "a.1", "a.2"]

    def test_collision_with_existing_suffixed_name(self):
        parser = DataParser()
        df = pd.DataFrame([[1, 2, 3, 4]], columns=["x", "x", "x.1", ""])
        parser._dedupe_columns(df)
        assert df.columns.is_unique
        assert df.columns.tolist()[:3] == ["x", "x.1", "x.1.1"]
        assert df.columns.tolist()[3] == "列4"
