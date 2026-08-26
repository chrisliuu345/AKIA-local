"""
Box-Behnken 设计 — 响应曲面实验设计
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from . import response_surface


def generate_bbd(factors: List[str], center_points: int = 3) -> pd.DataFrame:
    k = len(factors)
    if k < 3:
        raise ValueError("Box-Behnken 设计至少需要 3 个因子")

    base_points = _get_bbd_base(k)
    center = np.zeros((center_points, k))
    design_matrix = np.vstack([base_points, center])

    result = {}
    for i, factor_name in enumerate(factors):
        result[factor_name] = design_matrix[:, i]

    result["Block"] = ["Design"] * len(base_points) + ["Center"] * center_points
    result["RunOrder"] = range(1, len(design_matrix) + 1)
    return pd.DataFrame(result)


def _get_bbd_base(k: int) -> np.ndarray:
    """向量化构造 BBD 基础设计点"""
    pairs = [(i, j) for i in range(k - 1) for j in range(i + 1, k)]
    n_pairs = len(pairs)
    signs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    n_points = n_pairs * len(signs)
    points = np.zeros((n_points, k))
    idx = 0
    for s1, s2 in signs:
        for pi, (i, j) in enumerate(pairs):
            points[idx, i] = s1
            points[idx, j] = s2
            idx += 1
    return points


def analyze_box_behnken(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
) -> Dict[str, Any]:
    result = response_surface.analyze_response_surface(df, response_col, factor_cols)
    result["chart_type"] = "Box-Behnken Design"
    result["design_type"] = "Box-Behnken"
    return result
