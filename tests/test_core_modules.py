"""核心模块单元测试 — formatting/fmea/sheet_merger/splitter/layered/profiler"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest, tempfile, pandas as pd, numpy as np

from core.formatting import format_pvalue, format_cp, format_pct, format_ci
from core.fmea_engine import FMEAItem, FMEAEngine
from core.sheet_merger import SheetMerger
from core.sheet_splitter import SheetSplitter
from core.layered_form import LPAEngine
from core.data_profiler import DataProfiler, _clean_col_name


# ── formatting ──
class TestFormatting:
    def test_pvalue_small(self):
        assert format_pvalue(0.00005) == "<0.0001"

    def test_pvalue_medium(self):
        assert format_pvalue(0.0005) == "<0.001"

    def test_pvalue_normal(self):
        assert format_pvalue(0.0456) == "0.0456"

    def test_cp(self):
        assert format_cp(1.334) == "1.334"

    def test_pct(self):
        assert format_pct(0.856) == "85.6%"

    def test_ci(self):
        assert format_ci(12.345, 18.9) == "[12.35, 18.90]"


# ── FMEA ──
class TestFMEA:
    def test_rpn_calc(self):
        item = FMEAItem(severity=7, occurrence=5, detection=6)
        assert item.calc_rpn() == 210
        assert item.risk_level == "high"

    def test_risk_medium(self):
        item = FMEAItem(severity=5, occurrence=4, detection=3)
        item.calc_rpn()
        assert item.risk_level == "medium"

    def test_risk_low(self):
        item = FMEAItem(severity=2, occurrence=2, detection=2)
        item.calc_rpn()
        assert item.risk_level == "low"

    def test_sort(self):
        items = [FMEAItem(severity=s, occurrence=1, detection=1) for s in [3, 9, 5]]
        for i in items:
            i.calc_rpn()
        sorted_items = FMEAEngine.sort_by_rpn(items)
        assert sorted_items[0].rpn == 9
        assert sorted_items[-1].rpn == 3

    def test_default_pfmea(self):
        items = FMEAEngine.create_default("pfmea")
        assert len(items) == 3
        for i in items:
            assert i.rpn > 0

    def test_stats(self):
        items = FMEAEngine.create_default("pfmea")
        stats = FMEAEngine.get_stats(items)
        assert stats["total"] == 3
        assert stats["max_rpn"] > 0

    def test_dataframe(self):
        items = FMEAEngine.create_default("pfmea")
        df = FMEAEngine.to_dataframe(items)
        assert df.shape == (3, 12)


# ── Sheet Merger ──
class TestSheetMerger:
    def test_merge_append(self):
        tmp = tempfile.mkdtemp()
        p1 = os.path.join(tmp, "a.xlsx")
        p2 = os.path.join(tmp, "b.xlsx")
        pd.DataFrame({"x": [1, 2]}).to_excel(p1, index=False)
        pd.DataFrame({"x": [3, 4]}).to_excel(p2, index=False)
        df = SheetMerger.merge_append([p1, p2])
        assert len(df) == 4

    def test_merge_empty(self):
        df = SheetMerger.merge_append([])
        assert df.empty

    def test_merge_join(self):
        df1 = pd.DataFrame({"id": [1, 2], "a": [10, 20]})
        df2 = pd.DataFrame({"id": [1, 3], "b": [100, 300]})
        df = SheetMerger.merge_join(df1, df2, "id", "inner")
        assert len(df) == 1


# ── Sheet Splitter ──
class TestSheetSplitter:
    def test_split_by_rows(self):
        df = pd.DataFrame({"x": range(25)})
        tmp = tempfile.mkdtemp()
        paths = SheetSplitter.split_by_rows(df, 10, tmp)
        assert len(paths) == 3

    def test_split_by_column(self):
        df = pd.DataFrame({"cat": ["A", "A", "B", "B", "C"], "v": range(5)})
        tmp = tempfile.mkdtemp()
        paths = SheetSplitter.split_by_column(df, "cat", tmp)
        assert len(paths) == 3

    def test_split_by_condition(self):
        df = pd.DataFrame({"cpk": [0.8, 1.2, 0.9, 1.5]})
        tmp = tempfile.mkdtemp()
        paths = SheetSplitter.split_by_condition(df, "cpk", "<", 1.0, tmp)
        assert len(paths) == 2

    def test_split_by_column_hash_suffix(self):
        """W95: 超长列值截断后追加哈希后缀, 前 50 字符相同但更长的值不互相覆盖"""
        base = "Z" * 50
        a = base + "A"  # 与 b 前 50 字符完全相同
        b = base + "B"
        df = pd.DataFrame({"cat": [a, a, b], "v": range(3)})
        tmp = tempfile.mkdtemp()
        paths = SheetSplitter.split_by_column(df, "cat", tmp)
        assert len(paths) == 2, "两个不同长值应生成两个文件"
        assert "_" in os.path.basename(paths[0]), "截断文件名应含哈希后缀"
        # 短值文件名不含哈希后缀
        df2 = pd.DataFrame({"cat": ["短", "短"], "v": range(2)})
        paths2 = SheetSplitter.split_by_column(df2, "cat", tmp)
        assert os.path.basename(paths2[0]) == "短.xlsx"


# ── LPA ──
class TestLPA:
    def test_templates_exist(self):
        t = LPAEngine.get_templates()
        assert "5S" in t
        assert "安全" in t
        assert "质量" in t

    def test_generate(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "lpa.xlsx")
        result = LPAEngine.generate_excel(["OP10"], ["5S", "安全"], ["AuditorA"], path)
        assert os.path.exists(result)


# ── Data Profiler ──
class TestDataProfiler:
    def test_profile_basic(self):
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "b": ["x"] * 10})
        dp = DataProfiler()
        r = dp.profile({"Sheet1": df})
        assert r["global_summary"]["total_sheets"] == 1
        assert "recommendations" in r["sheets"]["Sheet1"]

    def test_clean_col_unnamed(self):
        assert _clean_col_name("Unnamed: 0") == "列 1"
        assert _clean_col_name("Unnamed: 5") == "列 6"

    def test_clean_col_numeric(self):
        assert _clean_col_name(0) == "列 1"
        assert _clean_col_name(3) == "列 4"

    def test_clean_col_named(self):
        assert _clean_col_name("Product") == "Product"

    def test_issues_detection(self):
        df = pd.DataFrame({"a": [1, None, 3, None, 5] * 20, "b": [1] * 100})
        dp = DataProfiler()
        r = dp.profile({"S": df})
        issues = r["sheets"]["S"]["issues"]
        assert len(issues) >= 1  # 40% missing

    def test_empty_spec_column_no_crash(self):
        """W90: USL/LSL 列全为文本/空值时 profile 不崩, usl/lsl 为 None"""
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "USL": ["x", "y", "z", "w", "v"],
                "LSL": [None, None, None, None, None],
            }
        )
        cols = [
            {
                "name": "a",
                "category": "measurement",
                "normality_pvalue": 0.5,
                "std": 1.0,
                "distribution": "normal",
            },
            {"name": "USL", "category": "text", "missing_pct": 0},
            {"name": "LSL", "category": "text", "missing_pct": 0},
        ]
        dp = DataProfiler()
        recs = dp._generate_recommendations(df, "S", cols)
        assert recs, "应产生推荐"
        assert recs[0]["params"].get("usl") is None
        assert recs[0]["params"].get("lsl") is None

    def test_high_correlation_detected(self):
        """W91: 两列 Pearson |r|>0.95 报高相关 (替代旧的偏度差值误判)"""
        df = pd.DataFrame(
            {"a": list(range(1, 101)), "b": [2 * x for x in range(1, 101)]}
        )
        dp = DataProfiler()
        r = dp.profile({"S": df})
        issues = r["sheets"]["S"]["issues"]
        assert any("高度相关" in i for i in issues)

    def test_no_false_correlation_from_skewness(self):
        """W91: 偏度相近但实际不相关的列不应报高相关 (旧逻辑会误判)"""
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                "a": rng.normal(0, 1, 100),
                "b": rng.exponential(3, 100),
                "c": rng.exponential(4, 100),
            }
        )
        dp = DataProfiler()
        r = dp.profile({"S": df})
        issues = [i for i in r["sheets"]["S"]["issues"] if "高度相关" in i]
        assert issues == []


# ── i18n 中文文案完整性 (v2.4.1 中文化后仅维护 zh.json) ──
class TestI18nZh:
    def test_zh_json_valid_and_has_keys(self):
        import json
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent
        zh = json.loads((base / "locales" / "zh.json").read_text(encoding="utf-8"))
        assert zh, "zh.json 为空"
        for k in ["sidebar.home", "menu.file", "status.loaded", "db.connection_title"]:
            assert k in zh, f"zh.json 缺键: {k}"


# ── Context Builder ──
class TestContextBuilder:
    def test_acceptance_string_no_crash(self):
        """W93: result.acceptance 为字符串时 build() 不抛 AttributeError"""
        from core.context_builder import ContextBuilder

        cb = ContextBuilder()
        analyses = {
            1: {
                "analysis_type": "GRR",
                "params": {},
                "result": {
                    "percentages": {"grr_pct_tv": 12.5},
                    "ndc": 5,
                    "acceptance": "通过",
                },
            },
        }
        text = cb.build(analyses, "f.xlsx")
        assert "判定=通过" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
