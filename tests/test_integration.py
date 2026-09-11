"""test_integration.py — 端到端集成冒烟（11 项）

原实现为脚本式模块级断言：pytest 收集 0 项（假绿），且会把
_tmp_test_report.xlsx 写进仓库。v3.7.1 转为真正的 pytest 用例，
报告输出改到 tmp_path。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from analysis.capability import normal_cap
from analysis.doe import factorial as fact
from analysis.hypothesis import normality, t_tests
from analysis.msa import gage_rr
from analysis.spc import imr, xbar_r
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from output.excel_report import ExcelReport


@pytest.fixture(scope="module")
def series():
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(10.0, 0.5, 125))


@pytest.fixture(scope="module")
def xbar_result(series):
    return xbar_r.analyze(series, subgroup_size=5)


@pytest.fixture(scope="module")
def sample_df():
    return pd.DataFrame({
        "测量值": [1.0, 2.0, 3.0, 4.0, 5.0],
        "组别": ["A", "A", "B", "B", "C"],
    })


class TestStatisticalPipeline:
    def test_xbar_r_control_chart(self, xbar_result):
        assert xbar_result["num_subgroups"] == 25
        assert 9.5 < xbar_result["xbar_chart"]["cl"] < 10.5

    def test_imr(self, series):
        result = imr.analyze(series)
        assert result["num_points"] == 125

    def test_capability(self, series):
        cap = normal_cap.analyze(series, usl=11.5, lsl=8.5)
        assert cap["capability"]["cpk"] > 0.5
        assert cap["capability"]["grade"]

    def test_two_sample_t_test(self):
        rng = np.random.default_rng(7)
        g1 = pd.Series(rng.normal(10, 0.5, 30))
        g2 = pd.Series(rng.normal(10.5, 0.5, 30))
        result = t_tests.two_sample(g1, g2)
        assert "p_value" in result

    def test_normality(self, series):
        result = normality.normality_test(series)
        assert "overall_conclusion" in result

    def test_gage_rr_crossed(self):
        rng = np.random.default_rng(11)
        msa_df = pd.DataFrame({
            "part": np.repeat(range(1, 11), 6),
            "operator": np.tile(np.repeat(["A", "B", "C"], 2), 10),
            "measurement": rng.normal(10, 0.1, 60),
        })
        result = gage_rr.analyze_crossed(msa_df, "measurement", "part", "operator", 1.0)
        assert "acceptance" in result
        assert result["percentages"]["grr_pct_tv"] >= 0

    def test_doe_factorial(self):
        rng = np.random.default_rng(5)
        factors = ["A", "B", "C"]
        design = fact.generate_design(factors, replicates=1)
        design["response"] = (design["A"] * 0.5 + design["B"] * 0.3
                              + rng.normal(0, 0.1, len(design)))
        result = fact.analyze_factorial(design, "response", factors)
        assert "significant_factors" in result


class TestCoreServices:
    def test_data_parser(self, sample_df):
        info = DataParser().analyze(sample_df)
        assert "measurement_columns" in info
        assert len(info["measurement_columns"]) >= 1
        assert info["numeric_columns"] == ["测量值"]

    def test_data_validator(self, sample_df):
        result = DataValidator().validate(sample_df, ["测量值"])
        assert "summary" in result
        assert result["error_count"] == 0

    def test_template_parser(self):
        assert len(TemplateParser().VALID_ANALYSIS_TYPES) > 10


class TestReportPipeline:
    def test_excel_report(self, xbar_result, tmp_path):
        out = ExcelReport().generate(
            [{"analysis_type": "XBar-R", "params": {"size": 5}, "result": xbar_result}],
            str(tmp_path / "test_report.xlsx"),
            "Test Report",
        )
        assert out
        assert (tmp_path / "test_report.xlsx").exists()
