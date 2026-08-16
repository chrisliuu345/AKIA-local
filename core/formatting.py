"""数值格式化工具 — p值/Cpk/百分比/统计量统一美观输出"""


def format_pvalue(p: float) -> str:
    """p 值: <0.001 时显示 '<0.001'，否则保留 4 位"""
    if p < 0.0001:
        return "<0.0001"
    if p < 0.001:
        return "<0.001"
    return f"{p:.4f}"


def format_cp(cp: float) -> str:
    """过程能力指数: 保留 3 位"""
    return f"{cp:.3f}"


def format_pct(value: float, decimals: int = 1) -> str:
    """百分比: 0.1234 → '12.3%'"""
    return f"{value * 100:.{decimals}f}%"


def format_stat(value: float, decimals: int = 3) -> str:
    """通用统计量: 保留指定小数位"""
    if abs(value) < 10 ** (-decimals):
        return f"<{10 ** (-decimals):.{decimals}f}"
    return f"{value:.{decimals}f}"


def format_ci(low: float, high: float, decimals: int = 2) -> str:
    """置信区间: '[12.34, 18.90]'"""
    return f"[{low:.{decimals}f}, {high:.{decimals}f}]"


def format_count(n: int) -> str:
    """大数格式化: 1234567 → '1,234,567'"""
    return f"{n:,}"
