"""
共享 Nelson 判异规则模块 — 全部 8 条规则独立实现

xbar_r / xbar_s / imr 统一调用 check_all_nelson_rules()
每条规则返回格式: {"point": int, "rule": int, "desc": str, "value": float}
"""

from typing import List, Dict
import numpy as np
from config.settings import NELSON_RULES


def check_all_nelson_rules(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    """执行全部 8 条 Nelson 判异规则，返回违规点列表"""
    violations: List[Dict] = []
    violations.extend(_rule_1(values, mean, sigma))
    violations.extend(_rule_2(values, mean))
    violations.extend(_rule_3(values))
    violations.extend(_rule_4(values, mean))
    violations.extend(_rule_5(values, mean, sigma))
    violations.extend(_rule_6(values, mean, sigma))
    violations.extend(_rule_7(values, mean, sigma))
    violations.extend(_rule_8(values, mean, sigma))
    return violations


def _mk(point: int, rule: int, value: float, desc: str = "") -> Dict:
    """构造统一的违规记录"""
    return {
        "point": point,
        "rule": rule,
        "desc": desc or NELSON_RULES.get(rule, ""),
        "value": round(float(value), 6),
    }


# ── 规则 1: 一点超出 3σ 控制限 ──────────────────────
def _rule_1(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    violations = []
    for i in range(len(values)):
        if abs(values[i] - mean) > 3 * sigma:
            violations.append(_mk(i + 1, 1, values[i]))
    return violations


# ── 规则 2: 连续 9 点在中心线同一侧 ──────────────────
def _rule_2(values: np.ndarray, mean: float) -> List[Dict]:
    violations = []
    n = len(values)
    if n < 9:
        return violations
    sign = np.sign(values - mean)
    for i in range(n - 8):
        if all(sign[i:i + 9] == 1) or all(sign[i:i + 9] == -1):
            violations.append(_mk(i + 9, 2, values[i + 8]))
    return violations


# ── 规则 3: 连续 6 点递增或递减 ──────────────────────
def _rule_3(values: np.ndarray) -> List[Dict]:
    violations = []
    n = len(values)
    if n < 6:
        return violations
    for i in range(n - 5):
        window = values[i:i + 6]
        if all(np.diff(window) > 0) or all(np.diff(window) < 0):
            violations.append(_mk(i + 6, 3, values[i + 5]))
    return violations


# ── 规则 4: 连续 14 点交替上下 ───────────────────────
def _rule_4(values: np.ndarray, mean: float) -> List[Dict]:
    """检测连续 14 点交替上下（锯齿模式）"""
    violations = []
    n = len(values)
    if n < 14:
        return violations
    diffs = np.diff(values)
    for i in range(n - 13):
        window = diffs[i:i + 13]
        # 每相邻两个差值的符号相反 → 交替
        alternating = all(window[j] * window[j + 1] < 0 for j in range(12))
        if alternating:
            violations.append(_mk(i + 14, 4, values[i + 13]))
    return violations


# ── 规则 5: 连续 3 点中有 2 点超出 2σ（同侧）─────────
def _rule_5(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    violations = []
    n = len(values)
    if n < 3:
        return violations
    for i in range(n - 2):
        window = values[i:i + 3]
        beyond = sum(1 for v in window if abs(v - mean) > 2 * sigma)
        if beyond >= 2 and (all(v > mean for v in window) or all(v < mean for v in window)):
            violations.append(_mk(i + 3, 5, values[i + 2]))
    return violations


# ── 规则 6: 连续 5 点中有 4 点超出 1σ（同侧）─────────
def _rule_6(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    violations = []
    n = len(values)
    if n < 5:
        return violations
    for i in range(n - 4):
        window = values[i:i + 5]
        beyond = sum(1 for v in window if abs(v - mean) > sigma)
        if beyond >= 4:
            # 同侧判断：多数在同侧
            above = sum(1 for v in window if v > mean)
            if above >= 4 or above <= 1:
                violations.append(_mk(i + 5, 6, values[i + 4]))
    return violations


# ── 规则 7: 连续 15 点在中心线 ±1σ 内 ─────────────────
def _rule_7(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    violations = []
    n = len(values)
    if n < 15:
        return violations
    for i in range(n - 14):
        window = values[i:i + 15]
        within = sum(1 for v in window if abs(v - mean) <= sigma)
        if within >= 15:
            violations.append(_mk(i + 15, 7, values[i + 14]))
    return violations


# ── 规则 8: 连续 8 点均在中心线 ±1σ 外（两侧）─────────
def _rule_8(values: np.ndarray, mean: float, sigma: float) -> List[Dict]:
    """检测连续 8 点均在中心线 ±1σ 外（不限定同侧）"""
    violations = []
    n = len(values)
    if n < 8:
        return violations
    i = 0
    while i <= n - 8:
        all_outside = all(abs(values[j] - mean) > sigma for j in range(i, i + 8))
        if all_outside:
            violations.append(_mk(i + 8, 8, values[i + 7]))
            i += 8  # 跳过已检出的点，避免重叠报告
        else:
            i += 1
    return violations
