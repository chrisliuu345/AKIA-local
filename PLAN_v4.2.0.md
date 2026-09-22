# QA-Tool v4.2.0 开发方案（执行版）

> 依据 `ROADMAP.md`「v4.2.0 — 算法可信度与深度」，把 P2–P6 拆成可直接排期的任务：
> 每项含**落点文件 / 验收方式 / 风险**。本文只描述执行路径，版本语义与设计决策仍以路线图为准。

**基线（2026-09-22 实测）**：144 个测试文件 / 1798 用例全绿（逐文件单进程执行）；ruff 全库零告警；
性能基线通过（冷启动 2.08s · 百万行导入 14.2s · 5k 图渲染 1.27s · 5k 行 ML 1.41s）；
Linux 发布形态为 **AppImage 单一格式**。

---

## 1. 现状盘点（P0–P6）

| 阶段 | 状态 | 证据 / 缺口 |
|------|------|-------------|
| **P0 契约基座** | ✅ 已交付 | `core/evidence.py`（`pd-hash-v1` 数据指纹 · 凭证 diff）· `core/improvement_case.py` · `.qap` 1.7 案例段 · `KNOWN_VALUES.md` |
| **P1 已知值矩阵** | ✅ 已交付 | `tests/known_values.py` 框架 + 13 个 `test_known_values_*.py`（SPC/能力/MSA/DOE/可靠性/时序/ML） |
| **P2 算法深度** | ❌ 未开工 | `analysis/spc/` 有 `hotelling.py`，**无 MEWMA / 广义方差 / 变点检测 / 自相关残差图**；`analysis/capability/non_normal_cap.py` 只有 percentile + Johnson，**无 Bootstrap 区间**；`analysis/time_series/arima.py::_auto_select` 已存在，需稳健性补强 |
| **P3 稳定性与大样本** | ❌ 未开工 | `tools/perf_baseline.json` 仅 4 项指标，无 10 万 / 100 万行档；无病态矩阵与极端值专项用例 |
| **P4 判定凭证接线** | ❌ 未开工 | `credential` 在 `core/evidence.py` 之外**零引用**——分析记录、报告、`.qap` 均未写入凭证 |
| **P5 闭环切片** | ❌ 未开工 | `ImprovementCase` 仅有 schema；Home（`ui/welcome_page.py`，已有卡片 + 最近项目）可直接复用为入口 |
| **P6 收尾** | ❌ 未开工 | — |

---

## 2. 任务分解

### P2 算法深度（≈1.5 周，只碰 `analysis/` + `tests/`）✅ 2026-09-22 完成

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P2-1 ✅ | **MEWMA 多元指数加权移动平均图** | `analysis/spc/mewma.py`（逐点精确 Σ_Z(i) + `baseline_size` + `variance="steady_state"` 可选） | `tests/test_known_values_spc_mewma.py` 10 例：递推手算、闭式 Σ_Z、r=1 与 `hotelling.py` 逐点一致、越限率 0.00267 ≈ α |
| P2-2 ✅ | **广义方差控制图** | `analysis/spc/gen_var.py`（b1/b2 闭式 + 合并协方差） | `tests/test_known_values_spc_genvar.py` 7 例：p=2,n=10 手算 b1=8/9、b2=2736/6561；方差放大子组被检出 |
| P2-3 ✅ | **变点检测 PELT（纯 numpy）** | `analysis/spc/change_point.py`（mean / meanvar 两种代价，K=0 剪枝） | `tests/test_known_values_spc_change_point.py` 8 例：与暴力 DP 全局最优代价一致（多罚项）、5σ 漂移定位 ±2、纯噪声 0 误报 |
| P2-4 ✅ | **自相关残差控制图** | `analysis/spc/residual_chart.py`（ARIMA 白化 → I-MR + 前后对照 + 降级路径） | `tests/test_known_values_spc_residual_chart.py` 6 例：AR(1) 原始 lag-1 自相关 >0.5、残差 <0.2、越限显著减少；常量/报错分支降级 |
| P2-5 ✅ | **非正态能力 Bootstrap 置信区间** | `analysis/capability/non_normal_cap.py::bootstrap_capability_ci` | `tests/test_known_values_capability_bootstrap.py` 11 例：可复现、覆盖率 0.94（n=1500）、区间随样本收窄；**小样本精度告警**（n<1000 点估计偏高） |
| P2-6 ✅ | **可靠性区间补强** | `analysis/reliability/weibull.py`（已有 Fisher CI 交叉验证）+ `analysis/reliability/alt.py`（外推区间修正） | `tests/test_known_values_reliability_intervals.py` 8 例：Weibull 与 lifelines 端点差 <1%、覆盖率 0.940/0.945；ALT CI 覆盖率 0.950（修正前忽略杠杆项）；KM CI 不变式 |
| P2-7 ✅ | **ARIMA 自动选阶稳健性** | `analysis/time_series/arima.py` | `tests/test_known_values_ts_arima_robustness.py` 10 例：**修复含缺测序列崩溃**（`No supported index`）、常量序列结构化 error、搜索空间按样本量收窄、随机游走 d≥1、季节序列有限诊断 |

**P2 完成记录（2026-09-22）**

- 交付：4 个新 SPC 模块 + 3 处能力/可靠性/时序增强；新增 7 个 known-value 文件共 60 例，全量与定向回归全绿（`ruff` 零告警）。
- 过程中发现并修复的真实缺陷：
  1. **ARIMA 含缺测序列崩溃** —— `dropna()` 后索引空洞导致 `get_forecast` 抛 `No supported index is available`；已重置索引并补预测失败兜底。
  2. **ALT 外推区间系统性过窄** —— 旧实现用 `±1.96·se` 忽略外推点杠杆项，与"平均寿命 CI / 单样本 PI"混用；改为带杠杆项的 t 区间，覆盖率由修复前不足升至 0.950。
  3. **MEWMA 早期点低估** —— 稳态 Σ_Z 会压低前 20 余点 T²（实测均值 1.40 vs 理论 2.0）；改默认逐点精确 Σ_Z(i)，稳态形式保留为可选项。
  4. **PELT 默认罚项过松** —— 固定种子标定显示 1.0σ̂²log n 时纯噪声 60 个误报/20 序列；改为 2.5σ̂²log n 后 0 误报且 1.5σ 漂移检出率不变（19/20）。
- 已知限制（写入模块文档与返回值）：百分位法能力区间在 n<1000 时有系统偏差（`accuracy_warning` 字段提示）；RBD 为确定性网络模型，暂无区间传播（后续按需评估 Monte Carlo）。
- **待接线**：按方案 P1–P3 只碰 `analysis/`+`tests/`，4 个新算法尚未进入 SPC Tab 与 Agent 工具（`core/agent/tools.py`）；建议在 P4 凭证接线时一并暴露，并补 Tab 路由回归。

**P2 出口标准**：每个新算法都有 known-value 用例文件；`ruff` 零告警；全量逐文件回归全绿。

### P3 稳定性与大样本（≈1 周，可与 P2 并行）✅ 2026-09-22 完成

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P3-1 ✅ | 大样本基准扩展 | `tools/benchmark.py` + `perf_baseline.json`（8 项，新增 SPC 10 万/100 万、MSA 10 万、ML 10 万） | 实测 3.12 / 20.73 / 0.96 / 3.78 s；`--tolerance 4` 门禁通过；每项独立子进程 + 线程上限，无内存峰值 |
| P3-2 ✅ | 病态矩阵与极端值鲁棒性用例 | `tests/test_robustness_numeric.py` 22 例 | 规格限倒置 → 结构化 error（修前输出负 Cp）；波动退化（σ≈0）→ 结构化 error（修前 Cp≈2e12 且评 A+）；常量/缺测控制图、秩亏协方差、单类别分类、零方差 DOE、单操作员 MSA 均不崩溃 |
| P3-3 ✅ | **质量棘轮**：`BLE001` 纳入门禁 | `ruff.toml`（算法与报告层 31 处逐处理由清零；core 81 / ui 111 / firmware 19 / connectors 10 / server 2 / 根文件 2 为存量，列入 per-file-ignores 并写明收敛顺序） | `ruff check .` 零告警；自测"新插入盲除即门禁失败"已验证 |
| P3-4 ✅ | 覆盖率补口 | `tests/test_core_coverage_gaps.py`（16 例）+ `tests/test_analysis_coverage_gaps.py`（12 例） | 7 个模块均有直接测试引用；过程中发现并修复 **会话 ID 秒级冲突导致 save() 互相覆盖** 与 `variance_tests` 返回 numpy bool（JSON 序列化隐患） |
| P3-5 ✅ | 遗留弃用清理 | `tests/test_live_dashboard.py`（websockets 改上下文管理器 / 硬断连场景显式 `legacy=True`）；`main.py` 全局 `RuntimeWarning` 屏蔽改 `once` | 50 条 DeprecationWarning 清零；数值退化告警每个位置提示一次而非静默丢弃 |

**P3 完成记录（2026-09-22）**

- 过程中发现并修复的真实缺陷：
  1. **能力指数在规格限倒置时输出负值**（Cp=−0.20、良率 −13.9%）—— 新增 `spec_limit_error` 校验，改返回结构化 error。
  2. **波动退化时 Cp 达 1e12 并被评 "A+ (特优)"** —— 新增 `degenerate_spread_error`（|max−min| ≤ 1e-9×公差宽度 视为数值退化）。
  3. **会话 ID 秒级冲突**：同一秒内连续建会话 → `session_{id}.json` 互相覆盖（列表里只剩一个）—— 建会话时与磁盘去重并加序号后缀。
  4. `variance_tests` 返回 `np.bool_`，写入 JSON 会抛 TypeError —— 统一 `bool()`。
- 性能观察（计入后续优化候选）：SPC 100 万点 20.7s，瓶颈在 Nelson 规则 2/3/4 的 Python 循环（逐点扫描）；如需在线大样本监控可向量化，当前列入 P4 之后候选。
- `main.py` 的 `np.errstate` 就地化未做（会把噪声推给用户），改为 `once` 策略并记录理由；彻底就地化需逐处定位 log/div 边界，列入后续候选。

### P4 判定凭证 + 方法文档（≈1 周，碰 `core/` + `ui/` + `output/`）✅ 2026-09-22 完成

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P4-1 ✅ | **分析记录写入凭证** | `_store_analysis` + `_analysis_source_frame` + `make_credential` | 记录含 rule_version / params / 数据指纹 / app_version；无数据记 `no-data`；取数异常不阻断分析 |
| P4-2 ✅ | 报告追溯码 | `base_report_engine.footers(trace=…)` + `credential_trace`；Excel / PDF / Word 接入；`locales/zh.json` 增 `report.trace_code` | Excel 报告落盘后页脚可回读 12 位追溯码（测试断言） |
| P4-3 ✅ | 重跑复核模式（核心） | `core/evidence.diff_analysis_records` + `_store_analysis` 自动写入 `rerun_diff` | 同数据重跑 `identical=True`；改参可见 `params` old/new；缺凭证 → `comparable=False` |
| P4-4 ✅ | guide.html「方法与参考」 | `config/help/guide.html` 新增 `#methods` 章节 + 目录项 | 16 类方法出处（NIST/Montgomery/AIAG/Lowry/Killick/…）+ 凭证与追溯码语义；`test_help_guide` 全通过 |
| P4-5 ✅ | `.qap` 凭证段（1.7 → 1.8） | `core/project_manager.py`（VERSION 1.8 / `credential_count` / 条目凭证） | 1.8 凭证往返一致；无凭证项目正常保存；手工 1.7 布局可读 |

**P4 完成记录（2026-09-22）**

- 交付：凭证闭环（分析记录 → 报告页脚 → `.qap` → 重跑 diff）+ 方法文档章节。
- 设计取舍：① 指纹取该 Tab 实际分析数据，逐级降级（`tab.df` → 导入首表 → `no-data`），失败绝不阻断分析；
  ② 追溯码由全部凭证内容压缩（顺序无关、内容变化即变码），不保存原始数据副本；
  ③ `.qap` 1.8 只读兼容 1.6/1.7，旧文件在复核模式下显示"不可比较"而非报错。
- 已知限制（已记入测试与文档）：**复核模式 UI 弹窗未做**（核心 diff 已可用并自动落档，对话框/复核视图归 P5–P6）；
  HTML 导出未接追溯码（Excel/PDF/Word 已接）。

### P5 首个改善闭环切片（≈1.5 周，时间盒，超期即缩范围）✅ 2026-09-22 完成

流程：**基线测量 → 时间研究 → 线平衡瓶颈 → 改善方案 → 复测 → 配对检验 → 结论 → 标准草稿**

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P5-1 ✅ | 工作台入口（新建 / 查看案例） | 菜单「工具 → 改善案例工作台」+ `ui/dialogs/case_workflow_dialog.py`（阶段进度 / 留痕预览 / 导出 Markdown） | 不新增 Tab；动作以当前导入数据自动建立案例基线；离屏测试验证菜单与入口 |
| P5-2 ✅ | 案例脊柱驱动各步（时间戳 + 数据引用 + 凭证） | `core/case_workflow.py`（8 阶段编排，`record_step` 留痕，复用 P4 凭证） | 单案例端到端可复现；每步可回看数据引用与指纹 |
| P5-3 ✅ | 数据源：手动 / CSV（插件数据源预留） | 工作流以 `frame` + `data_ref` 接收任意来源数据（手工/CSV/导入表） | 数据来源与编排解耦，插件可按同一契约喂数据 |
| P5-4 ✅ | 旧 `.qap` 零破坏 | `CaseWorkflow.from_dict` 兼容旧 cases 段（无阶段元数据亦可读） | 旧案例恢复用例通过 |
| P5-5 ✅ | E2E 演示 | `tests/test_case_workflow.py` 14 例（含全链路）+ 菜单/入口离屏验证 | 一键复现八阶段闭环（含真实配对检验） |

**P5 完成记录（2026-09-22）**

- 交付：`core/case_workflow.py`（无 Qt，分层守卫通过）+ 工作台对话框 + 菜单入口 + 14 例测试。
- 设计取舍：① 工作流**只编排与留痕**，统计计算全部复用既有引擎（配对检验真实接线），避免算法二套实现；
  ② 每步凭证复用 P4 的 `make_credential`，`data_ref` 与数据指纹一并入库，可与报告追溯码对齐；
  ③ 未走完的案例允许保存（`missing_phases` 明确提示），符合"边做边记"的现场用法。
- 过程中修复：`analysis.hypothesis`（t 检验 / ANOVA / 比例）与 `analysis/msa`（线性、Type 1）的
  `is_significant` 返回 numpy bool —— 写入 `.qap` 会被序列化成字符串，统一改 Python `bool`。
- 已知限制：案例的**步骤数据仍需由各 Tab 或引擎产出后喂给工作流**（TimeStudy / LineBalance 的引擎类型尚未直接接入编排层），
  完整"在各 Tab 内一键推进下一步"的联动归 P6 或 v4.3.0 案例工作台。

### P6 收尾（≈0.5 周）

- 版本 4.2.0 四端一致：`config/settings.py` · `version_info.txt` · `packaging/QA-Tool-installer.iss` · README/INSTALL/ROADMAP/guide → `tools/check_version.py` 通过
- 文档同步（中英）+ 全量逐文件回归 + ruff + 性能基线
- **发布形态**：Linux 仅 `build_appimage.sh` 产出 AppImage；Windows 安装包在 Windows 侧由 Inno 脚本构建

---

## 3. 排期与并行

| 周次 | 分析线 | 工程线 |
|------|--------|--------|
| W1 | P2-1 / P2-2（多元 SPC） | P3-1 大样本基准 |
| W2 | P2-3 / P2-4（变点 / 残差图） | P3-2 / P3-3（鲁棒性 + 质量棘轮） |
| W3 | P2-5 / P2-6 / P2-7（区间与稳健性） | P4-1 凭证接线 |
| W4 | P4-2 / P4-3 / P4-4（追溯与文档） | P3-4 / P3-5（覆盖率与弃用清理） |
| W5–W6 | P5 闭环切片（时间盒 1.5 周） | P6 收尾与发布 |

> 缓冲：整体 +20%。P2 与 P3 无文件冲突可并行；P5 依赖 P4-1 的凭证落地。

---

## 4. 每次提交的门禁（沿用 CI）

1. `ruff check .` 零告警
2. 逐文件 `pytest tests/test_xxx.py`（**严禁** `pytest tests/` 批量；conftest 有拦截器）
3. 新算法必须带 known-value 用例（`tests/known_values.py` 框架）
4. 性能敏感改动跑 `tools/benchmark.py --tolerance 4`
5. 发布前：`tools/check_version.py` + 打包冒烟（AppImage 启动 + 主窗口冷启动）

---

## 5. 技术债清单（2026-09-22 实测规模，按优先级）

| 项 | 规模 | 建议 | 归属 |
|----|------|------|------|
| 时间戳无时区（`datetime.now()`） | 56 处 | 与 v4.3.0 双时态一起定语义，勿单独改 | v4.3.0 |
| 遗留 `np.random` 全局随机 | 587 处 | 迁移 `np.random.Generator` + 显式种子（需同步已知值期望） | P3 |
| 盲除异常 `except Exception` | 271 处（非 UI 111） | 棘轮：`BLE001` 入门禁 + 逐处理由 | P3-3 |
| `except ...: pass` 静默吞异常 | 79 处（关键路径 6 处本次已补日志） | 按域补 `logger.debug/warning` | P3 |
| `PERF401` / `SIM105` | 37 / 22 处 | 机械清理（可自动修复） | P3 |
| `pathlib` 迁移（`PTH*`） | ≈250 处 | 低优先，禁止新增 `os.path` 用法 | 后续 |
| 全局 `RuntimeWarning` 屏蔽 | `main.py:24` | 改为就地 `np.errstate` | P3-5 |
| 全角标点告警（`RUF001/002/003`） | 4000+ | 中文语境噪声，不启用 | 不修 |

---

## 6. 风险与对策

| 风险 | 对策 |
|------|------|
| PELT 工程量超期 | 时间盒内降级为二分分割；先保证接口与用例 |
| 已知值来源与许可 | NIST 公有领域优先；文献值记录出处（进 guide「方法与参考」） |
| 闭环切片范围蔓延 | 只做单案例单模板，时间盒 1.5 周 |
| 性能回归 | P3 基线对比，超 tolerance ×4 即回退 |
| 大批量测试导致内存峰值/死锁 | 逐文件单进程执行 + `OMP/OPENBLAS/MKL_NUM_THREADS=2`；禁止多文件合并跑 |
| 沙箱/CI 无本地 socket | 服务端相关用例在具备 socket 的环境单独复跑（`test_dashboard_auth` 等 7 文件） |

---

## 7. 立刻可开工的前 5 件事

1. **P2-1 MEWMA**：以 `analysis/spc/hotelling.py` 为模板，先写已知值用例
2. **P2-5 非正态能力 Bootstrap CI**：改动面最小、用户可见价值高
3. **P3-1 大样本基准**：先加 10 万行档，跑通再上 100 万
4. **P4-1 凭证写入分析记录**：打通 `core/evidence.py` → `ui/main_window.py::_store_analysis`，是 P4/P5 的地基
5. **P3-3 质量棘轮**：`BLE001` 入门禁（非 UI 111 处）
