"""O1 回归 — QAM Harness 扩展工具（覆盖 36 个分析 Tab 的主要能力）。

每个工具都用真实分析引擎跑一遍合成数据，防止"工具存在但接线不通"。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.agent.tools import AgentContext, build_default_registry


@pytest.fixture(scope="module")
def frame():
    rng = np.random.default_rng(11)
    n = 60
    df = pd.DataFrame({
        "测量值": rng.normal(10, 0.12, n),
        "子组": [f"L{i % 5}" for i in range(n)],
        "操作员": [f"OP{i % 3}" for i in range(n)],
        "零件": [f"P{i % 10}" for i in range(n)],
        "参考值": rng.normal(10, 0.1, n),
        "判定": rng.choice(["OK", "NG"], n),
        "标准判定": rng.choice(["OK", "NG"], n),
        "不合格数": rng.integers(0, 4, n),
        "样本量": rng.integers(90, 110, n),
        "因素A": rng.choice(["-1", "1"], n),
        "因素B": rng.choice(["-1", "1"], n),
        "分类": rng.choice(["A", "B"], n),
        "X1": rng.normal(0, 1, n),
        "失效时间": np.round(rng.gamma(2, 50, n), 1) + 10,
        "事件": rng.integers(0, 2, n),
        "MTBF": rng.integers(800, 2000, n),
        "观测时间": rng.normal(12, 1.5, n),
        "状态": rng.choice(["工作", "等待", "走动"], n),
        "工序名称": [f"工序{i + 1}" for i in range(n)],
        "CT": rng.uniform(8, 16, n),
        "时序": (rng.normal(100, 2, 120).cumsum() / 10 + 50)[:n],
        "可用时间": rng.uniform(7, 9, n),
        "故障时间": rng.uniform(0, 1, n),
        "换型时间": rng.uniform(0, 0.5, n),
        "等待时间": rng.uniform(0, 0.5, n),
        "总产量": rng.integers(200, 400, n),
        "良品数": rng.integers(180, 380, n),
    })
    df["响应"] = (pd.to_numeric(df["因素A"]) * 0.5
                  + pd.to_numeric(df["因素B"]) * 0.2 + rng.normal(0, 0.1, n))
    df["Y"] = df["X1"] * 2 + rng.normal(0, 0.3, n)
    return df


@pytest.fixture
def ctx(frame):
    return AgentContext(data_frames={"Sheet1": frame})


@pytest.fixture
def registry(ctx):
    return build_default_registry(ctx)


def _call(registry, ctx, name, **args):
    result = registry.call(name, args, ctx)
    assert result.ok, f"{name} 失败: {result.error}"
    return result


# ---------- 工具集完整性 ----------


def test_toolset_covers_all_analysis_domains(registry):
    names = set(registry.names())
    for required in (
            "run_spc", "run_laney_chart", "run_hotelling_t2",
            "run_capability", "run_capability_sixpack", "run_capability_advanced",
            "run_msa_grr", "run_msa_advanced", "run_hypothesis_test",
            "run_hypothesis_advanced", "run_doe_analysis", "generate_doe_design",
            "run_power_analysis", "run_regression", "run_reliability",
            "run_time_series", "run_ie_analysis", "run_root_cause",
            "run_oee", "estimate_cost", "get_alerts", "get_project_context",
            "get_plant", "search_knowledge", "explain_metric"):
        assert required in names, f"缺少工具 {required}"
    assert len(names) >= 30
    assert len(registry.by_category()) >= 9


# ---------- 质量分析扩展 ----------


def test_laney_chart(registry, ctx):
    res = _call(registry, ctx, "run_laney_chart", defects_column="不合格数",
                sizes_column="样本量")
    assert res.data["cl"] is not None
    assert "σ_Z" in res.text


def test_hotelling_ucl_usable_without_subgroups(registry, ctx):
    """v3.8.0 修复：无子组（个体观测）时 T² UCL 不再为 0、不再误报。"""
    res = _call(registry, ctx, "run_hotelling_t2", columns="测量值,参考值")
    assert res.data["ucl_usable"] is True
    ucl = np.asarray(res.data["t2_ucl"], dtype=float)
    assert np.all(np.isfinite(ucl)) and np.all(ucl > 0)
    assert "控制限不可用" not in res.text

    fixed = _call(registry, ctx, "run_hotelling_t2", columns="测量值,参考值",
                  subgroup_column="子组")
    assert fixed.data["ucl_usable"] is True
    assert "控制限不可用" not in fixed.text


def test_hotelling_warns_when_limit_unusable():
    """自由度不足（子组大小 [2,1]，p=2）时控制限为 NaN → 工具仍须显式告警。"""
    df = pd.DataFrame({"X1": [1.0, 2.0, 3.0], "X2": [2.0, 1.0, 3.0],
                       "G": ["a", "a", "b"]})
    small_ctx = AgentContext(data_frames={"Sheet1": df})
    reg = build_default_registry(small_ctx)
    res = _call(reg, small_ctx, "run_hotelling_t2", columns="X1,X2",
                subgroup_column="G")
    assert res.data["ucl_usable"] is False
    assert "控制限不可用" in res.text


def test_capability_sixpack_and_advanced(registry, ctx):
    six = _call(registry, ctx, "run_capability_sixpack", column="测量值",
                usl=10.5, lsl=9.5)
    assert six.data["cpk"] is not None

    bw = _call(registry, ctx, "run_capability_advanced", method="between_within",
               column="测量值", subgroup_column="子组", usl=10.5, lsl=9.5)
    assert bw.data["std_within"] is not None
    assert "标准差比" in bw.text

    johnson = _call(registry, ctx, "run_capability_advanced", method="johnson",
                    column="测量值")
    assert johnson.data["johnson_type"]

    tol = _call(registry, ctx, "run_capability_advanced", method="tolerance_interval",
                column="测量值")
    assert tol.data["lower"] < tol.data["upper"]


def test_msa_advanced_methods(registry, ctx):
    t1 = _call(registry, ctx, "run_msa_advanced", method="type1",
               measurement_column="测量值", reference=10.0)
    assert t1.data["repeatability"] > 0 and t1.data["bias"] is not None

    attr = _call(registry, ctx, "run_msa_advanced", method="attribute_agreement",
                 result_column="判定", standard_column="标准判定",
                 operator_column="操作员")
    assert attr.data["kappa"] is not None

    emp = _call(registry, ctx, "run_msa_advanced", method="emp",
                measurement_column="测量值", part_column="零件",
                operator_column="操作员")
    assert emp.data["ndc"] is not None

    lin = _call(registry, ctx, "run_msa_advanced", method="linearity",
                measurement_column="测量值", reference_column="参考值")
    assert lin.data["slope"] is not None


def test_hypothesis_advanced_methods(registry, ctx):
    a2 = _call(registry, ctx, "run_hypothesis_advanced", method="anova_twoway",
               column="响应", factor_a="因素A", factor_b="因素B")
    assert "显著因素" in a2.text

    chi = _call(registry, ctx, "run_hypothesis_advanced", method="chi_square",
                column="判定", categorical_column="分类")
    assert chi.data["p_value"] is not None

    prop = _call(registry, ctx, "run_hypothesis_advanced", method="proportion",
                 successes1=8, n1=100, successes2=15, n2=100)
    assert prop.data["p_value"] is not None

    tost = _call(registry, ctx, "run_hypothesis_advanced", method="tost",
                 column="测量值", target_mean=10.0, margin=0.5)
    assert tost.data["equivalent"] is not None

    mw = _call(registry, ctx, "run_hypothesis_advanced", method="mann_whitney",
               column="测量值", second_column="参考值")
    assert mw.data["p_value"] is not None

    kw = _call(registry, ctx, "run_hypothesis_advanced", method="kruskal",
               column="测量值", group_column="子组")
    assert kw.data["p_value"] is not None


# ---------- DOE / 回归 / 可靠性 / 时序 ----------


def test_doe_analysis_and_design_generation(registry, ctx):
    doe = _call(registry, ctx, "run_doe_analysis", design="factorial",
                response_column="响应", factor_columns="因素A,因素B")
    assert doe.data["r_squared"] is not None
    assert "R²" in doe.text

    for design, factors in (("bbd", "温度,压力,时间"),
                            ("ccd", "温度,压力"),
                            ("fractional", "A,B,C,D"),
                            ("plackett_burman", "A,B,C"),
                            ("dsd", "A,B,C,D"),          # DSD 引擎要求 ≥4 因子
                            ("taguchi", "A,B,C"),
                            ("factorial", "A,B")):
        res = _call(registry, ctx, "generate_doe_design", design=design,
                    factors=factors)
        assert res.data["runs"] > 0 and res.data["head"]

    bad = registry.call("generate_doe_design", {"design": "不存在", "factors": "A,B"}, ctx)
    assert bad.ok is False and "不支持" in bad.error


def test_doe_rejects_non_numeric_factors(registry, ctx):
    res = registry.call("run_doe_analysis",
                        {"design": "factorial", "response_column": "响应",
                         "factor_columns": "分类"}, ctx)
    assert res.ok is False and "数值" in res.error


def test_power_analysis(registry, ctx):
    size = _call(registry, ctx, "run_power_analysis", method="sample_size",
                 test="two_sample", delta=0.5, sigma=1.0, power=0.8)
    assert size.data["value"] > 0
    power = _call(registry, ctx, "run_power_analysis", method="power",
                  test="one_sample", n=30, delta=0.5, sigma=1.0)
    assert 0 < power.data["value"] <= 1


def test_regression(registry, ctx):
    res = _call(registry, ctx, "run_regression", response_column="Y",
                factor_columns="X1")
    assert res.data["r_squared"] is not None
    assert res.data["p_value"] is not None


def test_reliability_methods(registry, ctx):
    wb = _call(registry, ctx, "run_reliability", method="weibull",
               time_column="失效时间")
    assert wb.data["beta"] > 0 and wb.data["eta"] > 0

    km = _call(registry, ctx, "run_reliability", method="kaplan_meier",
               time_column="失效时间", event_column="事件")
    assert km.data["summary"]

    cox = _call(registry, ctx, "run_reliability", method="cox",
                time_column="失效时间", event_column="事件", covariates="测量值")
    assert cox.data["concordance"] is not None

    crow = _call(registry, ctx, "run_reliability", method="crow_amsaa",
                 time_column="失效时间")
    assert crow.data["beta"] is not None

    wr = _call(registry, ctx, "run_reliability", method="warranty",
               time_column="失效时间", warranty_period=365, cost_per_failure=120,
               total_units=5000)
    assert wr.data["summary"]

    rbd = _call(registry, ctx, "run_reliability", method="rbd",
                mtbf_column="MTBF", structure="series", mission_time=100)
    assert 0 < rbd.data["system_reliability"] <= 1
    assert rbd.data["weakest_component"]


def test_time_series_methods(registry, ctx):
    arima = _call(registry, ctx, "run_time_series", method="arima",
                  column="时序", horizon=6)
    assert arima.data["order"] is not None

    es = _call(registry, ctx, "run_time_series", method="exp_smoothing",
               column="时序", horizon=6)
    assert es.data["forecast"]

    decomp = _call(registry, ctx, "run_time_series", method="decomposition",
                   column="时序")
    assert decomp.data["period"]

    acf = _call(registry, ctx, "run_time_series", method="acf_pacf",
                column="时序", lags=20)
    assert acf.data["stationary"] is not None


def test_ie_methods(registry, ctx):
    ts = _call(registry, ctx, "run_ie_analysis", method="time_study",
               time_column="观测时间", rating=1.05, allowance_pct=15)
    assert ts.data["standard_time"] > ts.data["normal_time"]

    lb = _call(registry, ctx, "run_ie_analysis", method="line_balance", takt=14)
    assert lb.data["balance_rate"] is not None

    vsm = _call(registry, ctx, "run_ie_analysis", method="vsm", daily_demand=100)
    assert vsm.data["lead_time_days"] is not None

    ws = _call(registry, ctx, "run_ie_analysis", method="work_sampling",
               status_column="状态")
    assert ws.data["observations"] == len(ctx.data_frames["Sheet1"])
    assert "有效作业率" in ws.text

    smed = _call(registry, ctx, "run_ie_analysis", method="smed",
                 task_column="工序名称", task_type_column="分类",
                 time_column="观测时间")
    assert smed.data["result"]["total_before"] > 0

    tpm = _call(registry, ctx, "run_ie_analysis", method="tpm")
    assert 0 <= tpm.data["overall"]["oee"] <= 1


def test_root_cause(registry, ctx):
    res = _call(registry, ctx, "run_root_cause", target_column="测量值", top_k=3)
    assert res.data["causes"]
    assert "根因分析" in res.text


# ---------- 错误处理 ----------


def test_missing_columns_report_clearly(registry, ctx):
    res = registry.call("run_reliability",
                        {"method": "weibull", "time_column": "不存在列"}, ctx)
    assert res.ok is False and "不存在" in res.error

    res = registry.call("run_ie_analysis", {"method": "vsm"}, ctx)
    assert res.ok is False and "daily_demand" in res.error

    res = registry.call("run_hypothesis_advanced", {"method": "tost",
                                                    "column": "测量值"}, ctx)
    assert res.ok is False and "target_mean" in res.error
