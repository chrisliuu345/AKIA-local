"""过程能力分析 — Cp/Cpk/Pp/Ppk/Cpm · 正态与非正态 · Johnson变换 · 公差区间 · Sixpack"""

_SUBMODULES = {
    "normal_cap": ".normal_cap",
    "non_normal_cap": ".non_normal_cap",
    "between_within_cap": ".between_within_cap",
    "tolerance_interval": ".tolerance_interval",
    "johnson_transform": ".johnson_transform",
    "sixpack": ".sixpack",
}

__all__ = list(_SUBMODULES.keys()) + ["get_capability_grade"]


def get_capability_grade(*args, **kwargs):
    from ._utils import get_capability_grade as _impl
    return _impl(*args, **kwargs)


def __getattr__(name):
    import importlib
    if name in _SUBMODULES:
        mod = importlib.import_module(_SUBMODULES[name], __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
