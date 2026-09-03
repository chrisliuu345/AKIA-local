"""DOE 实验设计 — 因子设计 · 响应曲面(CCD) · Box-Behnken · Plackett-Burman · DSD · 部分因子 · 田口 · 混合 · Power分析"""

_SUBMODULES = {
    "factorial": ".factorial",
    "response_surface": ".response_surface",
    "box_behnken": ".box_behnken",
    "doe_analysis": ".doe_analysis",
    "plackett_burman": ".plackett_burman",
    "definitive_screening": ".definitive_screening",
    "fractional": ".fractional",
    "taguchi": ".taguchi",
    "mixture": ".mixture",
    "power_analysis": ".power_analysis",
}

__all__ = list(_SUBMODULES.keys())


def __getattr__(name):
    import importlib
    if name in _SUBMODULES:
        mod = importlib.import_module(_SUBMODULES[name], __name__)
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
