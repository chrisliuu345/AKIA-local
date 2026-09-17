"""test_known_value_framework.py — P0 已知值框架自检（约定见 KNOWN_VALUES.md）"""

import numpy as np
import pytest

from tests.known_values import (
    TOL_PRESETS,
    KnownValueCase,
    assert_allclose,
    assert_close,
)


class TestKnownValueCase:
    def test_defaults_and_label(self):
        case = KnownValueCase(case_id="x-mean", source="NIST StRD",
                              reference="table 1")
        assert case.rel_tol == TOL_PRESETS["closed_form"][0]
        assert case.abs_tol == TOL_PRESETS["closed_form"][1]
        assert "x-mean" in case.label
        assert "NIST StRD" in case.label

    def test_preset_overrides_tolerances(self):
        case = KnownValueCase.with_preset("x-mle", "NIST StRD", preset="iterative")
        assert case.rel_tol == TOL_PRESETS["iterative"][0]
        assert case.abs_tol == TOL_PRESETS["iterative"][1]

    def test_presets_get_progressively_looser(self):
        assert (TOL_PRESETS["closed_form"][0]
                < TOL_PRESETS["iterative"][0]
                < TOL_PRESETS["bootstrap"][0])

    def test_rejects_empty_id_or_source(self):
        with pytest.raises(ValueError):
            KnownValueCase(case_id="", source="NIST")
        with pytest.raises(ValueError):
            KnownValueCase(case_id="x", source="")

    def test_rejects_negative_or_zero_tolerances(self):
        with pytest.raises(ValueError):
            KnownValueCase(case_id="x", source="NIST", rel_tol=-1e-9)
        with pytest.raises(ValueError):
            KnownValueCase(case_id="x", source="NIST", rel_tol=0.0, abs_tol=0.0)

    def test_rejects_unknown_preset(self):
        with pytest.raises(ValueError):
            KnownValueCase.with_preset("x", "NIST", preset="magic")


class TestAssertions:
    CASE = KnownValueCase(case_id="demo-mean", source="unit-test",
                          reference="demo", rel_tol=1e-9, abs_tol=1e-12)

    def test_close_within_tolerance(self):
        assert_close(1.0 + 1e-12, 1.0, self.CASE)
        assert_close(0.0, 0.0, self.CASE)

    def test_close_failure_carries_case_label(self):
        with pytest.raises(AssertionError) as excinfo:
            assert_close(1.1, 1.0, self.CASE, context="mean")
        message = str(excinfo.value)
        assert "demo-mean" in message
        assert "mean" in message

    def test_allclose_arrays(self):
        assert_allclose([1.0, 2.0, 3.0], np.array([1.0, 2.0, 3.0]), self.CASE)

    def test_allclose_allows_nan_when_matching(self):
        assert_allclose([1.0, float("nan")], [1.0, float("nan")], self.CASE)

    def test_allclose_failure(self):
        with pytest.raises(AssertionError):
            assert_allclose([1.0, 2.0], [1.0, 2.5], self.CASE)
