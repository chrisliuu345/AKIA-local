"""模型持久化 — .qamodel（HMAC 信封 + joblib 载荷）。

模型文件本质是 pickle。信封是普通字节，HMAC 在 ``joblib.load`` 之前完成；
校验失败或缺少签名时不得反序列化。签名密钥只用于识别本程序写出的文件，
不是用户持有的私钥。未签名的旧 pickle 不再加载。
"""

from __future__ import annotations

import hashlib
import hmac
import io
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config.settings import APP_VERSION

MODEL_EXT = ".qamodel"
FORMAT_NAME = "akia-model"
#: 载荷内仍接受旧格式标记，但外层必须是本程序签名的信封
LEGACY_FORMAT_NAMES = ("qa-tool-model",)
_ACCEPTED_FORMATS = (FORMAT_NAME, *LEGACY_FORMAT_NAMES)
FORMAT_VERSION = 1
_MAGIC = b"AKIA-MODEL-1"
# 应用格式密钥：让未签名的 pickle 在反序列化前被拒绝。更换会使已保存模型失效。
_HMAC_KEY = b"akia-qamodel-hmac-v1"


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
    buffer = io.BytesIO()
    joblib.dump(payload, buffer)
    body = buffer.getvalue()
    signature = hmac.new(_HMAC_KEY, body, hashlib.sha256).hexdigest().encode("ascii")
    target_path.write_bytes(_MAGIC + b"\n" + signature + b"\n" + body)
    return str(target_path)


def _signed_body(raw: bytes) -> bytes:
    """拆开信封并校验 HMAC。失败时不返回载荷，调用方不得反序列化。"""
    magic, sep, rest = raw.partition(b"\n")
    if magic != _MAGIC or not sep:
        raise ModelFileError("模型文件未通过 HMAC 校验，已拒绝加载")
    signature, sep, body = rest.partition(b"\n")
    expected = hmac.new(_HMAC_KEY, body, hashlib.sha256).hexdigest().encode("ascii")
    if not sep or len(signature) != len(expected) or not hmac.compare_digest(signature, expected):
        raise ModelFileError("模型文件 HMAC 校验失败，已拒绝加载")
    return body


def load_model(path) -> dict[str, Any]:
    """读取 .qamodel；文件缺失、签名不符或格式不符抛 ModelFileError。"""
    source = Path(path)
    if not source.exists():
        raise ModelFileError(f"模型文件不存在: {source}")
    try:
        body = _signed_body(source.read_bytes())
    except ModelFileError:
        raise
    except Exception as exc:
        raise ModelFileError(f"模型文件无法读取: {exc}") from exc
    try:
        payload = joblib.load(io.BytesIO(body))
    except ModelFileError:
        raise
    except Exception as exc:  # 签名已通过，这里只是载荷损坏
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
