"""SPC 计数型控制图输入净化 —— P / NP / C / U 四图共用

为什么需要（2026-09-28 质量审查发现）：
真实工作簿里计数列常含空单元格或 "NA" 等非数值文本。旧实现直接
``values.astype(float)`` 后转 int，遇到缺失/非有限值会抛出
``ValueError: cannot convert float NaN to integer`` 或
``OverflowError: cannot convert float infinity to integer`` —— 用户看到的是
底层 Python 报错，而不是"第几个子组数据有问题"。此处统一：
非数值 / ±inf → 缺失 → 剔除（配对列同步剔除，保持子组对齐）。
"""

import numpy as np
import pandas as pd


def clean_series(values) -> np.ndarray:
    """单列净化：非数值与 ±inf → NaN → 去缺失，返回 float 数组。"""
    arr = pd.to_numeric(pd.Series(values), errors="coerce").astype(float)
    return arr.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()


def clean_pairs(first, second) -> tuple[np.ndarray, np.ndarray]:
    """两列配对净化：任一侧缺失/非有限则整行剔除（保证子组一一对应）。"""
    left = pd.to_numeric(pd.Series(first), errors="coerce").astype(float)
    right = pd.to_numeric(pd.Series(second), errors="coerce").astype(float)
    frame = pd.DataFrame({"left": left, "right": right})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    return frame["left"].to_numpy(), frame["right"].to_numpy()


def require_min_subgroups(count: int, minimum: int = 2) -> None:
    """有效子组数不足时抛出统一中文错误（与既有图表文案保持一致）。"""
    if count < minimum:
        raise ValueError(f"数据量不足: 需要至少 {minimum} 个子组, 当前 {count}")


def require_non_negative(values: np.ndarray, label: str) -> None:
    """计数型指标不得为负（负值通常来自列错位或符号错误）。"""
    if values.size and np.any(values < 0):
        raise ValueError(f"{label}必须为非负数，检测到负值")
