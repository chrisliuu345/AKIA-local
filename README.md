## 功能总览

### 质量分析 (6 模块)

| 模块 | 功能 |
|------|------|
| **SPC 控制图** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 规则 |
| **过程能力** | 正态/非正态(Box-Cox) / 组间组内 · Cp/Cpk/Pp/Ppk/PPM |
| **MSA** | 量具 R&R (交叉/嵌套) · 偏倚/线性 · 属性一致性 |
| **假设检验** | t检验 · ANOVA · 正态性 · 方差齐性 · **非参数检验** (MWU/Wilcoxon/Kruskal) |
| **DOE** | 全因子/2^k · 响应曲面 CCD · Box-Behnken |
| **回归分析** | 线性/多元 · R² · 残差诊断 · 相关矩阵热力图 |

### IE 工业工程 (7 模块)

| 模块 | 功能 |
|------|------|
| 工时研究 | 标准工时 · 评比系数 · 宽放率 · 能力 vs 节拍 |
| 工作抽样 | 比率分析 · 置信区间 · 利用率 |
| 线平衡 | LPT 平衡 · 瓶颈识别 · 山积图 |
| **OEE** | A×P×Q · 损失分解 · 世界级/良好/落后分级 |
| VSM | 价值流图 · VA/NVA · 前置时间 |
| **人机配合** | Worker-Machine 时间线图 (预设+可编辑) |
| **标准作业组合票** | 手动/自动/步行堆叠柱状图 |

### 工程工具 (5 模块)

| 模块 | 功能 |
|------|------|
| **可靠性** | Weibull 2P/3P MLE · MTBF/MTTR · **ALT 加速寿命** (Arrhenius/逆幂律) |
| **鱼骨图** | 交互式 QGraphicsView · 3层嵌套 · 拖动/双击/右键 |
| **帕累托图** | 二层钻取 · Top-N · 阈值线 |
| **FMEA** | RPN=S×O×D · 风险着色 · PFMEA/DFMEA |
| 控制计划 | 9列模板 · Excel 导出 |

### 图表工具 (4 模块)

15 种图表: 直方图/箱线图/散点图/帕累托/概率图/矩阵图/残差图/主效应/交互/等值线/3D曲面/时间序列/气泡图/雷达图/瀑布图 + 工序能力对比 + 多系列趋势 + 统计摘要面板

### 工作表工具 (3 模块)

合并 (追加/JOIN/批量) · 拆分 (按列/行/条件/分组) · LPA 分层审核表

### 数据工具 + 抽样检验 (2 模块)

AQL 查表 (GB/T 2828.1) · 随机/分层/系统抽样 · 序贯检验 · 数据生成器 (7分布) · 格式转换 · 异常值检测 (IQR/Z/Grubbs)

---

## 快速开始

### 方式一: 便携版 (推荐)

下载 `QA-Tool-v2.0.exe` (195MB 单文件)，双击运行。无需 Python 环境，无需安装。

### 方式二: 源码运行

```bash
# 要求 Python 3.11+
pip install PySide6 pandas numpy scipy matplotlib scikit-learn statsmodels reportlab openpyxl
python main.py
```

### 默认登录

```
用户名: admin
密码:   admin
```

---

## 技术栈

| 层 | 技术 |
|------|------|
| UI | PySide6 (Qt) · Fusion 暗色主题 · 全局 QSS |
| 数值计算 | NumPy · SciPy · pandas |
| 机器学习 | scikit-learn (RandomForest) · SHAP |
| 图表 | matplotlib · seaborn |
| 报告 | reportlab (PDF) · python-docx (Word) · openpyxl (Excel) |
| AI | Ollama · OpenAI 兼容 API · char-ngram TF-IDF RAG |
| 认证 | PBKDF2-SHA256 (150K rounds) |
| 打包 | PyInstaller (单文件 .exe) |

---

## 项目结构

```
├── main.py              # 入口 + Splash 加载
├── analysis/            # 分析引擎 (14 模块)
│   ├── spc/             # SPC 控制图 (9种 + Nelson规则)
│   ├── capability/      # 过程能力 (3种)
│   ├── msa/             # 测量系统分析 (3种)
│   ├── hypothesis/      # 假设检验 + 非参数
│   ├── doe/             # 实验设计 (4种)
│   ├── regression/      # 回归分析
│   ├── ie/              # IE 工业工程 (5种)
│   ├── reliability/     # 可靠性 (Weibull/MTBF/ALT)
│   ├── quality/         # 鱼骨图引擎
│   ├── charts/          # 图表生成器 (15种)
│   └── ai/              # AI 根因分析 (SHAP)
├── core/                # 核心引擎 (17 模块)
│   ├── auth.py          # 4级角色 + PBKDF2 认证
│   ├── data_loader.py   # Excel/CSV 加载
│   ├── data_profiler.py # 智能诊断 (20+推荐类型)
│   ├── knowledge_base.py # TF-IDF RAG (99条目)
│   ├── llm_client.py    # Ollama + OpenAI 双后端
│   ├── plugin_manager.py # 插件系统
│   ├── sampling_engine.py # GB/T 2828.1 AQL
│   └── ...
├── ui/                  # PySide6 界面
│   ├── tabs/            # 30 个分析 Tab
│   ├── dialogs/         # 15 个对话框
│   ├── widgets/         # Toast/鱼骨图画布
│   └── theme.py         # 暗色主题 + 字体常量
├── config/              # 配置 + 知识库 + 模板
├── locales/             # zh.json / en.json
├── plugins/             # 第三方插件
├── output/              # 报告引擎 (Word/Excel/PDF)
└── tests/               # 65 项 pytest
```

---

## 企业特性

- **多用户**: 4级角色 (admin/dept_admin/analyst/readonly) + 部门/班组
- **.qap 项目文件**: ZIP 打包，包含数据+图表+分析
- **SQL 直连**: MySQL/PostgreSQL/SQL Server
- **批量调度**: 定时任务 (每日/每小时/一次性)
- **共享项目**: 部门级 .qap 文件共享
- **审计日志**: `~/.qa_tool_audit.log`

---

## License

MIT

---

*Built with Python 3.14 + PySide6 · 65 tests passing*
