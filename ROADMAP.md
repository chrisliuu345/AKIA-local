# AKIA 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v4.2.0 算法可信度与深度（已知值矩阵 / 多元 SPC / 变点检测 / 判定凭证 / 首个改善闭环）（✅ 2026-09-22 源码 · ✅ 2026-09-23 Linux AppImage + GitHub Release）| 下一版: **v4.3.0 改善案例与证据账本（规划）**
> 深化主线: **v4.2 可信 → v4.3 案例与证据 → v4.4 闭环 → v4.5 开放 → v4.6 智能**（从分析工具到现场改善证据链）| 测试: 1960+ pytest · 37 个分析 Tab | 更新: 2026-09-28
> 状态: **v4.2.0 P0–P6 全部完成并交付**（P0 ✅ 契约 · P1 ✅ 已知值 29 例 · P2 ✅ 算法深度 60 例 + 工具接线 · P3 ✅ 稳定性与大样本 · P4 ✅ 判定凭证与方法文档 · P5 ✅ 首个闭环切片 · P6 ✅ 收尾 · 打包 ✅ Linux AppImage + GitHub Release）；**2026-09-28 完成中间质量审查与算法优化（无版本号，版本仍为 4.2.0）**；下一阶段 **v4.3.0 改善案例与证据账本**

> **维护约定（2026-09-12 起）**：每条版本记录只写「一行摘要 + 关键数据」；实现细节写进代码/测试/使用指南，本文不展开。
> 本文件已由 1100+ 行压缩至 500 行内，展开版历史见 git 历史（`git log -p -- ROADMAP.md`）。

---

## 版本总览

```
v2.0 ──→ v2.1 ──→ v2.2 ──→ v2.3 ──→ v2.4 ──→ v2.4.1 ──→ v2.5 ──→ v2.6.0 ~ v2.6.5 ──→ v2.7.0
      ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0 ──→ v3.1.0 ──→ v3.2.0 ──→ v3.3.0 ──→ v3.4.0 ──→ v3.5.0
      ──→ v3.6.0（含 3.6.1）──→ v3.7.0（含 review）──→ v3.7.1 ──→ v3.7.2 ──→ v3.8.0 ──→ v4.0.0
      ──→ v4.2.0 ✅ 当前（可信 · AppImage 已发布）──→ v4.3.0 案例·证据（规划）──→ v4.4.0 闭环（规划）
      ──→ v4.5.0 开放（规划）──→ v4.6.0 智能（规划）
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
| 🔌 | [AKIA-Vision-expansion](https://github.com/chrisliuu345/AKIA-Vision-expansion) | 视觉插件独立仓库（视频时间研究），基于插件接口 v2 |
| ✅ | **v4.0.0** | **预测分析与机器学习（CART / 随机森林 / 梯度提升 / MARS / AutoML + 特征工程 / 评估 / SHAP 解释 / 模型部署）** |
| ✅ | **v4.1.0** | **图表与界面体验统一（B1 风格层 / B2 缺陷修复 / B3 命令面板·批量进度·Toast·空状态 / B4 质量与性能基线）** |
| ✅ | **v4.2.0** | **算法可信度与深度（已知值验证矩阵 / 多元 SPC·变点检测·残差控制图 / 判定凭证 / 首个闭环切片）· Linux AppImage 已发布** |
| 🚧 | v4.3.0 | 改善案例与证据账本（ImprovementCase 生命周期 / MeasurementEvent·插件数据源 / 标准版本记录 / 证据视图·脱敏分享） |
| 🚧 | v4.4.0 | 闭环执行与效果验证（告警自动立案 8D / 测量系统在线化 / 抽样转移 / 收益账本·COPQ / 技能约束线平衡） |
| 🚧 | v4.5.0 | 生态开放（MCP 服务·原生工具调用 / CLI·SDK 质量门禁 / 行业规则包·插件脚手架） |
| 🚧 | v4.6.0 | 智能在线化（模型治理·在线评分 / 工艺参数窗口 / IE 证据链 / 本地数据资产·边缘判异） |

---

## 核心竞争力定位与壁垒（2026-09 重规划）

> 定位：个人订阅级质量工程工具（类 Minitab）→ 深化为「面向现场改善的证据链工具」：开源界无同类全覆盖产品，最接近者为商业软件 Datalyzer（约 $2593/年）。
> 壁垒不靠功能数量，靠两层：① 竞品重写成本极高的数据模型——改善案例 + 双时态/血缘/可信度分级（仅测量·标准·结论三类对象，不做全库双时态）；② 越用越厚的数据资产（过程基线 / 量具健康史 / 收益账本 / 案例库）。

| # | 支柱 | 竞品现状 | 承载版本 |
|---|------|----------|----------|
| 1 | **质量工作流贯通**（FMEA→CP→SPC→PPAP→8D 数据链） | 空白 | v2.8.0 ✅ 持续深化 |
| 2 | **实时工厂集成**（ESP32/MaixCAM 原生 + PLC/CMM/量具连接器 + 云看板） | Minitab 需另购 Prolink；开源空白 | v3.7.0 ✅ |
| 3 | **IE 工程工具套件**（SMED/TPM/OEE/8D/FMEA/PPAP/控制计划） | Minitab 无 IE；竞品无 PPAP | v2.2.0 ✅ |
| 4 | **QAM Harness**（BYOK Agent：37 工具 + 离线路由 + 隐私门） | Copilot 仅云端；竞品 AI 为原型 | v3.8.0 ✅ 持续扩展 |
| 5 | **中文优先 + 离线桌面**（GB/T 内置） | 空白 | 全程 |
| 6 | **改善案例与证据系统**（ImprovementCase 脊柱 + 血缘/可信度分级 + 可重放判定 + 证据包交换） | Minitab / Datalyzer 均无 | v4.2.0–v4.3.0 |
| 7 | **开放接口生态**（MCP 服务 + headless CLI/SDK + 行业规则包） | AI 生态空白；插件标准未定 | v4.5.0 |

规划原则：

1. 缺陷修复优先于功能扩张；统计正确性以 NIST/文献已知值验证
2. 测试基线只增不减，逐文件回归 + ruff 零告警为发布门禁
3. 每版本聚焦一个领域补齐，不贪多；确需新增 Tab 才新增
4. 个人订阅定位：桌面单机 + 实时设备连接，不做企业多公司平台
5. 外部能力以插件接口 v2 承载（如视觉），主应用只保留接口
6. **数据模型优先**：时间（双时态）、血缘（provenance）、可信度分级先于功能扩张；每个结论必须可追溯、可重放
7. **能力开放**：核心引擎经 MCP/CLI/SDK 输出，主应用保留体验层与证据层
8. **案例优先**：新能力必须先挂进改善闭环（测量 → 分析 → 改善 → 验证 → 标准），不做孤立工具；现有工具是案例内的能力

---

## 版本历史（速览）

| 日期 | 版本 | 摘要 |
|------|------|------|
| 09-28 | **中间质量审查（无版本号）** | **全量代码质量审查 + 算法优化（源码更新，版本号保持 4.2.0）**：**P1 静态棘轮扩容**——11 条规则（RET505/506 · RUF010/RUF100 · SIM105/113/114/201 · C408/416/420 · PERF102 · PLW0108 · PLW3301）清零入闸，修复 2 处死代码（`sampling_engine` 只写不读的 total、`smed_tab` 甘特 y 计数），100 文件清理 · **P2 静默失败治理**——审计写入失败计数 + warning、会话/调度/一键分析/配置迁移补日志，31 处 pass-only 异常全部带理由；**修复批量调度必然失败**（对话框未注入执行器 → 新增无 Qt 默认执行器 `run_task_headless`，数据源→分析→docx/pdf/xlsx/Markdown 报告） · **P3 数值鲁棒性**——新增 `analysis/_sanitize.py` + `spc/_validation.py`，±inf/缺失值统一净化，修复 6 类底层报错（指数平滑 No supported index · 计数四图 NaN/inf 转换崩溃 · 残差图 Ljung-Box 空序列 IndexError · 能力六合图 range not finite） · **P4 性能**——Nelson 判异向量化（2100 项等价性对照 0 差异）→ **SPC 100 万点 21.96s → 1.62s（13.5×）**；解析逐格回调向量化 → **百万行导入 14.27s → 5.19s（2.7×）**，`perf_baseline.json` 同步收紧锁定收益 |
| 09-23 | **v4.2.0 打包发布** | **Linux AppImage 构建 + GitHub Release 交付**：`build_appimage.sh`（PyInstaller onedir → AppDir → appimagetool）产出历史资产 `QA-Tool-4.2.0-x86_64.AppImage` + `.sha256` 校验文件（更名后新产物为 `AKIA-*`）；无 FUSE 环境以 `--appimage-extract-and-run` 启动；README(中英) / ROADMAP(中英) / guide.html / `docs/releases/v4.2.0.md` 同步发布形态与校验步骤；版本号保持 4.2.0（`check_version.py` 通过、API 不变），Windows 安装包仍在 Windows 侧构建 |
| 09-22 | **v4.2.0 发布** | **算法可信度与深度（源码 prerelease）**：P0–P6 全部完成 —— 已知值矩阵 29 例 · 算法深度 60 例（MEWMA 逐点精确 Σ_z / 广义方差 / PELT 变点 / ARIMA 残差图 / 非正态 Bootstrap 区间 / 可靠性区间修正 / ARIMA 稳健性）· 基准扩至 8 项 + 鲁棒性契约 + BLE001 棘轮 + 覆盖率补口 · 判定凭证闭环（分析记录 → 报告追溯码 → `.qap` 1.8 → 重跑 diff）+ guide「方法与参考」· 首个改善闭环切片（案例脊柱 8 阶段 + 工作台入口）· 版本四端一致 + 全量门禁；全量逐文件回归 **157 文件 / 1950 例全绿**，ruff 零告警 |
| 09-22 | v4.2.0-P2 | **算法深度完成（7 文件 / 60 例）**：MEWMA（Lowry 1992，逐点精确 Σ_Z(i) + Phase I/II 口径 + 稳态近似可选；r=1 与 hotelling 逐点一致）· 广义方差图（Montgomery b1/b2）· PELT 变点检测（纯 numpy，与暴力 DP 全局最优一致，默认罚项 2.5σ̂²log n 经固定种子标定）· ARIMA 残差控制图（AR(1) 误报大幅下降）· 非正态能力 Bootstrap 区间（向量化，小样本精度告警：n<1000 时点估计偏高）· 可靠性区间（Weibull CI 与 lifelines 交叉验证；**ALT 外推区间修正**——旧实现忽略杠杆项，修正后覆盖率 0.950）· ARIMA 稳健性（**修复含缺测序列崩溃** No supported index；常量/短序列守卫；搜索空间按样本量收窄） |
| 09-17 | v4.2.0-audit | **UI 功能与接线全面审查**：37+1 Tab 离屏普查 + 全部按钮/菜单动作接收者扫描（无零接线）；修复 4 类缺口——时间序列/预测分析未接入工作簿路由 · 29-32 自包含工具被导入遮罩挡住 · 14/16/17/25/26 手工/上下文工具被挡住（含 FMEA→控制计划五链）· 菜单缺 35/36/37 入口；新增 3 例路由覆盖回归（分析 Tab 全覆盖 / 五链不被挡 / 自包含无遮罩） |
| 09-17 | fix-ie | **IE Tab 导入接线修复**：① 空状态蓝色按钮对所有 Tab 都连到工作表导入，而工作表路由又跳过 IE Tab（7-11/21-22）→ IE 导入型 Tab（7/9/10/11）改连「导入 IE 数据」并同步按钮文案；② `_tab_has_data` 只看 `df`，IE 数据存于 `ie_*` → 菜单导入后遮罩不消失，现在识别 IE 数据并在导入完成后立即刷新空状态；③ 8/21/22 为自包含 IE 工具（手工/预设驱动），不再套导入遮罩；新增 6 例接线回归 |
| 09-17 | fix-import | **真实报表表头重名列导入崩溃修复**：`CO401-20220930.xls` 表头含两个「二维码」→ `_apply_header` 后列名重复 → `df[col]` 返回 DataFrame → `pd.to_numeric` 抛 TypeError；解析器在 `_analyze_frame` 入口统一列名去重（`二维码.1`）并把重命名写入解析信息；新增 4 例回归（含真实表头结构复现），真实文件 722×77 → 589×77 导入成功 |
| 09-17 | v4.2.0-P1b | **已知值矩阵批次 2 完成**：+9 例——EWMA / CUSUM / Hotelling T² · Gage R&R（AIAG 均值-极差）· Weibull 2P-MLE（独立 brentq 解）· ARIMA(0,1,0) 随机游走 · CART 完美分裂；P1 合计 12 文件 / 29 例，7 域全覆盖 |
| 09-17 | fix-ui | **空状态「导入数据」按钮无响应修复**：遮罩的 `WA_TransparentForMouseEvents` 会连同子控件一起屏蔽鼠标事件，按钮永远收不到点击；移除该属性并新增「真实命中 + 鼠标点击」回归测试（`widgetAt` 定位按钮中心后 QTest 点击） |
| 09-17 | v4.2.0-P1a | **已知值矩阵批次 1**：7 域 20 例（SPC 控制图+Nelson 8 规则 / 正态能力 / Cohen κ / 2² 因子 / KM+Crow-AMSAA / 样本 ACF / 回归+分类指标）；**发现并修复 2 处缺陷**——`classification_metrics` 数值标签混淆矩阵全 0、DOE 完全拟合除零告警；容差预设扩展 `rounded_6dp`/`rounded_4dp` |
| 09-17 | v4.2.0-P0 | **契约与测试基座完成**：`core/evidence.py`（凭证 schema v1 + 数据指纹 + diff）· `core/improvement_case.py`（案例 schema v0）· `.qap` 1.6→1.7 案例段增量兼容 · `KNOWN_VALUES.md` + `tests/known_values.py` 已知值框架 · 4 个契约测试文件 / 40 例 |
| 09-17 | v4.2.0-plan | **v4.2.0 分阶段开发方案**：P0 契约基座 → P1 已知值矩阵 → P2 算法深度 → P3 稳定性 → P4 凭证与方法文档 → P5 首个闭环切片 → P6 收尾；无新硬依赖（statsmodels 仅测试参考）；`.qap` 1.6 → 1.7 增量兼容 |
| 09-17 | roadmap-rev | **方案复核修订（对照 GPT 观点）**：确立「改善案例为脊柱、双时态为机制」——v4.3 由存储优先改为案例优先（ImprovementCase → MeasurementEvent/插件数据源 → 标准版本 → 证据包）；v4.2 增加首个纵向闭环切片；技能约束线平衡由 v4.6 上移至 v4.4；案例关闭强制复测 + 统计判定；匿名基准降级为服务端阶段候选 |
| 09-17 | roadmap | **v4.2–v4.6 深化方向规划**：收敛为「可信 → 证据 → 闭环 → 开放 → 智能」五步主线；确立四层壁垒（双时态数据模型 / 判定验证 / 交换接口 / 数据资产）；新增条目：已知值矩阵、变点检测与残差控制图、判定凭证、双时态证据账本、脱敏证据包、告警自动立案 8D、测量系统在线化、抽样转移状态机、收益账本·COPQ、MCP 服务、CLI·SDK、行业规则包、参数窗口、IE 证据链、匿名基准、边缘判异 |
| 09-15 | v4.1.0 | **图表与界面体验统一发布**：B1 `output/chart_style.py` 统一风格层（深/浅双主题 + Okabe-Ito 语义色 + 智能 y 轴/违规标注/限值线）并迁移两图表入口；B2 审计 8 项缺陷清零（箱线图自动分面、帕累托 80% 线+柱值、控制图图例外置+规则标注、能力图统计卡、热力图发散色+对角消隐等）；B3 全局命令面板（Ctrl+K/Ctrl+P）、批量分析进度与取消（Ctrl+Shift+B）、Toast 接线、统一空状态；B4 类型现代化（UP 全家 + RUF013 清零，155 文件）、热点拆分（main_window/tools_ext → 两个 helper 模块）、性能基线入 CI（冷启动 2.2s / 百万行导入 14.0s / 5k 图 1.5s / 5k 行 ML 1.5s）；版本 4.1.0 四端一致；124 文件 / 1708 通过 / 2 跳过 / 0 失败，ruff 零告警；**源码 prerelease（不含安装包）** |
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

## 当前版本 v4.2.0 要点

- **品牌更名**：自本版起产品更名为 **AKIA（AKIM IE/Quality analyzer-local）**，仓库迁至
  [chrisliuu345/AKIA-local](https://github.com/chrisliuu345/AKIA-local)；v4.2.0 已发布的
  Linux AppImage 资产保留历史文件名 `QA-Tool-4.2.0-x86_64.AppImage`，自下一版起统一 `AKIA-*`

- **算法可信**：已知值矩阵 29 例（P1）+ 算法深度 60 例（P2）—— MEWMA、广义方差、PELT 变点检测、ARIMA 残差控制图、非正态能力 Bootstrap 区间；新算法已接入 QAM Harness（`run_spc` 新图型 + `detect_changepoints`，共 37 个本地工具）
- **可追溯**：判定凭证（规则版本 + 参数 + 数据指纹 + 软件版本）写入分析记录与 `.qap` 1.8；报告页脚 12 位追溯码；同数据重跑自动逐项 diff；guide.html「方法与参考」列出 16 类方法出处
- **闭环切片**：改善案例工作台（工具 → 改善案例工作台）以 8 阶段脊柱串联基线 → 时间研究 → 线平衡 → 改善 → 复测 → 配对检验 → 结论 → 标准草稿，每步留痕时间戳/数据引用/凭证
- **稳定性**：性能基准 8 项（SPC 10 万/100 万行、MSA 10 万行、ML 10 万行）入 CI；22 例退化输入契约；`BLE001` 盲除异常门禁自算法层启用
- **发布形态**：Linux 仅 AppImage；本版已交付 **`v4.2.0` GitHub Release** —— 历史资产名 `QA-Tool-4.2.0-x86_64.AppImage`（附 `.sha256` 校验文件）+ 源码 zip/tar.gz；Windows 安装包在 Windows 侧由 `packaging/AKIA-installer.iss` 构建

---

## 上一版本 v4.1.0 要点（历史）

- **图表风格层（B1）**：`output/chart_style.py` 作为唯一风格源——深/浅双主题、Okabe-Ito 色盲友好语义色（数据/中心线/控制限/规格限/拟合/违规）、统一 rcParams 与 `smart_ylim` / `add_limit_lines` / `mark_violations` / `style_for_export`；chart_engine、chart_generator、heatmap、faceting 全部迁移
- **图表缺陷修复（B2）**：审计 8 项清零——箱线图多量纲自动分面、帕累托 80% 线 + 柱值标签、控制图图例外置 + 判异规则标注、能力图统计卡 + 等级徽章、热力图发散色 + 对角消隐、时序智能 y 轴、主题耦合色与字号网格统一
- **界面体验（B3）**：全局命令面板（Ctrl+K / Ctrl+P，37 Tab + 插件 + 16 操作）、批量分析分步执行 + 进度 + 取消（Ctrl+Shift+B）、Toast 接线（分析/导出/批量）、统一空状态（无数据 Tab 自动"导入数据"遮罩）
- **质量与性能基线（B4）**：类型现代化全量完成（UP 家族 + RUF013 清零）、`main_window` / `tools_ext` 热点拆分、`tools/benchmark.py` 四项基准进 CI（tolerance ×4）
- **质量数据**：1708 通过 / 2 跳过 / 0 失败（124 文件逐文件回归）；ruff 扩展门禁（含 UP 全家）零告警；**源码 prerelease（不含安装包）**

---

## 已知遗留 / 候选方向

| 项 | 说明 | 归属 |
|----|------|------|
| 主动建议准确率人工评审（≥3.5/5） | 需工程师人工评分 | 待用户 |
| 视觉真机验收（现场视频 + 标注 CSV，一致性 ≥85%） | 需现场素材 | 插件项目 |
| 发布包（Windows Inno） | v4.2.0 已出 Linux AppImage 并入 Release；Windows 安装包需在 Windows 侧构建（脚本与 .iss 就绪） | 按需 |
| 改善案例对象 + 证据账本 | 双时态收窄至测量/标准/结论三类；见 v4.3.0 | v4.3.0 |
| 案例工作台入口 | 优先复用 Home；确需新增 Tab 时单独评审 | v4.3.0 决策 |
| MCP 服务 + 原生工具调用 | 决定 AI 生态位，见 v4.5.0 | v4.5.0 |
| 告警自动立案 8D / 测量系统在线化 / 技能约束线平衡 | 复用告警 · MSA · 连接器健康 · 线平衡引擎 | v4.4.0 |
| 完整英文包 | i18n 框架随 v4.5.0，全文翻译顺延 | v4.5 / 之后 |
| 连接器扩展（更多 PLC/CMM 协议） | 按现场需求 | v4.6.0 B4 |
| 匿名行业基准 | 需服务端汇聚与隐私评审，非本仓库近期 | 服务端阶段 |
| FMEA / 控制计划 Excel 导入 | 两表当前为手工录入 / 项目上下文 / 五链生成；工作簿导入未映射到表格模型 | 候选（按需） |

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

## 后续版本规划（v4.1.0 → v4.6.0）

> **总主线**：从「质量分析工具」演进为「面向现场改善的证据链工具」——以 **ImprovementCase（改善案例）为脊柱**：测量 → 分析 → 改善 → 复测 → 验证 → 标准。先让算法可信（4.2），再把案例、数据、标准、判定接成账本（4.3），在账本上执行闭环（4.4），以 MCP/CLI/规则包开放能力（4.5），最后让模型与时间积累的数据产生复利（4.6）。
> **壁垒分层**：L1 数据模型（改善案例 + 双时态/血缘/可信度分级，仅测量·标准·结论三类对象）· L2 判定验证（已知值矩阵 + 可重放结论）· L3 交换接口（.qap 证据包 / 脱敏分享 / MCP / 规则包）· L4 数据资产（过程基线 / 量具健康史 / 收益账本 / 案例库）。
> **节奏**：4–6 周/版，每版 3–5 项，保留 ~20% 缓冲给用户实测插单；沿用「逐文件回归 + ruff 扩展门禁 + 版本四端一致 + 打包冒烟」DoD。
> **边界**：原则上不新增 Tab（案例工作台优先复用 Home，确需新增须显式评审）；不引入重量级硬依赖、不做企业级功能；插件接口 2.x 保持向后兼容（新增能力为增量式 2.1）。
> **不做**：企业级多用户 QMS/MES · 通用 BI 看板 · 自研统计求解器 · 强依赖云端的 SaaS（保持单机离线 + 证据可信的差异化）。

### v4.1.0 ✅ 已发布 — 图表与界面体验统一（2026-09-15）

> **发布状态**：B1–B4 全部完成，版本 4.1.0 四端一致（settings / version_info / Inno / README·INSTALL·ROADMAP·guide）；
> 全量逐文件回归 124 文件通过；ruff 扩展门禁零告警；性能基线入 CI；**本版不打包，以源码 prerelease 发布（GitHub Source zip / tar.gz）**。

| 批次 | 交付 | 验收 |
|------|------|------|
| **B1 图表风格层** ✅ 2026-09-14 | 新增 `output/chart_style.py`（唯一风格源：深/浅主题 · Okabe-Ito 色盲友好语义色板 · rcParams · `smart_ylim` / `mark_violations` / `add_limit_lines`）；迁移 `chart_engine` + `chart_generator` + `heatmap`/`faceting`；控制图与时序接入智能 y 轴；热力图改发散色 + 对角消隐 | 16 例新测试通过；10+ 类图表风格一致；无默认色循环残留；深/浅主题可切换（对照图 `TEMP/chart_audit_{before,after_b1}_2026-09-14.png`） |
| **B2 图表缺陷修复** ✅ 2026-09-15 | 审计 8 项全消：时序 y 轴智能留白（B1）· 箱线图多量纲自动分面（`box_mode=auto/single/split`）· 帕累托 80% 参考线 + 柱值标签 · 控制图图例外置 + 判异规则标注 · 能力图统计卡片重排（指标双列 + 等级徽章）· 热力图发散色 + 对角消隐 + 注释对比度 · 主题耦合色消除 · 字号/网格统一 | 22 例风格/缺陷测试通过；对照图 `TEMP/chart_audit_{before,after_b1,after_b2}_2026-09-*.png` |
| **B3 界面体验** ✅ 2026-09-15 | 全局命令面板（Ctrl+K / Ctrl+P：37 Tab + 插件 + 16 项常用操作）· 批量分析分步执行 + 进度条 + 取消（Ctrl+Shift+B）· Toast 接线（分析完成 / 导出 / 批量汇总，批量期间抑制逐条弹窗）· 统一空状态（无数据 Tab 自动"导入数据"遮罩 + 按钮接线） | 15 例新测试通过；主流程键盘可达；批量分析全程 UI 可响应、可取消 |
| **B4 质量与性能基线** ✅ 2026-09-15 | 类型现代化全量完成（**UP 家族 + RUF013 清零**：PEP 585/604 注解、typing 弃用导入、隐式 Optional；154 文件）· 热点拆分：`ui/main_window_helpers.py`（Tab 判定 / 当前页 Stack / LLM 检测）+ `core/agent/tool_helpers.py`（工具共享助手），main_window 2295→2241、tools_ext 1175→1061 · 性能基线 `tools/benchmark.py` 四项指标（冷启动 2.2s / 百万行导入 14.0s / 5k 图渲染 1.5s / 5k 行 ML 训练 1.5s）+ `perf_baseline.json` + CI 步骤（tolerance ×4，子进程隔离） | 基准入 CI；ruff 扩展门禁（含 UP 全家）零告警；全量回归通过 |

### v4.2.0 — 算法可信度与深度（已发布）

> 信任层：先证明算得对，再证明当时是怎么算的；并以最小纵向切片验证案例闭环可行性。
> **阶段顺序**：P0 契约基座 → P1 已知值矩阵 → P2 算法深度 → P3 稳定性 → P4 判定凭证与方法文档 → P5 首个闭环切片 → P6 收尾；P1–P3 只碰 `analysis/` + `tests/`，P4–P5 碰 `core/` + `ui/`，可并行排期（总计 4–6 周 + 20% 缓冲）。
> **执行版任务分解**（落点文件 / 验收命令 / 排期 / 技术债清单）：见 `PLAN_v4.2.0.md`（2026-09-22）。

| 阶段 | 交付 | 验收 |
|------|------|------|
| **P0 契约与测试基座** ✅ 2026-09-17 | 已知值规范 `KNOWN_VALUES.md` + 框架 `tests/known_values.py` · 判定凭证 schema v1 `core/evidence.py`（数据指纹 `pd-hash-v1` + 结论 diff）· 案例 schema v0 `core/improvement_case.py` · `.qap` 1.7 案例段（1.6 只读兼容） | 4 个契约测试文件 40 例通过；ruff 全库零告警；分层守卫通过 |
| **P1 已知值验证矩阵**（B1）✅ 2026-09-17（批次 1+2） | 7 域 12 文件 29 例：SPC（Xbar-R / I-MR / EWMA / CUSUM / Hotelling T² + Nelson 8 规则）· 能力（Cp/Cpk/Pp/Ppk/Cpm/PPM）· MSA（Cohen κ / Gage R&R 均值-极差）· DOE（2² 效应/SS）· 可靠性（KM / Crow-AMSAA / Weibull 2P-MLE）· 时序（ACF / ARIMA 随机游走）· ML（回归分类指标 / CART） | 29 例全绿；**发现并修复 2 处缺陷**（数值标签混淆矩阵全 0；DOE 完全拟合除零告警）；更深算法（MEWMA / 非正态 / Weibull CI / 调参）归 P2 交叉验证 |
| **P2 算法深度**（B2）✅ 2026-09-22 | 多元 SPC：`analysis/spc/mewma.py`（Lowry 1992，**逐点精确 Σ_Z(i)**，`baseline_size` 区分 Phase I/II，可切稳态近似）· `analysis/spc/gen_var.py`（Montgomery b1/b2 广义方差图）· `analysis/spc/change_point.py`（PELT 纯 numpy，K=0 剪枝与全局最优等价）· `analysis/spc/residual_chart.py`（ARIMA 白化 + I-MR + 前后对照）· `analysis/capability/non_normal_cap.py::bootstrap_capability_ci`（向量化百分位 Bootstrap + 小样本精度告警）· 可靠性区间（Weibull CI 与 lifelines 交叉验证 · ALT 外推区间修正）· ARIMA 自动选阶稳健性（NaN 索引崩溃修复、常量/短序列守卫、搜索空间按样本量收窄） | 新增 7 个 known-value 文件 60 例：MEWMA 在 r=1 时与 `hotelling.py` 逐点一致、受限越限率 0.00267 ≈ α=0.0027；PELT 与暴力 DP 全局最优代价一致、纯噪声 0 误报；AR(1) 数据残差图越限显著低于原始 I-MR；Bootstrap CI 覆盖率 0.94（n=1500）；Weibull β/η 覆盖率 0.940/0.945 且与 lifelines 端点差 <1%；ALT 平均寿命 CI 覆盖率 0.950（旧实现忽略杠杆项）；含缺测序列的 ARIMA 不再崩溃 |
| **P3 稳定性与大样本**（B3）✅ 2026-09-22 | 大样本基准扩展至 8 项（新增 `spc_100k_rows_s` / `spc_1m_rows_s` / `msa_100k_rows_s` / `ml_train_100k_rows_s`，实测 3.12s / 20.73s / 0.96s / 3.78s）· `tests/test_robustness_numeric.py` 22 例（规格限倒置 / 波动退化 / 常量与缺测控制图 / 秩亏协方差 / 单类别分类 / 零方差 DOE / 单操作员 MSA）· 覆盖率补口 `test_core_coverage_gaps.py` 16 例 + `test_analysis_coverage_gaps.py` 12 例（excel_utils / session_manager / audit / base_report_engine / between_within_cap / variance_tests / eight_d_engine）· **质量棘轮**：`BLE001`（盲除异常）纳入门禁，算法与报告层 31 处逐处理由清零 · 弃用清理（websockets 旧式连接 50 条告警清零；`main.py` 全局 RuntimeWarning 屏蔽改 `once`） | 基准入 CI 且 8 项全在 tolerance ×4 内；鲁棒性/覆盖补口用例全绿；`ruff check .` 零告警（含新启用的 BLE001）；全量逐文件回归 154 文件全通过 |
| **P4 判定凭证 + 方法文档**（B4）✅ 2026-09-22 | 结论凭证写入分析记录（`_store_analysis` → `core/evidence.make_credential`，指纹取该 Tab 实际分析数据，取不到降级 `no-data`）· 报告追溯码（`credential_trace` + PDF/Word/Excel 页脚 + i18n `report.trace_code`）· 复核模式（`diff_analysis_records` + 同 Tab 重跑自动比对 `rerun_diff`）· `.qap` 1.8 凭证段（1.6/1.7 只读兼容）· guide.html「方法与参考」（16 类方法出处 + 凭证语义） | 新增 18 例（`test_evidence_wiring.py` 15 + `.qap` 凭证 3）：同数据重跑 `identical=True`、改参差异可见、追溯码顺序无关且内容变化即变码、Excel 页脚可回读追溯码；ruff 零告警 |
| **P5 首个改善闭环切片**（B5）✅ 2026-09-22 | `core/case_workflow.py`：案例脊柱编排（8 阶段 = 基线测量 → 时间研究 → 线平衡瓶颈 → 改善方案 → 复测 → 配对检验 → 结论 → 标准草稿），每步留痕**时间戳 + 数据引用 + 判定凭证**（复用 P4 凭证），内置配对检验真实接线（`analysis.hypothesis.t_tests.paired`），支持 Markdown 导出与字典往返（`.qap` cases 段）；UI 入口：菜单「工具 → 改善案例工作台」+ `ui/dialogs/case_workflow_dialog.py`（阶段进度 + 留痕预览 + 导出 Markdown），动作自动以当前导入数据建立案例基线 | 新增 `tests/test_case_workflow.py` 14 例（端到端 8 阶段全链、凭证/引用/时间戳留痕、配对检验显著与无效应两向、Markdown/字典往返、旧案例兼容、菜单与入口离屏验证）；全量逐文件回归 157 文件全绿；ruff 零告警 |
| **P6 收尾** ✅ 2026-09-23 | 版本 4.2.0 四端一致 · README / guide / 本路线图同步 · 全量逐文件回归 + ruff 门禁 · 发布方式决策与执行（09-22 源码 prerelease → 09-23 打包发布：Linux AppImage 构建 + GitHub Release + `.sha256`） | `check_version.py` 通过；全绿；Demo 可复现；`bash build_appimage.sh` 产物可启动 |

**关键设计决策**：不新增硬依赖（PELT 自研；statsmodels 仅 dev 参考）· 凭证与案例 schema 放 `core/`（无 Qt）· `.qap` 增量兼容（1.6 可读，1.7 写出）· UI 入口复用 Home，不新增 Tab · 完整 MeasurementEvent 合同留到 4.3.0，本版只预留接口 · **Linux 发布只出 AppImage（2026-09-22 决定，`.deb` 构建链与 `packaging/deb/` 已移除）**。
**风险与对策**：已知值来源与许可（NIST 公有领域优先，文献值记录出处）· PELT 工程量（超期降级为二分分割）· 闭环切片范围蔓延（时间盒 1.5 周，只做单案例单模板）· 性能回归（P3 基线对比，超限即回退）。

### v4.3.0 — 改善案例与证据账本（规划）

> 数据模型层（最重要一步）：先立案例脊柱，再让时间、血缘、可信度成为它的机制；双时态只覆盖测量 / 标准 / 结论三类对象，不做全库改造。

| 批次 | 交付 | 验收 |
|------|------|------|
| **B1 改善案例对象与生命周期** | `ImprovementCase` 一等对象：阶段（基线测量 / 分析 / 改善 / 复测 / 验证 / 标准）、基线数据引用、分析结论引用、改善方案与实施记录；UI 入口优先复用 Home（确需新增 Tab 再评审）；旧 `.qap` 文件可加载 | 一个案例可完整回放「问题 → 改善 → 结果」；旧 `.qap` 零破坏 |
| **B2 MeasurementEvent 合同 + 插件数据源** | 统一 `MeasurementEvent`（source / method / ts / recorded_at / confidence / validity / raw_ref）；设备连接器、视觉插件、手工录入、文件导入统一产出；插件 API 2.1 新增 `data_source` 能力（2.0 插件不受影响） | 视觉插件可作为数据源注入案例；人工/CSV 路径同样可用 |
| **B3 标准版本记录** | 规格限 / 控制限 / 标准工时 / 作业组合票 / 控制计划条目增 `valid_from / valid_to / change_reason`；变更自动留痕；仅测量 / 标准 / 结论三类对象做双时态 | 任意历史批次可还原当时标准；可查「谁在何时、为什么改」 |
| **B4 证据视图与交换 v1** | 结论凭证（规则版本 + 参数 + 数据指纹 + 事件引用）接入账本；结构化 append-only 审计事件（数据编辑 / 告警确认 / 8D 处置 / 报告导出）；报告追溯码 + 证据链视图；`.qap` 证据包导出 + 脱敏分享包（合成数据 + 统计等价声明） | 结论可重放；报告每个数字可回指事件；脱敏包无原始值且可独立复核 |

### v4.4.0 — 闭环执行与效果验证（规划）

> 闭环层：质量与 IE 的改善动作都落在案例上；案例关闭必须用数据验证效果，不是填表。

| 批次 | 交付 | 验收 |
|------|------|------|
| **B1 告警自动立案 8D** | critical 告警自动生成 8D 草稿：数据快照 + 违规点 + ProjectContext 特性 + FMEA 条目；D1–D3 预填、D4 留空；D6 必须关联复测数据 + 统计判定（配对/SPC/能力），不接受纯文字 | 异常发生即立案（≤1 分钟）；案例关闭有数据证据 |
| **B2 测量系统在线化** | 标准件/重复测量自动积累 → 滚动重复性与偏倚 · 测量过程控制图 · 量具健康分（复用连接器健康模型）· 漂移超限提示重做研究 | MSA 由一次性研究变为持续状态；漂移可报警 |
| **B3 抽样转移状态机** | GB/T 2828.1 正常/加严/放宽按供应商·产品线自动转移；检验批历史记忆；方案留痕（为何本批加严） | 转移规则确定性执行；审核可追溯 |
| **B4 收益账本与 COPQ** | 改善案例收益账本（按月复算、标准版本口径一致、防重复计入）· COPQ 四类（预防/鉴定/内部失败/外部失败）+ ROI；仅 A/A-/B 级可信数据入账；改善与考核数据分区 | 回答「这条改善省了多少」；低可信数据被拦截 |
| **B5 技能约束线平衡（案例模板 #2）** | 技能矩阵（人员 × 工序 × 熟练度）+ 设备/人数约束接入 LPT，输出可执行排班建议而非仅平衡率；结果作为改善案例挂接基线与复测 | 理论平衡率在技能约束下可现场排班；合成数据端到端演示 |

### v4.5.0 — 生态开放与 AI 基础设施（规划）

> 接口层：把核心引擎开放为外部可调用能力，让 .qap / MCP / 规则包成为交换标准。

| 批次 | 交付 | 验收 |
|------|------|------|
| **B1 MCP 服务** | 工具注册表暴露为 MCP server：Claude Desktop / Cursor / AI IDE 可直接调用 SPC · 能力 · MSA · DOE · ML 引擎；默认只读 + 权限模型 | 外部 MCP 客户端一条指令完成真实分析 |
| **B2 原生工具调用** | JSON Schema 工具调用 + 流式输出替代提示词正则解析（保留降级路径）；工具路由与并行调用增强 | 工具命中率/稳定性提升；旧路径仍可用 |
| **B3 CLI 质量门禁 + SDK** | `akia check --spec quality.yaml`（Cpk / 判异 / 抽样合规）· headless 报告导出 · `akia-core` 本地 Python SDK | 一条命令出 CI 判定；企业系统可嵌入调用 |
| **B4 规则包与插件生态** | 行业规则包（IATF / ISO 13485 / IPC / HACCP：判异策略 + 抽样 + 报告模板 + 术语 + 告警规则）· 插件脚手架 CLI + 索引 + 兼容矩阵 + 2 示例插件 · i18n 框架 | 第三方 30 分钟跑通插件；规则包可导入导出 |

### v4.6.0 — 智能在线化与数据资产（规划）

> 资产层：模型与时间积累的数据产生复利；AI 从「会分析」走向「会建议」。

| 批次 | 交付 | 验收 |
|------|------|------|
| **B1 模型治理与在线评分** | 模型注册表 / 版本 / 模型卡 · 训练 → 部署 → 实时看板在线推理与预测告警 · 漂移监控 · 模板批量分析接入 ML | 模型可追溯；漂移报警可演示；E2E 在线评分 |
| **B2 工艺参数窗口推荐** | DOE 响应曲面 + ML 特征重要性 + 实时数据 → 给定质量目标的参数可接受区间（置信水平 + 样本量要求）；注塑/焊接模板 | 冻结验证集命中率达标；输出可执行建议 |
| **B3 IE 证据链** | IE 版 SPC（标准工时 / 节拍 / 平衡率稳定性）· 面向操作员的标准作业票与班组视图 · 改善收益自动入账（技能约束线平衡已在 4.4 交付） | IE 波动可判定；操作员视图可用；收益自动入账 |
| **B4 本地数据资产与边缘** | 本地过程基线 / 量具健康史 / 案例库沉淀与检索 · ESP32 边缘判异 + 断网续传 · 连接器扩展 · 轻量调参与预测区间 | 资产随使用增厚、可检索；断网数据不丢 |

> 视觉在线化（无感测量、消除观测偏差）由 Vision-expansion 插件承载，主应用只提供接口与证据格式。

> 匿名行业基准需服务端汇聚与隐私评审，列为独立服务端阶段候选，不进本仓库近期批次。

> **4.6 之后（候选）**：完整英文语言包与本地化 · 浅色/高对比主题与可访问性 · 自动更新 · 订阅与激活 · 移动端看板 · 多站点协同 · 服务端阶段（匿名基准 / 多客户端汇聚 / 工厂级看板）。

---

## 工程约定

- **版本**：`config/settings.py::APP_VERSION` 为单一事实源；`tools/check_version.py` 校验 version_info / Inno / README / INSTALL / ROADMAP，CI 门禁
- **构建**：PyInstaller onedir（`build_pyinstaller.py`）→ Inno（Windows）/ AppImage（**Linux 唯一发布格式**）；`build/`、`dist/` 不入库
- **测试**：严禁 `pytest tests/` 批量（conftest 有拦截器），逐文件运行；GUI 测试 `QT_QPA_PLATFORM=offscreen`
- **质量门禁**：ruff 零告警 + 相关回归 + 打包冒烟（发布版本必做）
- **分层**：`analysis/` 禁 Qt；`core`/`config`/`output` 禁 import `ui`；`core/agent/` 保持无 Qt
- **插件**：只通过 `core/plugin_api.py` 交互，API 大版本兼容；未信任插件不导入
- **文档同步**：README 中英 / 使用指南 guide.html / 本路线图随功能变更同步
- **新增 Tab 检查清单**：注册表 → 工作表路由（`sheet_map` / `all_indices`）→ 空状态分类（`_EMPTY_STATE_SKIP` 或数据模型判定）→ 菜单 / 命令面板入口 → 回归用例（`tests/test_tab_data_routing.py`）

---

## 侧边栏演进

> v2.6.5 ~ v3.0.0 不新增 Tab（深化为主）；v3.8.0 以对话式 Agent 为主；v4.1.0 ~ v4.6.0 以深化为主，原则上不新增 Tab；案例工作台优先复用 Home，确需新增须显式评审。

| 版本 | Tab 数 | 变化 |
|------|--------|------|
| v2.0 | 28 | 初始（Home / Quality / IE / Charts / Eng / Worksheet / Sampling / Report / Data / Plugins） |
| v2.2 | 32 | +SMED · +TPM · +8D · +PPAP |
| v2.4 | 34 | +实时监控 · +多产线 |
| v2.5 ~ v2.6 | 35 | +设备监控（Tab 35） |
| v3.3.0 | 36 | +时间序列 |
| v3.8.0 | 36 + 插件 | 视觉 Tab 迁出；插件 Tab 动态索引（≥37）；QAM Harness 为对话窗口（非 Tab） |
| v4.0.0 | 37 + 插件 | +预测分析（Tab 37）；插件 Tab 从 38 起 |
| v4.1.0 ~ v4.6.0 | 37 + 插件 | 原则上不新增 Tab（案例工作台优先复用 Home；证据视图 / 在线评分挂接现有 Tab 与对话框；视觉在线化归插件项目） |
