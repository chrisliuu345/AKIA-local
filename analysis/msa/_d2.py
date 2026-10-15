"""MSA 控制图常数 — d2 / d2* 查表与表外精确计算（2026-10-15 审查修复）。

背景（v4.2.0–v4.4.0 缺陷）：`gage_rr.py` / `emp.py` 的样本内重复次数 r 或
操作员/零件数超出常数表范围时，回退到近似公式 ``1.128 * r**0.3``。该公式
严重低估 d2（r=25 时 2.963 vs 真值 3.931，误差 -24.6%；r=50 时 -18.9%），
会静默低估重复性 EV。

本模块提供替代实现：
- 表内（r ≤ 25）：直接用 ``config.settings.CONTROL_CHART_CONSTANTS`` / ``MSA_D2_STAR``；
- 表外：用 scipy ``studentized_range.expect`` 精确计算正态样本极差期望
  ``d2(n) = E[R]/σ``（与表值一致性 < 0.3%，见 tests/test_msa_d2_fallback.py），
  d2* 以 d2 近似（长程研究变异，n>15 无标准表）；
- scipy 不可用（无图表依赖环境）时回退旧近似并显式返回，由调用方标注。

数值口径：表内值保持与 AIAG / Montgomery 一致；表外值为精确期望（迭代积分，
结果缓存），已知值测试锁定（n=26 → 3.9638，n=30 → 4.0858）。
"""

from __future__ import annotations

from functools import lru_cache

from config import settings as _cfg

_MAX_TABLE_N = 25  # CONTROL_CHART_CONSTANTS d2 表覆盖范围（n=2..25）
_MAX_D2_STAR_N = 15  # MSA_D2_STAR 表覆盖范围（AIAG，n=2..15）


def _d2_exact(n: int) -> float | None:
    """正态样本 n 的极差期望 E[R]/σ = d2（scipy 精确计算，含缓存）。

    scipy 不可用时返回 None（调用方回退近似）。
    """
    try:
        from scipy.stats import studentized_range
    except ImportError:  # 无图表依赖环境：调用方回退近似并标注
        return None

    import math

    value = studentized_range.expect(lambda x: x, args=(n, math.inf), lb=0.0, ub=400.0)
    value = float(value)
    return value if math.isfinite(value) and value > 0 else None


@lru_cache(maxsize=256)
def d2_value(n: int) -> tuple[float, bool]:
    """极差法 d2(n)（E[R]/σ）。

    返回 ``(值, 是否表外/近似)``：
    - n ≤ 25：常数表值（与 AIAG / Montgomery 一致，不标注）；
    - n > 25：scipy 精确值（标注 True）；scipy 缺失时旧近似 1.128·n**0.3（标注 True）。
    """
    n = int(n)
    table = _cfg.CONTROL_CHART_CONSTANTS.get(n, {}).get("d2")
    if table and n <= _MAX_TABLE_N:
        return float(table), False
    exact = _d2_exact(n)
    if exact is not None:
        return exact, True
    return 1.128 * (n**0.3), True


@lru_cache(maxsize=256)
def d2_star_value(n: int) -> tuple[float, bool]:
    """MSA 研究变异 d2*(n)。

    返回 ``(值, 是否表外/近似)``：
    - n ≤ 15：AIAG MSA_D2_STAR 表值（不标注）；
    - 15 < n ≤ 25：常数表 d2（显著大于 d2*，为偏保守的上界，标注 True）；
    - n > 25：scipy 精确 d2（上界近似，标注 True）。
    """
    n = int(n)
    table = _cfg.MSA_D2_STAR.get(n)
    if table is not None and n <= _MAX_D2_STAR_N:
        return float(table), False
    if n <= _MAX_TABLE_N:
        fallback = _cfg.CONTROL_CHART_CONSTANTS.get(n, {}).get("d2")
        if fallback:
            return float(fallback), True
    return d2_value(n)
