# AKIA v4.4.0 开发方案（执行版）— 闭环执行与效果验证

> 依据 `ROADMAP.md`「v4.4.0 — 闭环执行与效果验证」（B1–B5 决策项 + 10-11 排期新增
> B3 扩容与 B6 抽样透明化收口），把数据模型、接线、UI、迁移、性能与发布拆成
> 可直接排期的 B0–B8 批次；每项含**落点文件 / 验收方式 / 依赖与风险**。
> 设计决策仍以路线图为准，本文只描述执行路径。
>
> 探索日期：2026-10-12（HEAD `b8228bb`，v4.3.0 + 10-11 质量审查修复）。
> **执行进度（2026-10-12）**：B0 ✅ 契约基座与 `.qap` 2.0（含抽样表重建，发现并修复
> v4.3.0 遗留缺陷）；B1–B8 待开工；B0 契约已冻结，功能批次可开工。

**基线（v4.3.0 发布 + 审查修复后实测）**：178 个测试文件 / 2194 通过 / 56 跳过 /
0 失败（514.2s）；ruff 全库零告警；性能基线 10 项通过；`.qap` 1.9（1.6–1.8 只读兼容）；
Linux AppImage `AKIA-4.3.0-x86_64.AppImage` 已发布。审查遗留项见
`docs/quality/2026-10-11-v4.3.0-review.md` 第 3 节（部分并入本版 B7）。

---

## 1. 现状盘点：已有资产与真实缺口

### 1.1 已具备（v4.2.0–v4.3.0 交付，直接复用）

| 能力 | 落点 | 现状 |
|------|------|------|
| 案例脊柱 | `core/improvement_case.py` / `core/case_workflow.py` | v1 状态机（关闭门禁=复测+统计判定）+ 8 阶段工作台 + `.qap` 持久化用例 |
| 证据链 | `core/evidence_ledger.py` / `core/evidence.py` / `core/evidence_pack.py` / `core/share_pack.py` | sha256 哈希链 + 判定凭证 + 证据包独立校验 + 脱敏分享包（有界扫描） |
| 测量四通道 | `core/measurement_event.py` / `core/measurement_store.py` / `core/plugin_manager.py` | MeasurementEvent 合同 + 连接器/插件/手工/文件适配器 + 来源强制与坏数据隔离 |
| 标准版本 | `core/standard_record.py` + `core/project_context.py` | 五类对象 + as-of 复判 + `standard_ref` 进凭证；注册表追加已原子化 |
| 实时告警 | `core/streaming/alerts.py` / `alert_journal.py` | AlertRule/AlertEvent 分级（info/warning/critical）+ 去抖 + 邮件/webhook/桌面/journal/联动动作；ack 进账本 |
| 实时数据 | `core/streaming/{bus,collector,live_spc,oee_live,cost,downtime}.py` | StreamBus + SQLite 时序 + LiveSPC（滚动 I-MR/XBar-R）+ LiveOEE（节拍/班次）+ 成本损失 + 停机原因码 |
| MSA 引擎 | `analysis/msa/{gage_rr,type1_study,linearity_bias,emp,attribute_agree}.py` | 一次性研究全部就绪（均值极差/R 法/嵌套/Type1 Cg-Cgk/线性偏倚/EMP/Kappa） |
| IE 引擎 | `analysis/ie/{line_balance,time_study,work_sampling}.py` | LPT 平衡（Process: 节拍/人数/前置）+ 时间研究 + 标准工时 |
| 健康模型 | `connectors/health.py` | 状态机（ok/error/stopped）+ 指数退避 + 快照 — 量具健康分可借形 |
| 抽样引擎 | `core/sampling_engine.py` / `ui/tabs/sampling_tab.py` | AQL 正常表 + 随机/分层/系统 + 序贯 + 计量型（GB/T 6378）+ C=0；手动计算器 UI |
| 8D 工具 | `analysis/quality/eight_d_engine.py` / `ui/tabs/eight_d_tab.py` | D1–D8 结构化报告 + 鱼骨/FMEA 导入 + D7 标准复审检查；报告存 `ProjectContext.eight_d_reports` |
| AI 工具链 | `core/agent/tools*.py` | 37 个本地工具（SPC/能力/MSA/IE/成本/告警/五链…），可挂新工具 |

### 1.2 关键缺口（直接影响 v4.4.0 验收）

| # | 缺口 | 证据 | 归属批次 |
|---|------|------|----------|
| G1 | **告警不立案**：critical 告警只通知/留痕/journal，无 8D 草稿与案例对象；全库无「自动立案」 | `core/streaming/alerts.py`；`rg "自动立案"` 无结果 | B1 |
| G2 | **D6 无数据门禁**：8D 的 D6 只是两个文本框（实施说明/验证结果），无法关联复测数据与统计判定 | `ui/tabs/eight_d_tab.py:339`；`analysis/quality/eight_d_engine.py:48` | B1 |
| G3 | **测量系统一次性**：MSA 只能对导入表跑一次性研究；无标准件滚动重复性/偏倚累计、无测量过程控制图、无漂移告警；health 模型未复用于量具 | `analysis/msa/*`（无滚动/状态类）；`connectors/health.py` 未被 MSA 引用 | B2 |
| G4 | **抽样无转移/无历史**：只有正常检验表；无加严/放宽表、无转移规则、无检验批记忆；抽样决定不进账本 | `core/sampling_engine.py:335`（仅 `_NORMAL_TABLE`）；`EVENT_TYPES` 无 sampling 事件 | B3 |
| G5 | **抽样不可复现**：`systematic_sample` 用 `np.random.randint` 无种子；抽样方案与样本行没有任何指纹留痕 | `core/sampling_engine.py:382` | B3/B6 |
| G6 | **无收益账本与 COPQ**：全库无 COPQ/收益概念；改善效益无法按月复算入账；`CostAnalyzer` 只算实时超规格损失 | `rg "COPQ|收益账本"` 无结果；`core/streaming/cost.py:29` | B4 |
| G7 | **线平衡无技能约束**：LPT 只用节拍/人数/前置，无技能矩阵；输出是平衡率而非可执行排班 | `analysis/ie/line_balance.py:12`；`rg "技能矩阵"` 无结果 | B5 |
| G8 | **展示/分析层抽样不透明**：图表 300 点系统抽稀、趋势 1000 点、画像大表跳过正态检验；无统一「抽样决定」记录 | `output/chart_engine.py:37`；`ui/tabs/trend_tab.py:153`；`core/data_profiler.py:110` | B6 |
| G9 | **v4.3.0 审查遗留**：`measurement_capture` 无开关（死路径）；控制计划逐次提交产生版本噪音；SPC 多图只记第一张控制限；主窗口菜单动作缺端到端冒烟 | `docs/quality/2026-10-11-v4.3.0-review.md` 第 3 节 | B7 |

### 1.3 复用而不重做的边界

- **案例/证据不推倒**：8D 自动立案复用 `ImprovementCase` + `CaseWorkflow`；草稿内容写入
  步骤 `result` 与 `measurement_refs`，关闭门禁沿用 v4.3.0 规则（不新造 8D 状态机）。
- **标准注册表不扩散**：抽样方案登记为 `StandardRegistry` 新对象类型 `sampling_plan`，
  复用 as-of/留痕/指纹，不建第二套版本表。
- **滚动统计复用 LiveSPC**：测量过程控制图直接用 `core/streaming/live_spc.py`（I-MR 已够用），
  不新写控制图算法；MSA 一次性引擎保持原样（在线化只是新增滚动层）。
- **健康分借形不借类**：量具健康分参考 `connectors/health.py` 的字段与退避思想，但独立
  无 Qt 的 `GaugeHealth`（量具语义：重复性/偏倚/覆盖率）。
- **`.qap` 增量兼容**：2.0 新增段，1.6–1.9 只读兼容；读旧写新，不迁移不改旧段语义。
- **不新增 Tab**：技能矩阵编辑器、收益台账、测量在线面板均以现有 Tab 的对话框/面板承载
  （如需新增，按「新增 Tab 检查清单」五步接线单独评审）。

## 2. 版本目标与范围

### 2.1 一句话目标

让「改善」从被动记录升级为**自动触发、在线验证、收益可算**的闭环：critical 异常自动立案 8D；
量具从一次性研究变为持续状态；抽样从查表计算器变为带转移规则与证据留痕的确定性流程；
改善收益按月按当时标准口径复算入账；线平衡输出可现场排班的技能约束方案。

### 2.2 范围内

1. B0 契约基座：抽样/量具/收益/技能四域 schema + 账本事件类型 + `.qap` 2.0（冻结后才写功能）；
2. B1 告警自动立案 8D（D1–D3 预填、D6 数据门禁、去重与冷却、案例中心入口）；
3. B2 测量系统在线化（滚动重复性/偏倚、测量过程控制图、量具健康分、漂移提示）；
4. B3 可信抽样（转移状态机、检验批历史、方案留痕、抽样决定入账本、方法选择与确定性）；
5. B4 收益账本与 COPQ（按月复算、口径=当时标准版本、防重复计入、置信分级入账）；
6. B5 技能约束线平衡（技能矩阵 + 约束排班 + 案例模板 #2）；
7. B6 抽样透明化收口（展示/分析层隐式抽稀统一「抽样决定」记录与可复现修复）；
8. B7 集成、性能与质量收口（含 v4.3.0 审查遗留项落地）；
9. B8 版本收尾与发布（版本四端一致、门禁、AppImage、迁移手册）。

### 2.3 范围外（明确不做，避免范围蔓延）

- 不做 MCP / CLI / SDK / 规则包 / i18n 框架（v4.5.0）；
- 不做模型治理与在线评分、工艺参数窗口、IE 证据链（v4.6.0）；
- 不做放宽检验的"自动放宽"（默认禁用，仅保留显式策略开关，见 §8 决策 3）；
- 不重写 MSA 一次性引擎、不重写告警引擎、不新建案例/证据/标准第二套体系；
- 不引入新硬依赖（转移状态机、滚动统计、收益计算全部标准库 + pandas/numpy）；
- 不做服务端汇聚/云/多公司平台；视觉由 `AKIA-Vision-expansion` 插件承载。

## 3. 核心数据契约（先冻结，再实现）

> 原则沿用 v4.3.0：**账本只存引用与摘要**；schema 带 `schema_version`，未知版本拒读；
> 时间一律走 `core/time_utils`（带时区 ISO-8601）；新模块保持无 Qt（core 分层守卫）。

### 3.1 抽样域（B0 冻结）

```
LotRecord        lot_id  supplier  product  line  qty  inspected  defects
                 plan_ref(StandardRecord ID)  ts  actor  raw_ref
TransferPolicy   scope_key(supplier+product)  state ∈ normal|tightened|reduced
                 history[{lot_id, decision, at}]  override_reason
SamplingDecision method(random|stratified|systematic|sequential|measurement|c0)
                 seed  n  aql  level  plan_ref  row_fingerprint(pd-hash-v1)
                 sampled_at  actor  source_ref
```

- 转移规则（确定性、每步可解释）：正常→加严（连续 2 批拒收，或 1 批严重不合格）；
  加严→正常（连续 5 批接收）；正常→放宽（连续 10 批接收 + 生产稳定声明 + 显式启用）；
  放宽→正常（1 批拒收，或生产不稳定声明）。每次转移写 `sampling_transfer_changed` 事件
  （含触发依据：哪几批、什么判定）。
- 样本选取必须可复现：记录 `seed` + `row_fingerprint`（对抽样结果 DataFrame 用
  `core/evidence.fingerprint_dataframe`，同数据同参数→逐行一致）。
- 账本新事件类型：`sampling_plan_selected` / `lot_inspected` / `sampling_transfer_changed`。
- 加严/放宽 AQL 表（GB/T 2828.1 表 2-A/B/C）进 `core/sampling_engine.py`；放宽附加条件
  默认关闭（§8 决策 3）。

### 3.2 告警立案域（B0 冻结）

```
AlertCaseLink   alert_id  case_id  rule_key(device+channel)  severity  at
                snapshot{device, channel, value, usl, lsl, kind, desc, ts, rule_version}
8D 草稿映射      D1 团队(默认值) · D2 问题描述(由 snapshot+ProjectContext 特性生成)
                D3 临时措施(留空待填) · D4 根因(留空) · D6 必须挂复测+统计判定
```

- 立案条件：`severity == critical`（默认）；去重规则：同一 `rule_key` 冷却 30 分钟
  （冷却期内的后续告警并入同案步骤，不重复立案）；一案一 `AlertCaseLink`。
- D6 门禁复用案例关闭门禁：`verify` 阶段须带凭证且含统计判定字段 + `measurement_refs`
  非空；纯文字不接受。
- 账本新事件类型：`alert_case_opened`（含 alert_id→case_id 链接）。

### 3.3 测量在线域（B0 冻结）

```
GaugeStudyPolicy  gauge_id(device:channel)  standard_ref(StandardRecord)  expected_value
                  window_n  drift_rule{ucl,lcl 或 cusum_h}  enabled  updated_at
GaugeRollingState gauge_id  n  repeatability_sigma  bias  bias_history[]  health_score(0-100)
                  state ∈ ok|watch|drift  last_prompt_at
```

- 数据来源：`MeasurementEvent`（手工/连接器/插件三通道统一入口）；标准件测量以
  `source_kind` 与 `characteristic_id` 约定识别（B2 在事件上补 `gage_id` 映射，不改 schema）。
- 重复性 = 滚动窗口内重复测量的组内标准差；偏倚 = 均值 − `expected_value`；
  测量过程控制图 = 对偏倚序列跑 LiveSPC(I-MR)；漂移 = 判异或超出 `drift_rule`。
- 健康分 0–100：由重复性区间、偏倚显著性与数据覆盖率加权（权重表进 constants，可调）。
- 漂移处理：写 `gauge_drift_alerted` 事件 + 状态栏/告警中心提示重做研究（不自动改标准）。

### 3.4 收益域（B0 冻结）

```
BenefitRecord  record_id  case_id  month(YYYY-MM)  ledger_kind ∈ improvement|cost_of_quality
               category ∈ 预防|鉴定|内部失败|外部失败|改善收益
               basis{standard_ref, standard_as_of, baseline_value, new_value, unit, quantity,
                     unit_cost, currency}
               confidence ∈ A|A-|B|C    evidence_refs[]  double_count_key
               computed_at  source ∈ case_close|monthly_recompute|manual
```

- 口径一致性：复算必须按 `standard_ref` 在 `month` 内 as-of 的版本取基线；标准变更后
  历史月不追溯改写，只影响新月复算（防"口径套利"）。
- 防重复：`double_count_key = hash(case_id + month + 计量口径)`，同键二次入账拒绝。
- 置信门禁：仅 A/A-/B 入账；C 级进入"待完善"清单（可查看不可计入汇总）。
- 改善收益与鉴定/损失数据分区（`ledger_kind`），考核视图与改善视图分开统计。
- 账本新事件类型：`benefit_recorded` / `benefit_recomputed`。

### 3.5 技能域（B0 冻结）

```
SkillMatrix     entries[{operator, process_id, level(1-5), updated_at}]
ProcessSkillReq process_id  min_level  (并入线平衡 Tab 的约束面板)
SchedulePlan    assignments[{process_id, operator, start_s, end_s}]
                constraints{headcount, equipment_capacity, takt}
                balance_rate_before/after  unmet[]（不可行原因）
```

- LPT 结果后处理：按技能兼容性做工位指派修复；无法满足时输出 `unmet` 明细而非静默降级。
- 结果挂接案例：作为 `baseline`/`remeasure` 步骤（案例模板 #2），凭证含技能矩阵指纹。

### 3.6 `.qap` 2.0 与兼容

- 新增段：`sampling.json`（方案/检验批/转移状态）、`gauge_studies.json`、
  `benefits.json`、`skills.json`；写出版本 2.0，1.6–1.9 只读兼容（无段按空处理）。
- 案例 schema 不升级（v1 够用）；证据事件 schema 不升级（仅扩 EVENT_TYPES）；
  插件 API 仍 2.1（如需新能力单列评审）。

## 4. 批次任务分解（B0–B8）

### B0 契约基座与 `.qap` 2.0（4–6 人日）✅ 2026-10-12 ← 最先做，冻结后才允许写功能

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B0-1 | 四域 schema 与校验（抽样/量具/收益/技能），纯 stdlib + pandas，无 Qt | 新 `core/sampling_plan.py`、`core/gauge_study.py`、`core/benefit_ledger.py`、`core/skill_matrix.py` | 契约测试：往返/未知版本拒读/非法字段中文报错 |
| B0-2 | 账本事件类型扩展 + 抽样方案挂 `StandardRegistry`（新 `sampling_plan` 对象类型） | `core/evidence_ledger.py`、`core/standard_record.py` | 事件类型枚举测试 + 抽样方案 as-of/留痕测试 |
| B0-3 | 加严/放宽 AQL 表与转移规则纯函数（确定性） | `core/sampling_engine.py` | 转移书全覆盖：同输入序列 → 同状态轨迹（含边界：连续计数、严重不合格） |
| B0-4 | `.qap` 2.0：四段读写 + 1.6–1.9 只读兼容 + manifest 计数 | `core/project_manager.py` | 兼容矩阵测试（1.6/1.7/1.8/1.9/2.0 五档） |
| B0-5 | 时间/分层守卫扩围：四个新模块进 `test_timezone_guard` 与分层扫描 | `tests/test_timezone_guard.py`、`tests/test_layering.py` | 守卫测试通过（无时区构造=0） |

**B0 完成记录（2026-10-12）**：

1. 四域契约落地：`core/sampling_plan.py`（LotRecord / SamplingDecision /
   TransferState / TransferDecision）· `core/gauge_study.py`（GaugeStudyPolicy /
   GaugeRollingState + 重复性/偏倚纯函数）· `core/benefit_ledger.py`
   （BenefitRecord / BenefitLedger，防重复键 + 置信门禁 + COPQ 分区 + ROI）·
   `core/skill_matrix.py`（SkillMatrix / SchedulePlan）。
2. 账本事件类型 +7（sampling_plan_selected / lot_inspected /
   sampling_transfer_changed / alert_case_opened / gauge_drift_alerted /
   benefit_recorded / benefit_recomputed）；标准域新增对象类型 `sampling_plan`。
3. **抽样表重建（本批最大发现）**：审查中发现 v4.3.0 及以前 `_NORMAL_TABLE`
   与标准原表不符——A~H 行数字格整体错位、J/K 行完全相同（约 95% 格子与标准
   不一致）、箭头（↓/↑）语义未实现、检验水平参数被静默忽略、加严/放宽表缺失。
   已以 GB/T 2828.1-2003（= ISO 2859-1:1999）原文数据重建三张主表（21 AQL 列 ×
   16 字码），实现箭头解析、7 档检验水平（S-1~III）与转移规则纯函数
   （`SamplingEngine.evaluate_transfer`，阈值按本方案 §3.1 冻结）。
   四重交叉验证：随包知识库节选 55 格逐格一致；2-A 全部 152 个数字格的 n·AQL
   落入接收数对应 R5 带心 ±6%（5–95% 区间 [0.94, 1.04]）；2-B 满足带心 ×1.6
   设计关系（中位 1.56）；2-C 与行业确认值一致（AQL2.5：K→5/6、L→6/7）。
4. `.qap` 2.0：新增 `sampling.json` / `gauge_studies.json` / `benefits.json` /
   `skills.json` 四段（1.6~1.9 只读兼容），manifest 增段位计数；
   `SharedProjectManager.save_shared` 同步透传（避免 v4.3.0 式接线遗漏）。
5. 验证：新增 6 个测试文件 / +75 例；**全量逐文件回归 184 文件 / 2269 通过 /
   56 跳过 / 0 失败（507.8s）**；ruff 零告警；时间守卫扩围 4 个新模块。
   已知边界：抽样表数据为行业工具的坐标级提取值 + 四重交叉验证（非购买版标准
   原文），B3 前建议人工抽查若干格；旧表纠错属**用户可见行为变更**（AQL 查表与
   计量型抽样的字码/样本量将变化，方向为修正）。

### B1 告警自动立案 8D（8–10 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B1-1 | 立案编排：critical 告警 → 8D 草稿 + ImprovementCase（D1–D3 预填、D4 留空） | 新 `core/alert_case.py`（无 Qt）；`core/streaming/alerts.py` 挂钩 | 合成 critical 告警 ≤1 分钟立案；快照/特性/FMEA 条目齐全 |
| B1-2 | 去重与冷却：同 rule_key 30 分钟合并为同案步骤；一案一号 | `core/alert_case.py` | 连发 3 条告警 → 1 案例 + 3 步骤；跨窗口 → 新案例 |
| B1-3 | D6 数据门禁与 8D 报告联动：D6 关联 `measurement_refs`+统计判定；草稿进入 8D Tab 可编辑 | `ui/tabs/eight_d_tab.py`、`core/case_workflow.py` | D6 无数据不能关闭案例；8D 报告与案例步骤双向可见 |
| B1-4 | 入口与通知：案例中心显示"自动立案"徽标；告警中心可一键打开案例 | `ui/dialogs/case_center_dialog.py`、`ui/dialogs/alert_center_dialog.py` | 离屏冒烟：critical 演示点 → 立案 → 打开工作台 |

### B2 测量系统在线化（8–10 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B2-1 | 标准件测量录入与识别：四通道事件 → gauge 滚动窗口（含标准件/期望值配置） | `core/gauge_study.py`、`ui/tabs/msa_tab.py`（配置面板） | 手工录入 10 次重复 → 滚动重复性/偏倚出数 |
| B2-2 | 测量过程控制图：偏倚序列接 LiveSPC(I-MR)，判异即漂移 | `core/gauge_study.py`（复用 `core/streaming/live_spc.py`） | 注入 3σ 漂移 → 判异；`.qap` 往返保持状态 |
| B2-3 | 量具健康分与漂移提示：ok/watch/drift + 状态栏/告警中心提示重做研究 | `core/gauge_study.py`、`ui/main_window.py` | 健康分分级正确；提示不重复轰炸（冷却） |
| B2-4 | 接线与持久化：`.qap` gauge 段 + 项目加载恢复 + 案例引用（标准件事件进凭证） | `core/project_manager.py`、`ui/main_window.py` | 往返测试 + 案例 `measurement_refs` 指向 gauge 事件 |

### B3 可信抽样（10–12 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B3-1 | 转移状态机落地：按供应商·产品线自动转移 + 检验批历史记忆 + 状态快照 | `core/sampling_engine.py`、新 `core/sampling_state.py` | 与 B0 规则书逐条对照；同输入重跑轨迹一致 |
| B3-2 | 确定性抽样：全部方法支持种子；抽样结果行指纹（pd-hash-v1）；`systematic_sample` 修复 | `core/sampling_engine.py` | 同参数重跑样本逐行一致（随机/分层/系统全查） |
| B3-3 | 方案留痕与账本接线：方案选择（含手动覆盖原因）→ `sampling_plan_selected`；判定 → `lot_inspected`；转移 → `sampling_transfer_changed` | `core/sampling_state.py`、`ui/tabs/sampling_tab.py`、`ui/main_window.py` | 证据视图可还原"为何本批加严/放宽"；证据包可独立校验 |
| B3-4 | 抽样 Tab 升级：方法选择统一入口、批历史/转移时间线、覆盖须填原因 | `ui/tabs/sampling_tab.py` | UI 冒烟：录入批 → 拒收触发加严 → 时间线可见 |
| B3-5 | 性能与基线：100 万行抽样 + 判定耗时进性能基线 | `tools/benchmark.py`、`tools/perf_baseline.json` | 新指标入 10+2 项基线并通过 |

### B4 收益账本与 COPQ（8–10 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B4-1 | 收益记录与月度复算：按当时标准版本口径计算，防重复键 | `core/benefit_ledger.py`、`core/standard_record.py`（as-of） | 标准变更后：历史月不变、新月按新口径；重复入账被拒 |
| B4-2 | 置信门禁与分区：A/A-/B 入账、C 进待完善；改善与鉴定分区统计 | `core/benefit_ledger.py`、`ui/dialogs/case_workflow_dialog.py` | C 级不计入汇总且可见；分区视图不混算 |
| B4-3 | COPQ 四类 + ROI：预防/鉴定/内部失败/外部失败 + ROI 面板 | `ui/tabs/dashboard_tab.py`（或成本面板） | 合成数据端到端：答复"这条改善省了多少" |
| B4-4 | 案例挂接：关闭案例时生成收益记录（可编辑/复核），账本事件留痕 | `core/case_workflow.py`、`core/benefit_ledger.py` | 案例关闭 → `benefit_recorded`；复算 → `benefit_recomputed` |

### B5 技能约束线平衡·案例模板 #2（6–8 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B5-1 | 技能矩阵数据与编辑器（对话框，不新增 Tab） | `core/skill_matrix.py`、`ui/tabs/line_balance_tab.py`（对话框） | 录入/编辑/持久化往返；空矩阵不阻断原 LPT |
| B5-2 | 约束求解：技能兼容工位指派 + 人数/设备上限；不可行输出 `unmet` | `analysis/ie/line_balance.py`（新函数，不破坏既有 LPT） | 既有 LPT 测试全绿；技能场景输出可执行排班 |
| B5-3 | 案例模板接线：技能线平衡作为 baseline/remeasure 场景；凭证含技能矩阵指纹 | `core/case_workflow.py`、`ui/tabs/line_balance_tab.py` | 合成数据端到端演示脚本通过 |

### B6 抽样透明化收口（4–5 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B6-1 | 统一「抽样决定」契约：方法/参数/种子/是否可复现/说明文本 | 新 `core/sampling_note.py`（纯逻辑） | 契约测试：图表/趋势/画像三类调用统一产出 |
| B6-2 | 展示层接线：图表 300 点、趋势 1000 点、画像大表正态检验口径——界面显式标注 + 可复现 | `output/chart_engine.py`、`ui/tabs/trend_tab.py`、`core/data_profiler.py` | 任一展示抽样有标注；同参数可复现；无未标注抽样 |
| B6-3 | 画像大表正态检验策略修复：>5000 行改为固定种子抽样（记录种子）而不是跳过 | `core/data_profiler.py` | >5000 行有 `normality_pvalue` 且重跑一致 |

### B7 集成、性能与质量收口（5–6 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B7-1 | 跨批次集成回归：八链路（告警→立案→复测→关闭→收益；量具漂移；抽样转移；技能排班）端到端演示脚本 | `tools/demo_v44_case.py` | 一条命令全绿，输出可粘贴证据 |
| B7-2 | v4.3.0 审查遗留：主窗口菜单动作离屏冒烟清单制度化（每个菜单动作至少一次真实命中） | 新 `tests/test_menu_smoke.py` | 清单覆盖 100% 菜单动作；`_on_save_shared` 类接线回归不再靠运气 |
| B7-3 | 审查遗留小项：控制计划版本节流（合并窗口/显式保存语义）、SPC 多图控制限全记录、`measurement_capture` 决策落地（默认维持关闭 + 注释与文档） | `ui/tabs/control_plan_tab.py`、`ui/tabs/spc_tab.py`、`ui/main_window.py` | 逐格编辑不再产生版本洪峰；XBar-R 的 X/R 图控制限均入库；决策写入迁移手册 |
| B7-4 | 性能基线扩容（抽样 1M / 收益复算 1 万条 / 量具滚动 10 万点）+ 迁移手册 | `tools/benchmark.py`、`docs/migration/v4.4.0.md` | 基线 13 项通过；迁移手册含 1.9→2.0 与决策记录 |

### B8 版本收尾与发布（2–3 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B8-1 | 版本四端一致（settings / version_info / Inno / 文档）+ 发布说明 | 同 v4.3.0 收尾流程 | `tools/check_version.py` 通过 |
| B8-2 | 发布门禁全绿 + Linux AppImage 构建 + 启动冒烟 + `.sha256` | `tools/release_check.py`、`build_appimage.sh` | 178+ 文件全绿、AppImage 启动冒烟通过 |
| B8-3 | README / ROADMAP（中英）/ 使用指南 / release notes 同步 | 文档 | 版本历史新增 v4.4.0 行 |

## 5. 排期（约 11–13 周，含 20% 缓冲）

| 阶段 | 批次 | 人日 | 前置 | 周 |
|------|------|------|------|----|
| 第 1 阶段 | B0 契约基座与 `.qap` 2.0 | 4–6 | — | W1 |
| 第 2 阶段 | B1 告警自动立案 8D | 8–10 | B0 | W2–W3 |
| 第 2 阶段 | B2 测量系统在线化 | 8–10 | B0 | W3–W4 |
| 第 3 阶段 | B3 可信抽样 | 10–12 | B0 | W5–W6 |
| 第 4 阶段 | B4 收益账本与 COPQ | 8–10 | B3（标准口径）+ B1/B2 输出 | W7–W8 |
| 第 4 阶段 | B5 技能约束线平衡 | 6–8 | B0 | W8–W9 |
| 第 5 阶段 | B6 抽样透明化收口 | 4–5 | B3（抽样决定契约） | W9–W10 |
| 第 6 阶段 | B7 集成与质量收口 | 5–6 | B1–B6 | W10–W11 |
| 第 7 阶段 | B8 发布 | 2–3 | B7 | W12 |

合计 **55–70 人日**（单人 ≈ 12 周；并行人力可压缩到 7–8 周）。
阶段门禁：每批完成即跑该批测试文件 + ruff；B0 未冻结不得开工 B1+；
B7 之前全量逐文件回归必须全绿（沿用 v4.3.0 节奏：每批完成记录一次回归数据）。

## 6. 测试与验收策略

### 6.1 新增测试（预计 +130~160 例）

| 批次 | 重点 | 预计 |
|------|------|------|
| B0 | 四域契约、事件类型、转移规则书、`.qap` 2.0 兼容矩阵 | +35 |
| B1 | 立案判定/去重/快照完整性、D6 门禁、UI 冒烟 | +25 |
| B2 | 滚动重复性/偏倚、判异漂移、健康分分级、往返 | +25 |
| B3 | 转移轨迹确定性、种子复现、指纹、账本接线、性能 | +25 |
| B4 | 复算口径、防重复、置信门禁、分区 | +20 |
| B5 | 技能约束可行/不可行、案例模板、既有 LPT 不回归 | +15 |
| B6 | 抽样决定契约、标注与复现、画像抽样 | +10 |
| B7 | 菜单冒烟清单、节流、多图控制限 | +10 |

### 6.2 兼容矩阵（必须全绿）

`.qap` 1.6 / 1.7 / 1.8 / 1.9 / 2.0；案例 schema v0/v1；插件 API 2.0/2.1；
证据事件 schema v1；标准注册表 schema v1。未知版本一律拒读并给结构化错误。

### 6.3 门禁

- ruff 全库零告警；逐文件回归（严禁批量）；`tools/check_version.py`；
- 性能基线 13 项（新增：1M 行抽样、收益复算 1 万条、量具滚动 10 万点）；
- 发布门禁 `tools/release_check.py` + AppImage 启动冒烟。

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 自动立案刷屏（抖动告警 → 案例洪峰） | 案例中心被噪音淹没 | 30 分钟冷却 + 同案合并 + critical 阈值 + 立案率可观测（账本事件统计） |
| 转移规则审计争议 | 审核不认"自动加严" | 每步转移记录触发依据（哪几批、什么判定、谁确认）；放宽默认禁用需显式启用 |
| 量具基线漂移误报 | 频繁"重做研究"提示 | 冷却 + 双条件（判异且偏倚超阈值）；健康分权重可配置 |
| 收益口径套利 | 数字好看但不可信 | 口径锁定当时标准版本 + 月度复算 + 防重复键 + 仅 A/A-/B 入账 |
| 技能矩阵录入成本高 | 功能被弃用 | 编辑器支持从现有工序/人员预填 + CSV 导入导出；空矩阵时保持旧行为 |
| `.qap` 2.0 兼容回归 | 旧项目打不开 | 五档兼容矩阵测试进 CI；B0 先写兼容测试再写功能 |
| 8D 草稿质量差（模板化） | 工程师不认 | D1–D3 只做"可编辑的预填"，D4 留空；预填字段附来源引用（快照/特性/FMEA 条目） |

## 8. 关键决策（默认值已给出，B0 开工前需用户确认）

| # | 决策 | 默认值 | 备选 |
|---|------|--------|------|
| 1 | `.qap` 版本号 | **2.0**（新增四段，1.6–1.9 只读兼容） | 1.10（保守） |
| 2 | 自动立案阈值 | **仅 critical** | critical+warning（案例可能过多） |
| 3 | 放宽检验（reduced） | **默认禁用**，策略显式启用 | 默认按规则自动放宽（审核风险） |
| 4 | 立案去重窗口 | **同规则 30 分钟**合并同案 | 按告警 id 一案一号（重复多） |
| 5 | 技能矩阵编辑器位置 | **线平衡 Tab 内对话框**（不新增 Tab） | 新增 Tab（触发五步接线清单） |
| 6 | 收益入账范围 | **仅案例验证关闭后的改善**可入账 | 手工录入也可入账（需复核流） |
| 7 | `measurement_capture` | **维持默认关闭**，代码注释 + 迁移手册写明"仅案例显式采集" | 增加配置开关（需评估账本/`.qap` 增长） |

## 9. v4.3.0 审查遗留 → 本版批次映射

| 审查遗留项 | 去向 |
|------------|------|
| 主窗口菜单动作缺端到端冒烟（共享保存/配对错配两类盲区） | B7-2 制度化 |
| 控制计划逐格编辑产生版本噪音 | B7-3 节流 |
| SPC 多图只记第一张控制限 | B7-3 全记录 |
| `measurement_capture` 无开关 | B7-3 + §8 决策 7 |
| `read_evidence_pack` 无大小上限 | 视 v4.5 CLI/SDK 暴露节奏，届时加条目上限（本版不做） |

## 10. 执行入口（常用命令）

```bash
# 单文件回归（严禁一次传多文件：PySide6+scipy 同进程并发会死锁）
python tools/run_tests.py --files test_sampling_state.py

# 全量逐文件回归
python tools/run_tests.py --quiet

# 性能基线（新增三项后 13 项）
python tools/benchmark.py

# 发布门禁
python tools/release_check.py

# 端到端演示（每批收口必跑）
python tools/demo_v44_case.py --output TEMP/demo_v44
```

## 11. 交付物清单

- 代码：B0–B6 各批次落点模块与 UI 接线；B7 集成与遗留修复；
- 测试：+130~160 例（含菜单冒烟清单、契约、转移规则、兼容矩阵、性能）；
- 文档：本方案、`docs/migration/v4.4.0.md`、`docs/releases/v4.4.0.md`、
  README/ROADMAP（中英）同步、使用指南新增章节（自动立案/测量在线/可信抽样/收益账本）；
- 发布：版本 4.4.0 四端一致 + 全量门禁 + `AKIA-4.4.0-x86_64.AppImage`（+`.sha256`）。
