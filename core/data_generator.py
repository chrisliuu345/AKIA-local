"""随机数据生成器 — 7种分布 + MSA/DOE/SPC 模板"""

from typing import ClassVar

import numpy as np, pandas as pd


class DataGenerator:
    DISTS: ClassVar[list[str]] = ["正态", "对数正态", "指数", "均匀", "Weibull", "二项", "泊松"]

    @staticmethod
    def generate(dist: str, n: int, **params) -> np.ndarray:
        if dist == "正态":
            return np.random.normal(params.get("mu", 0), params.get("sigma", 1), n)
        elif dist == "对数正态":
            return np.random.lognormal(params.get("mu", 0), params.get("sigma", 0.5), n)
        elif dist == "指数":
            return np.random.exponential(params.get("scale", 1), n)
        elif dist == "均匀":
            return np.random.uniform(params.get("low", 0), params.get("high", 1), n)
        elif dist == "Weibull":
            return params.get("scale", 1) * np.random.weibull(params.get("shape", 1.5), n)
        elif dist == "二项":
            return np.random.binomial(params.get("trials", 10), params.get("prob", 0.5), n)
        elif dist == "泊松":
            return np.random.poisson(params.get("lam", 5), n)
        return np.zeros(n)

    @staticmethod
    def spc_template(n_subgroups: int = 25, subgroup_size: int = 5,
                     mu: float = 10, sigma: float = 0.5) -> pd.DataFrame:
        data = np.random.normal(mu, sigma, n_subgroups * subgroup_size)
        df = pd.DataFrame(data.reshape(n_subgroups, subgroup_size))
        df.columns = [f"x{i+1}" for i in range(subgroup_size)]
        df.insert(0, "子组", range(1, n_subgroups + 1))
        return df

    @staticmethod
    def msa_template(n_parts: int = 10, n_operators: int = 3, n_reps: int = 2,
                     part_var: float = 0.5, measure_var: float = 0.05) -> pd.DataFrame:
        rows = []
        true_vals = np.random.normal(10, part_var, n_parts)
        for op in range(n_operators):
            for p in range(n_parts):
                for _r in range(n_reps):
                    measured = true_vals[p] + np.random.normal(0, measure_var)
                    rows.append([f"操作员{op+1}", f"零件{p+1}", round(measured, 4)])
        return pd.DataFrame(rows, columns=["操作员", "零件", "测量值"])

    @staticmethod
    def doe_template(n_factors: int = 3) -> pd.DataFrame:
        """2^k 全因子设计模板"""
        import itertools
        levels = list(itertools.product([-1, 1], repeat=n_factors))
        data = {"run": range(1, len(levels) + 1)}
        for i in range(n_factors):
            data[f"Factor_{chr(65+i)}"] = [l[i] for l in levels]
        data["Response"] = np.random.normal(50, 5, len(levels))
        return pd.DataFrame(data)
