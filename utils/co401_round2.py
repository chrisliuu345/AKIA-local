"""
CO401 第二轮分析 — 选取不同列，输出新报告到 D:\AI-agent\Output
"""
import sys, os
sys.path.insert(0, r"D:\AI-agent\projects\ie-quality-analyzer")

import matplotlib; matplotlib.use("Agg")
import pandas as pd, numpy as np
from analysis.spc import xbar_r, imr
from analysis.capability import normal_cap
from analysis.msa import gage_rr, linearity_bias
from analysis.hypothesis import anova, t_tests
from output.excel_report import ExcelReport
from output.word_report import WordReport

SRC = r"D:\AI-agent\projects\ie-quality-analyzer\CO401-20220930_清洗美化.xlsx"
OUT = r"D:\AI-agent\Output"
os.makedirs(OUT, exist_ok=True)

df = pd.read_excel(SRC, engine="openpyxl", header=None)
df.columns = [str(c).strip() if pd.notna(c) else f"Col_{i}" for i,c in enumerate(df.iloc[2])]
seen = {}
for i, c in enumerate(df.columns):
    if c in seen:
        seen[c] += 1
        df.columns.values[i] = f"{c}_{seen[c]}"
    else:
        seen[c] = 0
df = df.iloc[3:].reset_index(drop=True)

numeric = []
for c in df.columns:
    d = pd.to_numeric(df[c], errors="coerce")
    if d.notna().sum() > 50 and d.std() > 0.001:
        numeric.append((str(c), float(d.mean()), float(d.std()), d.notna().sum(), d))
numeric.sort(key=lambda x: x[2])
print(f"Loaded: {len(df)}r x {len(df.columns)}c, {len(numeric)} vars")

prec = [(n,m,s,c,d) for n,m,s,c,d in numeric if s < 0.3]
gen  = [(n,m,s,c,d) for n,m,s,c,d in numeric if 0.3 <= s < 3]
wide = [(n,m,s,c,d) for n,m,s,c,d in numeric if s >= 3]
get = lambda item: item[4].dropna()

analyses = []

# ── 第二轮：选与第一轮不同的列 ──
# 第一轮用了: general[0], general[1], wide[0], prec[0], prec[1]
# 第二轮用: general[2], general[3], wide[1], prec[2], prec[3], anova

# 1. SPC XBar-R: general[2]
col,data = gen[2][0], get(gen[2])
r = xbar_r.analyze(data, 5)
analyses.append({"analysis_type":f"XBar-R: {col}","params":{"col":col,"sub":5},"result":r,"chart_data":r})
print(f"[SPC] {col}: CL={r['xbar_chart']['cl']:.4f}")

# 2. I-MR: general[3]
col,data = gen[3][0], get(gen[3])
r2 = imr.analyze(data)
analyses.append({"analysis_type":f"I-MR: {col}","params":{"col":col},"result":r2,"chart_data":r2})
print(f"[I-MR] {col}: CL={r2['i_chart']['cl']:.4f}")

# 3. Capability: wide[1]
if len(wide)>1:
    col,data = wide[1][0], get(wide[1])
else:
    col,data = wide[0][0], get(wide[0])
usl,lsl = data.mean()+3*data.std(), max(data.mean()-3*data.std(),0.001)
r3 = normal_cap.analyze(data,usl,lsl)
analyses.append({"analysis_type":f"Capability: {col}","params":{"col":col,"usl":round(usl,4),"lsl":round(lsl,4)},"result":r3,"chart_data":r3})
print(f"[Capability] {col}: Cpk={r3['capability']['cpk']:.4f}, {r3['capability']['grade']}")

# 4. Capability: prec[2]
idx = 2 if len(prec)>2 else 1
col,data = prec[idx][0], get(prec[idx])
usl4,lsl4 = data.mean()+4*data.std(), data.mean()-4*data.std()
r4 = normal_cap.analyze(data,usl4,lsl4)
analyses.append({"analysis_type":f"Capability: {col}","params":{"col":col,"usl":round(usl4,4),"lsl":round(lsl4,4)},"result":r4,"chart_data":r4})
print(f"[Capability2] {col}: Cpk={r4['capability']['cpk']:.4f}")

# 5. Bias: prec[3]
idx = 3 if len(prec)>3 else min(len(prec)-1,2)
col,data = prec[idx][0], get(prec[idx])
ref = data.mean()
r5 = linearity_bias.analyze_bias(data,ref)
analyses.append({"analysis_type":f"Bias: {col}","params":{"col":col,"ref":round(ref,4)},"result":r5,"chart_data":r5})
print(f"[Bias] {col}: bias_mean={r5['mean_bias']:.6f}, sig={r5['is_significant']}")

# 6. t-Test: general[3] vs general[4]
if len(gen)>=5:
    g1,g2 = get(gen[3]), get(gen[4])
    n = min(len(g1),len(g2))
    r6 = t_tests.two_sample(g1[:n], g2[:n])
    analyses.append({"analysis_type":f"t-Test: {gen[3][0]} vs {gen[4][0]}","params":{},"result":r6,"chart_data":r6})
    print(f"[t-Test] p={r6['p_value']:.6f}, sig={r6['is_significant']}")

# ── 多格式报告 ──
print(f"\n--- Reports ---")
x = os.path.join(OUT,"CO401_Round2_Report.xlsx")
w = os.path.join(OUT,"CO401_Round2_Report.docx")

ExcelReport().generate(analyses,x)
print(f"[Excel] {x}")
WordReport().generate(analyses,w)
print(f"[Word] {w}")
for f in [x,w]:
    print(f"  {os.path.basename(f)}: {os.path.getsize(f)/1024:.1f} KB")
print("Done!")
