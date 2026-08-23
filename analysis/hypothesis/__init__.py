"""假设检验 — t检验/ANOVA/正态性检验/方差齐性检验/非参数检验/卡方/比例/等价检验"""
from . import t_tests, anova, normality, variance_tests, nonparametric, proportion, equivalence

__all__ = [
    "t_tests", "anova", "normality", "variance_tests", "nonparametric",
    "proportion", "equivalence",
]
