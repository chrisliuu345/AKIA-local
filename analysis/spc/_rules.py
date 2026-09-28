"""
共享 Nelson 判异规则模块 — 全部 8 条规则独立实现

xbar_r / xbar_s / imr 统一调用 check_all_nelson_rules()
每条规则返回格式: {"point": int, "rule": int, "desc": str, "value": float}

实现说明（2026-09-28 性能优化）：全部规则改为滑窗计数向量化实现。
旧版逐窗口调用 ``np.all`` / ``np.sum``，100 万点 I-MR 会产生约 400 万次
NumPy 调用（占单次分析 99% 的时间）；向量化后逐点语义保持不变
（`tests/test_known_values_spc_control_charts.py` + `tests/test_robustness_numeric.py`
对同一输入断言完全一致）。
"""

import numpy as np
from config.settings import NELSON_RULES


def check_all_nelson_rules(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    """执行全部 8 条 Nelson 判异规则，返回违规点列表"""
    violations: list[dict] = []
    violations.extend(_rule_1(values, mean, sigma))
    violations.extend(_rule_2(values, mean))
    violations.extend(_rule_3(values))
    violations.extend(_rule_4(values, mean))
    violations.extend(_rule_5(values, mean, sigma))
    violations.extend(_rule_6(values, mean, sigma))
    violations.extend(_rule_7(values, mean, sigma))
    violations.extend(_rule_8(values, mean, sigma))
    return violations


def _mk(point: int, rule: int, value: float, desc: str = "") -> dict:
    """构造统一的违规记录"""
    return {
        "point": point,
        "rule": rule,
        "desc": desc or NELSON_RULES.get(rule, ""),
        "value": round(float(value), 6),
    }


def _window_counts(flags: np.ndarray, window: int) -> np.ndarray:
    """长度 ``window`` 滑窗内 True 的个数（返回长度 n-window+1 的数组）。

    用前缀和实现，避免逐窗口切片 + np.sum 的 O(n·window) Python 循环。
    """
    n = len(flags)
    if n < window:
        return np.empty(0, dtype=np.int64)
    prefix = np.concatenate(([0], np.cumsum(flags, dtype=np.int64)))
    return prefix[window:] - prefix[:-window]


def _collect(starts, rule: int, offset: int, values: np.ndarray) -> list[dict]:
    """把"窗口起始下标"批次转换为违规记录（offset = 窗口末点的 1-based 序号）。"""
    return [_mk(int(start + offset), rule, values[start + offset - 1]) for start in starts]


def _rule_1(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    mask = np.abs(values - mean) > 3 * sigma
    idx = np.where(mask)[0]
    return [_mk(int(i + 1), 1, values[i]) for i in idx]


def _rule_2(values: np.ndarray, mean: float) -> list[dict]:
    above = _window_counts(values > mean, 9)
    below = _window_counts(values < mean, 9)
    starts = np.where((above == 9) | (below == 9))[0]
    return _collect(starts, 2, 9, values)


def _rule_3(values: np.ndarray) -> list[dict]:
    diffs = np.diff(values)
    rising = _window_counts(diffs > 0, 5)
    falling = _window_counts(diffs < 0, 5)
    starts = np.where((rising == 5) | (falling == 5))[0]
    return _collect(starts, 3, 6, values)


def _rule_4(values: np.ndarray, mean: float) -> list[dict]:
    """检测连续 14 点交替上下（锯齿模式）"""
    diffs = np.diff(values)
    sign_product = diffs[:-1] * diffs[1:]
    alternating = _window_counts(sign_product < 0, 12)
    starts = np.where(alternating == 12)[0]
    return _collect(starts, 4, 14, values)


def _rule_5(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    """W18 fix: 超2σ的点中≥2点同侧（不要求全部3点同侧）"""
    above = _window_counts(values - mean > 2 * sigma, 3)
    below = _window_counts(mean - values > 2 * sigma, 3)
    starts = np.where((above >= 2) | (below >= 2))[0]
    return _collect(starts, 5, 3, values)


def _rule_6(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    beyond = _window_counts(np.abs(values - mean) > sigma, 5)
    above = _window_counts(values > mean, 5)
    starts = np.where((beyond >= 4) & ((above >= 4) | (above <= 1)))[0]
    return _collect(starts, 6, 5, values)


def _rule_7(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    within = _window_counts(np.abs(values - mean) <= sigma, 15)
    starts = np.where(within == 15)[0]
    return _collect(starts, 7, 15, values)


def _rule_8(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    """检测连续 8 点均在中心线 ±1σ 外（不限定同侧）"""
    outside = _window_counts(np.abs(values - mean) > sigma, 8)
    candidates = np.where(outside == 8)[0]
    # 与旧实现一致：报告一段后跳过整段（不重复报告重叠窗口）
    starts: list[int] = []
    next_allowed = 0
    for start in candidates:
        if start >= next_allowed:
            starts.append(int(start))
            next_allowed = int(start) + 8
    return _collect(starts, 8, 8, values)
