"""集成测试 — 验证所有分析模块"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from analysis.spc import xbar_r, imr
from analysis.capability import normal_cap
from analysis.hypothesis import t_tests, normality
from analysis.msa import gage_rr
from analysis.doe import factorial as fact
from core.data_parser import DataParser
from core.data_validator import DataValidator
from core.template_parser import TemplateParser
from output.excel_report import ExcelReport

np.random.seed(42)

# ── 1. XBar-R Control Chart ──
data = np.random.normal(10.0, 0.5, 125)
series = pd.Series(data)
r = xbar_r.analyze(series, subgroup_size=5)
assert r["num_subgroups"] == 25
assert 9.5 < r["xbar_chart"]["cl"] < 10.5
print(f"[PASS] XBar-R: {r['num_subgroups']} subgroups, CL={r['xbar_chart']['cl']:.4f}")

# ── 2. I-MR ──
r2 = imr.analyze(series)
assert r2["num_points"] == 125
print(f"[PASS] I-MR: {r2['num_points']} points")

# ── 3. Capability ──
cap = normal_cap.analyze(series, usl=11.5, lsl=8.5)
assert cap["capability"]["cpk"] > 0.5
print(f"[PASS] Capability: Cp={cap['capability']['cp']:.4f}, Cpk={cap['capability']['cpk']:.4f}, {cap['capability']['grade']}")

# ── 4. t-Test ──
g1 = pd.Series(np.random.normal(10, 0.5, 30))
g2 = pd.Series(np.random.normal(10.5, 0.5, 30))
t = t_tests.two_sample(g1, g2)
assert "p_value" in t
print(f"[PASS] t-Test: t={t['t_statistic']:.4f}, p={t['p_value']:.6f}")

# ── 5. Normality ──
n = normality.normality_test(series)
assert "overall_conclusion" in n
print(f"[PASS] Normality: {n['overall_conclusion']}")

# ── 6. MSA Gage R&R ──
msa_df = pd.DataFrame({
    "part": np.repeat(range(1, 11), 6),
    "operator": np.tile(np.repeat(["A", "B", "C"], 2), 10),
    "measurement": np.random.normal(10, 0.1, 60),
})
msa = gage_rr.analyze_crossed(msa_df, "measurement", "part", "operator", 1.0)
assert "acceptance" in msa
print(f"[PASS] MSA: %GRR={msa['percentages']['grr_pct_tv']:.2f}%, NDC={msa['ndc']}, {msa['acceptance']['level']}")

# ── 7. DOE Factorial ──
factors = ["A", "B", "C"]
design = fact.generate_design(factors, replicates=1)
design["response"] = design["A"] * 0.5 + design["B"] * 0.3 + np.random.normal(0, 0.1, len(design))
doe = fact.analyze_factorial(design, "response", factors)
assert "significant_factors" in doe
print(f"[PASS] DOE: Effects={doe['effects']}, R^2={doe.get('model_r_squared','N/A'):.4f}")

# ── 8. DataParser ──
df_test = pd.DataFrame({"测量值": [1.0, 2.0, 3.0, 4.0, 5.0], "组别": ["A", "A", "B", "B", "C"]})
parser = DataParser()
info = parser.analyze(df_test)
assert "measurement_columns" in info
assert len(info["measurement_columns"]) >= 1
print(f"[PASS] DataParser: {len(info['measurement_columns'])} measurement cols")

# ── 9. DataValidator ──
validator = DataValidator()
v = validator.validate(df_test, ["测量值"])
assert "summary" in v
print(f"[PASS] DataValidator: valid={v['valid']}, errors={v['error_count']}, warnings={v['warning_count']}")

# ── 10. TemplateParser ──
tp = TemplateParser()
assert len(tp.VALID_ANALYSIS_TYPES) > 10
print(f"[PASS] TemplateParser: {len(tp.VALID_ANALYSIS_TYPES)} valid analysis types")

# ── 11. Excel/Word/PDF Report ──
er = ExcelReport()
out = er.generate(
    [{"analysis_type": "XBar-R", "params": {"size": 5}, "result": r}],
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_test_report.xlsx"),
    "Test Report",
)
print(f"[PASS] ExcelReport: {out}")

print("\n=== ALL 11 TESTS PASSED ===")
