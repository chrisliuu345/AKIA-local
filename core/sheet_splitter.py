"""工作表拆分引擎 — 按列值/行数/条件/分组"""

import hashlib, os, pandas as pd


class SheetSplitter:
    @staticmethod
    def split_by_column(df: pd.DataFrame, column: str, output_dir: str) -> list[str]:
        """按列值拆分为多个文件"""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for val, group in df.groupby(column):
            raw = str(val).replace("/", "_").replace("\\", "_")
            suffix = (
                "_" + hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:6]
                if len(raw) > 50
                else ""
            )
            safe = raw[:50] + suffix
            path = os.path.join(output_dir, f"{safe}.xlsx")
            group.to_excel(path, index=False)
            paths.append(path)
        return paths

    @staticmethod
    def split_by_rows(
        df: pd.DataFrame, rows_per_file: int, output_dir: str
    ) -> list[str]:
        """按行数拆分"""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i, start in enumerate(range(0, len(df), rows_per_file)):
            chunk = df.iloc[start : start + rows_per_file]
            path = os.path.join(output_dir, f"part_{i + 1:03d}.xlsx")
            chunk.to_excel(path, index=False)
            paths.append(path)
        return paths

    @staticmethod
    def split_by_condition(
        df: pd.DataFrame,
        condition_col: str,
        operator: str,
        threshold: float,
        output_dir: str,
    ) -> list[str]:
        """按条件拆分 (如 cpk < 1.0)"""
        os.makedirs(output_dir, exist_ok=True)
        col = pd.to_numeric(df[condition_col], errors="coerce")
        ops = {
            "<": lambda x: x < threshold,
            ">": lambda x: x > threshold,
            "<=": lambda x: x <= threshold,
            ">=": lambda x: x >= threshold,
            "==": lambda x: x == threshold,
        }
        op_func = ops.get(operator, ops["<"])
        mask = op_func(col)
        match = df[mask]
        rest = df[~mask]
        op_safe = operator.replace("<", "lt").replace(">", "gt").replace("=", "eq")
        p1 = os.path.join(
            output_dir, f"match_{condition_col}_{op_safe}_{threshold}.xlsx"
        )
        p2 = os.path.join(output_dir, "rest.xlsx")
        match.to_excel(p1, index=False)
        rest.to_excel(p2, index=False)
        return [p1, p2]

    @staticmethod
    def split_by_group(
        df: pd.DataFrame, columns: list[str], output_dir: str
    ) -> list[str]:
        """按多级分组拆分 (车间→产线)"""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for keys, group in df.groupby(columns):
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            name = "_".join(str(k).replace("/", "_")[:20] for k in key_tuple)
            path = os.path.join(output_dir, f"{name}.xlsx")
            group.to_excel(path, index=False)
            paths.append(path)
        return paths
