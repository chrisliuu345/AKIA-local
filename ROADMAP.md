# QA-Tool 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v4.0.0 预测分析与机器学习（AutoML / CART / 随机森林 / 梯度提升 / MARS + 6 个 Agent 工具）（✅ 2026-09-13）| 下一版: v4.1.0（待定）| 测试: 1665 pytest · 37 个分析 Tab | 更新: 2026-09-13

> **维护约定（2026-09-12 起）**：每条版本记录只写「一行摘要 + 关键数据」；实现细节写进代码/测试/使用指南，本文不展开。
> 本文件已由 1100+ 行压缩至 500 行内，展开版历史见 git 历史（`git log -p -- ROADMAP.md`）。

---

## 版本总览

```
v2.0 ──→ v2.1 ──→ v2.2 ──→ v2.3 ──→ v2.4 ──→ v2.4.1 ──→ v2.5 ──→ v2.6.0 ~ v2.6.5 ──→ v2.7.0
      ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0 ──→ v3.1.0 ──→ v3.2.0 ──→ v3.3.0 ──→ v3.4.0 ──→ v3.5.0
      ──→ v3.6.0（含 3.6.1）──→ v3.7.0（含 review）──→ v3.7.1 ──→ v3.7.2 ──→ v3.8.0 ──→ v4.0.0 ✅ 当前
```

| 状态 | 版本 | 主题 |
|------|------|------|
| ✅ | v2.0 ~ v3.0.0 | 初始发布 → 代码+AI → 工程工具 → 报告 → 实时看板 → 硬件扩展（ESP32/MaixCAM）→ 安全/RBAC → 统计加固 → UI 健壮性 → 缺陷清零 → 统计深化 → 五链贯通 → 安全重构 |
| ✅ | v3.1.0 | DOE 与功效分析 |
| ✅ | v3.2.0 | Linux 移植 + 双系统发行 |
| ✅ | v3.3.0 | 时间序列与预测（ARIMA / 指数平滑 / 季节分解） |
| ✅ | v3.4.0 | 可靠性与生存分析（Weibull / KM / Cox / ALT / RBD / Crow-AMSAA / 保修） |
| ✅ | v3.5.0 | MSA 与能力深化（属性一致性 / EMP / Gage R&R / Sixpack / Edgeworth） |
| ✅ | v3.6.0 | Graph Builder 增强与交互体验（含 v3.6.1 全量质量审查） |
| ✅ | v3.7.0 | 实时 SPC 云看板与数据连接器（P1-P6） |
| ✅ | v3.7.1 | 五链贯通修复 + 数据语义与工程一致性加固 |
| ✅ | v3.7.2 | 实时监控对标优化 8 项 |
| ✅ | **v3.8.0** | **Industrial AI Agent（QAM Harness + 插件接口 v2；视觉迁至独立插件项目）** |
| 🔌 | [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion) | 视觉插件独立仓库（视频时间研究），基于插件接口 v2 |
| ✅ | **v4.0.0** | **预测分析与机器学习（CART / 随机森林 / 梯度提升 / MARS / AutoML + 特征工程 / 评估 / SHAP 解释 / 模型部署）** |

---

## 核心竞争力定位（2026-08 重规划）

> 定位：个人订阅级质量工程工具（类 Minitab）。开源界无同类全覆盖产品，最接近者为商业软件 Datalyzer（约 $2593/年）。

| # | 支柱 | 竞品现状 | 承载版本 |
|---|------|----------|----------|
| 1 | **质量工作流贯通**（FMEA→CP→SPC→PPAP→8D 数据链） | 空白 | v2.8.0 ✅ 持续深化 |
| 2 | **实时工厂集成**（ESP32/MaixCAM 原生 + PLC/CMM/量具连接器 + 云看板） | Minitab 需另购 Prolink；开源空白 | v3.7.0 ✅ |
| 3 | **IE 工程工具套件**（SMED/TPM/OEE/8D/FMEA/PPAP/控制计划） | Minitab 无 IE；竞品无 PPAP | v2.2.0 ✅ |
| 4 | **QAM Harness**（BYOK Agent：30 工具 + 离线路由 + 隐私门） | Copilot 仅云端；竞品 AI 为原型 | v3.8.0 ✅ |
| 5 | **中文优先 + 离线桌面**（GB/T 内置） | 空白 | 全程 |

规划原则：

1. 缺陷修复优先于功能扩张；统计正确性以 NIST/文献已知值验证
2. 测试基线只增不减，逐文件回归 + ruff 零告警为发布门禁
3. 每版本聚焦一个领域补齐，不贪多；确需新增 Tab 才新增
4. 个人订阅定位：桌面单机 + 实时设备连接，不做企业多公司平台
5. 外部能力以插件接口 v2 承载（如视觉），主应用只保留接口

---

## 版本历史（速览）

| 日期 | 版本 | 摘要 |
|------|------|------|
| 09-13 | v4.0.0 | **预测分析与机器学习发布**：`analysis/ml/`（任务判定与防泄漏 Pipeline、CART 预/后剪枝、随机森林 OOB、HistGradientBoosting（XGBoost 可选）、纯 numpy MARS、SHAP 解释、AutoML 排名）；新增 Tab「预测分析」（37）+ 6 个 Agent 工具（30 → 36）+ `.qamodel` 模型保存/加载/预测；版本 4.0.0 四端一致；1665 通过 / 2 跳过 / 0 失败，ruff 零告警；Linux AppImage + .deb 双包已构建，Windows 安装包由 Inno 脚本在 Windows 侧构建 |
| 09-13 | v4.0.0-quality | **全量代码质量审查**：ruff 门禁扩展并清零（T10/ISC/PIE/RUF012/RUF021/RUF034/RUF059/PLW1510/PLW2901/PLW0602）；修复 12 处真实缺陷（鱼骨图重复条件、循环变量覆盖 ×2、global 误声明、SMED/成本/抽样/项目管理冗余分支、DOE/回归/图表未用解包、startswith 合并 ×3、subprocess 显式 check）；类级可变属性补 `ClassVar` 标注；仓库卫生（取消跟踪 `test_quality.db` 与旧合规 docx 产物）；全量回归 118 文件全绿 + 打包冒烟通过 |
| 09-13 | v4.0.0-fix2 | **共享滚动区高度残留修复（W58 复发）**：`QStackedWidget` 尺寸提示只取当前页（隐藏 Tab 的参数面板/数据表不再撑长滚动区）；切换 Tab 时显式重算滚动范围并置顶（0/120/260ms 分批同步，规避 Qt hint 缓存）；无 canvas 分析页记录并恢复上次页面高度（切回不再丢失滚动范围）；新增 2 例回归 |
| 09-13 | v4.0.0-fix | **QAM Harness 连接检测修复**：任一云供应商已配置密钥即视为已连接 → 打开对话窗口不再误弹「未连接到 API」；自动选中已连接供应商并持久化 `llm_active_provider`；下拉框填充屏蔽信号（不再被中间态切回 Ollama）；新增 5 例回归 |
| 09-13 | v4.0.0-dev | **预测分析与机器学习 P0-P4 实现**：`analysis/ml/`（common/prep/trees/evaluate/forest/boosting/explain/mars/automl/train/persist）——任务判定与防泄漏 Pipeline、CART（预/后剪枝 + 规则）、回归/分类指标与 CV/学习曲线/残差、随机森林（OOB/置换重要性）、HistGradientBoosting（XGBoost 可选降级）、SHAP 解释、纯 numpy MARS（Friedman #1 优于线性基线）、AutoML 排名推荐；新增 Tab「预测分析」（37：QThread 训练 + `.qamodel` 保存加载预测）；QAM Harness 工具 30 → 36 |
| 09-12 | v3.8.0 | **Industrial AI Agent 发布**：QAM Harness（30 真实工具 + 在线/离线双路径 + BYOK 6 家 + 自定义兼容端点 + 隐私门 + 流式对话 UI）；插件接口 v2（manifest/能力/依赖/信任 + Tab/工具/设置页贡献）；视觉迁至独立插件项目；收尾修复 Hotelling T² 控制限（误报 30%→0.06%）与 PyInstaller `unittest` 致启动崩溃；108 文件 / 1567 通过 / 2 跳过 / 0 失败，ruff 零告警，onedir 构建 + 启动冒烟通过 |
| 09-12 | v3.8.1-plugin-api | 插件接口 v2 + 视觉迁移（`core/plugin_api.py` / `plugin_manager.py` / `ui/plugin_host.py`；契约测试 7 例） |
| 09-11 | v3.8.0-P3 | Vision AI 视频时间研究（多源输入/流水线/姿态/状态机/周期切分；后整体迁出为独立插件） |
| 09-11 | v3.8.0-P1/P2 | QAM Harness Core（16→30 工具、在线+离线路由、对话 UI、BYOK + 隐私门） |
| 09-10 | v3.7.2 | 实时监控对标 8 项（规格线缩放 / plant 可视化 / 告警分级确认 / 成本损失 / 真实 P OEE / 降采样保留 / 连接器健康 / 看板鉴权） |
| 09-10 | v3.7.1 | 五链桥接修复 + 列类型语义 + 打包配置隔离与密钥加密 + APP_VERSION 单一事实源 |
| 09-08 | v3.7.0 | 实时 SPC 云看板与数据连接器（流总线 / SQLite 时序 / FastAPI+WS 看板 / 连接器 SPI / 产线拓扑 / 实时 OEE / 告警中心） |
| 09-07 | v3.7.0-前置 | 风格债清零 + ruff 门禁 + 构建链切 PyInstaller(onedir) |
| 09-06 | v3.6.0 / v3.6.1 | Graph Builder 增强（图表编辑/热力图/小多图/导出/帮助中心）+ 全量质量审查（7 处潜在崩溃修复） |
| 09-05 | v3.5.0 | MSA 与能力深化（Fleiss Kappa / EMP / Gage R&R 增强 / Sixpack / 自动能力 / Edgeworth） |
| 09-04 | v3.4.0 | 可靠性与生存分析（Weibull 2P-4P+CI / KM / Cox / ALT / RBD / Crow-AMSAA / 保修） |
| 09-01 | v3.3.0 | 时间序列（ARIMA 自动选阶 / 指数平滑 / 季节分解 / 预测 / E2E） |
| 09-01 | v3.2.0 | Linux 移植（字体系统 / keyring / AppImage / 双系统发行） |
| 08-28 | v3.1.0 | DOE 与功效分析（筛选 / 部分因子 / 田口 / 混料 / Power 引擎） |
| 08-25 | v3.0.0 | 稳定化里程碑（35 Tab 基线） |
| 08-25 | v2.9.0 | 安全架构重构（删除 Auth + 离线许可 + 构建链切换） |
| 08-25 | v2.8.0 | 工作流贯通（ProjectContext 单一事实源 + 五链） |
| 08-23 | v2.7.0 | 统计引擎深化（P1 7 项 + P2 6 项 + 4 个 UI 集成）· 537+ 测试 |
| 08-23 | v2.6.5 | W 系列缺陷清零 + Info 一期 · 450+ 测试 |
| 08-21 | v2.6.2 | RBAC 权限矩阵 + 认证加固 + 设备链路 + 实机验证 · 296 测试 |
| 08-19 | v2.6.1 | 安全校验（密码策略 / 审计日志 / 密钥库）· 282 测试 |
| 08-18 | v2.6.0 | ESP32 部署拓展 + 设备监控 Tab 35 + PyInstaller/Inno 打包 · 278 测试 |
| 08-15 | v2.4.1 | 自适应看板卡片 + 动画 · 215 测试 |
| 08-13 | v2.4 | 看板 E4（KPI 提取 / 实时刷新 / 卡片布局 / 公式编辑器 / 车间看板）· 136 测试 |
| 08-12 | v2.3 | 报告模板引擎 + HTML 导出 + 菜单重构 |
| 08-10 | v2.2 | 32 Tab · SMED/8D/TPM/PPAP · 87 测试 |
| 08-04 | v2.0 | 初始发布（28 Tab / 65 测试 / AI 助手 / 插件系统） |

> v2.1 ~ v3.0.0 的安全、硬件与稳定性细节见 git 历史，本文不再展开。

---

## 当前版本 v4.0.0 要点

- **预测分析 Tab（37）**：目标列/特征选择 → 任务类型自动判定 → 5 类模型（线性/逻辑回归 · CART · 随机森林 · 梯度提升 · MARS）→ 指标/CV/图表 → `.qamodel` 保存加载 → 预测导出；训练在后台线程执行
- **特征工程与评估**：缺失值 / 独热编码 / 分位数分箱 / 标准化（Pipeline 防泄漏）· R²/RMSE/MAE/MAPE · Accuracy/P/R/F1/AUC · 混淆矩阵 · ROC · K 折 CV · 学习曲线 · 残差诊断 · SHAP 解释（自动降级）
- **QAM Harness**：6 个机器学习工具（`ml_prepare_data` / `ml_train` / `ml_automl` / `ml_evaluate` / `ml_explain` / `ml_predict`），工具总数 30 → 36；配合 v3.8.0 的 BYOK + 隐私门 + 离线关键词路由
- **插件接口 v2**（v3.8.0）：三级发现 + 信任模型 + Tab/工具/设置页贡献；视觉能力在 [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion) 独立演进
- **质量数据**：1665 通过 / 2 跳过 / 0 失败（118 文件逐文件回归）；ruff 扩展门禁零告警；Linux AppImage + .deb 双包已构建（Windows 安装包脚本就绪，Windows 侧构建）

---

## 已知遗留 / 候选方向

| 项 | 说明 | 归属 |
|----|------|------|
| 主动建议准确率人工评审（≥3.5/5） | 需工程师人工评分 | 待用户 |
| 视觉真机验收（现场视频 + 标注 CSV，一致性 ≥85%） | 需现场素材 | 插件项目 |
| 发布包（AppImage / .deb / Inno） | 脚本就绪，按需构建上传 Release | 可选 |
| 多站点 / 多语言 | v3.7.2 候选第 9 项顺延 | 候选 |
| 连接器扩展（更多 PLC/CMM 协议） | 按现场需求 | 候选 |
| 预测分析与机器学习 | v4.0.0 ✅ 已发布 | 2026-09-13 完成 |

---

## v4.0.0 ✅ 已发布 — 预测分析与机器学习（2026-09-13）

> 主题：补齐 Minitab Predictive Analytics 级能力；纯主软件。复用 sklearn 1.9 / shap 0.52，不新增硬依赖（XGBoost 仅可选适配）。

> **发布状态**：P0-P5 全部完成 —— 版本 4.0.0 四端一致（settings / version_info / Inno / README·INSTALL·ROADMAP·guide）；
> 全量逐文件回归 118 文件通过；ruff 扩展门禁零告警；Linux AppImage + .deb 双包已构建（Windows 安装包由 Inno 脚本在 Windows 侧构建）。

### 阶段划分（P0 → P5）

| 阶段 | 交付 | 验收 |
|------|------|------|
| **P0 数据与契约** ✅ | `analysis/ml/{__init__,common,prep}.py`：任务类型判定（回归/分类）、缺失值、编码、分箱、标准化、训练/测试切分、K 折、Pipeline 防泄漏 | 预处理与 sklearn 行为一致；`analysis/ml` 无 Qt（分层守卫） |
| **P1 CART + 评估** ✅ | `trees.py`（分类/回归树、预剪枝 + ccp_alpha 后剪枝、规则导出）、`evaluate.py`（R²/adj-R²/RMSE/MAE/MAPE、Acc/P/R/F1/AUC、混淆矩阵、ROC、K 折 CV、学习曲线、残差诊断） | 同 seed 与 sklearn 指标一致（容差内）；回归 + 分类均覆盖 |
| **P2 集成 + 解释** ✅ | `forest.py`（OOB、特征重要性、permutation importance）、`boosting.py`（HistGradientBoosting 主实现 + XGBoost 可选适配）、`explain.py`（SHAP 采样上限 + 原生重要性降级 + 单样本解释） | 三模型可训/评/释；无 XGBoost、SHAP 超限或缺失时自动降级不报错 |
| **P3 MARS + AutoML** ✅ | `mars.py`（纯 numpy：前向基函数 + 后向剪枝 + GCV 选 knot + 交互项）、`automl.py`（模型库 CV 排名 + 时间预算 + 推荐 + leaderboard） | Friedman #1 合成集上 MARS 不劣于线性基线；AutoML 同 seed 可复现、与人工选模一致 |
| **P4 UI + Agent 工具** ✅ | Tab「预测分析」（索引 37；准备/训练/评估/预测 + QThread 训练）、`.qamodel` 模型保存加载与预测导出、`core/agent/tools_ml.py` 6 个工具（30 → 36） | E2E：准备→建模→评估→可视化→预测；离屏 UI 测试 + 工具真引擎测试通过 |
| **P5 收尾发布** | README 中英 / guide.html / 本路线图同步；版本 4.0.0 四端一致；全量逐文件回归 + 打包冒烟 | `tools/check_version.py` 通过；ruff 零告警；onedir 构建可启动且模型推断正常 |

### 关键设计决策

- **分层**：`analysis/ml/` 只用 numpy/pandas/sklearn（无 Qt）；UI 训练全部走后台线程，主线程不阻塞
- **防泄漏**：预处理统一封装为 sklearn Pipeline，CV 在折内拟合；切分支持分层抽样（分类）
- **依赖**：不新增硬依赖；XGBoost 为可选适配（未安装自动降级），MARS 自研避免 pyearth
- **模型文件**：`.qamodel` = joblib + JSON 元数据（模型/特征/指标/版本），只加载本工具产物
- **解释性能**：SHAP 默认采样上限 ≤300 行（沿用 `analysis/ai/root_cause.py` 策略），超限自动降级为原生重要性
- **接线点**（P4，已核对）：`ui/_tab_registry.py`（37）· `ui/sidebar.py` 质量分类 · `locales/zh.json` · `analyses[idx]` 记录 · 报告/PPT 导出 · Agent 工具注册（`build_default_registry` 挂钩）
- **暂不接入**：模板批量分析（`core/template_parser.py`）暂不扩展 ML 类型，列为候选

### 整版验收标准

- CART / 随机森林与 scikit-learn 交叉验证一致
- AutoML 选模与人工选模结论一致
- 端到端：数据准备 → 特征工程 → 建模 → 评估 → 可视化

---

## 工程约定

- **版本**：`config/settings.py::APP_VERSION` 为单一事实源；`tools/check_version.py` 校验 version_info / Inno / README / INSTALL / ROADMAP，CI 门禁
- **构建**：PyInstaller onedir（`build_pyinstaller.py`）→ Inno（Windows）/ AppImage / .deb；`build/`、`dist/` 不入库
- **测试**：严禁 `pytest tests/` 批量（conftest 有拦截器），逐文件运行；GUI 测试 `QT_QPA_PLATFORM=offscreen`
- **质量门禁**：ruff 零告警 + 相关回归 + 打包冒烟（发布版本必做）
- **分层**：`analysis/` 禁 Qt；`core`/`config`/`output` 禁 import `ui`；`core/agent/` 保持无 Qt
- **插件**：只通过 `core/plugin_api.py` 交互，API 大版本兼容；未信任插件不导入
- **文档同步**：README 中英 / 使用指南 guide.html / 本路线图随功能变更同步

---

## 侧边栏演进

> v2.6.5 ~ v3.0.0 不新增 Tab（深化为主）；v3.8.0 以对话式 Agent 为主，不新增独立 Tab。

| 版本 | Tab 数 | 变化 |
|------|--------|------|
| v2.0 | 28 | 初始（Home / Quality / IE / Charts / Eng / Worksheet / Sampling / Report / Data / Plugins） |
| v2.2 | 32 | +SMED · +TPM · +8D · +PPAP |
| v2.4 | 34 | +实时监控 · +多产线 |
| v2.5 ~ v2.6 | 35 | +设备监控（Tab 35） |
| v3.3.0 | 36 | +时间序列 |
| v3.8.0 | 36 + 插件 | 视觉 Tab 迁出；插件 Tab 动态索引（≥37）；QAM Harness 为对话窗口（非 Tab） |
| v4.0.0 | 37 + 插件 | +预测分析（Tab 37）；插件 Tab 从 38 起 |
