"""模型持久化 — .qamodel（joblib + 元数据）。

安全边界: 只接受本工具写出的格式标记（format="akia-model"）；
模型文件本质是 pickle，仍应只加载自己生成的文件。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config.settings import APP_VERSION

MODEL_EXT = ".qamodel"
FORMAT_NAME = "akia-model"
#: 旧格式标记 — 只读兼容，避免既有 .qamodel 模型失效
LEGACY_FORMAT_NAMES = ("qa-tool-model",)
_ACCEPTED_FORMATS = (FORMAT_NAME, *LEGACY_FORMAT_NAMES)
FORMAT_VERSION = 1


class ModelFileError(ValueError):
    """模型文件缺失 / 格式不符（UI 直接展示 message）。"""


def save_model(path, pipeline, *, task: str, target: str, features,
               model: str = "", params: dict | None = None,
               metrics: dict | None = None) -> str:
    """保存 Pipeline + 元数据，返回实际写入路径。"""
    target_path = Path(path)
    if target_path.suffix != MODEL_EXT:
        target_path = target_path.with_suffix(MODEL_EXT)
    payload = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "app_version": APP_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "task": task,
        "target": target,
        "features": list(features or []),
        "params": dict(params or {}),
        "metrics": metrics or {},
        "pipeline": pipeline,
    }
    joblib.dump(payload, target_path)
    return str(target_path)


def load_model(path) -> dict[str, Any]:
    """读取 .qamodel；文件缺失或格式不符抛 ModelFileError。"""
    source = Path(path)
    if not source.exists():
        raise ModelFileError(f"模型文件不存在: {source}")
    try:
        payload = joblib.load(source)
    except ModelFileError:
        raise
    except Exception as exc:  # 统一转换为可读错误（下面直接 re-raise，BLE001 不再适用）
        raise ModelFileError(f"模型文件无法读取: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("format") not in _ACCEPTED_FORMATS:
        raise ModelFileError("不是本工具生成的模型文件（缺少格式标记）")
    for key in ("pipeline", "task", "features"):
        if key not in payload:
            raise ModelFileError(f"模型文件缺少字段: {key}")
    return payload


def model_info(path) -> dict[str, Any]:
    """读取元数据（不含 Pipeline 使用）。"""
    payload = load_model(path)
    return {k: v for k, v in payload.items() if k != "pipeline"}


def predict_frame(bundle: dict[str, Any], df: pd.DataFrame,
                  proba: bool = True) -> pd.DataFrame:
    """用模型对数据表预测，返回含「预测值」（分类含「预测概率」）的表。"""
    if bundle.get("format") not in _ACCEPTED_FORMATS:
        raise ModelFileError("模型对象无效（请先用 load_model 读取）")
    missing = [c for c in bundle["features"] if c not in df.columns]
    if missing:
        raise ModelFileError(f"数据缺少模型所需特征列: {', '.join(map(str, missing))}")
    X = df[list(bundle["features"])]
    pipeline = bundle["pipeline"]
    out = pd.DataFrame(index=df.index)
    out["预测值"] = pipeline.predict(X)
    if proba and bundle.get("task") != "regression":
        try:
            scores = pipeline.predict_proba(X)
            if scores.ndim == 2 and scores.shape[1] == 2:
                out["预测概率"] = scores[:, 1]
        except Exception:  # noqa: BLE001 - 部分模型无 predict_proba
            pass
    return out
