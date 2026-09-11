"""test_data_parser_semantics.py — DataParser 列类型/数值列语义契约

修复背景（v3.7.1）:
1. 命名含“测量/尺寸/重量”等关键词的列被判为 measurement 后不再进入
   numeric_columns → 导入校验误报“未检测到数值列”、DOE 因子列表为空。
2. 命名含“时间”的数值时长列（可用时间/停机时间/观测时间）被误判为
   timestamp，从测量列中消失。
3. 数据清洗后用 select_dtypes 重算 numeric_columns（dtype=str 恒为空）。

本文件固化上述三类语义，防止回归。
"""

import os

import pandas as pd
import pytest

from core.data_loader import DataLoader
from core.data_parser import DataParser


def _parse(df):
    return DataParser().prepare(df)


class TestNumericColumnSemantics:
    def test_measurement_keyword_column_counts_as_numeric(self):
        df = pd.DataFrame({
            "零件编号": ["P1", "P2", "P3", "P4"],
            "测量值": ["10.1", "9.8", "10.3", "10.0"],
        })
        _, info = _parse(df)

        assert info["column_types"]["测量值"] == "measurement"
        assert info["numeric_columns"] == ["测量值"]
        assert info["measurement_columns"] == ["测量值"]

    def test_spec_limit_columns_excluded_from_numeric(self):
        df = pd.DataFrame({
            "测量值": ["10.1", "9.8", "10.3", "10.0"],
            "上规格": ["10.5"] * 4,
            "下规格": ["9.5"] * 4,
        })
        _, info = _parse(df)

        assert info["numeric_columns"] == ["测量值"]
        assert info["spec_limits"]["上规格"]["usl"] == 10.5
        assert info["spec_limits"]["下规格"]["lsl"] == 9.5

    def test_subgroup_index_excluded_from_numeric(self):
        df = pd.DataFrame({
            "样本号": ["1", "2", "3", "4"],
            "温度": ["25.1", "25.3", "24.9", "25.2"],
        })
        _, info = _parse(df)

        assert info["column_types"]["样本号"] == "subgroup"
        assert info["numeric_columns"] == ["温度"]

    def test_text_measurement_named_column_not_numeric(self):
        df = pd.DataFrame({
            "测量方法": ["卡尺", "千分尺", "目视", "气动量仪"],
            "实测值": ["1.1", "2.2", "3.3", "4.4"],
        })
        _, info = _parse(df)

        assert info["column_types"]["测量方法"] == "text"
        assert info["numeric_columns"] == ["实测值"]


class TestTimestampSemantics:
    def test_duration_columns_stay_numeric(self):
        df = pd.DataFrame({
            "设备": ["M1", "M2", "M3"],
            "可用时间": ["480", "480", "470"],
            "停机时间": ["30", "45", "20"],
            "观测时间": ["46.7", "51.2", "49.8"],
        })
        _, info = _parse(df)

        for col in ("可用时间", "停机时间", "观测时间"):
            assert info["column_types"][col] == "numeric", col
            assert col in info["numeric_columns"], col

    def test_real_date_columns_stay_timestamp(self):
        df = pd.DataFrame({
            "日期": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "时间戳": ["2026-01-01 08:30:00", "2026-01-02 09:00:00",
                       "2026-01-03 09:15:00"],
            "数值": ["1", "2", "3"],
        })
        _, info = _parse(df)

        assert info["column_types"]["日期"] == "timestamp"
        assert info["column_types"]["时间戳"] == "timestamp"
        assert info["numeric_columns"] == ["数值"]


class TestRefreshInfo:
    def test_refresh_after_column_drop(self):
        df = pd.DataFrame({
            "测量值": ["10.1", "9.8", "10.3"],
            "温度": ["25.1", "25.3", "24.9"],
        })
        parser = DataParser()
        _, info = parser.prepare(df)
        assert set(info["numeric_columns"]) == {"测量值", "温度"}

        cleaned = df.drop(columns=["温度"])
        refreshed = parser.refresh_info(cleaned, info)

        assert refreshed["numeric_columns"] == ["测量值"]
        assert refreshed["row_count"] == 3
        assert "header_row" in refreshed

    def test_refresh_after_filled_missing_values(self):
        df = pd.DataFrame({"测量值": ["1.0", "2.1", "3.0", "", ""]})
        parser = DataParser()
        _, info = parser.prepare(df)
        assert info["numeric_columns"] == ["测量值"]

        filled = pd.DataFrame({"测量值": ["1.0", "2.1", "3.0", "4.2", "5.5"]})
        refreshed = parser.refresh_info(filled, info)
        assert refreshed["measurement_columns"] == ["测量值"]
        assert refreshed["row_count"] == 5

    def test_refresh_empty_raises(self):
        with pytest.raises(ValueError):
            DataParser().refresh_info(pd.DataFrame())


@pytest.fixture(scope="module")
def raw_sample_data():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "公司仪器测试数据.xlsx")
    if not os.path.exists(path):
        pytest.skip("样本数据文件不存在")
    return DataLoader().load(path)


class TestBundledSampleData:
    """真实样本文件契约 — 列语义与 v3.7.1 修复后一致"""

    def test_quality_sheet_numeric_columns(self, raw_sample_data):
        parser = DataParser()
        _, info = parser.prepare(raw_sample_data["质量数据"])
        assert info["numeric_columns"] == ["测量值"]

    def test_equipment_sheet_durations_are_numeric(self, raw_sample_data):
        parser = DataParser()
        _, info = parser.prepare(raw_sample_data["设备清单"])
        assert "可用时间" in info["numeric_columns"]
        assert "停机时间" in info["numeric_columns"]

    def test_time_observation_numeric_columns(self, raw_sample_data):
        parser = DataParser()
        _, info = parser.prepare(raw_sample_data["时间观测"])
        assert "观测时间" in info["numeric_columns"]
