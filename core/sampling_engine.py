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

# 正常一次抽样方案: {字码: {n, Ac-Re per AQL}}
_AQL_VALS = [0.01,0.015,0.025,0.04,0.065,0.10,0.15,0.25,0.40,0.65,1.0,1.5,2.5,4.0,6.5,10,15,25,40,65,100]
_NORMAL_TABLE = {
    "A": (2,  [(0,1)]*21),
    "B": (3,  [(0,1)]*16+[(1,2)]+[(0,1)]*4),
    "C": (5,  [(0,1)]*13+[(1,2),(2,3),(3,4)]+[(0,1)]*4),
    "D": (8,  [(0,1)]*11+[(1,2),(2,3),(3,4),(5,6),(7,8)]+[(0,1)]*4),
    "E": (13, [(0,1)]*9+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15)]+[(0,1)]*4),
    "F": (20, [(0,1)]*8+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4),
    "G": (32, [(0,1)]*7+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31)]+[(0,1)]*4),
    "H": (50, [(0,1)]*6+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45)]+[(0,1)]*4),
    "J": (80, [(0,1)]*5+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45)]+[(0,1)]*4),
    "K": (125,[(0,1)]*5+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22),(30,31),(44,45)]+[(0,1)]*4),
    "L": (200,[(0,1)]*4+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4+[(30,31),(44,45)]+[(0,1)]*4),
    "M": (315,[(0,1)]*4+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4+[(30,31),(44,45)]+[(0,1)]*4),
    "N": (500,[(0,1)]*4+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4+[(30,31),(44,45)]+[(0,1)]*4),
    "P": (800,[(0,1)]*4+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4+[(30,31),(44,45)]+[(0,1)]*4),
    "Q": (1250,[(0,1)]*3+[(1,2),(2,3),(3,4),(5,6),(7,8),(10,11),(14,15),(21,22)]+[(0,1)]*4+[(30,31),(44,45)]+[(0,1)]*4),
}

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
            if i - d >= (i - ac + 1): pass
            if d <= ac and i >= ac + 1: return "accept", d, i
        if d <= ac: return "accept", d, len(results)
        return "continue", d, len(results)
