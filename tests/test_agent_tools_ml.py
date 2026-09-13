"""v4.0.0 P4 — QAM Harness 机器学习工具（6 个真引擎工具 + 离线路由）。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from core.agent.tools import AgentContext, build_default_registry

ML_TOOLS = ("ml_prepare_data", "ml_train", "ml_automl", "ml_evaluate",
            "ml_explain", "ml_predict")


@pytest.fixture(scope="module")
def frame():
    rng = np.random.default_rng(51)
    n = 200
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    df = pd.DataFrame({
        "温度": x1,
        "压力": x2,
        "产线": rng.choice(["L1", "L2"], n),
        "强度": 3 * x1 + np.sin(2 * x2) + rng.normal(0, 0.4, n),
    })
    df["判定"] = np.where(x1 + x2 + rng.normal(0, 0.5, n) > 0, "PASS", "FAIL")
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


def test_ml_tools_registered(registry):
    names = set(registry.names())
    for tool in ML_TOOLS:
        assert tool in names, f"缺少工具 {tool}"
    assert "机器学习" in registry.by_category()
    assert len(names) >= 36


def test_prepare_data_tool(registry, ctx):
    res = _call(registry, ctx, "ml_prepare_data", target="强度",
                features="温度,压力")
    assert res.data["task"] == "regression"
    assert res.data["features"] == ["温度", "压力"]
    assert "数据准备" in res.text

    cls = _call(registry, ctx, "ml_prepare_data", target="判定")
    assert cls.data["task"] == "classification"
    assert cls.data["class_counts"]


def test_train_tree_tool(registry, ctx):
    res = _call(registry, ctx, "ml_train", target="强度", model="tree", cv=3)
    assert res.data["task"] == "regression"
    assert res.data["metrics"]["test"]["r2"] > 0.8
    assert res.data["rules"]
    assert res.data["importances"]
    assert "机器学习训练" in res.text


def test_train_classification_tool(registry, ctx):
    res = _call(registry, ctx, "ml_train", target="判定", model="forest", cv=3)
    assert res.data["task"] == "classification"
    assert res.data["metrics"]["test"]["accuracy"] > 0.7


def test_automl_tool(registry, ctx):
    res = _call(registry, ctx, "ml_automl", target="强度", models="linear,tree",
                cv=3, time_budget_s=60)
    assert res.data["best_model"] in {"linear", "tree"}
    assert len(res.data["leaderboard"]) == 2
    assert "推荐" in res.text


def test_evaluate_and_explain_tools(registry, ctx):
    ev = _call(registry, ctx, "ml_evaluate", target="强度", model="forest",
               cv=3, learning_curve=True)
    assert ev.data["cv_scores"]["r2"]
    assert ev.data["residuals"]["std"] >= 0
    assert ev.data["learning_curve"]["train_mean"]

    ex = _call(registry, ctx, "ml_explain", target="强度", model="forest",
               max_rows=100)
    assert ex.data["method"] in {"shap", "native", "permutation"}
    assert ex.data["importances"]
    assert "模型解释" in ex.text

    row = _call(registry, ctx, "ml_explain", target="强度", model="tree",
                row_index=3)
    assert row.data["contributions"]


def test_predict_tool_saves_and_loads_model(registry, ctx, tmp_path):
    save_path = tmp_path / "strength"
    res = _call(registry, ctx, "ml_predict", target="强度", model="tree",
                save_path=str(save_path))
    assert res.data["model_path"].endswith(".qamodel")
    assert res.data["predictions"]

    loaded = _call(registry, ctx, "ml_predict", model_path=res.data["model_path"])
    assert loaded.data["source"] == "file"
    assert "加载模型预测" in loaded.text
    assert loaded.data["predictions"]


def test_offline_routing_hits_ml_tools(registry, ctx):
    from core.agent.engine import AgentEngine, _match_offline

    assert _match_offline("帮我用随机森林做个机器学习模型", False) == "ml_automl"
    assert _match_offline("哪些特征重要", False) == "ml_explain"
    assert _match_offline("用模型预测新数据", False) == "ml_predict"

    engine = AgentEngine(registry, context=ctx)
    args = engine._offline_args("ml_predict", "加载模型 models/强度.qamodel 做预测")
    assert args["model_path"].endswith(".qamodel")
    assert engine._offline_args("ml_explain", "解释第 12 行")["row_index"] == 12
