"""抽样检验引擎 — GB/T 2828.1 AQL（正常/加严/放宽 + 箭头解析 + 7 档检验水平 + 转移规则）
+ GB/T 6378 计量型 + C=0 抽样 + 随机/分层/系统抽样 + 序贯"""

import numpy as np, pandas as pd
from typing import Any

from core.sampling_plan import TRANSFER_STATES, LotRecord, TransferDecision


# ---------------------------------------------------------------- 抽样表（B0 重建，2026-10-12）
# 数据来源：GB/T 2828.1-2003（= ISO 2859-1:1999）主表坐标级提取值，经四重交叉验证：
#   ① 随包知识库《AQL 正常检验抽样表（节选）》55 格逐格一致；
#   ② 表 2-A 全部 152 个数字格的 n·AQL 均落在接收数对应的 R5 带心 ±6%（5–95% 区间 [0.94, 1.04]）；
#   ③ 表 2-B 满足"带心×1.6"设计关系（中位 1.56，偏差 ≤6%）；
#   ④ 表 2-C 与行业确认值一致（AQL2.5：字码 K→5/6、L→6/7）。
# 修正的旧表缺陷（v4.3.0 及以前）：A~H 行数字格整体错位、J/K 行完全相同、
# 箭头（↓/↑）语义未实现、检验水平参数被忽略、加严/放宽表缺失。
# 表示法：每行 21 列（AQL 0.01~100）；"_D"=↓（采用下方第一个抽样方案）、
# "_U"=↑（采用上方第一个抽样方案）；数字格为 (Ac, Re)，n 取方案所在行的样本量。
# 表 2-C（放宽）必须使用 _REDUCED_SAMPLE_SIZE，不能复用正常样本量。

_LEVEL_KEYS = ("S-1", "S-2", "S-3", "S-4", "I", "II", "III")

_AQL_VALS = [
    0.01, 0.015, 0.025, 0.04, 0.065, 0.10, 0.15, 0.25, 0.40, 0.65,
    1.0, 1.5, 2.5, 4.0, 6.5, 10, 15, 25, 40, 65, 100,
]

_LOT_RANGES = [
    (2, 8, ('A', 'A', 'A', 'A', 'A', 'A', 'B')),
    (9, 15, ('A', 'A', 'A', 'A', 'A', 'B', 'C')),
    (16, 25, ('A', 'A', 'B', 'B', 'B', 'C', 'D')),
    (26, 50, ('A', 'B', 'B', 'C', 'C', 'D', 'E')),
    (51, 90, ('B', 'B', 'C', 'C', 'C', 'E', 'F')),
    (91, 150, ('B', 'B', 'C', 'D', 'D', 'F', 'G')),
    (151, 280, ('B', 'C', 'D', 'E', 'E', 'G', 'H')),
    (281, 500, ('B', 'C', 'D', 'E', 'F', 'H', 'J')),
    (501, 1200, ('C', 'C', 'E', 'F', 'G', 'J', 'K')),
    (1201, 3200, ('C', 'D', 'E', 'G', 'H', 'K', 'L')),
    (3201, 10000, ('C', 'D', 'F', 'G', 'J', 'L', 'M')),
    (10001, 35000, ('C', 'D', 'F', 'H', 'K', 'M', 'N')),
    (35001, 150000, ('D', 'E', 'G', 'J', 'L', 'N', 'P')),
    (150001, 500000, ('D', 'E', 'G', 'J', 'M', 'P', 'Q')),
    (500001, None, ('D', 'E', 'H', 'K', 'N', 'Q', 'R')),
]

_CODE_ORDER = ("A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R")
_SAMPLE_SIZES = {"A": 2, "B": 3, "C": 5, "D": 8, "E": 13, "F": 20, "G": 32, "H": 50, "J": 80, "K": 125, "L": 200, "M": 315, "N": 500, "P": 800, "Q": 1250, "R": 2000}
_REDUCED_SAMPLE_SIZE = {"A": 2, "B": 2, "C": 2, "D": 3, "E": 5, "F": 8, "G": 13, "H": 20, "J": 32, "K": 50, "L": 80, "M": 125, "N": 200, "P": 315, "Q": 500, "R": 800}

_ARROW_DOWN = "\u2193"   # ↓ 采用下方第一个抽样方案
_ARROW_UP = "\u2191"     # ↑ 采用上方第一个抽样方案
_D = [_ARROW_DOWN]       # 行内批量拼接用：_D*N + [...]
_U = [_ARROW_UP]

_NORMAL_CELLS = {
    "A": _D*14 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6)],
    "B": _D*13 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8)],
    "C": _D*12 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11)],
    "D": _D*11 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15)],
    "E": _D*10 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)],
    "F": _D*9 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U,
    "G": _D*8 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*2,
    "H": _D*7 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*3,
    "J": _D*6 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*4,
    "K": _D*5 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*5,
    "L": _D*4 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*6,
    "M": _D*3 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*7,
    "N": _D*2 + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*8,
    "P": _D + [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*9,
    "Q": [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*10,
    "R": _U*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (7, 8), (10, 11), (14, 15), (21, 22)] + _U*11,
}

_TIGHTENED_CELLS = {
    "A": _D*15 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4)],
    "B": _D*14 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6)],
    "C": _D*13 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9)],
    "D": _D*12 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13)],
    "E": _D*11 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)],
    "F": _D*10 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U,
    "G": _D*9 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*2,
    "H": _D*8 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*3,
    "J": _D*7 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*4,
    "K": _D*6 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*5,
    "L": _D*5 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*6,
    "M": _D*4 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*7,
    "N": _D*3 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*8,
    "P": _D*2 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*9,
    "Q": _D + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*10,
    "R": [(0, 1)] + _U + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (8, 9), (12, 13), (18, 19)] + _U*11,
}

_REDUCED_CELLS = {
    "A": _D*14 + [(0, 1)] + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6)],
    "B": _D*13 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6)],
    "C": _D*12 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7)],
    "D": _D*11 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9)],
    "E": _D*10 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)],
    "F": _D*9 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U,
    "G": _D*8 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*2,
    "H": _D*7 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*3,
    "J": _D*6 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*4,
    "K": _D*5 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*5,
    "L": _D*4 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*6,
    "M": _D*3 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*7,
    "N": _D*2 + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*8,
    "P": _D + [(0, 1)] + _U + _D*2 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*9,
    "Q": [(0, 1)] + _U*2 + _D + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*10,
    "R": _U*3 + [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (10, 11)] + _U*11,
}

_INSPECTION_TABLES = {
    "normal": _NORMAL_CELLS,
    "tightened": _TIGHTENED_CELLS,
    "reduced": _REDUCED_CELLS,
}
_INSPECTION_NAMES = ("normal", "tightened", "reduced")

for _table_name, _table in _INSPECTION_TABLES.items():
    for _code, _row in _table.items():
        if len(_row) != len(_AQL_VALS):
            raise ValueError(
                f"sampling_engine: {_table_name} 字码 {_code} 列数 {len(_row)} "
                f"与 AQL 列数 {len(_AQL_VALS)} 不匹配")
        for _cell in _row:
            if _cell in (_ARROW_DOWN, _ARROW_UP):
                continue
            if (not isinstance(_cell, tuple) or len(_cell) != 2
                    or int(_cell[1]) != int(_cell[0]) + 1):
                raise ValueError(
                    f"sampling_engine: {_table_name} 字码 {_code} 非法格 {_cell!r}")

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
        """样本量字码（GB/T 2828.1 表 1）：按检验水平 S-1~III 取字码。

        批量 < 2 按 2 处理（表从 2 起）；未知检验水平给结构化中文错误。
        """
        key = str(level or "II").strip().upper()
        if key not in _LEVEL_KEYS:
            raise ValueError(
                f"未知检验水平: {level!r}（可选 {list(_LEVEL_KEYS)}）")
        lot = max(2, int(lot_size))
        column = _LEVEL_KEYS.index(key)
        for lo, hi, codes in _LOT_RANGES:
            if lot >= lo and (hi is None or lot <= hi):
                return codes[column]
        return "R"

    @staticmethod
    def _resolve_plan(table: dict, code: str, column: int,
                      sizes: dict[str, int]) -> tuple[str, int, int, int, bool]:
        """按箭头语义解析抽样方案：返回 (方案字码, n, Ac, Re, 是否经箭头)。"""
        row = _CODE_ORDER.index(code)
        steps = 0
        while 0 <= row < len(_CODE_ORDER) and steps <= len(_CODE_ORDER):
            steps += 1
            resolved_code = _CODE_ORDER[row]
            cell = table[resolved_code][column]
            if isinstance(cell, tuple):
                return (resolved_code, sizes[resolved_code],
                        int(cell[0]), int(cell[1]), resolved_code != code)
            row += 1 if cell == _ARROW_DOWN else -1
        raise ValueError(
            f"抽样表缺少可解析方案: 字码 {code} 第 {column + 1} 列（AQL 轴）")

    @staticmethod
    def aql_lookup(lot_size: int, aql: float = 1.0, level: str = "II",
                   inspection: str = "normal") -> dict:
        """AQL 查表（GB/T 2828.1 一次抽样）：正常/加严/放宽 + 箭头解析。

        - 箭头语义按标准：↓ 采用下方第一个抽样方案、↑ 采用上方第一个方案，
          样本量取方案所在行；``via_arrow`` 标记是否经箭头解析；
        - 放宽（reduced）使用缩减样本量（约为正常样本量的 2/5）；
        - ``plan_code`` 为解析后方案所在字码（无箭头时与 ``code`` 相同）。
        """
        mode = str(inspection or "normal").strip().lower()
        if mode not in _INSPECTION_NAMES:
            raise ValueError(
                f"未知检验严格度: {inspection!r}（可选 {list(_INSPECTION_NAMES)}）")
        code = SamplingEngine.get_code(lot_size, level)
        try:
            idx = _AQL_VALS.index(float(aql))
        except ValueError:
            idx = min(range(len(_AQL_VALS)),
                      key=lambda i: abs(_AQL_VALS[i] - float(aql)))
        sizes = _REDUCED_SAMPLE_SIZE if mode == "reduced" else _SAMPLE_SIZES
        plan_code, n, ac, re, via_arrow = SamplingEngine._resolve_plan(
            _INSPECTION_TABLES[mode], code, idx, sizes)
        return {
            "code": code,
            "plan_code": plan_code,
            "sample_size": n,
            "accept": ac,
            "reject": re,
            "aql_actual": _AQL_VALS[idx],
            "lot_size": int(lot_size),
            "level": str(level or "II"),
            "inspection": mode,
            "via_arrow": via_arrow,
        }

    # ------------------------------------------------------------ 转移规则（B0 冻结）
    @staticmethod
    def evaluate_transfer(current_state: str, recent_lots,
                          *, production_stable: bool = True,
                          reduced_enabled: bool = False,
                          scope_key: str = "") -> TransferDecision:
        """按 GB/T 2828.1 转移规则评估下一步状态（纯函数、确定性）。

        规则（阈值即 PLAN_v4.4.0 §3.1 冻结值；每次判定后调用一次）：

        - 正常 → 加严：最近 1 批严重不合格（拒收且 ``serious``），
          或连续 2 批拒收；
        - 加严 → 正常：连续 5 批接收；
        - 正常 → 放宽：连续 10 批接收 + 生产稳定声明 + 放宽显式启用（默认禁用）；
        - 放宽 → 正常：1 批拒收，或生产稳定性声明失效。
        """
        state = str(current_state or "normal").strip().lower()
        if state not in TRANSFER_STATES:
            raise ValueError(
                f"非法检验状态: {current_state!r}（可选 {list(TRANSFER_STATES)}）")
        lots = [item for item in (recent_lots or [])
                if isinstance(item, LotRecord)]

        def _tail_all(decision: str, count: int) -> bool:
            tail = lots[-count:]
            return len(tail) == count and all(
                lot.decision == decision for lot in tail)

        def _tail_ids(count: int) -> list[str]:
            return [lot.lot_id for lot in lots[-count:]]

        def _decision(to_state: str, rule: str, reason: str,
                      trigger: list[str]) -> TransferDecision:
            return TransferDecision(
                scope_key=str(scope_key or ""), from_state=state,
                to_state=to_state, rule=rule, reason=reason,
                triggering_lots=trigger)

        if state == "normal":
            if lots and lots[-1].serious and lots[-1].decision == "reject":
                return _decision(
                    "tightened", "serious_nonconformity",
                    f"最近一批 {lots[-1].lot_id} 严重不合格", [lots[-1].lot_id])
            if _tail_all("reject", 2):
                return _decision(
                    "tightened", "two_consecutive_rejects",
                    "连续 2 批拒收: " + "、".join(_tail_ids(2)), _tail_ids(2))
            if reduced_enabled and production_stable and _tail_all("accept", 10):
                return _decision(
                    "reduced", "ten_consecutive_accepts",
                    "连续 10 批接收且生产稳定（放宽显式启用）",
                    _tail_ids(10))
        elif state == "tightened":
            if _tail_all("accept", 5):
                return _decision(
                    "normal", "five_consecutive_accepts",
                    "连续 5 批接收: " + "、".join(_tail_ids(5)), _tail_ids(5))
        else:  # reduced
            if not production_stable:
                return _decision(
                    "normal", "production_unstable",
                    "生产稳定性声明失效", [])
            if lots and lots[-1].decision == "reject":
                return _decision(
                    "normal", "lot_rejected",
                    f"最近一批 {lots[-1].lot_id} 拒收", [lots[-1].lot_id])
        return TransferDecision(scope_key=str(scope_key or ""),
                                from_state=state, to_state=state)

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
