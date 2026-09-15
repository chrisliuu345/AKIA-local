"""模型解释 — SHAP（树模型）+ 原生重要性 / 置换重要性降级。

SHAP 行数默认上限 300（沿用 analysis/ai/root_cause.py 策略），
超限自动抽样；SHAP 不可用或模型不支持时逐级降级，保证界面不报错。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from analysis.ml.common import base_result

DEFAULT_MAX_ROWS = 300
DEFAULT_TOP_FEATURES = 10

_TREE_MODELS = ("RandomForest", "ExtraTrees", "DecisionTree", "GradientBoosting",
                "HistGradientBoosting", "XGB")


def shap_available() -> bool:
    try:
        import shap  # noqa: F401
        return True
    except Exception:  # noqa: BLE001 - 可选依赖
        return False


def _is_tree_model(model) -> bool:
    name = type(model).__name__
    return any(key in name for key in _TREE_MODELS)


def explain_model(
    pipeline,
    X: pd.DataFrame,
    y: pd.Series | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
    use_shap: bool = True,
    random_state: int = 42,
) -> dict[str, Any]:
    """全局解释 — 返回按重要性排序的特征列表（SHAP 优先，逐级降级）。"""
    if X is None or len(X) == 0:
        raise ValueError("解释需要非空特征数据")

    model = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["prep"]
    names = [str(n) for n in preprocessor.get_feature_names_out()]
    used = X.sample(n=min(int(max_rows), len(X)), random_state=int(random_state))

    if use_shap and shap_available() and _is_tree_model(model):
        try:
            import shap
            matrix = preprocessor.transform(used)
            explainer = shap.TreeExplainer(model)
            values = explainer.shap_values(matrix)
            arr = np.asarray(getattr(values, "values", values), dtype=float)
            if arr.ndim == 3:                      # (n, features, classes)
                arr = np.abs(arr).mean(axis=2)
            importance = np.abs(arr).mean(axis=0)
            expected = getattr(explainer, "expected_value", None)
            base_value = _flatten_base_value(expected)
            return base_result(
                "explain",
                method="shap",
                n_rows_used=int(len(used)),
                importances=_pairs(names, importance),
                base_value=base_value,
                note=f"SHAP 树解释（采样 {len(used)}/{len(X)} 行）",
            )
        except Exception as exc:  # noqa: BLE001 - 降级，不阻塞主流程
            fallback_note = f"SHAP 失败已降级: {type(exc).__name__}"
    else:
        fallback_note = "SHAP 不可用或模型不支持，已降级"

    native = getattr(model, "feature_importances_", None)
    if native is None:
        coef = getattr(model, "coef_", None)
        native = np.abs(np.asarray(coef, dtype=float)).ravel() if coef is not None else None
    if native is not None and len(native) == len(names):
        return base_result(
            "explain", method="native", n_rows_used=int(len(used)),
            importances=_pairs(names, np.asarray(native, dtype=float)),
            base_value=None, note=fallback_note + "（原生重要性）")

    if y is not None:
        try:
            result = permutation_importance(
                pipeline, X, y, n_repeats=3, random_state=int(random_state),
                n_jobs=1)
            return base_result(
                "explain", method="permutation", n_rows_used=int(len(X)),
                importances=_pairs(names, result.importances_mean),
                base_value=None, note=fallback_note + "（置换重要性）")
        except Exception as exc:  # noqa: BLE001
            fallback_note += f"；置换重要性失败: {type(exc).__name__}"

    return base_result("explain", method="none", n_rows_used=int(len(used)),
                       importances=[], base_value=None,
                       note=fallback_note + "（无可用解释方法）")


def explain_sample(
    pipeline,
    row: pd.Series,
    max_features: int = DEFAULT_TOP_FEATURES,
    use_shap: bool = True,
) -> dict[str, Any]:
    """单样本解释 — 返回贡献最大的前 N 个特征（SHAP）或全局重要性提示。"""
    frame = row.to_frame().T if isinstance(row, pd.Series) else row
    model = pipeline.named_steps["model"]
    preprocessor = pipeline.named_steps["prep"]
    names = [str(n) for n in preprocessor.get_feature_names_out()]
    matrix = preprocessor.transform(frame)

    if use_shap and shap_available() and _is_tree_model(model):
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            values = explainer.shap_values(matrix)
            arr = np.asarray(getattr(values, "values", values), dtype=float)
            if arr.ndim == 3:                      # (n, features, classes)
                arr = arr.mean(axis=2)
            contributions = arr[0]
            pairs = sorted(zip(names, contributions, strict=False),
                           key=lambda kv: abs(kv[1]), reverse=True)
            return base_result(
                "explain_sample", method="shap",
                contributions=[{"feature": k, "value": float(v)}
                               for k, v in pairs[:int(max_features)]],
                note="正贡献推向高预测值，负贡献相反")
        except Exception as exc:  # noqa: BLE001
            note = f"SHAP 失败已降级: {type(exc).__name__}"
    else:
        note = "SHAP 不可用或模型不支持，已降级为全局重要性"

    globals_out = explain_model(pipeline, frame, use_shap=False)
    return base_result(
        "explain_sample", method=globals_out["method"],
        contributions=[{"feature": item["feature"],
                        "value": float(item["importance"])}
                       for item in globals_out["importances"][:int(max_features)]],
        note=note)


def _pairs(names: list[str], values: np.ndarray) -> list[dict[str, Any]]:
    pairs = sorted(zip(names, (float(v) for v in values), strict=False),
                   key=lambda kv: abs(kv[1]), reverse=True)
    return [{"feature": k, "importance": v} for k, v in pairs]


def _flatten_base_value(expected) -> float | None:
    if expected is None:
        return None
    try:
        arr = np.asarray(expected, dtype=float).ravel()
        return float(np.mean(arr))
    except Exception:  # noqa: BLE001
        return None
