# QA-Tool

> 个人订阅级AI桌面工业分析平台，融合 SPC + MSA + DOE + IE + 可靠性 + AI 分析

[中文](README.md) | [English](README.en.md)

---

## 快速开始

### Linux (AppImage)

```bash
chmod +x QA-Tool-3.7.2-x86_64.AppImage
./QA-Tool-3.7.2-x86_64.AppImage
```

### Linux (.deb)

```bash
sudo dpkg -i qa-tool_3.7.2_amd64.deb
qa-tool
```

### 源码运行

```bash
git clone https://github.com/chrisliuu345/QA-Tool.git
cd QA-Tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

需要 Python 3.11+

---

## 核心功能

### 统计分析

| 模块 | 能力 |
|------|------|
| **SPC 控制图** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 规则 |
| **过程能力** | 正态 / 非正态 / Johnson / Sixpack · Cp/Cpk/Pp/Ppk |
| **MSA 测量系统** | Gage R&R · EMP 方法 · 属性一致性 · Type 1 · 不确定度预算 |
| **假设检验** | t 检验 · ANOVA · 正态性 · 非参数 · 等价检验 |
| **DOE 试验设计** | 全/部分因子 · CCD · Box-Behnken · PB · DSD · 田口 · 混合设计 |
| **可靠性** | Weibull 2P/3P/4P · KM 生存曲线 · Cox 回归 · ALT · RBD |
| **时间序列** | ARIMA · 指数平滑 · 季节分解 · 预测 |

### IE 工业工程

| 模块 | 能力 |
|------|------|
| **时间研究** | 秒表法 · 评比系数 · 宽放 · 标准时间 |
| **OEE** | 设备综合效率 · 损失分解 · 世界级分级 |
| **SMED** | 快速换模 · 内外作业分离 · 改善前后对比 |
| **TPM** | 全面生产维护 · 六大损失分析 |
| **线平衡** | LPT 平衡 · 瓶颈识别 · 山积图 |
| **VSM** | 价值流图 · VA/NVA · 生产周期 |

### 质量工具

| 模块 | 能力 |
|------|------|
| **8D** | 八项纪律问题解决 · D1-D8 分步向导 |
| **FMEA** | RPN=S×O×D · 风险着色 · PFMEA/DFMEA |
| **PPAP** | 生产件批准程序 · 18 项检查清单 |
| **控制计划** | FMEA → 控制计划 → SPC 五链贯通 |

### AI 与报告

| 模块 | 能力 |
|------|------|
| **QAM Harness** | AI Agent：30 个本地工具调用（SPC/能力/MSA/假设检验/DOE/回归/可靠性/时间序列/IE/成本/实时/五链/根因）+ 离线工具模式 · BYOK 云供应商（OpenAI/Claude/Gemini/DeepSeek/Z.ai/KIMI + 自定义端点）· 密钥加密 + 云调用隐私门 · 知识库 RAG |
| **插件接口 v2** | 外部插件独立开发/发布：pip entry point 或用户目录加载 · 贡献 Tab / Agent 工具 / 设置页 · 能力与依赖声明 · 信任模型（如独立项目 [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion)） |
| **图表** | 15+ 种图表 · 深色主题 · 中文字体 |
| **报告** | PDF / Word / Excel / HTML · 图表内联 |

### 硬件扩展

| 模块 | 能力 |
|------|------|
| **设备监控** | ESP32 / MaixCAM · 自动发现 · 实时数据 |
| **ESP32** | 7 通道采集 · 执行器控制 · MicroPython 固件 |

### 实时监控与看板

| 模块 | 能力 |
|------|------|
| **实时 SPC** | 滚动窗口 I-MR/XBar-R · USL/LSL 规格线 · 滚轮缩放 · Nelson 判异 |
| **产线拓扑** | plant.json 可视化配置（表格编辑 + 模板导入导出）· 工位状态灯 |
| **实时 OEE** | 节拍 → 真实性能 P · 停机原因码 · 班次日历 |
| **成本损失** | 超规格量 × 单件损失 + 停机成本（Cost Inspector 思路） |
| **告警中心** | 预告/警告/严重分级 · 确认与审计留存 · 邮件 / webhook / 联动动作 |
| **看板部署** | 可选 API token 鉴权 · host 绑定 · 连接器健康页与自动重连 |
| **数据保留** | 分钟降采样（avg/min/max/count）· 原始点与聚合点分档保留期 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| UI | PySide6 (Qt) · Fusion 深色主题 |
| 数值 | NumPy · SciPy · pandas · scikit-learn |
| 图表 | matplotlib · seaborn |
| 报告 | reportlab · python-docx · openpyxl |
| AI | Ollama · OpenAI 兼容 API · TF-IDF RAG |
| 硬件 | pyserial · MicroPython (ESP32) |
| 实时看板 | FastAPI · uvicorn · websockets（需 `pip install -r requirements-server.txt`，可选） |
| 构建 | PyInstaller (onedir) · Inno 安装器 · AppImage · .deb |

---

## 项目结构

```
main.py                # 入口
analysis/              # 分析引擎 (14 模块)
├── spc/               # SPC 控制图
├── capability/        # 过程能力 + Sixpack + 自动能力
├── msa/               # 测量系统 (Gage R&R / EMP / 属性一致性)
├── hypothesis/        # 假设检验
├── doe/               # 试验设计
├── reliability/       # 可靠性分析
├── time_series/       # 时间序列
├── ie/                # IE 工业工程
├── charts/            # 图表生成器
└── ai/                # AI 根因分析
core/                  # 核心引擎
ui/                    # PySide6 UI (37 个 Tab)
output/                # 报告引擎
tests/                 # 1000+ 测试
```

---

## 下载

从 [Releases](https://github.com/chrisliuu345/QA-Tool/releases) 下载最新版本。

---

## 许可证

闭源商业软件，未经授权不得复制、修改或分发。

© 2026 QA-Tool. All rights reserved.

---

*Python 3.14 + PySide6 · 1500+ 测试 · 36 个分析 Tab + 插件接口 v2*
