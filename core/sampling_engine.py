"""抽样检验引擎 — GB/T 2828.1 AQL + GB/T 6378 计量型 + C=0 抽样 + 随机/分层/系统抽样 + 序贯"""

import numpy as np, pandas as pd
from typing import Any


_LOT_CODE = [
    (2, 8, "A"),
    (9, 15, "B"),
    (16, 25, "C"),
    (26, 50, "D"),
    (51, 90, "E"),
    (91, 150, "F"),
    (151, 280, "G"),
    (281, 500, "H"),
    (501, 1200, "J"),
    (1201, 3200, "K"),
    (3201, 10000, "L"),
    (10001, 35000, "M"),
    (35001, 150000, "N"),
    (150001, 500000, "P"),
    (500001, 9999999, "Q"),
]

_AQL_VALS = [
    0.01,
    0.015,
    0.025,
    0.04,
    0.065,
    0.10,
    0.15,
    0.25,
    0.40,
    0.65,
    1.0,
    1.5,
    2.5,
    4.0,
    6.5,
    10,
    15,
    25,
    40,
    65,
    100,
]

_Z = (0, 1)

_NORMAL_TABLE = {
    "A": (2, [_Z] * 21),
    "B": (3, [_Z] * 16 + [(1, 2)] + [_Z] * 4),
    "C": (5, [_Z] * 12 + [(1, 2), (2, 3), (3, 4), (5, 6)] + [_Z] * 5),
    "D": (
        8,
        [_Z] * 11
        + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15)]
        + [_Z] * 3,
    ),
    "E": (
        13,
        [_Z] * 9
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
        ]
        + [_Z] * 2,
    ),
    "F": (
        20,
        [_Z] * 8
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
        ]
        + [_Z] * 2,
    ),
    "G": (
        32,
        [_Z] * 7
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
        ]
        + [_Z] * 2,
    ),
    "H": (
        50,
        [_Z] * 6
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
        ]
        + [_Z] * 2,
    ),
    "J": (
        80,
        [_Z] * 5
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
        ]
        + [_Z] * 3,
    ),
    "K": (
        125,
        [_Z] * 5
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
        ]
        + [_Z] * 3,
    ),
    "L": (
        200,
        [_Z] * 4
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
            (120, 121),
            (150, 151),
        ]
        + [_Z] * 2,
    ),
    "M": (
        315,
        [_Z] * 4
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
            (120, 121),
            (150, 151),
        ]
        + [_Z] * 2,
    ),
    "N": (
        500,
        [_Z] * 4
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
            (120, 121),
            (150, 151),
        ]
        + [_Z] * 2,
    ),
    "P": (
        800,
        [_Z] * 4
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
            (120, 121),
            (150, 151),
        ]
        + [_Z] * 2,
    ),
    "Q": (
        1250,
        [_Z] * 2
        + [
            (1, 2),
            (2, 3),
            (3, 4),
            (5, 6),
            (7, 8),
            (10, 11),
            (14, 15),
            (21, 22),
            (30, 31),
            (44, 45),
            (60, 61),
            (80, 81),
            (100, 101),
            (120, 121),
            (150, 151),
            (200, 201),
            (250, 251),
        ]
        + [_Z] * 2,
    ),
}

_NAQL = len(_AQL_VALS)
for _code, (_n, _ac_re) in _NORMAL_TABLE.items():
    if len(_ac_re) != _NAQL:
        raise ValueError(
            f"sampling_engine: 字码 {_code} 的 Ac-Re 列表长度 {len(_ac_re)} "
            f"与 AQL 列表长度 {_NAQL} 不匹配"
        )


_MEASUREMENT_AQLS = [0.10, 0.15, 0.25, 0.40, 0.65, 1.0, 1.5, 2.5, 4.0, 6.5]

_MEASUREMENT_TABLE = {
    "A": (3, [1.45, 1.31, 1.12, 0.958, 0.823, 0.709, 0.596, 0.473, 0.336, 0.188]),
    "B": (4, [1.61, 1.48, 1.33, 1.17, 1.01, 0.864, 0.716, 0.559, 0.394, 0.218]),
    "C": (5, [1.72, 1.61, 1.47, 1.33, 1.20, 1.07, 0.911, 0.733, 0.519, 0.284]),
    "D": (6, [1.81, 1.72, 1.58, 1.45, 1.32, 1.19, 1.04, 0.847, 0.599, 0.325]),
    "E": (7, [1.87, 1.79, 1.66, 1.53, 1.41, 1.29, 1.14, 0.938, 0.663, 0.357]),
    "F": (8, [1.92, 1.85, 1.72, 1.60, 1.48, 1.36, 1.21, 1.00, 0.713, 0.383]),
    "G": (10, [1.98, 1.91, 1.79, 1.67, 1.55, 1.43, 1.29, 1.06, 0.754, 0.404]),
    "H": (12, [2.02, 1.96, 1.84, 1.73, 1.62, 1.50, 1.35, 1.12, 0.792, 0.422]),
    "J": (15, [2.06, 2.00, 1.89, 1.78, 1.67, 1.55, 1.41, 1.17, 0.824, 0.437]),
    "K": (20, [2.09, 2.04, 1.93, 1.82, 1.72, 1.60, 1.46, 1.21, 0.850, 0.450]),
    "L": (25, [2.11, 2.06, 1.96, 1.85, 1.75, 1.63, 1.49, 1.24, 0.869, 0.459]),
    "M": (30, [2.13, 2.08, 1.98, 1.88, 1.77, 1.65, 1.51, 1.26, 0.884, 0.466]),
    "N": (35, [2.14, 2.09, 1.99, 1.89, 1.79, 1.67, 1.53, 1.27, 0.895, 0.471]),
    "P": (40, [2.15, 2.10, 2.00, 1.90, 1.80, 1.68, 1.54, 1.28, 0.904, 0.475]),
}


_C_ZERO_TABLE = {
    (2, 9): [(2, 0.65), (3, 0.27)],
    (10, 15): [(3, 0.44), (5, 0.21)],
    (16, 25): [(4, 0.35), (5, 0.21)],
    (26, 50): [(5, 0.29), (7, 0.17)],
    (51, 90): [(6, 0.25), (8, 0.15)],
    (91, 150): [(7, 0.22), (10, 0.14)],
    (151, 280): [(8, 0.19), (12, 0.12)],
    (281, 500): [(9, 0.17), (13, 0.11)],
    (501, 1200): [(10, 0.15), (15, 0.10)],
    (1201, 3200): [(12, 0.13), (18, 0.09)],
    (3201, 10000): [(14, 0.11), (20, 0.08)],
    (10001, 35000): [(16, 0.10), (25, 0.07)],
    (35001, 150000): [(20, 0.09), (30, 0.06)],
}


class SamplingEngine:
    @staticmethod
    def get_code(lot_size: int, level: str = "II") -> str:
        for lo, hi, code in _LOT_CODE:
            if lo <= lot_size <= hi:
                return code
        return "Q"

    @staticmethod
    def aql_lookup(lot_size: int, aql: float = 1.0, level: str = "II") -> dict:
        code = SamplingEngine.get_code(lot_size, level)
        entry = _NORMAL_TABLE.get(code, (2, [(0, 1)] * 21))
        n = entry[0]
        try:
            idx = _AQL_VALS.index(aql)
        except ValueError:
            idx = min(range(len(_AQL_VALS)), key=lambda i: abs(_AQL_VALS[i] - aql))
        ac_re = entry[1][idx] if idx < len(entry[1]) else (0, 1)
        return {
            "code": code,
            "sample_size": n,
            "accept": ac_re[0],
            "reject": ac_re[1],
            "aql_actual": _AQL_VALS[idx],
            "lot_size": lot_size,
            "level": level,
        }

    @staticmethod
    def random_sample(df: pd.DataFrame, n: int, seed: int | None = None) -> pd.DataFrame:
        if n >= len(df):
            return df.copy()
        return df.sample(n, random_state=seed).reset_index(drop=True)

    @staticmethod
    def stratified_sample(
        df: pd.DataFrame, column: str, n: int, seed: int | None = None
    ) -> pd.DataFrame:
        groups = df.groupby(column)
        frac = min(n / len(df), 1.0)
        result = []
        for _, g in groups:
            k = max(1, int(len(g) * frac))
            result.append(g.sample(min(k, len(g)), random_state=seed))
        return pd.concat(result).reset_index(drop=True)

    @staticmethod
    def systematic_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
        if n >= len(df):
            return df.copy()
        step = len(df) // n
        start = np.random.randint(0, step)
        idx = range(start, len(df), step)
        return df.iloc[list(idx)[:n]].reset_index(drop=True)

    @staticmethod
    def sequential_decision(
        results: list[int], ac: int, re: int
    ) -> tuple[str, int, int]:
        """序贯抽样判定: 返(decision, defects, inspected)"""
        d = 0
        for i, r in enumerate(results, 1):
            if r == 1:
                d += 1
            if d >= re:
                return "reject", d, i
            if d <= ac and i >= ac + 1:
                return "accept", d, i
        if d <= ac:
            return "accept", d, len(results)
        return "continue", d, len(results)

    @staticmethod
    def measurement_sampling(
        lot_size: int,
        aql: float = 1.0,
        usl: float | None = None,
        lsl: float | None = None,
        sigma: float | None = None,
        level: str = "II",
    ) -> dict[str, Any]:
        """计量型抽样检验 (GB/T 6378 / ANSI/ASQ Z1.9)

        基于均值和标准差的计量型抽样方案。

        Args:
            lot_size: 批量大小
            aql: 可接收质量水平 (默认1.0)
            usl: 上规格限
            lsl: 下规格限
            sigma: 过程标准差（如已知）。如未提供且有规格限，将自动估算为 (usl-lsl)/6
            level: 检验水平 (I, II, III)

        Returns:
            Dict包含抽样方案和判定规则
        """
        code = SamplingEngine.get_code(lot_size, level)

        if code not in _MEASUREMENT_TABLE:
            return {"error": f"无效的字码: {code}"}

        n, k_values = _MEASUREMENT_TABLE[code]

        aql_idx = min(
            range(len(_MEASUREMENT_AQLS)), key=lambda i: abs(_MEASUREMENT_AQLS[i] - aql)
        )
        k = k_values[aql_idx]
        aql_actual = _MEASUREMENT_AQLS[aql_idx]

        if sigma is None:
            if usl is not None and lsl is not None:
                sigma = (usl - lsl) / 6
            else:
                sigma = 1.0

        if usl is not None and lsl is not None:
            target = (usl + lsl) / 2
            spec_range = usl - lsl
        else:
            target = None
            spec_range = None

        if usl is not None and lsl is not None:
            accept_lower = lsl + k * sigma
            accept_upper = usl - k * sigma
        elif usl is not None:
            accept_lower = None
            accept_upper = usl - k * sigma
        elif lsl is not None:
            accept_lower = lsl + k * sigma
            accept_upper = None
        else:
            accept_lower = None
            accept_upper = None

        return {
            "method": "Measurement Sampling (GB/T 6378)",
            "lot_size": lot_size,
            "code": code,
            "sample_size": n,
            "aql": aql,
            "aql_actual": aql_actual,
            "k_factor": round(k, 3),
            "level": level,
            "usl": usl,
            "lsl": lsl,
            "target": target,
            "spec_range": spec_range,
            "sigma_used": round(float(sigma), 4),
            "sigma_source": "provided" if sigma is not None else "estimated",
            "accept_lower": round(accept_lower, 4)
            if accept_lower is not None
            else None,
            "accept_upper": round(accept_upper, 4)
            if accept_upper is not None
            else None,
        }

    @staticmethod
    def measurement_decision(
        sample_data: np.ndarray,
        k_factor: float,
        usl: float | None = None,
        lsl: float | None = None,
    ) -> dict[str, Any]:
        """计量型抽样判定

        根据样本数据和k因子判定批次是否接收。

        判定规则:
        - 接收: x̄ - k*s ≥ LSL 且 x̄ + k*s ≤ USL
        - 拒收: 否则

        Args:
            sample_data: 样本数据
            k_factor: k因子（从measurement_sampling获取）
            usl: 上规格限
            lsl: 下规格限

        Returns:
            Dict包含判定结果和统计量
        """
        clean = sample_data[np.isfinite(sample_data)]
        n = len(clean)

        if n < 2:
            return {"error": "样本量不足", "decision": "error"}

        x_bar = np.mean(clean)
        s = np.std(clean, ddof=1)

        if s == 0:
            return {
                "error": "样本标准差为0",
                "decision": "error",
                "x_bar": round(float(x_bar), 4),
                "s": 0.0,
            }

        lower_stat = x_bar - k_factor * s
        upper_stat = x_bar + k_factor * s

        decision = "accept"
        reasons = []

        if lsl is not None:
            if lower_stat < lsl:
                decision = "reject"
                reasons.append(f"x̄ - k*s = {lower_stat:.4f} < LSL = {lsl}")

        if usl is not None:
            if upper_stat > usl:
                decision = "reject"
                reasons.append(f"x̄ + k*s = {upper_stat:.4f} > USL = {usl}")

        return {
            "decision": decision,
            "reasons": reasons,
            "sample_size": n,
            "x_bar": round(float(x_bar), 4),
            "s": round(float(s), 4),
            "lower_stat": round(float(lower_stat), 4),
            "upper_stat": round(float(upper_stat), 4),
            "k_factor": k_factor,
            "usl": usl,
            "lsl": lsl,
        }

    @staticmethod
    def c_zero_sampling(
        lot_size: int,
        aql: float = 0.10,
        level: str = "normal",
    ) -> dict[str, Any]:
        """C=0 抽样方案 (零缺陷接收)

        C=0抽样方案要求零缺陷才能接收批次。
        适用于关键质量特性或高价值产品。

        Args:
            lot_size: 批量大小
            aql: 可接收质量水平 (默认0.10)
            level: 检验水平 (normal, tightened, reduced)

        Returns:
            Dict包含抽样方案
        """
        for (lo, hi), plans in _C_ZERO_TABLE.items():
            if lo <= lot_size <= hi:
                best_plan = min(plans, key=lambda p: abs(p[1] - aql))
                n, aql_actual = best_plan

                return {
                    "method": "C=0 Sampling Plan",
                    "lot_size": lot_size,
                    "sample_size": n,
                    "accept_number": 0,
                    "reject_number": 1,
                    "aql": aql,
                    "aql_actual": aql_actual,
                    "level": level,
                    "description": f"从{lot_size}件中抽取{n}件，0件缺陷则接收",
                }

        n = max(3, int(lot_size * 0.1))
        return {
            "method": "C=0 Sampling Plan",
            "lot_size": lot_size,
            "sample_size": n,
            "accept_number": 0,
            "reject_number": 1,
            "aql": aql,
            "aql_actual": None,
            "level": level,
            "description": f"从{lot_size}件中抽取{n}件，0件缺陷则接收",
            "note": "批量不在标准表中，使用保守估计",
        }

    @staticmethod
    def c_zero_decision(results: list[int]) -> dict[str, Any]:
        """C=0 抽样判定

        根据检验结果判定批次是否接收。
        C=0方案：有1件缺陷即拒收。

        Args:
            results: 检验结果列表 (0=合格, 1=缺陷)

        Returns:
            Dict包含判定结果
        """
        n = len(results)
        defects = sum(results)

        if defects == 0:
            decision = "accept"
            description = f"检验{n}件，0件缺陷，接收"
        else:
            decision = "reject"
            description = f"检验{n}件，{defects}件缺陷，拒收"

        return {
            "decision": decision,
            "description": description,
            "sample_size": n,
            "defects": defects,
            "defect_rate": round(defects / n * 100, 2) if n > 0 else 0.0,
        }
