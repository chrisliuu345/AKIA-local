"""QAM Harness 机器学习工具（v4.0.0 P4）— 6 个真引擎工具。

ml_prepare_data · ml_train · ml_automl · ml_evaluate · ml_explain · ml_predict

沿用 tools.py 约定：直接调用 analysis/ml 引擎，返回结构化 data + 中文 text。
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from core.agent.tools import AgentContext, ToolRegistry, ToolResult, _fmt
from core.agent.tools_ext import _as_list, _df, _match_columns


def _target_column(frame: pd.DataFrame, target: Optional[str]) -> str:
    if not target:
        raise ValueError("请指定目标列 target（数值列做回归，文本/0-1 列做分类）")
    return _match_columns(frame, [target], kind="any")[0]


def _feature_columns(ctx: AgentContext, name: str, frame: pd.DataFrame,
                     target: str, features) -> list[str]:
    wanted = _as_list(features)
    if wanted:
        return _match_columns(frame, wanted)
    numeric = [c for c in ctx.numeric_columns(name) if c != target]
    if numeric:
        return numeric
    return [c for c in frame.columns if c != target]


def _model_runner(frame: pd.DataFrame, target: str, features: list[str],
                  task: Optional[str], model: str, cv: int, test_size: float,
                  random_state: int) -> dict:
    """按模型名分发到对应真引擎（保持各引擎的丰富输出）。"""
    from analysis.ml import boosting, forest, mars, train, trees
    from analysis.ml.train import normalize_model

    name = normalize_model(model)
    if name == "tree":
        return trees.analyze(frame, target, features, task=task, cv=cv,
                             test_size=test_size, random_state=random_state,
                             auto_prune=True)
    if name == "forest":
        return forest.analyze(frame, target, features, task=task, cv=cv,
                              test_size=test_size, random_state=random_state,
                              n_estimators=120)
    if name == "boosting":
        return boosting.analyze(frame, target, features, task=task, cv=cv,
                                test_size=test_size, random_state=random_state,
                                max_iter=150)
    if name == "mars":
        return mars.analyze(frame, target, features, task=task, cv=cv,
                            test_size=test_size, random_state=random_state)
    return train.fit_pipeline(frame, target, features, task=task, model="linear",
                              cv=cv, test_size=test_size,
                              random_state=random_state)


def _trim_leaderboard(leaderboard: list[dict], task: str) -> list[dict]:
    key = "r2_mean" if task == "regression" else "accuracy_mean"
    trimmed = []
    for item in leaderboard:
        trimmed.append({
            "rank": item["rank"], "model": item["model"], "label": item["label"],
            "cv_score": float(item["cv"].get(key, float("nan"))),
            "test_score": float(item["test"].get(
                "r2" if task == "regression" else "accuracy", float("nan"))),
            "duration_s": item["duration_s"],
        })
    return trimmed


def register_ml_tools(reg: ToolRegistry, ctx: AgentContext) -> None:
    """注册 6 个机器学习工具（工具数 30 → 36）。"""

    # ---------------- 数据准备 ----------------
    @reg.tool("ml_prepare_data", "机器学习数据准备",
              "对数据表做机器学习体检：任务类型判定（回归/分类）、特征建议、缺失与类别分布",
              {"sheet": "表名(可选)", "target": "目标列(必填)", "features": "特征列(逗号分隔，可选)"},
              category="机器学习", returns="task/columns/class_counts")
    def _prepare_data(context: AgentContext, sheet: str = None,
                      target: str = None, features=None):
        from analysis.ml import prep
        name, frame = _df(context, sheet)
        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        out = prep.describe_dataset(frame, tgt, cols)
        lines = [f"数据准备 — 表「{name}」目标列「{tgt}」: "
                 f"{out['n_rows']} 行，任务类型 {out['task']}"]
        for col in out["columns"]:
            lines.append(f"  · {col['name']}（{col['kind']}）缺失 {col['missing']}，"
                         f"唯一值 {col['unique']}")
        if out["class_counts"]:
            lines.append("  类别分布: " + "，".join(
                f"{k}={v}" for k, v in out["class_counts"].items()))
        return ToolResult("ml_prepare_data",
                          data={"sheet": name, "target": tgt, "features": cols, **out},
                          text="\n".join(lines))

    # ---------------- 训练 ----------------
    @reg.tool("ml_train", "机器学习模型训练",
              "训练单个模型并返回训练/测试指标与交叉验证（CART/随机森林/梯度提升/MARS/线性）",
              {"sheet": "表名(可选)", "target": "目标列(必填)", "features": "特征列(可选)",
               "model": "tree/forest/boosting/mars/linear", "task": "regression/classification(可选)",
               "cv": "折数(默认5)"},
              category="机器学习", returns="metrics/cv/importances/rules")
    def _train(context: AgentContext, sheet: str = None, target: str = None,
               features=None, model: str = "tree", task: str = None,
               cv: int = 5):
        name, frame = _df(context, sheet)
        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        result = _model_runner(frame, tgt, cols, task, model, int(cv), 0.2, 42)
        importances = (result.get("importances") or [])[:5]
        data = {
            "sheet": name, "target": tgt, "features": cols,
            "task": result.get("task"), "model": result.get("model", model),
            "metrics": result.get("metrics"), "cv": result.get("cv"),
            "importances": importances,
            "rules": result.get("rules") or result.get("terms") or [],
        }
        lines = [f"机器学习训练（表「{name}」→ {data['model']}）: "
                 f"{result.get('summary_text', '')}"]
        if importances:
            lines.append("  关键特征: " + "，".join(
                f"{i['feature']}({_fmt(i['importance'])})" for i in importances))
        if data["rules"]:
            lines.append("  规则/基函数示例: " + "；".join(data["rules"][:3]))
        return ToolResult("ml_train", data=data, text="\n".join(lines))

    # ---------------- AutoML ----------------
    @reg.tool("ml_automl", "AutoML 自动选模",
              "多模型交叉验证排名并推荐最优模型（线性/CART/随机森林/梯度提升/MARS）",
              {"sheet": "表名(可选)", "target": "目标列(必填)", "features": "特征列(可选)",
               "models": "模型列表(可选)", "cv": "折数(默认5)", "time_budget_s": "时间预算秒(默认90)"},
              category="机器学习", returns="leaderboard/best_model")
    def _automl(context: AgentContext, sheet: str = None, target: str = None,
                features=None, models=None, cv: int = 5,
                time_budget_s: float = 90.0):
        from analysis.ml import automl
        name, frame = _df(context, sheet)
        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        wanted = _as_list(models) or None
        result = automl.analyze(frame, tgt, cols, models=wanted, cv=int(cv),
                                time_budget_s=float(time_budget_s),
                                model_params={"forest": {"n_estimators": 120},
                                              "boosting": {"max_iter": 150}})
        leaderboard = _trim_leaderboard(result["leaderboard"], result["task"])
        lines = [f"AutoML（表「{name}」，按 {result['ranking_metric']} 排名）: "
                 f"{result['summary_text']}"]
        for item in leaderboard:
            lines.append(f"  {item['rank']}. {item['label']}: "
                         f"CV={_fmt(item['cv_score'])}，测试={_fmt(item['test_score'])}，"
                         f"{item['duration_s']}s")
        if result["skipped"]:
            lines.append("  跳过: " + "，".join(
                f"{s['model']}（{s['reason']}）" for s in result["skipped"]))
        return ToolResult("ml_automl",
                          data={"sheet": name, "target": tgt, "features": cols,
                                "task": result["task"], "ranking_metric": result["ranking_metric"],
                                "leaderboard": leaderboard,
                                "best_model": result["best_model"],
                                "best_label": result["best_label"]},
                          text="\n".join(lines))

    # ---------------- 评估 ----------------
    @reg.tool("ml_evaluate", "机器学习模型评估",
              "输出交叉验证各折、ROC/混淆矩阵、残差诊断，可选学习曲线",
              {"sheet": "表名(可选)", "target": "目标列(必填)", "features": "特征列(可选)",
               "model": "模型名", "cv": "折数(默认5)", "learning_curve": "是否输出学习曲线(true/false)"},
              category="机器学习", returns="cv_scores/roc/residuals/learning_curve")
    def _evaluate(context: AgentContext, sheet: str = None, target: str = None,
                  features=None, model: str = "forest", cv: int = 5,
                  learning_curve: bool = False):
        from analysis.ml import evaluate, train
        name, frame = _df(context, sheet)
        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        fit = train.fit_pipeline(frame, tgt, cols, model=model, cv=int(cv))
        task = fit["task"]
        pipeline = fit["pipeline"]
        y_test = fit["y_test"]
        preds = pipeline.predict(fit["X_test"])
        scores = pipeline.predict_proba(fit["X_test"]) if task != "regression" else None
        roc = evaluate.roc_curve_data(y_test, scores) if scores is not None else None
        residuals = (evaluate.residual_diagnostics(y_test, preds)
                     if task == "regression" else None)
        curve = None
        if learning_curve:
            X = pd.concat([fit["X_train"], fit["X_test"]])
            y = pd.concat([fit["y_train"], fit["y_test"]])
            curve = evaluate.learning_curve_data(pipeline, X, y, task, cv=int(cv))
        data = {"sheet": name, "target": tgt, "model": fit["model"],
                "task": task, "cv_scores": fit["cv_scores"], "cv": fit["cv"],
                "metrics": fit["metrics"], "roc": roc, "residuals": residuals,
                "learning_curve": curve}
        lines = [f"模型评估（{fit['model']}）: "
                 f"{'R²' if task == 'regression' else '准确率'}="
                 f"{_fmt(fit['metrics']['test'].get('r2' if task == 'regression' else 'accuracy'))}"]
        if residuals:
            lines.append(f"  残差: 均值 {_fmt(residuals['mean'])}，"
                         f"标准差 {_fmt(residuals['std'])}"
                         + (f"；{residuals['note']}" if residuals["note"] else ""))
        if roc:
            lines.append(f"  ROC AUC={_fmt(roc['auc'])}")
        if curve:
            lines.append("  学习曲线: 训练得分 "
                         + "→ ".join(_fmt(v) for v in curve["train_mean"]))
        return ToolResult("ml_evaluate", data=data, text="\n".join(lines))

    # ---------------- 解释 ----------------
    @reg.tool("ml_explain", "机器学习模型解释",
              "输出特征重要性（SHAP 优先，自动降级），可指定行号做单样本解释",
              {"sheet": "表名(可选)", "target": "目标列(必填)", "features": "特征列(可选)",
               "model": "模型名(默认forest)", "row_index": "单样本行号(0 起，可选)",
               "max_rows": "SHAP 采样上限(默认300)"},
              category="机器学习", returns="method/importances/contributions")
    def _explain(context: AgentContext, sheet: str = None, target: str = None,
                 features=None, model: str = "forest", row_index: int = None,
                 max_rows: int = 300):
        from analysis.ml import explain as explain_mod
        from analysis.ml import train
        name, frame = _df(context, sheet)
        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        fit = train.fit_pipeline(frame, tgt, cols, model=model)
        out = explain_mod.explain_model(fit["pipeline"], fit["X_train"],
                                        y=fit["y_train"], max_rows=int(max_rows))
        data: dict[str, Any] = {"sheet": name, "model": fit["model"],
                                "task": fit["task"], "method": out["method"],
                                "importances": out["importances"][:10],
                                "note": out["note"]}
        lines = [f"模型解释（{fit['model']}，方法 {out['method']}）: "
                 f"{out['note']}",
                 "  重要性 Top: " + "，".join(
                     f"{i['feature']}({_fmt(i['importance'])})"
                     for i in out["importances"][:5])]
        if row_index is not None:
            if not 0 <= int(row_index) < len(frame):
                raise ValueError(f"行号超出范围: {row_index}（0~{len(frame) - 1}）")
            sample = explain_mod.explain_sample(
                fit["pipeline"], frame[cols].iloc[int(row_index)], max_features=6)
            data["contributions"] = sample["contributions"]
            data["sample_method"] = sample["method"]
            lines.append(f"  第 {row_index} 行贡献: " + "，".join(
                f"{c['feature']}={_fmt(c['value'])}" for c in sample["contributions"]))
        return ToolResult("ml_explain", data=data, text="\n".join(lines))

    # ---------------- 预测 ----------------
    @reg.tool("ml_predict", "机器学习模型预测",
              "用已保存的 .qamodel 或即时训练的模型做预测；返回留出集预览，可保存模型",
              {"sheet": "表名(可选)", "target": "目标列(训练时必填；加载模型时可空)",
               "features": "特征列(可选)", "model": "模型名", "model_path": ".qamodel 路径(可选)",
               "rows": "预览行数(默认10)", "save_path": "训练后保存模型路径(可选)"},
              category="机器学习", returns="predictions/model_path")
    def _predict(context: AgentContext, sheet: str = None, target: str = None,
                 features=None, model: str = "forest", model_path: str = None,
                 rows: int = 10, save_path: str = None):
        from analysis.ml import persist, train
        name, frame = _df(context, sheet)
        preview_rows = max(1, int(rows))
        if model_path:
            bundle = persist.load_model(model_path)
            predictions = persist.predict_frame(bundle, frame)
            data = {"sheet": name, "source": "file", "model_path": str(model_path),
                    "task": bundle.get("task"), "target": bundle.get("target"),
                    "predictions": predictions.head(preview_rows).to_dict(orient="records")}
            text = (f"加载模型预测（{model_path}）: 共 {len(predictions)} 行，"
                    f"预览 {min(preview_rows, len(predictions))} 行"
                    + (f"；目标列 {bundle['target']}" if bundle.get("target") else ""))
            return ToolResult("ml_predict", data=data, text=text)

        tgt = _target_column(frame, target)
        cols = _feature_columns(context, name, frame, tgt, features)
        fit = train.fit_pipeline(frame, tgt, cols, model=model)
        bundle = {"format": persist.FORMAT_NAME, "task": fit["task"],
                  "target": tgt, "features": fit["features"],
                  "pipeline": fit["pipeline"]}
        holdout = frame.loc[fit["X_test"].index]
        predictions = persist.predict_frame(bundle, holdout)
        saved = None
        if save_path:
            saved = persist.save_model(
                save_path, fit["pipeline"], task=fit["task"], target=tgt,
                features=fit["features"], model=fit["model"],
                params=fit["params"], metrics=fit["metrics"])
        lines = [f"模型预测（{fit['model']}）: 留出集 {len(predictions)} 行，"
                 f"完整度 {_fmt(fit['metrics']['test'].get('r2' if fit['task'] == 'regression' else 'accuracy'))}"]
        preview = predictions.head(preview_rows)
        lines.extend(f"  · {row}" for row in
                     preview.to_dict(orient="records"))
        if saved:
            lines.append(f"  模型已保存: {saved}")
        return ToolResult("ml_predict",
                          data={"sheet": name, "source": "trained",
                                "task": fit["task"], "model": fit["model"],
                                "model_path": saved,
                                "predictions": preview.to_dict(orient="records")},
                          text="\n".join(lines))
