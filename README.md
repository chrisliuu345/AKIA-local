# QA-Tool — 工业工程与质量分析工具

> [中文](README.md) | [English](README.en.md)

基于 Python 3.14 + PySide6 的桌面应用，面向质量工程（QE）与工业工程（IE）分析：35 个分析模块、AI 智能洞察、完整报告输出，并支持 ESP32 系列硬件数据采集与设备监控。

<img width="1280" height="800" alt="{20844337-54A4-41EC-B974-20397A2571B1}" src="https://github.com/user-attachments/assets/6d4b7fbb-993b-4030-8fc4-f7c3db5ce4dd" />

---

## 快速开始

### 方式 1：安装器（推荐）

下载 `QA-Tool-Setup-3.1.0.exe`，安装到 Program Files。安装时可选择是否包含 ESP-32 硬件拓展。

### 方式 2：便携版

下载 `QA-Tool-v3.1.0-portable.zip`，解压后直接运行 `QA-Tool.exe`，无需安装。

### 方式 3：源码运行

```bash
# 需要 Python 3.11+
pip install -r requirements.txt
python main.py
```

### 默认登录

```
用户名: admin
密码: admin
```

<img width="274" height="168" alt="{F6DD1BCE-DBE8-4CBF-97AE-EA87F4837AD2}" src="https://github.com/user-attachments/assets/a6f3746c-56a3-4562-b0f1-acf661e5f9a0" />

---

## 核心功能

### 质量分析

| 模块 | 能力 |
|------|------|
| **SPC 控制图** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 条判异规则 |
| **过程能力** | 正态 / 非正态（Box-Cox）/ Between-Within · Cp/Cpk/Pp/Ppk/PPM |
| **MSA 测量系统** | Gauge R&R（交叉/嵌套）· 偏倚/线性 · 属性一致性 · Type1 |
| **假设检验** | t 检验 · ANOVA · 正态性 · 方差齐性 · 非参数 · 等价检验 |
| **DOE 试验设计** | 全因子/部分因子 · CCD/Box-Behnken · Plackett-Burman · DSD · 田口 · 混合设计 · **Power & Sample Size** |
| **回归分析** | 线性 / 多元 · R² · 残差诊断 · 相关性热图 |

### IE 工业工程

| 模块 | 能力 |
|------|------|
| 时间研究 | 标准时间 · 评比系数 · 宽放 · 产能 vs 节拍 |
| 工作抽样 | 比率分析 · 置信区间 · 稼动率 |
| 线平衡 | LPT 平衡 · 瓶颈识别 · 山积图 |
| **OEE** | A×P×Q · 损失分解 · 世界级/良好/一般分级 |
| VSM 价值流 | 价值流图 · VA/NVA · 生产周期 |
| **SMED** | 快速换模 · 内外作业分离 · 甘特时间线 · 改善前后对比 |
| **TPM** | 全面生产维护 · OEE / MTBF / MTTR · 六大损失 |
| **8D** | 八项纪律问题解决 · D1-D8 分步向导 · 鱼骨图 |
| **PPAP** | 生产件批准程序 · 18 项检查清单 · 尺寸 Cp/Cpk |

### 工程工具

| 模块 | 能力 |
|------|------|
| **可靠性** | Weibull 2P/3P MLE · MTBF/MTTR · ALT（Arrhenius / 逆幂律） |
| **鱼骨图** | 交互式 3 级嵌套 · 拖拽 / 双击 / 右键 |
| **柏拉图** | 二级钻取 · Top-N · 阈值线 |
| **FMEA** | RPN=S×O×D · 风险着色 · PFMEA/DFMEA · 控制计划 |
| **图表** | 15 种图表：直方图 / 箱线图 / 散点图 / 柏拉图 / 概率图 / 残差图 / 主效应图 / 等高线图 / 3D 曲面 / 时序图 / 气泡图 / 雷达图 / 瀑布图 |

### 数据与报告

| 模块 | 能力 |
|------|------|
| **数据工具** | 合并 / 拆分 · AQL 抽样（GB/T 2828.1）· 数据生成器（7 种分布）· 异常值检测 |
| **报告系统** | 5 套内置 HTML 模板 · 导出 PDF / Word / HTML · 图表 base64 内联 |
| **AI 助手** | Ollama 本地模型 + OpenAI 兼容 API · 知识库 RAG · 根因分析 |

### 硬件扩展

| 模块 | 能力 |
|------|------|
| **设备监控** | ESP32/MaixCAM 设备卡片 · 自动发现 · 实时数据预览 · 数据导入 |
| **ESP32-IN** | 7 通道采集（DS18B20 + 6×ADC）· MicroPython 固件 |
| **ESP32-OUT** | 执行设备（LED/继电器/舵机）· 指令下发 ACK 应答 |
| **配置门控** | `esp32_extension` 开关，可关闭硬件拓展 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| UI | PySide6 (Qt) · Fusion 深色主题 · 全局 QSS |
| 数值 | NumPy · SciPy · pandas |
| ML | scikit-learn (RandomForest) · SHAP |
| 图表 | matplotlib · seaborn |
| 报告 | reportlab (PDF) · python-docx (Word) · openpyxl (Excel) |
| AI | Ollama · OpenAI 兼容 API · char-ngram TF-IDF RAG |
| 认证 | Ed25519 离线许可 · 硬件指纹绑定 |
| 硬件 | pyserial · MicroPython (ESP32, v1.20.0) |
| 打包 | PyInstaller (onedir) + Inno Setup 安装器 |

---

## 项目结构

```
├── main.py              # 入口 + Splash 加载
├── analysis/            # 分析引擎（14 个模块）
│   ├── spc/             # SPC 控制图（12 种 + Nelson 规则）
│   ├── capability/      # 过程能力（正态/非正态/Johnson变换）
│   ├── msa/             # 测量系统分析（Gage R&R/Type1/属性一致性）
│   ├── hypothesis/      # 假设检验 + 非参数 + 等价检验
│   ├── doe/             # 试验设计（PB/DSD/部分因子/田口/混合/Power）
│   ├── regression/      # 回归分析
│   ├── ie/              # IE 工业工程（SMED/TPM/OEE/VSM）
│   ├── reliability/     # 可靠性（Weibull/MTBF/ALT）
│   ├── quality/         # 8D/PPAP/鱼骨图引擎
│   ├── charts/          # 图表生成器（15 种）
│   └── ai/              # AI 根因分析（SHAP）
├── core/                # 核心引擎
│   ├── devices/         # ESP32 设备框架
│   ├── llm_client.py    # LLM 双后端（Ollama + OpenAI）
│   ├── knowledge_base.py # TF-IDF RAG（124 条）
│   └── plugin_manager.py # 插件系统
├── ui/                  # PySide6 UI
│   ├── tabs/            # 35 个分析 Tab
│   ├── dialogs/         # 对话框（设置/导入/Power分析）
│   └── theme.py         # 深色主题
├── config/              # 配置 + 知识库 + 模板
├── output/              # 报告引擎（Word/Excel/PDF/HTML）
├── firmware/            # ESP32 MicroPython 固件
└── tests/               # 857 个 pytest 测试
```

---

## 企业特性

- **离线许可**: Ed25519 签名 + 硬件指纹绑定 + AES-256 加密
- **.qap 项目文件**: 含数据 + 图表 + 分析的 ZIP 打包项目
- **SQL 直连**: MySQL / PostgreSQL / SQL Server
- **批量调度**: 计划任务（每日 / 每小时 / 一次性）
- **审计日志**: 操作记录追踪

---

## 版本历史

| 版本 | 亮点 |
|------|------|
| **v3.1.0** | DOE 全链路：PB/DSD/部分因子/田口/混合设计 + Power & Sample Size 引擎 |
| **v3.0.0** | 稳定化里程碑 · Info 清零 · 性能基线 · 624 tests |
| **v2.9.0** | 离线许可系统（Ed25519）· Nuitka 构建 |
| **v2.8.0** | 五链贯通（FMEA→控制计划→SPC→PPAP→8D） |
| **v2.7.0** | 统计引擎深化：Type1/Hotelling T²/TOST/分布拟合 |
| **v2.6.0** | ESP32 设备监控 · 安装器 · 278 tests |
| **v2.0.0** | 初始发布：28 tabs · AI 助手 · 插件系统 |

---

## 许可证

本项目为闭源商业软件，未经授权不得复制、修改或分发。

© 2026 QA-Tool. All rights reserved.

---

*基于 Python 3.14 + PySide6 构建 · 688 测试通过 · 35 个分析 Tab*
