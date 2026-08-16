"""工作表合并引擎 — 追加/JOIN/批量合并"""

import os, pandas as pd, numpy as np
from typing import List, Dict, Optional


class SheetMerger:
    @staticmethod
    def merge_append(files: List[str], sheet_name: str = "Sheet1") -> pd.DataFrame:
        """多文件同结构纵向追加"""
        dfs = []
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(f, dtype=str)
            else:
                df = pd.read_excel(f, sheet_name=sheet_name, dtype=str)
            dfs.append(df)
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    @staticmethod
    def merge_join(df1: pd.DataFrame, df2: pd.DataFrame, key: str,
                   how: str = "inner") -> pd.DataFrame:
        """按关键列 JOIN (inner/left/right/outer)"""
        return pd.merge(df1, df2, on=key, how=how)

    @staticmethod
    def merge_folder(folder: str, pattern: str = "*.*") -> pd.DataFrame:
        """批量合并文件夹中所有 Excel/CSV

        pattern: 文件匹配模式。默认 "*.*" 匹配所有 Excel/CSV 文件；
        传入自定义模式（如 "*.txt"）时按该模式匹配。
        """
        import glob
        if pattern in ("*", "*.*"):
            files = []
            for ext in ["*.xlsx", "*.xls", "*.xlsm", "*.csv"]:
                files.extend(glob.glob(os.path.join(folder, ext)))
        else:
            files = glob.glob(os.path.join(folder, pattern))
        if not files:
            return pd.DataFrame()
        return SheetMerger.merge_append(sorted(files))

    @staticmethod
    def merge_sheets(file_path: str) -> Dict[str, pd.DataFrame]:
        """单文件多 Sheet 合并"""
        xl = pd.ExcelFile(file_path)
        result = {}
        for sn in xl.sheet_names:
            result[sn] = pd.read_excel(file_path, sheet_name=sn, dtype=str)
        return result
