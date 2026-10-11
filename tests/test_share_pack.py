"""脱敏分享包与泄漏扫描测试（v4.3.0 B4-4）。"""

import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from core.share_pack import build_share_pack, scan_share_pack, synthesize_frame


def _raw(n: int = 3000, seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    return {
        "尺寸": pd.DataFrame({
            "轴径": rng.normal(10.0, 0.05, n),
            "班组": rng.choice(["张三", "李四"], n),
        }),
        "备注": pd.DataFrame({"说明": ["客户A样品"] * n}),
    }


def _zip_text(path: str) -> str:
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            data.decode("utf-8", errors="ignore")
            for data in (archive.read(name) for name in archive.namelist()))


class TestSynthesis:
    def test_numeric_statistics_preserved(self):
        rng = np.random.default_rng(2)
        frame = pd.DataFrame({"x": rng.normal(50.0, 2.0, 5000)})
        synthetic, statement = synthesize_frame(frame, seed=7)
        assert list(synthetic.columns) == ["C1"]
        column = statement["columns"]["C1"]
        assert column["kind"] == "numeric"
        assert abs(column["synthetic"]["mean"] - 50.0) < 0.2
        assert abs(column["synthetic"]["std"] - 2.0) < 0.2
        assert statement["all_equivalent"] is True

    def test_categorical_labels_are_generic(self):
        frame = pd.DataFrame({"name": ["张三", "李四", "张三", "王五"]})
        synthetic, statement = synthesize_frame(frame, seed=3)
        assert set(synthetic["C1"]) <= {"Cat_1", "Cat_2", "Cat_3"}
        assert statement["columns"]["C1"]["kind"] == "categorical"

    def test_reproducible_with_same_seed(self):
        frame = pd.DataFrame({"x": list(range(100))})
        first, _ = synthesize_frame(frame, seed=11)
        second, _ = synthesize_frame(frame, seed=11)
        assert first.equals(second)


class TestSharePack:
    def test_build_structure_and_no_leak(self, tmp_path):
        result = build_share_pack(str(tmp_path / "share"), raw_data=_raw())
        assert result["path"].endswith(".zip")
        assert result["scan"]["ok"] is True
        with zipfile.ZipFile(result["path"]) as archive:
            names = set(archive.namelist())
            assert {"manifest.json", "README.md", "equivalence.json",
                    "case_summary.json", "events_summary.json",
                    "synthetic/sheet_1.csv", "synthetic/sheet_2.csv"} <= names
        text = _zip_text(result["path"])
        for sensitive in ("张三", "李四", "客户A样品", "尺寸", "轴径"):
            assert sensitive not in text

    def test_case_summary_strips_identifiers(self, tmp_path):
        case = {"case": {"id": "CASE-1", "status": "closed", "title": "客户A节拍改善",
                         "owner": "张三", "product": "A100",
                         "steps": [{"phase": "baseline"}, {"phase": "verify"}]}}
        result = build_share_pack(str(tmp_path / "case.zip"), raw_data=_raw(),
                                  case=case)
        with zipfile.ZipFile(result["path"]) as archive:
            summary = json.loads(archive.read("case_summary.json").decode("utf-8"))
        assert summary == {"case_id": "CASE-1", "status": "closed",
                           "stage_count": 2, "phases": ["baseline", "verify"]}
        text = _zip_text(result["path"])
        for sensitive in ("客户A节拍改善", "张三", "A100"):
            assert sensitive not in text

    def test_equivalence_statement(self, tmp_path):
        result = build_share_pack(str(tmp_path / "eq.zip"), raw_data=_raw())
        with zipfile.ZipFile(result["path"]) as archive:
            statement = json.loads(archive.read("equivalence.json").decode("utf-8"))
        assert statement["schema_version"] == "1"
        assert statement["sheets"]["sheet_1"]["method"] == "parametric-synthetic-v1"
        assert statement["sheets"]["sheet_1"]["all_equivalent"] is True

    def test_empty_path_rejected(self):
        with pytest.raises(ValueError, match="路径"):
            build_share_pack("", raw_data=_raw(10))


class TestLeakScan:
    def _fake_pack(self, tmp_path, content: str) -> str:
        path = str(tmp_path / "fake.zip")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("leak.txt", content)
        return path

    def test_forbidden_name_detected(self, tmp_path):
        raw = _raw(10)
        path = self._fake_pack(tmp_path, "负责人 张三")
        scan = scan_share_pack(path, raw_data=raw, forbidden=["张三"])
        assert scan["ok"] is False
        assert any(item["kind"] == "forbidden" for item in scan["findings"])

    def test_high_precision_original_value_detected(self, tmp_path):
        raw = {"S": pd.DataFrame({"x": [123456.789123]})}
        path = self._fake_pack(tmp_path, "value=123456.789123")
        scan = scan_share_pack(path, raw_data=raw)
        assert scan["ok"] is False
        assert any(item["kind"] == "original" for item in scan["findings"])

    def test_original_column_name_detected(self, tmp_path):
        raw = {"S": pd.DataFrame({"客户A轴径": [1.0, 2.0]})}
        path = self._fake_pack(tmp_path, "字段: 客户A轴径")
        scan = scan_share_pack(path, raw_data=raw)
        assert scan["ok"] is False

    def test_clean_pack_passes(self, tmp_path):
        raw = {"S": pd.DataFrame({"客户A轴径": [1.0, 2.0]})}
        path = self._fake_pack(tmp_path, "generic synthetic content C1")
        scan = scan_share_pack(path, raw_data=raw, forbidden=["某公司"])
        assert scan["ok"] is True

    def test_large_file_numeric_detection_via_token_scan(self, tmp_path):
        """超过子串扫描字节上限的文件仍通过数字 token 通道检出原始值。"""
        raw = {"S": pd.DataFrame({"x": [123456.789123]})}
        filler = "x" * 1_100_000
        path = self._fake_pack(tmp_path, f"start {filler} value=123456.789123 end")
        scan = scan_share_pack(path, raw_data=raw)
        assert scan["ok"] is False
        assert any(item["kind"] == "original" for item in scan["findings"])

    def test_scan_reports_candidate_metadata(self, tmp_path):
        raw = _raw(50)
        path = self._fake_pack(tmp_path, "clean generic content")
        scan = scan_share_pack(path, raw_data=raw)
        assert scan["ok"] is True
        assert scan["candidates_total"] >= 1
        assert scan["candidates_numeric"] >= 0 and scan["candidates_text"] >= 1
        assert scan["capped"] is False

    def test_bad_zip_reported(self, tmp_path):
        target = tmp_path / "bad.zip"
        target.write_text("not a zip", encoding="utf-8")
        scan = scan_share_pack(str(target), raw_data={})
        assert scan["ok"] is False
