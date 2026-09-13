"""模型评估 — 指标 / 混淆矩阵 / ROC / 交叉验证 / 学习曲线 / 残差诊断。

回归: R² · 调整 R² · RMSE · MAE · MAPE
分类: Accuracy · Precision/Recall/F1（weighted/macro）· AUC（二分类或 OVR）
验证: K 折交叉验证（回归 KFold / 分类分层）· 学习曲线 · 残差诊断
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    learning_curve,
)

from analysis.ml.common import TASK_CLASSIFICATION, TASK_REGRESSION, MLDataError

_CV_SCORING = {
    TASK_REGRESSION: {"r2": "r2", "rmse": "neg_root_mean_squared_error"},
    TASK_CLASSIFICATION: {"accuracy": "accuracy", "f1_weighted": "f1_weighted"},
}


def regression_metrics(y_true, y_pred, n_features: Optional[int] = None) -> Dict[str, Any]:
    """回归指标（与 sklearn 定义一致）。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    n = int(len(y_true))
    r2 = float(r2_score(y_true, y_pred)) if n >= 2 else float("nan")
    adj = None
    if n_features is not None and n - n_features - 1 > 0:
        adj = float(1 - (1 - r2) * (n - 1) / (n - n_features - 1))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred))) if n else float("nan")
    mae = float(mean_absolute_error(y_true, y_pred)) if n else float("nan")
    mask = y_true != 0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100) \
        if mask.any() else None
    return {
        "n": n,
        "r2": r2,
        "adj_r2": adj,
        "rmse": rmse,
        "mae": mae,
        "mape_pct": mape,
    }


def classification_metrics(y_true, y_pred, y_score=None) -> Dict[str, Any]:
    """分类指标 — 混淆矩阵 + weighted/macro 指标 + AUC（可选）。"""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    labels = sorted({str(v) for v in y_true} | {str(v) for v in y_pred})
    report = classification_report(y_true, y_pred, zero_division=0,
                                   output_dict=True)
    out: Dict[str, Any] = {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_weighted": float(report.get("weighted avg", {}).get("f1-score", 0.0)),
        "precision_weighted": float(report.get("weighted avg", {}).get("precision", 0.0)),
        "recall_weighted": float(report.get("weighted avg", {}).get("recall", 0.0)),
        "f1_macro": float(report.get("macro avg", {}).get("f1-score", 0.0)),
        "labels": labels,
        "confusion_matrix": confusion_matrix(y_true, y_pred,
                                             labels=labels).tolist(),
        "per_class": {
            str(k): {
                "precision": float(v["precision"]),
                "recall": float(v["recall"]),
                "f1": float(v["f1-score"]),
                "support": int(v["support"]),
            }
            for k, v in report.items()
            if k not in ("accuracy", "macro avg", "weighted avg")
            and isinstance(v, dict)
        },
        "auc": None,
        "auc_kind": None,
    }
    if y_score is not None:
        try:
            scores = np.asarray(y_score, dtype=float)
            if scores.ndim == 1 or scores.shape[1] == 2:
                out["auc"] = float(roc_auc_score(y_true, scores[:, 1]
                                                 if scores.ndim == 2 else scores))
                out["auc_kind"] = "binary"
            elif scores.shape[1] > 2:
                out["auc"] = float(roc_auc_score(
                    y_true, scores, multi_class="ovr", average="weighted"))
                out["auc_kind"] = "ovr_weighted"
        except ValueError:
            out["auc"] = None
    return out


def compute_metrics(task: str, y_true, y_pred, y_score=None,
                    n_features: Optional[int] = None) -> Dict[str, Any]:
    """按任务类型分发指标计算。"""
    if task == TASK_REGRESSION:
        return regression_metrics(y_true, y_pred, n_features=n_features)
    if task == TASK_CLASSIFICATION:
        return classification_metrics(y_true, y_pred, y_score=y_score)
    raise MLDataError(f"未知任务类型: {task}")


def _cv_splitter(task: str, cv: int, random_state: int,
                 y: Optional[pd.Series] = None):
    if task == TASK_CLASSIFICATION:
        folds = min(int(cv), int(pd.Series(y).value_counts().min()))
        folds = max(2, folds)
        return StratifiedKFold(n_splits=folds, shuffle=True,
                               random_state=int(random_state))
    folds = max(2, min(int(cv), len(pd.Series(y)) - 1)) if y is not None else max(2, int(cv))
    return KFold(n_splits=folds, shuffle=True, random_state=int(random_state))


def cross_validation(pipeline, X, y, task: str, cv: int = 5,
                     random_state: int = 42) -> Dict[str, Any]:
    """K 折交叉验证 — 每折在训练部分拟合 Pipeline（无泄漏）。"""
    splitter = _cv_splitter(task, cv, random_state, y)
    scoring = _CV_SCORING[task]
    scores: Dict[str, List[float]] = {}
    for key, name in scoring.items():
        raw = cross_val_score(clone(pipeline), X, y, cv=splitter, scoring=name)
        scores[key] = [float(-v if name.startswith("neg_") else v) for v in raw]

    summary: Dict[str, Any] = {"folds": len(next(iter(scores.values())))}
    for key, values in scores.items():
        summary[f"{key}_mean"] = float(np.mean(values))
        summary[f"{key}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    return {"scores": scores, "summary": summary}


def learning_curve_data(pipeline, X, y, task: str, cv: int = 5,
                        train_sizes: int = 5,
                        random_state: int = 42) -> Dict[str, Any]:
    """学习曲线 — 训练集/验证集得分随样本量变化（用于过拟合诊断）。"""
    splitter = _cv_splitter(task, cv, random_state, y)
    scoring = "r2" if task == TASK_REGRESSION else "accuracy"
    sizes, train_scores, valid_scores = learning_curve(
        clone(pipeline), X, y, cv=splitter, scoring=scoring,
        train_sizes=np.linspace(0.2, 1.0, int(train_sizes)), shuffle=True,
        random_state=int(random_state))
    return {
        "scoring": scoring,
        "train_sizes": [int(v) for v in sizes],
        "train_mean": [float(v) for v in train_scores.mean(axis=1)],
        "train_std": [float(v) for v in train_scores.std(axis=1)],
        "valid_mean": [float(v) for v in valid_scores.mean(axis=1)],
        "valid_std": [float(v) for v in valid_scores.std(axis=1)],
    }


def roc_curve_data(y_true, y_score) -> Optional[Dict[str, Any]]:
    """二分类 ROC 曲线数据；多分类返回 None（由混淆矩阵/指标承担）。"""
    y_true = np.asarray(y_true)
    classes = sorted({str(v) for v in y_true})
    if len(classes) != 2:
        return None
    scores = np.asarray(y_score, dtype=float)
    if scores.ndim == 2:
        scores = scores[:, 1]
    pos_label = classes[1]
    binary_true = (np.asarray([str(v) for v in y_true]) == pos_label).astype(int)
    fpr, tpr, thresholds = roc_curve(binary_true, scores)
    return {
        "fpr": [float(v) for v in fpr],
        "tpr": [float(v) for v in tpr],
        "thresholds": [float(v) for v in thresholds],
        "auc": float(roc_auc_score(binary_true, scores)),
        "positive_label": pos_label,
    }


def residual_diagnostics(y_true, y_pred) -> Dict[str, Any]:
    """残差诊断 — 分布/正态性/异方差提示。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    residuals = y_true - y_pred
    std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    out: Dict[str, Any] = {
        "mean": float(np.mean(residuals)),
        "std": std,
        "max_abs": float(np.max(np.abs(residuals))) if len(residuals) else float("nan"),
        "outliers_3sigma": int(np.sum(np.abs(residuals) > 3 * std)) if std > 0 else 0,
        "shapiro_p": None,
        "corr_with_pred": None,
        "note": "",
    }
    if 3 <= len(residuals) <= 5000 and out["std"] > 0:
        from scipy import stats
        out["shapiro_p"] = float(stats.shapiro(residuals).pvalue)
    if len(residuals) >= 3 and out["std"] > 0 and np.std(y_pred) > 0:
        out["corr_with_pred"] = float(np.corrcoef(residuals, y_pred)[0, 1])
    if out["shapiro_p"] is not None and out["shapiro_p"] < 0.05:
        out["note"] = "残差偏离正态（Shapiro p<0.05），关注异常点与非线性"
    if out["corr_with_pred"] is not None and abs(out["corr_with_pred"]) > 0.3:
        out["note"] = (out["note"] + "；" if out["note"] else "") + \
            "残差与预测值相关（可能存在异方差/欠拟合）"
    return out
