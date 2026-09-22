"""分析层覆盖补口（v4.2.0 P3-4）

覆盖此前无直接测试引用的模块:
analysis/capability/between_within_cap.py · analysis/hypothesis/variance_tests.py ·
analysis/quality/eight_d_engine.py
"""

import numpy as np
import pandas as pd
import pytest

from analysis.capability.between_within_cap import analyze as between_within_analyze
from analysis.hypothesis.variance_tests import variance_tests
from analysis.quality.eight_d_engine import (
    D1Step, D2Step, D4Step, D5Step, D8Step, EightDReport,
)


class TestBetweenWithinCapability:
    @staticmethod
    def _frame(shift: float = 1.0, noise: float = 0.1, seed: int = 3) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        rows = []
        for group in range(1, 6):
            center = shift * group
            for value in rng.normal(center, noise, size=5):
                rows.append({"g": group, "v": value})
        return pd.DataFrame(rows)

    def test_summary_orders_within_below_total(self):
        result = between_within_analyze(self._frame(), "v", "g", usl=8.0, lsl=0.0)
        summary = result["summary"]
        assert summary["num_subgroups"] == 5
        assert summary["sample_size"] == 25
        assert 0 < summary["within_std"] < summary["total_std"]
        assert summary["between_std"] > 0

    def test_capability_indices_present_and_finite(self):
        result = between_within_analyze(self._frame(noise=0.2), "v", "g",
                                        usl=8.0, lsl=0.0)
        capability = result["capability"]
        assert np.isfinite(capability["cp"]) and np.isfinite(capability["cpk"])
        assert capability["cp"] >= capability["cpk"]
        assert "grade" in capability

    def test_without_limits_only_summary(self):
        result = between_within_analyze(self._frame(), "v", "g")
        assert "capability" not in result
        assert "summary" in result

    def test_insufficient_subgroups_raises(self):
        frame = pd.DataFrame({"g": [1, 1, 2], "v": [1.0, 2.0, 3.0]})
        with pytest.raises(ValueError):
            between_within_analyze(frame, "v", "g")


class TestVarianceTests:
    def test_equal_variance_groups_conclude_homogeneous(self):
        rng = np.random.default_rng(11)
        a = pd.Series(rng.normal(0, 1.0, 200))
        b = pd.Series(rng.normal(0, 1.05, 200))
        result = variance_tests(a, b)
        assert result["overall_conclusion"] == "方差齐性"
        assert result["tests"]["levene"]["equal_variance"] is True
        assert result["num_groups"] == 2

    def test_heterogeneous_groups_detected(self):
        rng = np.random.default_rng(12)
        a = pd.Series(rng.normal(0, 1.0, 200))
        b = pd.Series(rng.normal(0, 8.0, 200))
        result = variance_tests(a, b)
        assert result["overall_conclusion"] == "方差不齐"
        assert result["tests"]["levene"]["p_value"] < 0.05
        assert result["tests"]["bartlett"]["p_value"] < 0.05

    def test_group_statistics_reported(self):
        result = variance_tests(pd.Series([1.0, 2.0, 3.0]), pd.Series([5.0, 6.0, 7.0]))
        stats = result["groups"]
        assert [g["n"] for g in stats] == [3, 3]
        assert stats[0]["mean"] == pytest.approx(2.0)
        assert stats[1]["variance"] == pytest.approx(1.0)

    def test_nan_values_are_dropped(self):
        result = variance_tests(pd.Series([1.0, np.nan, 2.0, 3.0]),
                                pd.Series([4.0, 5.0, np.nan, 6.0]))
        assert [g["n"] for g in result["groups"]] == [3, 3]

    def test_single_valid_group_raises(self):
        with pytest.raises(ValueError, match="至少2个有效组"):
            variance_tests(pd.Series([1.0, 2.0, 3.0]), pd.Series([np.nan]))


class TestEightDEngine:
    @staticmethod
    def _report() -> EightDReport:
        report = EightDReport(title="漏装螺钉", product="A100", customer="客户甲")
        report.d1 = D1Step(team_leader="张三", members="李四/王五")
        report.d2 = D2Step(problem_statement="3 台漏装", what="漏装", where="总装",
                           when="2026-09-01")
        report.d4 = D4Step(root_cause="定位销磨损", five_why="为什么1/为什么2")
        report.d5 = D5Step(pca_items=["更换定位销"], verification_method="首件确认")
        report.d8 = D8Step(recognition_notes="团队奖励", closure_date="2026-09-20")
        return report

    def test_markdown_contains_all_disciplines(self):
        markdown = self._report().to_markdown()
        assert "# 8D 报告: 漏装螺钉" in markdown
        for index in range(1, 9):
            assert f"## D{index}:" in markdown
        assert "定位销磨损" in markdown
        assert "关闭日期: 2026-09-20" in markdown

    def test_to_dict_structure(self):
        payload = self._report().to_dict()
        assert payload["product"] == "A100"
        assert payload["created_at"]
        assert set(payload["steps"]) == {f"D{i}" for i in range(1, 9)}
        assert payload["steps"]["D1"]["team_leader"] == "张三"
        assert payload["steps"]["D5"]["pca_items"] == ["更换定位销"]

    def test_created_at_auto_filled(self):
        report = EightDReport(title="空报告")
        assert report.created_at
        assert "空报告" in report.to_markdown()
