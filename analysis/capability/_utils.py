"""过程能力分析共享工具函数"""
from config.settings import CAPABILITY_GRADES


def spec_limit_error(usl: float | None, lsl: float | None) -> str:
    """规格限合法性检查，返回错误信息（空字符串 = 通过）。

    USL ≤ LSL 时 Cp/Cpk 会算出负数（如 Cp = −0.19）、良率出现负百分比，
    属于"看起来像结果"的错误输出，必须在此拦下。
    """
    if usl is not None and lsl is not None and float(usl) <= float(lsl):
        return f"上规格限必须大于下规格限（USL={usl} ≤ LSL={lsl}）"
    return ""


def degenerate_spread_error(
    values,
    usl: float | None,
    lsl: float | None,
    rel_tol: float = 1e-9,
) -> str:
    """判定"过程波动相对公差可忽略"，返回错误信息（空字符串 = 通过）。

    仅当 |max−min| ≤ rel_tol × 公差宽度（或规格量级）时触发：此时 Cp 可达
    1e12 量级并被评成 "A+"，属数值退化而非真实高能力。
    """
    import numpy as np

    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return ""
    scale = None
    if usl is not None and lsl is not None:
        scale = abs(float(usl) - float(lsl))
    elif usl is not None or lsl is not None:
        scale = max(abs(float(usl if usl is not None else lsl)), 1.0)
    if not scale or scale <= 0:
        return ""
    spread = float(np.max(arr) - np.min(arr))
    # spread == 0 属"精确常量"：各模块既有语义为 None / inf（见 test_cpm、
    # test_percentile_constant_data），保留不动；本守卫只拦"带数值噪声的伪常量"
    # （如 1+1e-13·i 这类浮点噪声），它会算出 Cp≈1e12 并被评 "A+"。
    if 0.0 < spread <= rel_tol * scale:
        return (f"过程波动 {spread:.3g} 相对公差 {scale:.3g} 可忽略（≤{rel_tol:g}×），"
                "能力指数无数值意义")
    return ""


def get_capability_grade(cpk: float) -> str:
    """
    根据 Cpk/Ppk 值返回能力等级
    
    Args:
        cpk: 能力指数值
        
    Returns:
        格式化的等级字符串，如 "A+ (特优)"
    """
    for grade, (low, high, desc) in CAPABILITY_GRADES.items():
        if low <= cpk < high:
            return f"{grade} ({desc})"
    return "D (差)"
