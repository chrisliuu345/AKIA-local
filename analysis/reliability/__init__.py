"""可靠性工程分析 — Weibull 寿命分析 + MTBF/MTTR + ALT 加速寿命 + 生存分析 + RBD

子模块:
  weibull  — Weibull 分布拟合 (2P/3P/4P MLE), 参数置信区间, B10/B50寿命, R(t), h(t), 概率图
  mtbf     — MTBF/MTTR/可用度分析, 故障间隔统计, Crow-AMSAA 增长模型
  alt      — 加速寿命试验 (Arrhenius / 逆幂律 / Eyring / 试验规划)
  survival — 生存分析 (Kaplan-Meier / Log-rank / Cox PH)
  rbd      — 可靠性框图 (串联/并联/混合/k-of-n)
  warranty — 保修分析
"""

_SUBMODULES = {
    "weibull": ".weibull",
    "mtbf": ".mtbf",
    "alt": ".alt",
    "survival": ".survival",
    "rbd": ".rbd",
    "warranty": ".warranty",
}

# Class-level exports (lazy resolved from submodules)
_CLASS_EXPORTS = {
    "WeibullAnalyzer": (".weibull", "WeibullAnalyzer"),
    "WeibullResult": (".weibull", "WeibullResult"),
    "MTBFAnalyzer": (".mtbf", "MTBFAnalyzer"),
    "MTBFResult": (".mtbf", "MTBFResult"),
    "ALTEngine": (".alt", "ALTEngine"),
}

__all__ = list(_CLASS_EXPORTS.keys()) + list(_SUBMODULES.keys()) + ["survival"]


def __getattr__(name):
    import importlib
    if name in _SUBMODULES:
        mod = importlib.import_module(_SUBMODULES[name], __name__)
        globals()[name] = mod
        return mod
    if name in _CLASS_EXPORTS:
        mod_path, attr = _CLASS_EXPORTS[name]
        mod = importlib.import_module(mod_path, __name__)
        val = getattr(mod, attr)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
