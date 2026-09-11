"""QAM Harness 工具注册表测试 — 真实引擎接线 / 参数缺省 / 异常兜底。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.agent.explain import explain_metric
from core.agent.tools import AgentContext, ToolResult, build_default_registry


@pytest.fixture(scope="module")
def frames():
    rng = np.random.default_rng(11)
    n = 60
    return {
        "Sheet1": pd.DataFrame({
            "直径": rng.normal(10.0, 0.12, n),
            "操作员": [f"OP{i % 3 + 1}" for i in range(n)],
            "零件": [f"P{i % 10 + 1}" for i in range(n)],
            "USL": [10.5] * n,
            "LSL": [9.5] * n,
        }),
        "IE": pd.DataFrame({
            "资源ID": ["L1", "L2"],
            "可用时间": [8.0, 8.0],
            "停机时间": [0.5, 1.0],
            "理想节拍": [12.0, 15.0],
            "总产量": [380, 300],
            "良品数": [370, 280],
        }),
    }


@pytest.fixture
def ctx(frames):
    return AgentContext(data_frames=frames)


@pytest.fixture
def registry(ctx):
    return build_default_registry(ctx)


# ---------- 注册表框架 ----------


def test_registry_exposes_full_toolset(registry):
    names = registry.names()
    # 覆盖软件主要能力（14+ 工具）
    for required in ("list_data", "describe_column", "run_spc", "run_capability",
                     "run_msa_grr", "run_hypothesis_test", "run_oee",
                     "get_live_oee", "estimate_cost", "get_alerts",
                     "get_connector_health", "get_project_context", "get_plant",
                     "list_analyses", "search_knowledge", "explain_metric"):
        assert required in names, f"缺少工具 {required}"
    assert len(names) >= 16
    assert len(registry.by_category()) >= 5
    assert "run_spc" in registry and registry.get("run_spc").parameters
    assert "list_data" in registry.describe()


def test_registry_unknown_tool_and_bad_args(registry, ctx):
    bad = registry.call("no_such_tool", {}, ctx)
    assert bad.ok is False and "未知工具" in bad.error
    # 未知参数被忽略而非异常
    res = registry.call("list_data", {"bogus": 1}, ctx)
    assert res.ok is True


def test_registry_captures_handler_exception(ctx):
    reg = build_default_registry(ctx)
    text_only = AgentContext(data_frames={"T": pd.DataFrame({"名称": ["a", "b", "c"]})})
    res = reg.call("describe_column", {"sheet": "T", "column": "名称"}, text_only)
    assert res.ok is False and res.error


def test_tool_result_summary_truncates():
    res = ToolResult(name="t", text="x" * 2000)
    assert len(res.summary(max_chars=100)) <= 101
    assert res.as_dict()["name"] == "t"


# ---------- 上下文 ----------


def test_context_helpers(ctx):
    assert ctx.sheet_names() == ["Sheet1", "IE"]
    assert "直径" in ctx.numeric_columns("Sheet1")
    assert "操作员" in ctx.text_columns("Sheet1")
    assert ctx.pick_column("Sheet1", "直径") == "直径"
    assert ctx.pick_column("Sheet1", preferred="不存在") == "直径"   # 回退首个数值列
    assert ctx.sheet_of("sheet1") == "Sheet1"                       # 大小写不敏感
    assert ctx.frame() is not None
    assert "数据表 2 张" in ctx.summary()


# ---------- 工具行为 ----------


def test_list_data_and_describe_column(registry, ctx):
    res = registry.call("list_data", {}, ctx)
    assert res.ok and len(res.data["sheets"]) == 2
    assert "Sheet1" in res.text and "IE" in res.text

    res = registry.call("describe_column", {"sheet": "Sheet1", "column": "直径"}, ctx)
    assert res.ok and res.data["count"] == 60
    assert res.data["min"] < res.data["mean"] < res.data["max"]
    assert "均值" in res.text


def test_run_spc_imr_and_xbar(registry, ctx):
    imr = registry.call("run_spc", {"chart_type": "imr", "column": "直径"}, ctx)
    assert imr.ok and imr.data["ucl"] > imr.data["cl"] > imr.data["lcl"]
    assert "判异点" in imr.text

    xbar = registry.call("run_spc",
                         {"chart_type": "xbar_r", "column": "直径", "subgroup_size": 5},
                         ctx)
    assert xbar.ok and xbar.data["chart_type"] == "xbar_r"

    bad = registry.call("run_spc", {"chart_type": "not_a_chart"}, ctx)
    assert bad.ok is False and "不支持" in bad.error


def test_run_capability_uses_table_specs_and_reports_metrics(registry, ctx):
    res = registry.call("run_capability", {"sheet": "Sheet1", "column": "直径"}, ctx)
    assert res.ok, res.error
    assert res.data["usl"] == 10.5 and res.data["lsl"] == 9.5     # 从 USL/LSL 列读取
    assert res.data["cp"] and res.data["cpk"]
    assert "Cpk=" in res.text and "PPM" in res.text

    missing = registry.call("run_capability",
                            {"sheet": "IE", "column": "总产量"}, ctx)
    assert missing.ok is False and "USL" in missing.error


def test_run_msa_grr_and_hypothesis(registry, ctx):
    grr = registry.call("run_msa_grr", {"sheet": "Sheet1", "measurement_column": "直径"},
                        ctx)
    assert grr.ok, grr.error
    assert grr.data["grr_pct"] is not None and "ndc" in grr.data

    norm = registry.call("run_hypothesis_test",
                         {"test": "normality", "sheet": "Sheet1", "column": "直径"}, ctx)
    assert norm.ok and "正态" in norm.text

    anova = registry.call("run_hypothesis_test",
                          {"test": "anova_oneway", "sheet": "Sheet1", "column": "直径",
                           "group_column": "操作员"}, ctx)
    assert anova.ok and "p=" in anova.text


def test_run_oee_from_ie_sheet(registry, ctx):
    res = registry.call("run_oee", {"sheet": "IE"}, ctx)
    assert res.ok, res.error
    overall = res.data["overall"]
    assert 0 <= overall["oee"] <= 1
    assert overall["availability"] <= 1.0
    assert "OEE" in res.text


def test_tools_that_need_missing_context_return_clear_errors(registry, ctx):
    for tool, args, keyword in (
            ("get_live_oee", {}, "未接入"),
            ("get_alerts", {}, "未接入"),
            ("get_connector_health", {}, "未接入"),
            ("get_project_context", {}, "未接入"),
            ("get_plant", {}, "未配置产线"),
            ("estimate_cost", {}, "未配置产线"),
            ("list_analyses", {}, "还没有")):
        res = registry.call(tool, args, ctx)
        assert res.ok is False, f"{tool} 应返回失败"
        assert keyword in res.error, f"{tool} 错误信息应包含「{keyword}」: {res.error}"


def test_explain_metric_known_and_unknown():
    cpk = explain_metric("Cpk", 0.8)
    assert cpk["level"] == "不足" and "对中" in cpk["advice"]
    assert explain_metric("grr", 5)["level"] == "可接受"
    assert explain_metric("oee", 0.9)["level"] == "世界级"
    assert explain_metric("p_value", 0.01)["level"] == "显著"
    assert explain_metric("不存在的指标", 1) is None
