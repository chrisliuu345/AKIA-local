"""
CO401 全自动分析 + 报告生成
"""
import sys, os
sys.path.insert(0, r"D:\AI-agent\projects\ie-quality-analyzer")

import matplotlib; matplotlib.use("Agg")
import pandas as pd, numpy as np
from analysis.spc import xbar_r, imr
from analysis.capability import normal_cap
from analysis.msa import linearity_bias
from analysis.hypothesis import t_tests
from output.excel_report import ExcelReport
from output.word_report import WordReport

SRC = r"D:\AI-agent\projects\ie-quality-analyzer\CO401-20220930_清洗美化.xlsx"
OUT_DIR = r"D:\AI-agent\Output"
os.makedirs(OUT_DIR, exist_ok=True)

# 手工装载: 3-row header, row 2 = column names
df = pd.read_excel(SRC, engine="openpyxl", header=None)
df.columns = [str(c).strip() if pd.notna(c) else f"Col_{i}" for i, c in enumerate(df.iloc[2])]
seen = {}
for i, c in enumerate(df.columns):
    if c in seen:
        seen[c] += 1
        df.columns.values[i] = f"{c}_{seen[c]}"
    else:
        seen[c] = 0
df = df.iloc[3:].reset_index(drop=True)
print(f"Loaded: {df.shape[0]}r x {df.shape[1]}c")

# 直接识别数值列
numeric_cols = []
for c in df.columns:
    try:
        d = pd.to_numeric(df[c], errors="coerce")
        if d.notna().sum() > 50 and d.std() > 0.001:
            numeric_cols.append((str(c), float(d.mean()), float(d.std()), d.notna().sum(), d))
    except (ValueError, TypeError):
        pass

numeric_cols.sort(key=lambda x: x[2])  # sort by std
print(f"Numeric cols with variance: {len(numeric_cols)}")

# 选列
precision = [(n,m,s,c,d) for n,m,s,c,d in numeric_cols if s < 0.3]
general   = [(n,m,s,c,d) for n,m,s,c,d in numeric_cols if 0.3 <= s < 3]
wide      = [(n,m,s,c,d) for n,m,s,c,d in numeric_cols if s >= 3]

for tag, cols in [("PRECISION", precision), ("GENERAL", general), ("WIDE", wide)]:
    for n,m,s,c,d in cols[:5]:
        print(f"  [{tag}] {n[:30]:30s} mean={m:10.3f} std={s:.3f} n={c}")

def get_data(item):
    return item[4].dropna()

analyses = []

# 1. SPC XBar-R — general col
col, data = general[0][0], get_data(general[0])
r = xbar_r.analyze(data, 5)
analyses.append({"analysis_type": f"XBar-R: {col}", "params": {"column":col,"subgroup":5}, "result":r, "chart_data":r})
print(f"\n[SPC] {col}: CL={r['xbar_chart']['cl']:.4f}")

# 2. I-MR — another general col
idx = 1 if len(general)>1 else 0
col, data = general[idx][0], get_data(general[idx])
r2 = imr.analyze(data)
analyses.append({"analysis_type": f"I-MR: {col}", "params": {"column":col}, "result":r2, "chart_data":r2})
print(f"[I-MR] {col}: CL={r2['i_chart']['cl']:.4f}")

# 3. Capability — wide col
if wide:
    col, data = wide[0][0], get_data(wide[0])
else:
    col, data = general[-1][0], get_data(general[-1])
usl, lsl = data.mean()+3*data.std(), max(data.mean()-3*data.std(), 0.001)
r3 = normal_cap.analyze(data, usl, lsl)
analyses.append({"analysis_type": f"Capability: {col}", "params": {"column":col,"usl":round(usl,4),"lsl":round(lsl,4)}, "result":r3, "chart_data":r3})
print(f"[Capability] {col}: Cpk={r3['capability']['cpk']:.4f}, {r3['capability']['grade']}")

# 4. Capability precision
col, data = precision[0][0] if precision else general[2][0] if len(general)>2 else general[0][0], get_data(precision[0] if precision else general[2] if len(general)>2 else general[0])
usl4, lsl4 = data.mean()+4*data.std(), data.mean()-4*data.std()
r4 = normal_cap.analyze(data, usl4, lsl4)
analyses.append({"analysis_type": f"Capability: {col}", "params": {"column":col,"usl":round(usl4,4),"lsl":round(lsl4,4)}, "result":r4, "chart_data":r4})
print(f"[Capability2] {col}: Cpk={r4['capability']['cpk']:.4f}")

# 5. Bias
col, data = (precision[1] if len(precision)>1 else precision[0])[0], get_data(precision[1] if len(precision)>1 else precision[0])
ref = data.mean()
r5 = linearity_bias.analyze_bias(data, ref)
analyses.append({"analysis_type": f"Bias: {col}", "params": {"column":col}, "result":r5, "chart_data":r5})
print(f"[Bias] {col}: mean_bias={r5['mean_bias']:.6f}, sig={r5['is_significant']}")

# 6. t-Test
if len(general) >= 2:
    g1, g2 = get_data(general[0]), get_data(general[1])
    n = min(len(g1), len(g2))
    r6 = t_tests.two_sample(g1[:n], g2[:n])
    analyses.append({"analysis_type": f"t-Test: {general[0][0]} vs {general[1][0]}", "params": {}, "result":r6, "chart_data":r6})
    print(f"[t-Test] p={r6['p_value']:.6f}, sig={r6['is_significant']}")

# ── 生成报告 ──
print(f"\n--- Generating Reports ---")
xlsx = os.path.join(OUT_DIR, "CO401_Quality_Report.xlsx")
docx = os.path.join(OUT_DIR, "CO401_Quality_Report.docx")

ExcelReport().generate(analyses, xlsx)
print(f"[Excel] {xlsx}")
WordReport().generate(analyses, docx)
print(f"[Word] {docx}")

for f in [xlsx,docx]:
    kb = os.path.getsize(f)/1024
    print(f"  {os.path.basename(f)}: {kb:.1f} KB")
print("\nAll reports generated successfully!")
