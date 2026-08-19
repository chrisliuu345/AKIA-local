"""
生成冒烟测试所需的合成测试数据 公司仪器测试数据.xlsx

用法: python tests/generate_test_data.py
输出: <项目根目录>/公司仪器测试数据.xlsx（6 个 Sheet）

该文件被 tests/run_all_tests.py 的 T06/T07/T42/T43 用例依赖，
缺失时会导致冒烟测试失败（代码审查 C18）。
"""
import os

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "公司仪器测试数据.xlsx")


def build_sheets():
    rng = np.random.default_rng(42)

    n1 = 50
    sheets = {}

    # 1. 质量数据 (QualityRecord)
    sheets["质量数据"] = pd.DataFrame({
        "零件编号": [f"P{i:03d}" for i in range(1, n1 + 1)],
        "测量值": np.round(rng.normal(10.0, 0.3, n1), 3),
        "上规格": [10.5] * n1,
        "下规格": [9.5] * n1,
    })

    # 2. SPC控制图数据（含纯数值列，满足 DataParser 的 numeric_columns 检测）
    n2 = 100
    sheets["SPC控制图数据"] = pd.DataFrame({
        "样本号": list(range(1, n2 + 1)),
        "温度": np.round(rng.normal(25.0, 1.5, n2), 2),
        "压力": np.round(rng.normal(101.0, 2.0, n2), 2),
    })

    # 3. 工序表 (Process)
    sheets["工序表"] = pd.DataFrame({
        "工序编号": ["OP1", "OP2", "OP3", "OP4", "OP5", "OP6"],
        "工序名称": ["下料", "车削", "铣削", "钻孔", "打磨", "装配"],
        "标准工时": [45.0, 60.0, 30.0, 25.0, 40.0, 55.0],
        "设备": ["锯床", "车床", "铣床", "钻床", "砂轮机", "装配台"],
    })

    # 4. 时间观测 (TimeObservation)
    n4 = 20
    ops = ["张三", "李四", "王五"]
    sheets["时间观测"] = pd.DataFrame({
        "工序": ["OP1"] * n4,
        "操作员": [ops[i % 3] for i in range(n4)],
        "循环时间": np.round(rng.normal(50.0, 5.0, n4), 1),
        "观测次数": [5] * n4,
    })

    # 5. 设备清单 (Resource)
    sheets["设备清单"] = pd.DataFrame({
        "设备编号": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"],
        "设备名称": ["车床", "铣床", "钻床", "磨床", "冲床", "焊接机", "注塑机", "检测台"],
        "可用时间": [480] * 8,
        "停机时间": [30, 45, 20, 35, 40, 25, 50, 15],
    })

    # 6. 物流数据 (MaterialFlow)
    sheets["物流数据"] = pd.DataFrame({
        "起点": ["OP1", "OP2", "OP3", "OP4", "OP5", "OP1", "OP2", "OP3", "OP4", "OP5", "OP1", "OP2"],
        "终点": ["OP2", "OP3", "OP4", "OP5", "OP6", "OP3", "OP4", "OP5", "OP6", "OP1", "OP4", "OP5"],
        "距离": [12.0, 8.0, 15.0, 6.0, 10.0, 14.0, 9.0, 11.0, 7.0, 13.0, 16.0, 5.0],
        "批量": [100] * 12,
    })

    return sheets


def main():
    sheets = build_sheets()
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    print(f"已生成 {OUTPUT}")
    print(f"共 {len(sheets)} 个 Sheet: {list(sheets.keys())}")


if __name__ == "__main__":
    main()
