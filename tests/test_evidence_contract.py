"""test_evidence_contract.py — P0 判定凭证 schema v1 契约测试"""

import json

import numpy as np
import pandas as pd
import pytest

from config.settings import APP_VERSION
from core.evidence import (
    CREDENTIAL_SCHEMA_VERSION,
    NO_DATA_FINGERPRINT,
    ConclusionCredential,
    diff_credentials,
    fingerprint_dataframe,
    make_credential,
)


@pytest.fixture
def frame():
    return pd.DataFrame({"x": [1.0, 2.0, 3.0], "g": ["a", "a", "b"]})


class TestFingerprint:
    def test_stable_across_calls(self, frame):
        first = fingerprint_dataframe(frame)
        second = fingerprint_dataframe(frame.copy())
        assert first == second
        assert first.startswith("pd-hash-v1:")

    def test_changes_with_values(self, frame):
        changed = frame.copy()
        changed.loc[0, "x"] = 9.9
        assert fingerprint_dataframe(frame) != fingerprint_dataframe(changed)

    def test_changes_with_columns_and_order(self, frame):
        assert fingerprint_dataframe(frame) != fingerprint_dataframe(frame[["g", "x"]])
        renamed = frame.rename(columns={"x": "y"})
        assert fingerprint_dataframe(frame) != fingerprint_dataframe(renamed)

    def test_handles_nan_and_empty(self):
        with_nan = pd.DataFrame({"x": [1.0, np.nan]})
        assert fingerprint_dataframe(with_nan) == fingerprint_dataframe(with_nan.copy())
        empty = pd.DataFrame({"x": pd.Series(dtype="float64")})
        assert fingerprint_dataframe(empty).startswith("pd-hash-v1:")

    def test_handles_unhashable_cells(self):
        df = pd.DataFrame({"tags": [["a"], ["b"]]})
        fingerprint = fingerprint_dataframe(df)
        assert fingerprint.split(":", 1)[0] in {"pd-hash-v1", "csv-hash-v1"}

    def test_rejects_non_dataframe(self):
        with pytest.raises(TypeError):
            fingerprint_dataframe([1, 2, 3])


class TestCredential:
    def test_make_credential_fills_metadata(self, frame):
        cred = make_credential("xbar_r@1", {"subgroup": 5}, frame,
                               algorithm="XBar-R")
        assert cred.rule_version == "xbar_r@1"
        assert cred.app_version == APP_VERSION
        assert cred.computed_at
        assert cred.algorithm == "XBar-R"
        assert cred.data_fingerprint == fingerprint_dataframe(frame)
        assert cred.schema_version == CREDENTIAL_SCHEMA_VERSION

    def test_no_data_credential(self):
        cred = make_credential("rule-check@1")
        assert cred.data_fingerprint == NO_DATA_FINGERPRINT
        assert cred.params == {}

    def test_params_are_json_safe(self):
        cred = make_credential("x@1", {"alpha": np.float64(0.05), "n": np.int64(5)})
        assert isinstance(cred.params["alpha"], float)
        assert isinstance(cred.params["n"], int)
        json.dumps(cred.to_dict(), ensure_ascii=False)

    def test_roundtrip(self, frame):
        cred = make_credential("capability@2", {"usl": 10.5}, frame)
        restored = ConclusionCredential.from_dict(cred.to_dict())
        assert restored.to_dict() == cred.to_dict()

    def test_from_dict_ignores_unknown_keys(self):
        data = make_credential("x@1").to_dict()
        data["future_field"] = "ignored"
        assert ConclusionCredential.from_dict(data).rule_version == "x@1"

    def test_requires_rule_version_and_fingerprint(self):
        with pytest.raises(ValueError):
            ConclusionCredential(rule_version="", data_fingerprint="pd-hash-v1:x")
        with pytest.raises(ValueError):
            ConclusionCredential(rule_version="x@1", data_fingerprint="")
        with pytest.raises(ValueError):
            ConclusionCredential.from_dict({"rule_version": "x@1"})

    def test_rejects_unknown_schema_version(self):
        with pytest.raises(ValueError):
            ConclusionCredential(rule_version="x@1", data_fingerprint="pd-hash-v1:x",
                                 schema_version="99")
        data = make_credential("x@1").to_dict()
        data["schema_version"] = "99"
        with pytest.raises(ValueError):
            ConclusionCredential.from_dict(data)

    def test_verify_dataframe(self, frame):
        cred = make_credential("x@1", df=frame)
        assert cred.verify_dataframe(frame)
        changed = frame.copy()
        changed.loc[0, "x"] = 42.0
        assert not cred.verify_dataframe(changed)


class TestDiff:
    def test_identical_credentials_have_no_diff(self, frame):
        left = make_credential("x@1", {"n": 5}, frame)
        right = ConclusionCredential.from_dict(left.to_dict())
        assert diff_credentials(left, right) == {}

    def test_detects_parameter_and_fingerprint_changes(self, frame):
        old = make_credential("x@1", {"n": 5}, frame)
        changed = frame.copy()
        changed.loc[0, "x"] = 7.0
        new = make_credential("x@2", {"n": 6}, changed)
        diff = diff_credentials(old, new)
        assert set(diff) == {"rule_version", "params", "data_fingerprint"}
        assert diff["params"]["old"] == {"n": 5}
        assert diff["params"]["new"] == {"n": 6}

    def test_rejects_non_credentials(self):
        with pytest.raises(TypeError):
            diff_credentials(make_credential("x@1"), {"rule_version": "x@1"})
