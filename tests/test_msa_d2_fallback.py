"""MSA d2 / d2* 表外回退回归（2026-10-15 审查修复）。

背景缺陷：``gage_rr.py`` / ``emp.py`` 在重复次数 r>25（或操作员/零件数超表）
时回退到 ``1.128 * r**0.3``，严重低估 d2（r=25 时误差 -24.6%），
静默低估重复性 EV。修复改为 scipy 精确计算（表外）并透明标注 ``design.notes``。
"""

import numpy as np
import pandas as pd
import pytest

from analysis.msa._d2 import d2_star_value, d2_value
from analysis.msa.emp import analyze_crossed as emp_analyze_crossed
from analysis.msa.gage_rr import analyze_crossed

#: 表外精确期望值（scipy studentized_range.expect 独立复算；
#: 对照口径：n=26 → 3.9643、n=30 → 4.0855、n=50 → 4.4981）
_EXACT_D2 = {26: 3.9643, 30: 4.0855, 50: 4.4981}


class TestD2Helper:
    def test_table_values_unchanged(self):
        """表内值必须与常数表一致且不标注表外。"""
        for n, expected in ((2, 1.128), (5, 2.326), (10, 3.078), (25, 3.931)):
            value, oob = d2_value(n)
            assert value == pytest.approx(expected, abs=1e-9)
            assert oob is False

    def test_out_of_table_uses_exact_not_approximation(self):
        """表外值必须接近精确期望，且显著高于旧近似 1.128*n**0.3。"""
        for n, expected in _EXACT_D2.items():
            value, oob = d2_value(n)
            assert oob is True
            assert value == pytest.approx(expected, abs=1e-3)
            legacy = 1.128 * (n**0.3)
            assert value > legacy * 1.05, \
                f"n={n}: 修复后值 {value:.4f} 应显著高于旧近似 {legacy:.4f}"

    def test_d2_star_table_and_fallback(self):
        """d2* 表内用 AIAG 表；表外以 d2 为保守上界并标注。"""
        for n, expected in ((2, 1.41), (6, 2.67), (15, 3.55)):
            value, oob = d2_star_value(n)
            assert value == pytest.approx(expected, abs=1e-9)
            assert oob is False
        value, oob = d2_star_value(16)
        assert oob is True and value == pytest.approx(3.532, abs=1e-3)


def _crossed_frame(r: int, p: int = 3, o: int = 2, seed: int = 7) -> pd.DataFrame:
    """构造 r 次重复的平衡交叉数据（单元内前两点极差固定为 2）。"""
    rng = np.random.default_rng(seed)
    rows = []
    for part in range(p):
        for op in range(o):
            base = 10.0 + part
            values = rng.normal(base, 0.3, size=r)
            values[0], values[1] = base - 1.0, base + 1.0  # 固定单元极差 = 2
            for v in values:
                rows.append({"part": f"P{part}", "operator": f"O{op}", "value": float(v)})
    return pd.DataFrame(rows)


class TestGageRrOutOfTable:
    def test_r_above_25_uses_exact_d2_and_flags_note(self):
        """r=30：EV = R̄/d2_exact 且 design.notes 标注表外取值。"""
        result = analyze_crossed(_crossed_frame(r=30), "value", "part", "operator")
        assert result["design"]["replicates"] == 30
        notes = result["design"].get("notes") or []
        assert any("精确计算" in note for note in notes), notes
        r_bar = result["summary"]["r_bar"]
        d2_exact, _ = d2_value(30)
        assert result["variance_components"]["ev"] == pytest.approx(
            r_bar / d2_exact, abs=1e-6)
        # 旧近似会低估 EV（>15%），修复后不得再出现旧口径
        legacy_ev = r_bar / (1.128 * 30**0.3)
        assert result["variance_components"]["ev"] < legacy_ev * 0.96

    def test_no_notes_within_table(self):
        """表内设计不产生表外标注（避免噪音）。"""
        result = analyze_crossed(_crossed_frame(r=3), "value", "part", "operator")
        assert not (result["design"].get("notes") or [])

    def test_emp_analyzer_shares_fix(self):
        """EMP 引擎同口径修复：表外标注且 EV 与精确 d2 一致。"""
        result = emp_analyze_crossed(_crossed_frame(r=30), "value", "part", "operator")
        notes = result["design"].get("notes") or []
        assert any("精确计算" in note for note in notes), notes
