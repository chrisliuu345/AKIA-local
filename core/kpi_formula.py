"""KPI 公式引擎 — AST 白名单安全解析器 (v2.4 F3)

零依赖安全设计:
- ast.parse(mode="eval") 仅允许数值表达式
- 节点白名单: Expression/BinOp/UnaryOp/Name/Constant
- 运算符白名单: + - * / // % ** 与正负号
- 禁止 Call/Attribute/Subscript → 无法执行函数调用或访问对象属性, 杜绝注入

变量命名空间由 describe_variables() 构建:
KPI 指标 (core/kpi_extractor.build_variable_namespace) + 数据列统计 (mean/std/max/min)。
"""

import ast

import pandas as pd

from core.kpi_extractor import build_variable_namespace

_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Constant,
                  ast.operator, ast.unaryop, ast.expr_context)
_ALLOWED_BIN_OPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_UNARY_OPS = (ast.UAdd, ast.USub)


class FormulaError(Exception):
    """公式校验/求值错误 — message 为友好中文提示"""


MAX_EXPR_LEN = 500
MAX_EVAL_DEPTH = 200

_MAX_PARSE_CACHE = 256
_parse_cache: dict[str, ast.Expression] = {}


def _parse(expr: str) -> ast.Expression:
    """ast.parse(mode='eval') + 缓存复用, 异常由调用方捕获"""
    cached = _parse_cache.get(expr)
    if cached is not None:
        return cached
    tree = ast.parse(expr, mode="eval")
    if len(_parse_cache) >= _MAX_PARSE_CACHE:
        _parse_cache.clear()
    _parse_cache[expr] = tree
    return tree


def validate(expr: str) -> None:
    """语法 + 白名单校验, 不通过抛 FormulaError"""
    if not expr or not expr.strip():
        raise FormulaError("公式为空")
    if len(expr) > MAX_EXPR_LEN:
        raise FormulaError(f"表达式过长 (上限 {MAX_EXPR_LEN} 字符)")
    try:
        tree = _parse(expr)
    except SyntaxError as e:
        raise FormulaError(f"语法错误: {e.msg} (位置 {e.offset})") from e
    except RecursionError:
        raise FormulaError("表达式嵌套过深") from None
    except MemoryError:
        raise FormulaError("表达式过于复杂") from None

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise FormulaError(f"不支持的语法: {type(node).__name__} (仅允许数值运算)")
        if isinstance(node, ast.BinOp) and not isinstance(node.op, _ALLOWED_BIN_OPS):
            raise FormulaError(f"不支持的运算符: {type(node.op).__name__}")
        if isinstance(node, ast.UnaryOp) and not isinstance(node.op, _ALLOWED_UNARY_OPS):
            raise FormulaError(f"不支持的一元运算符: {type(node.op).__name__}")
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise FormulaError("只支持数值常量")


def evaluate(expr: str, variables: dict[str, float]) -> float:
    """校验并求值 — NameError/除零等转为 FormulaError, 保证只抛 FormulaError"""
    import math
    validate(expr)
    tree = _parse(expr)
    depth = 0

    def _eval(node):
        nonlocal depth
        depth += 1
        if depth > MAX_EVAL_DEPTH:
            depth -= 1
            raise FormulaError("表达式嵌套过深")
        try:
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            if isinstance(node, ast.Constant):
                return float(node.value)
            if isinstance(node, ast.Name):
                if node.id not in variables:
                    raise FormulaError(f"未知变量: {node.id}")
                value = variables[node.id]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise FormulaError(f"变量 {node.id} 不是数值")
                return float(value)
            if isinstance(node, ast.UnaryOp):
                v = _eval(node.operand)
                return v if isinstance(node.op, ast.UAdd) else -v
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0:
                        raise FormulaError("除数为零")
                    return left / right
                if isinstance(node.op, ast.FloorDiv):
                    if right == 0:
                        raise FormulaError("除数为零")
                    return left // right
                if isinstance(node.op, ast.Mod):
                    if right == 0:
                        raise FormulaError("除数为零")
                    return left % right
                if isinstance(node.op, ast.Pow):
                    if isinstance(node.right, ast.Constant) and abs(node.right.value) >= 1e6:
                        raise FormulaError("指数过大")
                    return left ** right
            raise FormulaError(f"无法求值的节点: {type(node).__name__}")
        finally:
            depth -= 1

    try:
        result = _eval(tree)
    except FormulaError:
        raise
    except (OverflowError, ZeroDivisionError, RecursionError) as e:
        raise FormulaError(f"数值错误: {e}") from e
    if isinstance(result, complex) or not math.isfinite(result):
        raise FormulaError("结果无效 (复数或非有限值)")
    return result


def sanitize_name(name: str) -> str:
    """列名 → 合法 Python 标识符 (保留中文, 其它非法字符替换为 _)"""
    out = []
    for ch in str(name):
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    result = "".join(out) or "_"
    if result[0].isdigit():
        result = "_" + result
    return result


def _column_stats(df: pd.DataFrame) -> dict[str, float]:
    """数值列统计变量 — {列名}_mean/_std/_max/_min (重复列名用位置访问)

    sanitize 后同名的列 (如 "A/B" 与 "A B" → A_B) 追加序号防覆盖。
    """
    stats: dict[str, float] = {}
    seen: dict[str, int] = {}
    for i, col in enumerate(df.columns):
        try:
            series = pd.to_numeric(df.iloc[:, i], errors="coerce")
        except Exception:
            continue
        valid = series.dropna()
        if len(valid) < 2:
            continue
        base = sanitize_name(str(col))
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            base = f"{base}_{seen[base]}"
        stats[f"{base}_mean"] = float(valid.mean())
        stats[f"{base}_std"] = float(valid.std())
        stats[f"{base}_max"] = float(valid.max())
        stats[f"{base}_min"] = float(valid.min())
    return stats


def describe_variables(analyses: dict[int, dict], df: pd.DataFrame = None) -> dict[str, float]:
    """构建公式变量命名空间 — KPI 指标 + 数据列统计

    analyses: MainWindow.analyses; df: 主数据表 (可选)
    返回: {变量名: 当前值}, 供公式求值与变量列表展示
    """
    ns = build_variable_namespace(analyses)
    if df is not None and not df.empty:
        for name, value in _column_stats(df).items():
            if name not in ns:
                ns[name] = value
    return ns


def variable_list(variables: dict[str, float]) -> list[tuple[str, str]]:
    """变量列表 [(名称, 格式化值)] — 供对话框展示"""
    return [(name, f"{value:.4g}") for name, value in sorted(variables.items())]
