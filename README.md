# AKIA

> **AKIA（AKIM IE/Quality analyzer-local）**——个人订阅级 AI 桌面工业分析平台，
> 融合 SPC + MSA + DOE + IE + 可靠性 + AI 分析

[中文](README.md) | [English](README.en.md)

> **命名说明**：自 v4.2.0 起产品更名为 **AKIA（AKIM IE/Quality analyzer-local）**。
> v4.2.0 Release 中的 Linux AppImage 资产仍沿用旧文件名 `QA-Tool-4.2.0-x86_64.AppImage`
> （GitHub 资产无法追溯改名）；自 v4.3.0 起统一为 `AKIA-*`。
>
> **发布形态**：当前版本 **v4.4.0 闭环执行与效果验证** —— 源码 + Linux AppImage
> （`AKIA-4.4.0-x86_64.AppImage`，附 `.sha256` 校验文件）；Windows 安装包在 Windows 侧构建。

---

## 快速开始

最新发布为 v4.4.0，提供免装 Python 环境的离线运行包；Linux 侧为 **AppImage**（随 Release 发布），
Windows 侧为 **Inno Setup 安装包**（需在 Windows 机器上构建）：

| 版本 | 安装文件 | 适用系统 | 发布状态 | 安装方式 |
|------|----------|----------|----------|----------|
| **Linux AppImage** | `AKIA-4.4.0-x86_64.AppImage` | 任意 x86_64 Linux（Debian / Ubuntu / Fedora / elementary 等） | ✅ 随 [v4.4.0 Release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.4.0) 提供（附 `.sha256` 校验文件） | 免安装：赋予执行权限后直接运行 |
| **Windows 安装包** | `AKIA-Setup-4.4.0.exe` | Windows 10/11（64 位） | Windows 侧构建（`build_pyinstaller.py` + `packaging/AKIA-installer.iss`） | 双击 Inno Setup 向导安装，开始菜单/桌面启动 |

> Linux 仅发布 **AppImage** 单一格式（不再构建 `.deb`）；Debian/Ubuntu/Fedora 等发行版通用。

### Linux（AppImage，免安装）

```bash
# 从 v4.4.0 Release 下载 AppImage 与同名 .sha256 校验文件后
sha256sum -c AKIA-4.4.0-x86_64.AppImage.sha256
chmod +x AKIA-4.4.0-x86_64.AppImage
./AKIA-4.4.0-x86_64.AppImage
```

> 无 FUSE 的环境（容器 / 精简发行版）追加 `--appimage-extract-and-run` 参数即可解包运行。
> 从源码自行打包：`bash build_appimage.sh`（产物落在 `build/`）。

### Windows（安装包）

在 Windows 上执行 `python build_pyinstaller.py --onefile`，再用 Inno Setup 编译
`packaging/AKIA-installer.iss`，产物 `AKIA-Setup-4.4.0.exe` 双击按向导安装
（含开始菜单与桌面快捷方式）。

### 源码运行

> 依赖锁定：`requirements.lock` 是本机验证过的完整版本快照（CI 与发布门禁使用），
> `requirements*.txt` 保留宽松约束便于本地开发/升级。lock 需在**干净环境**由
> `requirements*.txt` 生成（当前快照含少量本机工具链/插件包，待联网环境收口重生成）。

```bash
git clone https://github.com/chrisliuu345/AKIA-local.git
cd AKIA-local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

需要 Python 3.11+

> **图形依赖可选**：matplotlib / seaborn 缺失不影响主界面与数据/分析/证据功能；
> 打开图表类 Tab 会提示安装（`pip install matplotlib seaborn`），完整依赖见 `requirements.txt`。

> **连接器可选依赖**：Modbus TCP / OPC UA / MQTT 与 SQL Server（pyodbc）按需安装：
> `pip install -r requirements-connectors.txt`。未安装时对应功能显示明确提示，
> 不会静默失败。

---

## 核心功能

### 统计分析

| 模块 | 能力 |
|------|------|
| **SPC 控制图** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA · **MEWMA** · **广义方差 \|S\|** · Hotelling T² + Nelson 8 规则 · **变点检测（PELT）** · **ARIMA 残差图** |
| **过程能力** | 正态 / 非正态 / Johnson / Sixpack · Cp/Cpk/Pp/Ppk |
| **MSA 测量系统** | Gage R&R · EMP 方法 · 属性一致性 · Type 1 · 不确定度预算 |
| **假设检验** | t 检验 · ANOVA · 正态性 · 非参数 · 等价检验 |
| **DOE 试验设计** | 全/部分因子 · CCD · Box-Behnken · PB · DSD · 田口 · 混合设计 |
| **可靠性** | Weibull 2P/3P/4P · KM 生存曲线 · Cox 回归 · ALT · RBD |
| **时间序列** | ARIMA · 指数平滑 · 季节分解 · 预测 |

### 预测分析与机器学习（v4.0.0）

| 模块 | 能力 |
|------|------|
| **AutoML 选模** | 线性/逻辑回归 · CART · 随机森林（OOB）· 梯度提升（内置 HistGradientBoosting，可选 XGBoost）· MARS；CV 排名与推荐 |
| **特征工程** | 缺失值 · 独热编码 · 分位数分箱 · 标准化；Pipeline 防泄漏 · 分层切分 |
| **模型评估** | R²/调整 R²/RMSE/MAE/MAPE · Accuracy/P/R/F1/AUC · 混淆矩阵 · ROC · K 折 CV · 学习曲线 · 残差诊断 |
| **解释与部署** | SHAP（自动降级原生/置换重要性）· 单样本解释 · `.qamodel` 保存/加载 · 预测导出 |
| **QAM Harness 工具** | `ml_prepare_data` · `ml_train` · `ml_automl` · `ml_evaluate` · `ml_explain` · `ml_predict` |

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
| **改善案例工作台** | 案例脊柱：基线测量 → 时间研究 → 线平衡瓶颈 → 改善方案 → 复测 → 配对检验 → 结论 → 标准草稿；每步留痕时间戳 · 数据引用 · 判定凭证 · 测量事件；**标准版本记录**（规格限/控制限/标准工时/组合票/控制计划条目 + 变更原因 + as-of 历史复判）；**证据链**（哈希链账本 · 证据视图/指纹重算/追溯码定位 · 可独立校验的证据包 · 脱敏分享包+泄漏扫描） |
| **闭环执行（v4.4.0）** | **告警自动立案 8D**（critical 同步立案 · 30 分钟冷却合并 · D6 数据门禁：关闭必须带复测数据）· **测量系统在线化**（滚动重复性/偏倚 · MPC 判异 · 健康分与漂移提示）· **可信抽样**（GB/T 2828.1 转移状态机 · 确定性抽样带种子与行指纹 · 方案留痕入证据账本 · 批检验面板）· **收益账本与 COPQ**（月度复算 · 防重复计入 · 置信门禁 · ROI）· **技能约束线平衡**（技能矩阵 + 人数/设备约束输出可执行排班）· **抽样透明化**（图表/趋势/画像抽样统一标注且可复现） |

### AI 与报告

| 模块 | 能力 |
|------|------|
| **QAM Harness** | AI Agent：37 个本地工具调用（SPC/能力/MSA/假设检验/DOE/回归/可靠性/时间序列/IE/成本/实时/五链/根因/机器学习）+ 离线工具模式 · BYOK 云供应商（OpenAI/Claude/Gemini/DeepSeek/Z.ai/KIMI + 自定义端点）· 密钥加密 + 云调用隐私门 · 知识库 RAG |
| **插件接口 v2.1** | 外部插件独立开发/发布：pip entry point 或用户目录加载 · 贡献 Tab / Agent 工具 / 设置页 / **测量数据源 `data_source`** · 能力与依赖声明 · 信任/超时/坏数据隔离（如独立项目 [AKIA-Vision-expansion](https://github.com/chrisliuu345/AKIA-Vision-expansion)；合同与示例见 [插件数据源合同](docs/plugin-data-source.md)） |
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
| 构建 | PyInstaller (onedir) · Inno 安装器 · AppImage（Linux 唯一格式） |

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
├── ai/                # AI 根因分析
└── ml/                # 预测分析与机器学习（AutoML/MARS/解释）
core/                  # 核心引擎
ui/                    # PySide6 UI (37 个 Tab + 插件 Tab)
output/                # 报告引擎
tests/                 # 2400+ 测试
```

---

## 下载

从 [Releases](https://github.com/chrisliuu345/AKIA-local/releases) 下载最新版本：

- `v4.4.0`（当前）— **闭环执行与效果验证**（B0–B8）：告警自动立案 8D / 测量系统在线化 /
  可信抽样（转移状态机 + 抽样决定留痕）/ 收益账本与 COPQ / 技能约束线平衡 / 抽样透明化
  （八链路端到端演示 `tools/demo_v44_case.py`）；Linux AppImage `AKIA-4.4.0-x86_64.AppImage`
  + 源码包（zip / tar.gz）；发布说明见 [`docs/releases/v4.4.0.md`](docs/releases/v4.4.0.md)
- `v4.3.0` — **改善案例与证据账本**（B0–B6）：案例生命周期 / 测量四通道 / 标准版本记录 /
  证据账本与交换 v1；Linux AppImage（x86_64）+ 源码包（zip / tar.gz）；
  发布说明见 [`docs/releases/v4.3.0.md`](docs/releases/v4.3.0.md)
- `v4.2.1` — **源码补丁**（质量加固 + 品牌/体验/启动修复），仅源码 zip / tar.gz，无新安装包；
  发布说明见 [`docs/releases/v4.2.1.md`](docs/releases/v4.2.1.md)
- `v4.2.0` — Linux AppImage（历史资产名 `QA-Tool-4.2.0-x86_64.AppImage` + `.sha256`）与源码包（zip / tar.gz）；
  发布说明见 [`docs/releases/v4.2.0.md`](docs/releases/v4.2.0.md)

---

## 开发文档

- [插件数据源合同（API 2.1）](docs/plugin-data-source.md)
- [v4.4.0 迁移手册](docs/migration/v4.4.0.md)
- [v4.4.0 发布说明](docs/releases/v4.4.0.md)
- 闭环八链路端到端演示：`python tools/demo_v44_case.py --output TEMP/demo_v44`
- [v4.3.0 迁移手册](docs/migration/v4.3.0.md)
- [v4.3.0 发布说明](docs/releases/v4.3.0.md)
- 端到端证据链演示：`python tools/demo_v43_case.py --output TEMP/demo_v43`

---

## 许可证

闭源商业软件，未经授权不得复制、修改或分发。

© 2026 AKIA. All rights reserved.

---

*Python 3.14 + PySide6 · 2400+ 测试 · 37 个分析 Tab + 插件接口 v2.1*
