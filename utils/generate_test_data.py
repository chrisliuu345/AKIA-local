"""生成大型公司仪器测试数据表 — 覆盖SPC/Capability/MSA/DOE/Hypothesis"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
output_path = r"D:\AI-agent\projects\ie-quality-analyzer\公司仪器测试数据.xlsx"

writer = pd.ExcelWriter(output_path, engine="xlsxwriter")

# ═══════════════════════════════════════════════
# Sheet 1: SPC 控制图数据 (XBar-R / I-MR)
# ═══════════════════════════════════════════════
subgroup_size = 5
num_subgroups = 50
n_total = subgroup_size * num_subgroups

dates = [datetime(2026, 1, 1) + timedelta(hours=i * 2) for i in range(num_subgroups)]

# 过程均值10.00, 组内sigma=0.15, 组间sigma=0.05
within_noise = np.random.normal(0, 0.15, n_total)
between_shift = np.repeat(np.random.normal(0, 0.05, num_subgroups), subgroup_size)
measurements = 10.00 + within_noise + between_shift

# 在第30组加入异常偏移
measurements[29 * subgroup_size:(29 * subgroup_size + subgroup_size)] += 0.35

df_spc = pd.DataFrame({
    "日期": np.repeat(dates, subgroup_size),
    "批次号": np.repeat([f"B{str(i).zfill(4)}" for i in range(1, num_subgroups + 1)], subgroup_size),
    "子组序号": np.tile([1, 2, 3, 4, 5], num_subgroups),
    "孔径测量值_mm": np.round(measurements, 4),
    "USL": 10.50,
    "LSL": 9.50,
})
df_spc.to_excel(writer, sheet_name="SPC控制图数据", index=False)

# ═══════════════════════════════════════════════
# Sheet 2: 过程能力分析数据
# ═══════════════════════════════════════════════
n_cap = 300
cap_data = np.random.normal(10.00, 0.20, n_cap)
# 前段加一些偏移使得Cpk略低
cap_data[:60] += 0.18

df_cap = pd.DataFrame({
    "样品编号": [f"S{i:05d}" for i in range(1, n_cap + 1)],
    "检测时间": [datetime(2026, 3, 15, 8, 0) + timedelta(minutes=i * 3) for i in range(n_cap)],
    "内径_mm": np.round(cap_data, 4),
    "外径_mm": np.round(np.random.normal(25.00, 0.12, n_cap), 4),
    "厚度_mm": np.round(np.random.normal(3.00, 0.05, n_cap), 4),
    "硬度_HRC": np.round(np.random.normal(58.0, 1.2, n_cap), 1),
    "内径_USL": 10.60,
    "内径_LSL": 9.40,
    "外径_USL": 25.30,
    "外径_LSL": 24.70,
    "厚度_USL": 3.15,
    "厚度_LSL": 2.85,
    "线别": np.random.choice(["A线", "B线", "C线", "D线"], n_cap),
    "班次": np.random.choice(["早班", "中班", "晚班"], n_cap),
})
df_cap.to_excel(writer, sheet_name="过程能力分析", index=False)

# ═══════════════════════════════════════════════
# Sheet 3: MSA 量具R&R 数据
# ═══════════════════════════════════════════════
parts = np.repeat(range(1, 11), 6)  # 10个零件
operators = np.tile(np.repeat(["张三", "李四", "王五"], 2), 10)  # 3个操作员 x 2次重复
repeats = np.tile([1, 2], 30)

true_values = {i: 10.0 + (i - 1) * 0.02 for i in range(1, 11)}
part_means = np.array([true_values[p] for p in parts])
op_bias = {"张三": 0.003, "李四": -0.001, "王五": 0.005}
op_measurement_noise = np.array([np.random.normal(op_bias[op], 0.008) for op in operators])

measures = np.round(part_means + op_measurement_noise, 4)

df_msa = pd.DataFrame({
    "零件编号": [f"P{i:02d}" for i in parts],
    "操作员": operators,
    "重复次数": repeats,
    "测量值_mm": measures,
    "公差_mm": 0.40,
})
df_msa.to_excel(writer, sheet_name="MSA量具R&R", index=False)

# ═══════════════════════════════════════════════
# Sheet 4: DOE 因子实验数据 (2^3 全因子 + 3中心点)
# ═══════════════════════════════════════════════
doe_design = pd.DataFrame({
    "StdOrder": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "RunOrder":  [5, 2, 8, 1, 10, 3, 7, 11, 6, 4, 9],
    "温度_C":    [-1, 1, -1, 1, -1, 1, -1, 1, 0, 0, 0],
    "压力_bar":  [-1, -1, 1, 1, -1, -1, 1, 1, 0, 0, 0],
    "速度_rpm":  [-1, -1, -1, -1, 1, 1, 1, 1, 0, 0, 0],
    "Block":     [1]*8 + [2]*3,
})

# 响应 = 50 + 8*温度 + 5*压力 + 2*速度 + 3*温度*压力 + noise
response_doe = (
    50.0
    + 8.0 * doe_design["温度_C"]
    + 5.0 * doe_design["压力_bar"]
    + 2.0 * doe_design["速度_rpm"]
    + 3.0 * doe_design["温度_C"] * doe_design["压力_bar"]
    + np.random.normal(0, 1.5, len(doe_design))
)
doe_design["成品率_%"] = np.round(response_doe, 2)
df_doe = doe_design
df_doe.to_excel(writer, sheet_name="DOE因子实验", index=False)

# ═══════════════════════════════════════════════
# Sheet 5: 假设检验数据 (双样本/ANOVA)
# ═══════════════════════════════════════════════
n_hyp = 80

df_hyp = pd.DataFrame({
    "试样编号": [f"T{i:04d}" for i in range(1, n_hyp + 1)],
    "工艺A_强度_MPa": np.round(np.random.normal(520, 8, n_hyp), 1),
    "工艺B_强度_MPa": np.round(np.random.normal(527, 8, n_hyp), 1),
    "材料类型": np.random.choice(["合金X", "合金Y", "合金Z"], n_hyp),
    "热处理炉号": np.random.choice(["F1", "F2", "F3", "F4"], n_hyp),
    "硬度_HV": np.round(np.random.normal(210, 15, n_hyp), 0),
})
df_hyp.to_excel(writer, sheet_name="假设检验数据", index=False)

# ═══════════════════════════════════════════════
# Sheet 6: 分析要求 (模板参考)
# ═══════════════════════════════════════════════
df_req = pd.DataFrame({
    "参数": [
        "analysis_type", "data_sheet", "measurement_column",
        "subgroup_size", "usl", "lsl",
    ],
    "值_控制图": [
        "xbar_r", "SPC控制图数据", "孔径测量值_mm",
        "5", "10.50", "9.50",
    ],
    "值_能力分析": [
        "normal_capability", "过程能力分析", "内径_mm",
        "", "10.60", "9.40",
    ],
    "值_MSA": [
        "gage_rr_crossed", "MSA量具R&R", "测量值_mm",
        "", "", "",
    ],
    "值_DOE": [
        "factorial_design", "DOE因子实验", "成品率_%",
        "", "", "",
    ],
})
df_req.to_excel(writer, sheet_name="分析要求模板", index=False)

# ═══════════════════════════════════════════════
# Sheet 7: 大批量过程数据 (模拟真实产线长时间采集)
# ═══════════════════════════════════════════════
n_large = 2000

# 多个特征维度
large_data = {
    "采集时间": [datetime(2026, 6, 1, 8, 0) + timedelta(seconds=i * 45) for i in range(n_large)],
    "工位编号": np.random.choice([f"WS-{i:02d}" for i in range(1, 13)], n_large),
    "产品型号": np.random.choice(["M-A01", "M-A02", "M-B03", "M-C01"], n_large),
    "尺寸1_长度_mm": np.round(np.random.normal(150.00, 0.35, n_large), 3),
    "尺寸2_宽度_mm": np.round(np.random.normal(80.00, 0.25, n_large), 3),
    "尺寸3_高度_mm": np.round(np.random.normal(45.00, 0.15, n_large), 3),
    "重量_g": np.round(np.random.normal(320.0, 2.5, n_large), 1),
    "扭矩_Nm": np.round(np.random.normal(12.5, 0.8, n_large), 2),
    "表面粗糙度_Ra": np.round(np.abs(np.random.normal(0.8, 0.15, n_large)), 3),
    "电性能_mV": np.round(np.random.normal(1200, 35, n_large), 1),
    "密封性_合格": np.random.choice(["合格", "不合格"], n_large, p=[0.97, 0.03]),
    "外观_合格": np.random.choice(["合格", "不合格"], n_large, p=[0.99, 0.01]),
    "班次": np.random.choice(["白班", "夜班"], n_large),
    "操作员工号": np.random.choice(["OP001", "OP002", "OP003", "OP004", "OP005"], n_large),
    "设备编号": np.random.choice(["MC-101", "MC-102", "MC-103", "MC-104"], n_large),
    "环境温度_C": np.round(np.random.normal(23.0, 2.0, n_large), 1),
    "环境湿度_%": np.round(np.random.normal(55.0, 10.0, n_large), 1),
}

df_large = pd.DataFrame(large_data)
df_large.to_excel(writer, sheet_name="大批量过程数据", index=False)

writer.close()

# ── 打印摘要 ──
xl = pd.ExcelFile(output_path, engine="openpyxl")
total_rows = 0
for name in xl.sheet_names:
    df = pd.read_excel(xl, name)
    total_rows += len(df)
    print(f"  [{name}] {len(df)} 行 x {len(df.columns)} 列")

print(f"\n总计: {len(xl.sheet_names)} 个Sheet, {total_rows} 行数据")
print(f"\n文件: {output_path}")
