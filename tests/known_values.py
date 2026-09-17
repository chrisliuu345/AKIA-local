"""已知值测试框架 — v4.2.0 P0 契约（约定见 KNOWN_VALUES.md）。

用法::

    from tests.known_values import KnownValueCase, assert_close

    CASE = KnownValueCase.with_preset(
        "nist-norris-mean", "NIST StRD Norris",
        preset="closed_form", reference="Norris dataset, column 1 mean",
    )

    def test_mean_norris():
        assert_close(actual=..., expected=..., case=CASE)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

# (rel_tol, abs_tol) 预设 — 与 KNOWN_VALUES.md 容差政策保持一致
TOL_PRESETS: dict[str, tuple[float, float]] = {
    "closed_form": (1e-9, 1e-12),
    "rounded_6dp": (1e-9, 5.1e-7),
    "rounded_4dp": (1e-9, 5.1e-5),
    "iterative": (1e-6, 1e-9),
    "bootstrap": (1e-3, 1e-3),
}


@dataclass(frozen=True)
class KnownValueCase:
    """一条已知值用例的元数据：来源、出处与容差。"""

    case_id: str
    source: str
    reference: str = ""
    rel_tol: float = TOL_PRESETS["closed_form"][0]
    abs_tol: float = TOL_PRESETS["closed_form"][1]
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.case_id or "").strip():
            raise ValueError("case_id 不能为空")
        if not str(self.source or "").strip():
            raise ValueError("source 不能为空")
        if self.rel_tol < 0 or self.abs_tol < 0:
            raise ValueError("容差不能为负")
        if self.rel_tol == 0 and self.abs_tol == 0:
            raise ValueError("rel_tol 与 abs_tol 不能同时为 0")

    @property
    def label(self) -> str:
        suffix = f"，{self.reference}" if self.reference else ""
        return f"{self.case_id} [{self.source}{suffix}]"

    @classmethod
    def with_preset(cls, case_id: str, source: str, preset: str = "closed_form",
                    **kwargs: Any) -> KnownValueCase:
        if preset not in TOL_PRESETS:
            raise ValueError(f"未知容差预设: {preset}（可选 {sorted(TOL_PRESETS)}）")
        rel_tol, abs_tol = TOL_PRESETS[preset]
        return cls(case_id=case_id, source=source,
                   rel_tol=rel_tol, abs_tol=abs_tol, **kwargs)


def assert_close(actual: float, expected: float, case: KnownValueCase,
                 context: str = "") -> None:
    """标量已知值断言；失败信息自动携带用例来源与容差。"""
    if not math.isclose(float(actual), float(expected),
                        rel_tol=case.rel_tol, abs_tol=case.abs_tol):
        detail = (f"actual={actual!r} expected={expected!r} "
                  f"rel_tol={case.rel_tol} abs_tol={case.abs_tol}")
        if context:
            detail += f"（{context}）"
        raise AssertionError(f"已知值校验失败: {case.label} — {detail}")


def assert_allclose(actual: Any, expected: Any, case: KnownValueCase,
                    context: str = "") -> None:
    """向量/矩阵已知值断言（逐元素容差）。"""
    actual_arr = np.asarray(actual, dtype=float)
    expected_arr = np.asarray(expected, dtype=float)
    if not np.allclose(actual_arr, expected_arr, rtol=case.rel_tol,
                       atol=case.abs_tol, equal_nan=True):
        try:
            max_err = float(np.max(np.abs(actual_arr - expected_arr)))
        except ValueError:
            max_err = float("nan")
        detail = (f"max_abs_error={max_err:.6g} shape={actual_arr.shape} "
                  f"rel_tol={case.rel_tol} abs_tol={case.abs_tol}")
        if context:
            detail += f"（{context}）"
        raise AssertionError(f"已知值校验失败: {case.label} — {detail}")
