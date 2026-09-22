"""QAM Harness — v4.2.0 P2 新算法的工具接线测试

覆盖 `run_spc` 新增图型（mewma / gen_var / residual）与 `detect_changepoints`：
真实引擎接线、参数解析（columns / lambda_ / subgroup_size）、异常兜底。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.agent.tools import AgentContext, build_default_registry


@pytest.fixture(scope="module")
def frames():
    rng = np.random.default_rng(29)
    n = 120
    return {
        "Sheet1": pd.DataFrame({
            "直径": rng.normal(10.0, 0.12, n),
            "圆度": rng.normal(0.02, 0.004, n),
            "子组": [f"G{i // 5 + 1}" for i in range(n)],
            "漂移": np.concatenate([rng.normal(0, 1, 60), rng.normal(4, 1, 60)]),
        }),
    }


@pytest.fixture
def ctx(frames):
    return AgentContext(data_frames=frames)


@pytest.fixture
def registry(ctx):
    return build_default_registry(ctx)


class TestMewmaTool:
    def test_runs_with_explicit_columns(self, registry, ctx):
        result = registry.call("run_spc",
                               {"chart_type": "mewma", "columns": "直径,圆度",
                                "lambda_": 0.2}, ctx)
        assert result.ok, result.error
        assert result.data["detail"]["chart"] == "mewma"
        assert result.data["ucl"] is not None
        assert result.data["violations"] >= 0
        assert "MEWMA" in result.text

    def test_defaults_to_first_two_numeric_columns(self, registry, ctx):
        result = registry.call("run_spc", {"chart_type": "mewma"}, ctx)
        assert result.ok, result.error
        assert result.data["ucl"] > 0

    def test_missing_column_reports_error(self, registry, ctx):
        result = registry.call("run_spc",
                               {"chart_type": "mewma", "columns": "直径,不存在"}, ctx)
        assert not result.ok
        assert "列不存在" in result.error


class TestGenVarTool:
    def test_subgroup_size_mode(self, registry, ctx):
        result = registry.call("run_spc",
                               {"chart_type": "gen_var", "columns": "直径,圆度",
                                "subgroup_size": 5}, ctx)
        assert result.ok, result.error
        assert result.data["detail"]["chart"] == "genvar"
        assert result.data["detail"]["cl"] > 0

    def test_subgroup_column_mode(self, registry, ctx):
        result = registry.call("run_spc",
                               {"chart_type": "gen_var", "columns": "直径,圆度",
                                "subgroup_col": "子组"}, ctx)
        assert result.ok, result.error
        assert result.data["ucl"] >= result.data["cl"]


class TestResidualChartTool:
    def test_residual_chart_runs(self, registry, ctx):
        result = registry.call("run_spc",
                               {"chart_type": "residual", "column": "直径"}, ctx)
        assert result.ok, result.error
        assert result.data["detail"]["chart"] == "residual"
        assert result.data["ucl"] is not None and result.data["cl"] is not None
        assert "残差" in result.text

    def test_unknown_chart_type_lists_supported(self, registry, ctx):
        result = registry.call("run_spc", {"chart_type": "bogus"}, ctx)
        assert not result.ok
        assert "mewma" in result.error and "gen_var" in result.error


class TestChangePointTool:
    def test_detects_known_shift(self, registry, ctx):
        result = registry.call("detect_changepoints",
                               {"column": "漂移", "model": "mean"}, ctx)
        assert result.ok, result.error
        points = result.data["changepoints"]
        assert points, "应检出均值漂移"
        assert abs(points[0] - 60) <= 3
        assert result.data["segments"][0]["mean"] < result.data["segments"][-1]["mean"]
        assert "变点" in result.text

    def test_meanvar_model_and_penalty(self, registry, ctx):
        result = registry.call("detect_changepoints",
                               {"column": "漂移", "model": "meanvar",
                                "penalty": 8.0, "min_size": 5}, ctx)
        assert result.ok, result.error
        assert result.data["model"] == "meanvar"
        assert result.data["penalty"] == 8.0
        assert result.data["min_size"] == 5

    def test_invalid_model_returns_error(self, registry, ctx):
        result = registry.call("detect_changepoints",
                               {"column": "漂移", "model": "bogus"}, ctx)
        assert not result.ok
