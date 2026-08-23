# QA-Tool — 工业工程与质量分析工具

> [中文](README.md) | [English](README.en.md)

基于 Python 3.14 + PySide6 的桌面应用，面向质量工程（QE）与工业工程（IE）分析：35 个分析模块、AI 智能洞察、完整报告输出，并支持 ESP32 系列硬件数据采集与设备监控。

<img width="1280" height="800" alt="{20844337-54A4-41EC-B974-20397A2571B1}" src="https://github.com/user-attachments/assets/6d4b7fbb-993b-4030-8fc4-f7c3db5ce4dd" />

## 功能特性

### 质量分析（6 个模块）

| 模块 | 能力 |
|------|------|
| **SPC 控制图** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 条判异规则 |
| **过程能力** | 正态 / 非正态（Box-Cox）/ Between-Within · Cp/Cpk/Pp/Ppk/PPM |
| **MSA 测量系统分析** | Gauge R&R（交叉/嵌套）· 偏倚/线性 · 属性一致性 |
| **假设检验** | t 检验 · ANOVA · 正态性 · 方差齐性 · **非参数检验**（MWU/Wilcoxon/Kruskal） |
| **DOE 试验设计** | 全因子 / 2^k · 响应曲面 CCD · Box-Behnken |
| **回归分析** | 线性 / 多元 · R² · 残差诊断 · 相关性热图 |


### IE 工业工程（7 个模块）

| 模块 | 能力 |
|------|------|
| 时间研究 | 标准时间 · 评比系数 · 宽放 · 产能 vs 节拍 |
| 工作抽样 | 比率分析 · 置信区间 · 稼动率 |
| 线平衡 | LPT 平衡 · 瓶颈识别 · 山积图 |
| **OEE** | A×P×Q · 损失分解 · 世界级/良好/一般分级 |
| VSM 价值流 | 价值流图 · VA/NVA · 生产周期 |
| **人机分析** | 人机时间线图（预设 + 可编辑） |
| **标准作业** | 手动 / 自动 / 步行堆叠柱状图 |

### 工程工具（5 个模块）

| 模块 | 能力 |
|------|------|
| **可靠性** | Weibull 2P/3P MLE · MTBF/MTTR · **ALT**（Arrhenius / 逆幂律） |
| **鱼骨图** | 交互式 QGraphicsView · 3 级嵌套 · 拖拽 / 双击 / 右键 |
| **柏拉图** | 二级钻取 · Top-N · 阈值线 |
| **FMEA** | RPN=S×O×D · 风险着色 · PFMEA/DFMEA |
| 控制计划 | 9 列模板 · Excel 导出 |

### 图表工具（4 个模块）

15 种图表：直方图 / 箱线图 / 散点图 / 柏拉图 / 概率图 / 矩阵图 / 残差图 / 主效应图 / 交互图 / 等高线图 / 3D 曲面 / 时序图 / 气泡图 / 雷达图 / 瀑布图 + 能力对比 + 多序列趋势 + 统计汇总面板

### 工作表工具（3 个模块）

合并（追加 / JOIN / 批量）· 拆分（按列 / 行 / 条件 / 分组）· LPA 稽核表

### 数据工具与抽样（2 个模块）

AQL 抽样（GB/T 2828.1 / ANSI/ASQ Z1.4）· 随机 / 分层 / 系统抽样 · 序贯检验 · 数据生成器（7 种分布）· 格式转换 · 异常值检测（IQR / Z / Grubbs）

### IE 工程工具（v2.2 新增）

| 模块 | 能力 |
|------|------|
| **SMED** | 快速换模 · 内外作业分离 · 甘特时间线 · 改善前后对比 |
| **8D** | 八项纪律问题解决 · D1-D8 分步向导 · 鱼骨图（D4）· PDF/Markdown 导出 |
| **TPM** | 全面生产维护 · OEE / MTBF / MTTR · 六大损失 · 柏拉图 + 日历 |
| **PPAP** | 生产件批准程序 · 18 项检查清单 · 尺寸 Cp/Cpk · 提交等级 |

### 报告系统（v2.3 新增）

| 功能 | 说明 |
|------|------|
| **模板引擎** | 5 套内置 HTML 模板（日报 / 月度 SPC / 稽核 / 8D / PPAP） |
| **模板对话框** | 预览 + 导出 PDF / Word / HTML |
| **HTML 导出** | 图表 base64 内联的自包含离线报告 |

### 硬件扩展：ESP32 设备监控（v2.5/v2.6 新增）

| 功能 | 说明 |
|------|------|
| **设备监控 Tab** | 设备卡片（状态/心跳/端口）、自动发现、实时数据预览（20 行）、事件日志、输出控制台、识别记录 |
| **停止/继续监控** | 卡片双按钮，停止后跨刷新保持，随时恢复 |
| **数据导入** | 设备采样一键导入到其他分析 Tab |
| **ESP32-IN** | 7 通道采集（DS18B20 + 6×ADC），MicroPython 固件 v1.1.0 实测运行 |
| **ESP32-OUT** | 执行设备（LED/继电器/舵机），指令下发 ACK 应答 |
| **MaixCAM** | 视觉识别（规划中） |
| **配置门控** | `esp32_extension` 开关，可关闭硬件拓展 |

---

## 快速开始

### 方式 1：安装器（推荐）

下载 `QA-Tool-Setup-2.6.0.exe`（135MB，Inno Setup 中文安装向导），安装到 Program Files。安装时可选择是否包含 ESP-32 硬件拓展。

### 方式 2：便携版

下载 `QA-Tool-v2.6.0-portable.zip`（约 230MB），解压后直接运行 `QA-Tool.exe`，无需安装。

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

## 技术栈

| 层级 | 技术 |
|------|------|
| UI | PySide6 (Qt) · Fusion 深色主题 · 全局 QSS |
| 数值 | NumPy · SciPy · pandas |
| ML | scikit-learn (RandomForest) · SHAP |
| 图表 | matplotlib · seaborn |
| 报告 | reportlab (PDF) · python-docx (Word) · openpyxl (Excel) |
| AI | Ollama · OpenAI 兼容 API · char-ngram TF-IDF RAG |
| 认证 | PBKDF2-SHA256 (150K 轮) |
| 硬件 | pyserial · MicroPython (ESP32, v1.20.0) |
| 打包 | PyInstaller (onedir) + Inno Setup 安装器 |

---

## 项目结构

```
├── main.py              # 入口 + Splash 加载
├── analysis/            # 分析引擎（14 个模块）
│   ├── spc/             # SPC 控制图（9 种 + Nelson 规则）
│   ├── capability/      # 过程能力（3 种）
│   ├── msa/             # 测量系统分析（3 种）
│   ├── hypothesis/      # 假设检验 + 非参数
│   ├── doe/             # 试验设计（4 种）
│   ├── regression/      # 回归分析
│   ├── ie/              # IE 工业工程（SMED, TPM）
│   ├── reliability/     # 可靠性（Weibull/MTBF/ALT）
│   ├── quality/         # 8D 引擎, PPAP 引擎, 鱼骨图引擎
│   ├── charts/          # 图表生成器（15 种）
│   └── ai/              # AI 根因分析（SHAP）
├── core/                # 核心引擎（含硬件设备）
│   ├── auth.py          # 4 级 RBAC + PBKDF2 认证
│   ├── devices/         # ESP32 设备框架（协议/传输/发现/注册表）
│   ├── data_loader.py   # Excel/CSV 加载器
│   ├── data_profiler.py # 智能诊断（20+ 建议类型）
│   ├── knowledge_base.py # TF-IDF RAG（124 条）
│   ├── llm_client.py    # Ollama + OpenAI 双后端
│   ├── plugin_manager.py # 插件系统
│   ├── report_templates.py # 模板引擎（5 套内置）
│   ├── sampling_engine.py # GB/T 2828.1 AQL
│   └── ...
├── ui/                  # PySide6 UI
│   ├── tabs/            # 35 个分析 Tab
│   ├── dialogs/         # 16 个对话框
│   ├── widgets/         # Toast / 鱼骨图画布
│   └── theme.py         # 深色主题 + 字体常量
├── config/              # 配置 + 知识库 + 模板
│   ├── templates/       # HTML 报告模板
│   └── knowledge/       # 知识库 JSON 文件
├── locales/             # zh.json（中文 UI 字符串）
├── firmware/            # ESP32 MicroPython 固件源码（esp32_in/esp32_out）
├── plugins/             # 第三方插件
├── output/              # 报告引擎（Word/Excel/PDF/HTML）
├── packaging/           # Inno Setup 安装脚本
└── tests/               # 278 个 pytest 测试
```

---

## 企业特性

- **多用户**: 4 级角色（admin / dept_admin / analyst / readonly）+ 部门/团队
- **.qap 项目文件**: 含数据 + 图表 + 分析的 ZIP 打包项目
- **SQL 直连**: MySQL / PostgreSQL / SQL Server
- **批量调度**: 计划任务（每日 / 每小时 / 一次性）
- **共享项目**: 部门级 .qap 文件共享
- **审计日志**: `~/.qa_tool_audit.log`

---

## 版本历史

| 日期 | 版本 | 亮点 |
|------|---------|------------|
| 2026-08-18 | **v2.6.0** | ESP32-IN 部署拓展（固件 v1.1.0 实机验证）· 设备监控 Tab 35（停止/继续监控、20 行预览、数据导入）· ESP-32 配置门控 · onedir 打包 + Inno Setup 安装器 · 278 tests |
| 2026-08-15 | **v2.4.1** | 自适应看板卡片网格 · 淡入/数字滚动/交叉淡化动画 · 大屏宽高比与可读性修复 · 批量分析防护 · 215 tests |
| 2026-08-13 | **v2.4** | 看板增强：统一 KPI 提取器 · 实时刷新 · 卡片布局 · 公式编辑器 · 车间看板模式 |
| 2026-08-12 | v2.3 | 报告模板引擎 · 模板对话框 · HTML 自包含导出 · 菜单重构 |
| 2026-08-10 | v2.2 | SMED · 8D · TPM · PPAP（4 个新工程工具）· 32 tabs |
| 2026-08-10 | v2.1 | 代码审计 · AI 增强 · 懒加载 · 一键分析 · 87 tests |
| 2026-08-04 | v2.0 | 初始发布：28 tabs · 65 tests · AI 助手 · 插件系统 |

---

## 许可证

本项目为闭源商业软件，未经授权不得复制、修改或分发。

© 2026 QA-Tool. All rights reserved.

---

## 使用指南

详细使用说明请参阅 [使用指南文档](使用指南.docx)。

---

*基于 Python 3.14 + PySide6 构建 · 450+ 测试通过 · 35 个分析 Tab*
