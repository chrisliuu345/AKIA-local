"""
共享 Nelson 判异规则模块 — 全部 8 条规则独立实现

xbar_r / xbar_s / imr 统一调用 check_all_nelson_rules()
每条规则返回格式: {"point": int, "rule": int, "desc": str, "value": float}
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


def _rule_1(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    mask = np.abs(values - mean) > 3 * sigma
    idx = np.where(mask)[0]
    return [_mk(int(i + 1), 1, values[i]) for i in idx]


def _rule_2(values: np.ndarray, mean: float) -> list[dict]:
    violations = []
    n = len(values)
    if n < 9:
        return violations
    sign = np.sign(values - mean)
    for i in range(n - 8):
        if all(sign[i:i + 9] == 1) or all(sign[i:i + 9] == -1):
            violations.append(_mk(i + 9, 2, values[i + 8]))
    return violations


def _rule_3(values: np.ndarray) -> list[dict]:
    n = len(values)
    if n < 6:
        return []
    all_diffs = np.diff(values)
    violations = []
    for i in range(n - 5):
        segment = all_diffs[i:i + 5]
        if np.all(segment > 0) or np.all(segment < 0):
            violations.append(_mk(i + 6, 3, values[i + 5]))
    return violations


def _rule_4(values: np.ndarray, mean: float) -> list[dict]:
    """检测连续 14 点交替上下（锯齿模式）"""
    n = len(values)
    if n < 14:
        return []
    diffs = np.diff(values)
    sign_product = diffs[:-1] * diffs[1:]
    violations = []
    for i in range(len(sign_product) - 11):
        if np.all(sign_product[i:i + 12] < 0):
            violations.append(_mk(i + 14, 4, values[i + 13]))
    return violations


def _rule_5(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    """W18 fix: 超2σ的点中≥2点同侧（不要求全部3点同侧）"""
    n = len(values)
    if n < 3:
        return []
    violations = []
    for i in range(n - 2):
        w = values[i:i + 3]
        above_2s = np.sum(w - mean > 2 * sigma)
        below_2s = np.sum(mean - w > 2 * sigma)
        if above_2s >= 2 or below_2s >= 2:
            violations.append(_mk(i + 3, 5, values[i + 2]))
    return violations


def _rule_6(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    n = len(values)
    if n < 5:
        return []
    violations = []
    for i in range(n - 4):
        w = values[i:i + 5]
        beyond_count = np.sum(np.abs(w - mean) > sigma)
        if beyond_count >= 4:
            above_count = np.sum(w > mean)
            if above_count >= 4 or above_count <= 1:
                violations.append(_mk(i + 5, 6, values[i + 4]))
    return violations


def _rule_7(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    n = len(values)
    if n < 15:
        return []
    violations = []
    for i in range(n - 14):
        w = values[i:i + 15]
        within_count = np.sum(np.abs(w - mean) <= sigma)
        if within_count >= 15:
            violations.append(_mk(i + 15, 7, values[i + 14]))
    return violations


def _rule_8(values: np.ndarray, mean: float, sigma: float) -> list[dict]:
    """检测连续 8 点均在中心线 ±1σ 外（不限定同侧）"""
    n = len(values)
    if n < 8:
        return []
    violations = []
    i = 0
    while i <= n - 8:
        w = values[i:i + 8]
        all_outside = np.all(np.abs(w - mean) > sigma)
        if all_outside:
            violations.append(_mk(i + 8, 8, values[i + 7]))
            i += 8
        else:
            i += 1
    return violations
