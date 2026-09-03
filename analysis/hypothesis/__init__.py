"""假设检验 — t检验/ANOVA/正态性检验/方差齐性检验/非参数检验/卡方/比例/等价检验"""

_SUBMODULES = {
    "t_tests": ".t_tests",
    "anova": ".anova",
    "normality": ".normality",
    "variance_tests": ".variance_tests",
    "nonparametric": ".nonparametric",
    "proportion": ".proportion",
    "equivalence": ".equivalence",
}

__all__ = list(_SUBMODULES.keys())


def __getattr__(name):
    import importlib
    if name in _SUBMODULES:
        mod = importlib.import_module(_SUBMODULES[name], __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
