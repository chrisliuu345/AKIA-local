"""KPI 公式引擎单测 — AST 白名单安全性与求值正确性 (v2.4 F3)"""

import pytest
import pandas as pd

from core.kpi_formula import (
    validate, evaluate, FormulaError, sanitize_name,
    describe_variables, variable_list,
)


class TestValidate:
    def test_simple_expr_ok(self):
        validate("cpk / (1 + grr_pct)")
        validate("oee * 0.85 + 2.5")
        validate("(a + b) ** 2")
        validate("-x + 3.14")
        validate("a // b % 2")

    def test_empty_rejected(self):
        with pytest.raises(FormulaError):
            validate("")

    def test_syntax_error(self):
        with pytest.raises(FormulaError):
            validate("cpk +")
        with pytest.raises(FormulaError):
            validate("1 / (2 - 2")

    def test_call_rejected(self):
        """禁止函数调用 — 防注入"""
        for evil in ["__import__('os')", "eval('1')", "abs(-3)", "open('/etc/passwd')",
                     "max(1, 2)", "pow(2, 3)"]:
            with pytest.raises(FormulaError):
                validate(evil)

    def test_attribute_and_subscript_rejected(self):
        with pytest.raises(FormulaError):
            validate("obj.attr")
        with pytest.raises(FormulaError):
            validate("d['key']")
        with pytest.raises(FormulaError):
            validate("a.b.c")

    def test_string_constant_rejected(self):
        with pytest.raises(FormulaError):
            validate("'hello' + 1")

    def test_bool_constant_rejected(self):
        with pytest.raises(FormulaError):
            validate("True + 1")

    def test_bitwise_rejected(self):
        with pytest.raises(FormulaError):
            validate("a & b")
        with pytest.raises(FormulaError):
            validate("a | b")
        with pytest.raises(FormulaError):
            validate("a << 1")

    def test_chinese_variable_names(self):
        validate("长度_mean / 长度_std")

    def test_expr_too_long_rejected(self):
        with pytest.raises(FormulaError, match="过长"):
            validate("1+" * 300 + "1")

    def test_long_chain_no_crash(self):
        """审查 #1: 长表达式要么正确求值, 要么 FormulaError — 绝不逃逸为
        RecursionError/MemoryError (此前 1100+ 项链会逃逸中断 Dashboard)"""
        # 深度/长度限制内的长链: 正常求值
        assert evaluate("1+" * 100 + "1", {}) == 101.0
        # 超长: FormulaError (长度上限拦截)
        with pytest.raises(FormulaError):
            evaluate("1+" * 300 + "1", {})
        # 指数链在限制内: 正常求值 (1 的幂恒为 1)
        assert evaluate("1**" * 60 + "1", {}) == 1.0
        # 深括号: FormulaError (ast.parse 自身嵌套限制)
        with pytest.raises(FormulaError):
            validate("(" * 5000 + "1" + ")" * 5000)


class TestEvaluate:
    def test_basic_arithmetic(self):
        v = {"a": 10.0, "b": 4.0}
        assert evaluate("a + b", v) == 14.0
        assert evaluate("a - b", v) == 6.0
        assert evaluate("a * b", v) == 40.0
        assert evaluate("a / b", v) == 2.5
        assert evaluate("a // b", v) == 2.0
        assert evaluate("a % b", v) == 2.0
        assert evaluate("a ** 2", v) == 100.0

    def test_parse_cache_reused(self):
        """W96: validate+evaluate 复用同一 parse 结果, 不重复 ast.parse"""
        from core import kpi_formula as kf
        kf._parse_cache.clear()
        validate("a + 1")
        evaluate("a + 1", {"a": 2.0})
        assert len(kf._parse_cache) == 1

    def test_huge_constant_power_rejected(self):
        """W96: 常量指数过大时拒绝 (防超长幂运算), 变量指数不受限"""
        with pytest.raises(FormulaError, match="指数过大"):
            evaluate("2 ** 1000000", {})
        with pytest.raises(FormulaError, match="指数过大"):
            evaluate("10 ** 9999999", {})
        assert evaluate("2 ** x", {"x": 10.0}) == 1024.0

    def test_precedence(self):
        v = {"x": 2.0, "y": 3.0, "z": 4.0}
        assert evaluate("x + y * z", v) == 14.0
        assert evaluate("(x + y) * z", v) == 20.0
        assert evaluate("x ** y + z", v) == 12.0

    def test_unary(self):
        v = {"x": 5.0}
        assert evaluate("-x", v) == -5.0
        assert evaluate("+x", v) == 5.0
        assert evaluate("-x + 10", v) == 5.0

    def test_unknown_variable(self):
        with pytest.raises(FormulaError, match="未知变量"):
            evaluate("missing_var + 1", {"x": 1.0})

    def test_division_by_zero(self):
        with pytest.raises(FormulaError, match="除数为零"):
            evaluate("1 / 0", {})
        with pytest.raises(FormulaError, match="除数为零"):
            evaluate("1 / (2 - 2)", {})

    def test_injection_attempts(self):
        """安全: 注入表达式必须被拒绝"""
        for evil in ["__import__('os').system('dir')", "().__class__"]:
            with pytest.raises(FormulaError):
                evaluate(evil, {})

    def test_complex_result_rejected(self):
        """审查 #4: 负底数小数次幂返回 complex, 违反 float 契约"""
        with pytest.raises(FormulaError, match="复数"):
            evaluate("(-8) ** 0.5", {})

    def test_inf_nan_rejected(self):
        """审查 #4: 1e999 产生 inf, inf-inf 产生 nan — 均须拒绝"""
        with pytest.raises(FormulaError):
            evaluate("1e999", {})
        with pytest.raises(FormulaError):
            evaluate("1e999 - 1e999", {})


class TestSanitize:
    def test_chinese_preserved(self):
        assert sanitize_name("长度") == "长度"

    def test_special_chars_replaced(self):
        assert sanitize_name("长度(mm)") == "长度_mm_"
        assert sanitize_name("a b/c") == "a_b_c"
        assert sanitize_name("") == "_"
        assert sanitize_name("123") == "_123"


class TestDescribeVariables:
    def test_kpi_plus_column_stats(self):
        analyses = {
            2: {"analysis_type": "能力", "params": {},
                "result": {"capability": {"cp": 1.5, "grade": "A"}}},
        }
        df = pd.DataFrame({
            "长度": [10.0, 10.1, 9.9, 10.2],
            "名称": ["a", "b", "c", "d"],
        })
        ns = describe_variables(analyses, df)
        assert ns["cp"] == pytest.approx(1.5)
        assert ns["长度_mean"] == pytest.approx(10.05)
        assert ns["长度_std"] == pytest.approx(0.1290994, abs=1e-4)
        assert ns["长度_max"] == 10.2
        assert ns["长度_min"] == 9.9
        assert "名称_mean" not in ns  # 文本列无统计

    def test_sanitize_collision_gets_suffix(self):
        """'A/B' 与 'A B' 都 sanitize 为 A_B, 冲突列追加序号防覆盖"""
        df = pd.DataFrame({"A/B": [1.0, 2.0], "A B": [3.0, 4.0]})
        ns = describe_variables({}, df)
        assert ns["A_B_mean"] == pytest.approx(1.5)
        assert ns["A_B_2_mean"] == pytest.approx(3.5)

    def test_no_df(self):
        analyses = {10: {"analysis_type": "OEE", "params": {},
                         "result": {"overall": {"oee": 0.8}}}}
        ns = describe_variables(analyses)
        assert ns["oee"] == pytest.approx(0.8)

    def test_variable_list_sorted(self):
        items = variable_list({"b": 2.0, "a": 1.5})
        assert [name for name, _ in items] == ["a", "b"]
        assert items[0][1] == "1.5"
