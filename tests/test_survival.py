"""生存分析 — Kaplan-Meier / Log-rank / Cox PH 单元测试"""

import numpy as np
import pandas as pd
import pytest

from analysis.reliability.survival import (
    kaplan_meier, kaplan_meier_compare, logrank_test, cox_regression,
)


class TestKaplanMeier:

    def test_basic_km(self):
        np.random.seed(42)
        T = pd.Series(np.random.exponential(100, 50))
        E = pd.Series(np.random.binomial(1, 0.7, 50))
        result = kaplan_meier(T, E)
        assert result["analysis_type"] == "reliability.survival.km"
        assert result["summary"]["n_subjects"] == 50
        assert result["summary"]["n_events"] + result["summary"]["n_censored"] == 50
        assert len(result["timeline"]) > 0
        assert len(result["survival_function"]) == len(result["timeline"])
        assert result["summary"]["median_survival"] is not None

    def test_km_with_all_events(self):
        T = pd.Series([10, 20, 30, 40, 50])
        E = pd.Series([1, 1, 1, 1, 1])
        result = kaplan_meier(T, E)
        assert result["summary"]["n_censored"] == 0
        assert result["summary"]["n_events"] == 5

    def test_km_with_all_censored(self):
        T = pd.Series([10, 20, 30, 40, 50])
        E = pd.Series([0, 0, 0, 0, 0])
        result = kaplan_meier(T, E)
        assert result["summary"]["n_events"] == 0
        assert result["summary"]["median_survival"] is None

    def test_km_insufficient_data(self):
        T = pd.Series([10])
        E = pd.Series([1])
        result = kaplan_meier(T, E)
        assert "error" in result


class TestKaplanMeierCompare:

    def test_basic_compare(self):
        np.random.seed(42)
        T_A = pd.Series(np.random.exponential(100, 50))
        E_A = pd.Series(np.random.binomial(1, 0.7, 50))
        T_B = pd.Series(np.random.exponential(80, 50))
        E_B = pd.Series(np.random.binomial(1, 0.7, 50))
        result = kaplan_meier_compare(T_A, E_A, T_B, E_B)
        assert result["analysis_type"] == "reliability.survival.km_compare"
        assert "group_a" in result
        assert "group_b" in result
        assert "logrank_p_value" in result["summary"]

    def test_compare_significant_difference(self):
        np.random.seed(42)
        T_A = pd.Series(np.random.exponential(200, 100))
        E_A = pd.Series(np.random.binomial(1, 0.5, 100))
        T_B = pd.Series(np.random.exponential(50, 100))
        E_B = pd.Series(np.random.binomial(1, 0.9, 100))
        result = kaplan_meier_compare(T_A, E_A, T_B, E_B)
        # With such different rates, log-rank should detect difference
        assert result["summary"]["logrank_p_value"] < 0.1


class TestLogrankTest:

    def test_basic_logrank(self):
        np.random.seed(42)
        T_A = pd.Series(np.random.exponential(100, 50))
        E_A = pd.Series(np.random.binomial(1, 0.7, 50))
        T_B = pd.Series(np.random.exponential(80, 50))
        E_B = pd.Series(np.random.binomial(1, 0.7, 50))
        result = logrank_test(T_A, E_A, T_B, E_B)
        assert result["analysis_type"] == "reliability.survival.logrank"
        assert "test_statistic" in result["summary"]
        assert "p_value" in result["summary"]
        assert result["summary"]["is_significant"] in (True, False)

    def test_logrank_identical_groups(self):
        np.random.seed(42)
        T = pd.Series(np.random.exponential(100, 50))
        E = pd.Series(np.random.binomial(1, 0.7, 50))
        result = logrank_test(T, E, T, E)
        # Identical groups → p ≈ 1.0
        assert result["summary"]["p_value"] > 0.9

    def test_logrank_insufficient_data(self):
        T_A = pd.Series([10])
        E_A = pd.Series([1])
        T_B = pd.Series([20])
        E_B = pd.Series([1])
        result = logrank_test(T_A, E_A, T_B, E_B)
        assert "error" in result


class TestCoxRegression:

    def test_basic_cox(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "T": np.random.exponential(100, 80),
            "E": np.random.binomial(1, 0.7, 80),
            "X1": np.random.randn(80),
            "X2": np.random.randn(80),
        })
        result = cox_regression(df, "T", "E", ["X1", "X2"])
        assert result["analysis_type"] == "reliability.survival.cox"
        assert result["summary"]["n_subjects"] == 80
        assert 0 < result["summary"]["concordance_index"] < 1
        assert "X1" in result["coefficients"]
        assert "X2" in result["coefficients"]
        # CI should contain estimate
        for var in ["X1", "X2"]:
            ci = result["coefficients"][var]
            assert ci["ci_lower"] < ci["coef"] < ci["ci_upper"]

    def test_cox_single_covariate(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "T": np.random.exponential(100, 60),
            "E": np.random.binomial(1, 0.7, 60),
            "group": np.random.binomial(1, 0.5, 60),
        })
        result = cox_regression(df, "T", "E", ["group"])
        assert "group" in result["coefficients"]
        assert result["summary"]["AIC_partial"] > 0

    def test_cox_missing_column(self):
        df = pd.DataFrame({"T": [1, 2], "E": [1, 0]})
        result = cox_regression(df, "T", "E", ["missing_col"])
        assert "error" in result

    def test_cox_insufficient_data(self):
        df = pd.DataFrame({"T": [1, 2, 3], "E": [1, 0, 1], "X": [1, 2, 3]})
        result = cox_regression(df, "T", "E", ["X"])
        assert "error" in result

    def test_cox_no_covariates(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "T": np.random.exponential(100, 60),
            "E": np.random.binomial(1, 0.7, 60),
        })
        result = cox_regression(df, "T", "E")
        assert result["summary"]["n_subjects"] == 60
        assert result["coefficients"] == {}

    def test_cox_baseline_survival(self):
        np.random.seed(42)
        df = pd.DataFrame({
            "T": np.random.exponential(100, 60),
            "E": np.random.binomial(1, 0.7, 60),
            "X1": np.random.randn(60),
        })
        result = cox_regression(df, "T", "E", ["X1"])
        bs = result["baseline_survival"]
        assert "timeline" in bs
        assert "survival" in bs
        assert len(bs["timeline"]) > 0
        assert len(bs["survival"]) == len(bs["timeline"])
