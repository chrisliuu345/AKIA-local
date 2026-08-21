"""抽样检验引擎 — GB/T 2828.1 AQL + 随机/分层/系统抽样 + 序贯"""

import numpy as np, pandas as pd
from typing import List, Dict, Tuple, Optional

# GB/T 2828.1 样本字码表 (批量范围 → 一般II级字码)
_LOT_CODE = [
    (2,8,"A"),(9,15,"B"),(16,25,"C"),(26,50,"D"),(51,90,"E"),
    (91,150,"F"),(151,280,"G"),(281,500,"H"),(501,1200,"J"),
    (1201,3200,"K"),(3201,10000,"L"),(10001,35000,"M"),
    (35001,150000,"N"),(150001,500000,"P"),(500001,9999999,"Q"),
]

# 正常一次抽样方案: {字码: (n, Ac-Re list per AQL)}
# 每个Ac-Re列表必须恰好有 len(_AQL_VALS) = 21 项
_AQL_VALS = [0.01,0.015,0.025,0.04,0.065,0.10,0.15,0.25,0.40,0.65,1.0,1.5,2.5,4.0,6.5,10,15,25,40,65,100]

# _ZERO = (0,1) — 默认 Ac=0,Re=1 用于无条目 AQL 列
_Z = (0, 1)

_NORMAL_TABLE = {
    # Code A (n=2):  全部 (0,1)
    "A": (2,    [_Z]*21),
    # Code B (n=3): AQL ≤10 → (0,1); AQL 15 → (1,2); AQL ≥25 → (0,1)
    "B": (3,    [_Z]*16 + [(1,2)] + [_Z]*4),
    # Code C (n=5): AQL ≤1.5 → (0,1); AQL 2.5~10 → 递增; AQL ≥15 → (0,1)
    "C": (5,    [_Z]*12 + [(1,2),(2,3),(3,4),(5,6)] + [_Z]*5),
    # Code D (n=8): AQL ≤1.0 → (0,1); AQL 1.5~25 → 递增; AQL ≥40 → (0,1)
    "D": (8,    [_Z]*11 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15)] + [_Z]*3),
    # Code E (n=13): AQL ≤0.65 → (0,1); AQL 1.0~40 → 递增; AQL ≥65 → (0,1)
    "E": (13,   [_Z]*9 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45)] + [_Z]*2),
    # Code F (n=20): AQL ≤0.40 → (0,1); AQL 0.65~65 → 递增; AQL 100 → (0,1)
    "F": (20,   [_Z]*8 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61)] + [_Z]*2),
    # Code G (n=32): AQL ≤0.25 → (0,1); AQL 0.40~100 → 递增
    "G": (32,   [_Z]*7 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81)] + [_Z]*2),
    # Code H (n=50): AQL ≤0.15 → (0,1); AQL 0.25~100 → 递增
    "H": (50,   [_Z]*6 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101)] + [_Z]*2),
    # Code J (n=80): AQL ≤0.10 → (0,1); AQL 0.15~100 → 递增
    "J": (80,   [_Z]*5 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101)] + [_Z]*3),
    # Code K (n=125): AQL ≤0.10 → (0,1); AQL 0.15~100 → 递增
    "K": (125,  [_Z]*5 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101)] + [_Z]*3),
    # Code L (n=200): AQL ≤0.065 → (0,1); AQL 0.10~100 → 递增
    "L": (200,  [_Z]*4 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101),(120,121),(150,151)] + [_Z]*2),
    # Code M (n=315): 同 L 结构
    "M": (315,  [_Z]*4 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101),(120,121),(150,151)] + [_Z]*2),
    # Code N (n=500): 同 L 结构
    "N": (500,  [_Z]*4 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101),(120,121),(150,151)] + [_Z]*2),
    # Code P (n=800): 同 L 结构
    "P": (800,  [_Z]*4 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101),(120,121),(150,151)] + [_Z]*2),
    # Code Q (n=1250): AQL ≤0.015 → (0,1); AQL 0.025~100 → 递增
    "Q": (1250, [_Z]*2 + [(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45),(60,61),(80,81),(100,101),(120,121),(150,151),(200,201),(250,251)] + [_Z]*2),
}

# W39: 运行时验证 Ac-Re 列表长度
_NAQL = len(_AQL_VALS)
for _code, (_n, _ac_re) in _NORMAL_TABLE.items():
    if len(_ac_re) != _NAQL:
        raise ValueError(
            f"sampling_engine: 字码 {_code} 的 Ac-Re 列表长度 {len(_ac_re)} "
            f"与 AQL 列表长度 {_NAQL} 不匹配"
        )

class SamplingEngine:
    @staticmethod
    def get_code(lot_size: int, level: str = "II") -> str:
        for lo, hi, code in _LOT_CODE:
            if lo <= lot_size <= hi: return code
        return "Q"

    @staticmethod
    def aql_lookup(lot_size: int, aql: float = 1.0, level: str = "II") -> dict:
        code = SamplingEngine.get_code(lot_size, level)
        entry = _NORMAL_TABLE.get(code, (2, [(0,1)]*21))
        n = entry[0]
        try:
            idx = _AQL_VALS.index(aql)
        except ValueError:
            idx = min(range(len(_AQL_VALS)), key=lambda i: abs(_AQL_VALS[i]-aql))
        ac_re = entry[1][idx] if idx < len(entry[1]) else (0,1)
        return {"code": code, "sample_size": n, "accept": ac_re[0], "reject": ac_re[1], "aql_actual": _AQL_VALS[idx], "lot_size": lot_size, "level": level}

    @staticmethod
    def random_sample(df: pd.DataFrame, n: int, seed: int = None) -> pd.DataFrame:
        if n >= len(df): return df.copy()
        return df.sample(n, random_state=seed).reset_index(drop=True)

    @staticmethod
    def stratified_sample(df: pd.DataFrame, column: str, n: int, seed: int = None) -> pd.DataFrame:
        groups = df.groupby(column)
        frac = min(n / len(df), 1.0)
        result = []
        for _, g in groups:
            k = max(1, int(len(g) * frac))
            result.append(g.sample(min(k, len(g)), random_state=seed))
        return pd.concat(result).reset_index(drop=True)

    @staticmethod
    def systematic_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
        if n >= len(df): return df.copy()
        step = len(df) // n
        start = np.random.randint(0, step)
        idx = range(start, len(df), step)
        return df.iloc[list(idx)[:n]].reset_index(drop=True)

    @staticmethod
    def sequential_decision(results: List[int], ac: int, re: int) -> Tuple[str, int, int]:
        """序贯抽样判定: 返(decision, defects, inspected)"""
        d, total = 0, 0
        for i, r in enumerate(results, 1):
            total += 1
            if r == 1: d += 1
            if d >= re: return "reject", d, i
            if d <= ac and i >= ac + 1: return "accept", d, i
        if d <= ac: return "accept", d, len(results)
        return "continue", d, len(results)
