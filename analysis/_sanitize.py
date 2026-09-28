"""分析层输入净化 —— 统一处理非数值、±inf 与缺失值（2026-09-28 质量审查）

背景: 真实工作簿里既有空单元格（NaN）、"NA" 等文本，也可能出现 inf/-inf
（公式除零、导入溢出）。旧实现普遍只做 ``dropna()``：

* ±inf **不会被 dropna 去掉**，会一路进入 scipy/matplotlib，抛出
  ``autodetected range ... is not finite``、``cannot convert float NaN to integer``
  等底层报错；
* 去缺失后索引有空洞时 statsmodels 无法构建预测索引。

因此分析层入口统一走本模块净化，保证"喂进来的是干净有限数值"。
"""

import numpy as np
import pandas as pd


def sanitize_series(values) -> pd.Series:
    """非数值文本 / ±inf → NaN → 去缺失 → float，并重置索引。"""
    series = pd.to_numeric(pd.Series(values), errors="coerce").astype(float)
    return series.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)


def sanitize_array(values) -> np.ndarray:
    """``sanitize_series`` 的数组版本（供直接吃 ndarray 的算法使用）。"""
    return sanitize_series(values).to_numpy()


def sanitize_pairs(first, second) -> tuple[np.ndarray, np.ndarray]:
    """两列配对净化：任一侧缺失/非有限则整行剔除（保持一一对应）。"""
    left = pd.to_numeric(pd.Series(first), errors="coerce").astype(float)
    right = pd.to_numeric(pd.Series(second), errors="coerce").astype(float)
    frame = pd.DataFrame({"left": left, "right": right})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    return frame["left"].to_numpy(), frame["right"].to_numpy()


def sanitize_groups(groups) -> list[np.ndarray]:
    """多组数据各自净化（组内去缺失，组间互不影响）。"""
    return [sanitize_array(group) for group in groups]


def sanitize_frame(frame: pd.DataFrame, columns) -> pd.DataFrame:
    """按指定列净化整表：任一指名列缺失/非有限则整行剔除。"""
    subset = frame.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    subset = subset.replace([np.inf, -np.inf], np.nan)
    return frame.loc[subset.dropna().index]
