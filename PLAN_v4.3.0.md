# AKIA v4.3.0 开发方案（执行版）— 改善案例与证据账本

> 依据 `ROADMAP.md`「v4.3.0 — 改善案例与证据账本」的 B1–B4，把数据模型、接线、
> UI、迁移、性能与发布拆成可直接排期的 B0–B6 批次；每项含**落点文件 / 验收方式 /
> 依赖与风险**。版本语义与设计决策仍以路线图为准，本文只描述执行路径。
>
> 探索日期：2026-10-03（HEAD `69faec9`，v4.2.1）。
> **执行进度（2026-10-08）**：B0 契约基座 ✅ · B1 案例生命周期与持久化 ✅ ·
> B2 测量四通道 + 插件数据源 ✅ · B3 标准版本记录 ✅ · B4 证据账本与交换 v1 ✅ ·
> B5 集成、性能与质量收口 ✅（累计新增 263 例测试；全量逐文件回归 178 文件 /
> 2180 通过 / 56 跳过 / 0 失败，性能基线 10 项通过（冷启动 1.258s），ruff 零告警）；
> B6 版本收尾与发布待开工。

**基线（v4.2.1 发布门禁实测）**：159 个测试文件 / 1917 通过 / 56 跳过 / 0 失败；
ruff 全库零告警；性能 8 项通过（冷启动 1.064s · 百万行导入 4.951s · SPC 100 万 1.553s ·
MSA 10 万 1.073s · ML 10 万 3.149s）；Linux 最新安装包仍为 v4.2.0 AppImage，v4.2.1 仅源码。

---

## 1. 现状盘点：已有资产与真实缺口

### 1.1 已具备（v4.2.0/v4.2.1 交付）

| 能力 | 落点 | 现状 |
|------|------|------|
| 案例 schema v0 | `core/improvement_case.py` | id/title/status/6 阶段常量/baseline_refs/conclusion_refs/steps；校验最小字段 |
| 案例编排 | `core/case_workflow.py` | 8 阶段脊柱（baseline→time_study→line_balance→improvement→remeasure→paired_test→conclusion→standard），逐步留痕时间戳/数据引用/凭证；内置配对检验真实接线；Markdown 导出；字典往返 |
| 判定凭证 | `core/evidence.py` | 凭证 schema v1（rule_version + params + `pd-hash-v1` 指纹 + app_version + computed_at）；同数据重跑 diff；12 位报告追溯码（Excel/PDF/Word 已接） |
| 项目文件 | `core/project_manager.py` | `.qap` 1.8：data / analyses（含 credential）/ context / cases.json / charts；1.6–1.7 只读兼容 |
| 工作台 UI | `ui/dialogs/case_workflow_dialog.py` + `ui/main_window.py` | 菜单「工具 → 改善案例工作台」以当前导入数据建立案例基线，打开**只读**对话框 |
| 插件接口 | `core/plugin_api.py` | API v2.0：`tab` / `agent_tools` / `settings` 三类能力；manifest 信任模型；2.x 同大版本兼容 |
| 插件宿主 | `ui/plugin_host.py` | 只读门面：data_frames / analyses / project_context / theme / notify / switch_tab |
| 实时数据 | `core/devices/driver.py`、`core/streaming/`、`core/storage/timeseries.py` | `Sample(device, channel, value, ts)` → StreamBus → SQLite 时序库；连接器插件 5 个 |
| 审计 | `core/audit.py` | 人类可读文本日志（轮转 5MB + 失败计数），**不是**机器可验证的结构化账本 |

### 1.2 关键缺口（直接影响 v4.3.0 验收）

| # | 缺口 | 证据 | 归属批次 |
|---|------|------|----------|
| G1 | **案例未随项目保存**：`_on_save_project` 调用 `ProjectManager.save_project(...)` 时没有传 `cases=`，UI 中建立的案例只存在于内存 | `ui/main_window.py:1548`；全库仅 `core/project_manager.py` 与测试引用 `project["cases"]` | B1 |
| G2 | **案例未随项目恢复**：`_apply_loaded_project` 读取了 `project["cases"]` 但未赋值/展示；`_last_case_workflow` 只在内存 | `ui/main_window.py:1576`；rg 无 `self.cases` 类成员 | B1 |
| G3 | **生命周期不完整**：`CASE_STATUSES` 仅 draft/active/closed，无状态迁移校验、关闭门禁（复测+统计判定）、重开、owner/product 落盘 | `core/improvement_case.py:14`；`owner/product` 只在 `CaseWorkflow` 包装层 | B1 |
| G4 | **MeasurementEvent 不存在**：设备/插件/手工/文件四条路径没有统一事件契约；`Sample` 无 recorded_at、confidence、validity、raw_ref | 全库 rg 无 `MeasurementEvent`；`core/devices/driver.py:14` | B2 |
| G5 | **插件不能作为数据源**：能力枚举无 `data_source`；`PluginHost` 只读，插件无法把测量批量注入案例 | `core/plugin_api.py:24`；`ui/plugin_host.py` | B2 |
| G6 | **标准无版本**：规格限（`QualityCharacteristic.usl/lsl/target`）、控制计划行（`list[dict]`）、标准工时（藏在 `analysis/ie/time_study.py` 结果里）都无 valid_from/valid_to/change_reason | `core/project_context.py:15`；`ui/tabs/control_plan_tab.py:140` | B3 |
| G7 | **审计不可验证**：文本日志无事件 ID、无对象引用、无哈希链，报告数字无法回指事件 | `core/audit.py:52` | B4 |
| G8 | **无证据视图/交换**：没有"结论→事件→原始引用"的 UI；`.qap` 无证据包导出；无脱敏分享；HTML 报告未接追溯码（v4.2.0 已知遗留） | `output/base_report_engine.py`；`docs/releases/v4.2.0.md` 已知限制 | B4 |
| G9 | **时区语义未定义**：存量 56 处无时区时间戳，双时态需要先定义 `ts` / `recorded_at` 的权威格式 | `docs/quality/2026-09-28-quality-review.md` 第 5 节 | B0 |

### 1.3 复用而不重做的边界

- **凭证/追溯码不推倒重来**：`ConclusionCredential` schema v1 与 `credential_trace_code` 保持不变；
  账本通过**分析记录外层**的 `ledger_seq` 关联凭证，避免改动凭证字段导致旧 diff/追溯码失效。
- **`.qap` 增量兼容**：1.9 新增 `standards.json`、`evidence/events.jsonl` 与
  `measurements.jsonl`（B2 测量事件），1.6/1.7/1.8 全部可读；写出版本统一 1.9。
- **不新增 Tab**：案例中心与证据视图都用 Home 卡片 + 对话框承载；若 B5 评审证明必须新增，
  单独按「新增 Tab 检查清单」走五步接线（注册表/工作表路由/空状态/菜单/回归）。

---

## 2. 版本目标与范围

### 2.1 一句话目标

把「改善案例」从一次性的执行轨迹升级为**可持久化、可回放、可验证、可交换**的一等对象：
测量与标准带双时态，结论带凭证，所有关键动作进入 append-only 证据账本，案例关闭必须由
复测数据与统计判定放行。

### 2.2 范围内

1. ImprovementCase v1 生命周期 + `.qap` 持久化 + Home/案例中心入口 + 关闭门禁；
2. MeasurementEvent v1 合同与四类适配器（连接器/插件/手工/文件）+ 插件 API 2.1 `data_source`；
3. 标准版本记录（规格限/控制限/标准工时/作业组合票/控制计划条目）+ as-of 历史还原；
4. 结构化证据账本（哈希链）+ 证据视图 + `.qap` 1.9 + 证据包/脱敏分享 v1；
5. 迁移（旧 `.qap`、旧案例、2.0 插件）、性能、文档与 4.3.0 发布收尾。

### 2.3 范围外（明确不做，避免范围蔓延）

- 不做全库双时态：只覆盖**测量 / 标准 / 结论**三类对象；
- 不做服务端/云/匿名基准/多公司平台；
- 不在本版做告警自动立案 8D、抽样转移、收益账本（v4.4.0）；
- 不做 MCP/CLI/SDK/规则包/i18n 框架（v4.5.0）；
- 不引入新硬依赖：哈希链、JSONL、zip 全部用标准库；
- 主仓库不内置视觉能力，只定义合同并给测试夹具插件；真实视觉适配在
  `AKIA-Vision-expansion` 插件仓库单独跟进。

---

## 3. 核心数据契约（先冻结，再实现）

> 原则：**账本只存引用与摘要，不复制原始数据**；所有 schema 带 `schema_version`，
> 未知版本拒读并给结构化错误；时间统一 ISO-8601 带时区偏移。

### 3.1 时间语义（B0 决策，单独立项）

| 字段 | 含义 | 格式 | 不变量 |
|------|------|------|--------|
| `ts_start` / `ts_end` | 测量**发生**时间（事件时间） | ISO-8601 带偏移；设备 epoch 保留原值到 `ts_epoch` | `ts_end >= ts_start` |
| `recorded_at` | 数据**入库/录入**时间（记录时间） | ISO-8601 带偏移 | `recorded_at >= ts_end`（允许 `clock_skew_s` 容差并标记） |
| 存量无时区时间戳 | 读取时按本机时区（默认 Asia/Shanghai）解释并标记 `legacy_naive=True` | — | 不静默改写旧值 |

新增代码一律使用 `datetime.now().astimezone()`；B5 加 AST 棘轮测试，禁止
`core/measurement_event.py`、`core/evidence_ledger.py`、`core/standard_record.py`
新增无时区 `datetime.now()`（存量 56 处不在本版全量迁移，但不得增长）。

### 3.2 MeasurementEvent v1（新 `core/measurement_event.py`，无 Qt）

**批量粒度事件**（一次 poll、一列导入、一次手工录入 = 一条事件），避免百万行产生百万事件：

```
schema_version  event_id  source{kind,id,name}  subject{device,channel,characteristic_id}
method          gage/method 标识              confidence  high/medium/low
validity        valid/suspect/invalid + reason ts_start/ts_end/recorded_at
summary         {n, mean, std, min, max}      values        可选（仅手工/小批量内联）
raw_ref         timeseries://… | file://… | sheet://… | dataframe://<指纹>
fingerprint     pd-hash-v1:<sha256>（物化批次时）  parent_event_ids  追溯合并/派生
```

- API：`validate()`、`to_dict()/from_dict()`、`fingerprint_batch(df)`、`to_dataframe()`；
- 适配器：`from_samples(list[Sample])`（连接器/插件）、`from_dataframe(df, ...)`（文件/工作表）、
  `from_manual(...)`、`from_timeseries(store_query)`；
- 持久化：`MeasurementStore`（默认上限 2000 条 FIFO）→ `.qap` `measurements.jsonl`；
  案例步骤以 `measurement_refs` 引用事件 ID；
- 拒绝规则：空批次、时间倒序、`recorded_at < ts_end - 容差`、非法 confidence/validity、
  不可解析 raw_ref —— 全部返回结构化中文错误，不抛底层异常给 UI。

### 3.3 StandardRecord v1（新 `core/standard_record.py`，无 Qt）

```
schema_version  record_id  object_type   spec_limit | control_limit | standard_time |
                                        work_combination | control_plan_row
object_ref      QC-001 / 工序-3 / CP-row-7
payload         版本化内容（usl/lsl/target、ucl/lcl/cl、standard_time_s、组合票字段…）
valid_from      valid_to（None=现行）  change_reason  changed_by  recorded_at
supersedes      source_case_id（由哪条改善产生）  origin=manual|migration|case
fingerprint     内容指纹
```

- `StandardRegistry`：`append()`（自动关闭上一条，禁止同对象时间区间重叠）、
  `current(object_ref)`、`as_of(object_ref, ts)`、`history(object_ref)`、`diff(record_a, record_b)`；
- 迁移：加载 1.6–1.8 项目时，把现有 `QualityCharacteristic.usl/lsl/target` 转成
  `origin=migration` 的首条 `spec_limit` 记录（`valid_from=项目 created_at`，`change_reason="历史数据迁移"`）；
- 分析接线：SPC/能力分析把 `standard_ref` + `standard_as_of` 写入凭证 `params`，
  这样"同数据重跑 diff"能同时暴露**算法变化**与**标准变化**，历史批次按当时标准复判。

### 3.4 EvidenceEvent v1 + 哈希链账本（新 `core/evidence_ledger.py`，无 Qt）

```
seq  event_id  at  type  actor  object_refs[]  payload  prev_hash  hash
type: data_imported | measurement_recorded | standard_changed | analysis_run |
      case_created | case_step | case_status_changed | case_closed | case_reopened |
      report_exported | evidence_pack_exported | alert_ack | data_edited |
      share_pack_exported
hash = sha256(prev_hash + canonical_json(event_without_hash))
```

- 存储：项目内 `evidence/events.jsonl`（append-only，单写者，`flush` + 崩溃后截断尾行恢复）；
  本机 `~/.akia_audit.log` 继续作为人类可读合规日志，两者职责在文档中写清；
- API：`append(type, actor, object_refs, payload) -> seq`、`iter_events()`、`verify_chain()`、
  `events_for(ref)`、`export_manifest()`；链断裂时返回**首个断点 seq + 原因**，不静默通过；
- 性能预算：单事件 < 1ms、1 万事件文件 < 5MB；批量导入只记 1 条 `data_imported` +
  每批 `measurement_recorded`，不做逐行事件；
- 与凭证的关系：分析记录新增外层 `ledger_seq`（不改凭证 schema），证据视图负责 join。

### 3.5 ImprovementCase v1 + CaseWorkflow v1（`core/improvement_case.py` / `core/case_workflow.py`）

- schema v1 新增：`owner`、`product`、`problem_statement`、`target`、`due_date`、`tags`、
  `measurement_refs`、`standard_refs`、`report_refs`、`closed_at`、`close_reason`、`reopen_count`；
- 生命周期：`draft → active → verifying → closed`，另有 `abandoned`；`closed` 仅允许经
  `reopen(reason)` 回到 `active`，每次迁移写账本事件；
- **关闭门禁**（路线图"案例关闭强制复测 + 统计判定"）：
  1. 阶段齐备：baseline / remeasure / verify 必填；
  2. 至少一条 `measurement_recorded` 复测事件，且晚于改善步骤；
  3. `verify` 阶段必须有统计判定结果（配对检验 / SPC 判定 / 能力对比任一，且带凭证）；
  4. 未满足时 `close_case()` 返回结构化错误与缺失项，UI 不允许绕过；
- `from_dict` 接受 schema v0（原样读、按 v1 语义补默认值），v1 严格校验；
- 落盘规范：`cases.json` 条目 = `CaseWorkflow.to_dict()`（`{case, product, owner, phase_order,
  missing_phases}`）；裸 `ImprovementCase` dict（v0 旧文件）仍可读。

---

## 4. 批次任务分解（B0–B6）

> 与路线图映射：B0/B5/B6 为执行新增批次；B1–B4 与路线图同名批次一一对应。
> 工作量按单人推进估算（人日），可在 B0 冻结后部分并行（B2 ∥ B3）。

### B0 契约基座与 `.qap` 1.9（4–6 人日）✅ 2026-10-03 ← 最先做，冻结后才允许写功能

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B0-1 ✅ | MeasurementEvent v1 契约 + 校验 + 指纹 + 往返 | `core/measurement_event.py` | `tests/test_measurement_event.py` 36 例全绿：批量/手工/时序/异常路径、时间不变量、指纹稳定 |
| B0-2 ✅ | StandardRecord v1 + Registry（重叠检测/as-of/diff） | `core/standard_record.py` | `tests/test_standard_record.py` 30 例全绿：区间不重叠、as-of 边界、迁移记录 |
| B0-3 ✅ | EvidenceEvent v1 + 哈希链账本（append/verify/断点恢复） | `core/evidence_ledger.py` | `tests/test_evidence_ledger.py` 27 例全绿：篡改即检出、尾行截断恢复、文件模式 |
| B0-4 ✅ | `.qap` 1.9 设计：`standards.json` + `evidence/events.jsonl` + manifest 字段；1.6–1.8 只读 | `core/project_manager.py` | `tests/test_qap_evidence.py` 7 例全绿：旧版样例可读、1.9 往返一致、截断/坏行容错 |
| B0-5 ✅ | 时间语义与迁移策略落地 + AST 棘轮测试 | `core/time_utils.py`、`tests/test_timezone_guard.py` | 3 例全绿：新模块禁止无时区构造；新契约时间戳全部带偏移 |
| B0-6 ✅ | 案例 schema v1 迁移脚手架（v0→v1 只读） | `core/improvement_case.py` | `tests/test_case_lifecycle.py::TestSchemaCompatibility`：v0 恢复、v1 严格校验 |

**出口标准（M0 门禁）**：契约测试全绿；`core/` 新模块零 Qt、零 ui 依赖（`tests/test_layering.py`）；
ruff 零告警；schema 文档写入 `docs/` 或模块 docstring。

**B0 完成记录（2026-10-03）**：新增 `core/time_utils.py`（时区语义单一入口）·
`core/measurement_event.py`（批量粒度 + 四类适配器 + pd-hash 指纹）·
`core/standard_record.py`（append-only + as-of + legacy 迁移）·
`core/evidence_ledger.py`（sha256 前后链 + JSONL + 尾行恢复）；`.qap` 升级 1.9
（standards / evidence 段，1.6–1.8 只读）。契约测试 103 例全绿；ruff 零告警；
分层守卫通过。实现与规划的差异：账本事件类型新增 `case_created` / `case_status_changed`
两个生命周期事件（已回写 3.4 节）。

### B1 改善案例对象与生命周期（7–9 人日）✅ 2026-10-03

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B1-1 ✅ | ImprovementCase v1：字段 + 状态机 + 关闭门禁 + 重开 | `core/improvement_case.py` | `tests/test_case_lifecycle.py` 32 例全绿：非法迁移/缺判定/草稿关闭被拒、重开留痕 |
| B1-2 ✅ | CaseWorkflow v1：测量事件/标准记录引用、阶段校验、to_dict/from_dict v0 兼容 | `core/case_workflow.py` | 每步可挂 MEV/标准 ref；v0 裸案例与 v1 包装结构均可恢复 |
| B1-3 ✅ | **持久化接线**：保存项目传 `cases=`；加载项目恢复案例列表；内存状态改为 `self.case_workflows`；共享项目同步 | `ui/main_window.py`、`core/project_manager.py` | `tests/test_case_persistence.py` 10 例全绿：UI 建案→保存 `.qap`→重开→案例/步骤一致；损坏单条跳过；共享项目 cases/context 保留 |
| B1-4 ✅ | 案例中心对话框 + Home 卡片 + 工具菜单入口；工作台从只读升级为可推进（记录当前数据/最近分析/结论/标准/关闭） | `ui/dialogs/case_center_dialog.py`（新）、`ui/dialogs/case_workflow_dialog.py`、`ui/welcome_page.py` | 离屏 UI 回归 12 文件 / 95 例全绿：Home 入口可达、列表状态/进度正确、关闭门禁提示缺失项 |
| B1-5 ✅ | 分析结果类型化接入案例步骤（时间研究 / 线平衡 / 配对检验 / 能力 / SPC） | `core/case_workflow.py`、`ui/dialogs/case_workflow_dialog.py` | `record_analysis_step` 映射 analysis_type→阶段并复用凭证；未知类型结构化报错 |

**出口标准（M1 门禁）**：一个案例在 UI 中完成「问题→基线→分析→改善→复测→配对检验→结论→关闭」，
保存重开后可完整回放；关闭门禁在缺复测或纯文字结论时拒绝。

**B1 完成记录（2026-10-03）**：`ImprovementCase` v1 生命周期（draft/active/verifying/
closed/abandoned + 关闭门禁 + reopen 留痕）· `CaseWorkflow` v1（MEV/标准引用、分析类型化
接入、可选账本事件）· 主窗口案例列表持久化（保存/加载/共享三条路径）· Home「改善案例」
卡片 + 工具菜单「改善案例中心」+ 可推进工作台。B1 新增 42 例测试
（lifecycle 32 + persistence 10）；相关回归 14 文件 / 215 例、UI 回归 12 文件 / 95 例全绿；
**全量逐文件回归 166 文件 / 2062 通过 / 56 跳过 / 0 失败（476.6s）**，性能基线 8 项通过
（冷启动 1.236s vs 基线 2.101s，tolerance ×4），ruff 零告警。
过程中修复 3 个真实缺陷：主窗口保存项目未传 `cases=`（案例丢失）、加载项目未恢复案例、
共享保存既丢 cases 又丢 project_context。

### B2 MeasurementEvent 合同 + 插件数据源（8–10 人日）✅ 2026-10-04

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B2-1 ✅ | 连接器适配：`Sample` 批量 → MeasurementEvent；raw_ref 指向时序库查询键 | `core/streaming/collector.py`、`core/storage/timeseries.py`、`core/measurement_event.py` | `test_measurement_intake.py`：单批一次事件（O(通道数)）、跨通道拆分、sink 异常隔离、`query_ref` 回读窗口 |
| B2-2 ✅ | 文件/工作表适配：导入表列 → MeasurementEvent（可选时间列）；项目内事件集合 | `core/measurement_event.py`、`core/measurement_store.py`、`core/project_manager.py` | 文件事件指纹与判定凭证一致；非数值表跳过；`.qap` `measurements.jsonl` 往返 + 截断恢复 |
| B2-3 ✅ | 插件 API 2.1：`data_source` 能力 + `provide_measurements(context)`；PluginManager 超时/坏数据隔离；PluginHost 受控注入 | `core/plugin_api.py`、`core/plugin_manager.py`、`ui/plugin_host.py` | `test_plugin_data_source.py` 15 例：来源强制覆盖、2.0 插件零影响、未信任/不可用不调用、坏 schema/异常/超时/非列表被隔离 |
| B2-4 ✅ | 测试夹具插件（仅 tests，不进产品）：注入合成测量批次并驱动案例闭环 | `tests/test_plugin_data_source.py` | 夹具插件 2 批测量 → MeasurementStore → 案例 baseline/remeasure → 配对检验 → 关闭；账本链校验通过 |
| B2-5 ✅ | 插件数据源合同文档 + 视觉插件适配说明（接口/示例/隐私边界） | `docs/plugin-data-source.md`、README 中英链接 | 合同含能力声明、错误隔离矩阵、返回值表、异步注入、视觉适配 7 条与隐私边界 |

**出口标准（M2 门禁）**：同一份测量既可从连接器、文件、手工、插件四条路径进入案例；
MeasurementEvent 校验失败不崩溃、有中文原因；2.0 插件行为不变。

**B2 完成记录（2026-10-04）**：连接器采集旁路 `event_sink`（采集/入库不受影响）·
`TimeseriesStore.query_ref` 按 `timeseries://` 引用回读 · `MeasurementStore`
（事件集合 + 上限截断 + JSONL 崩溃恢复）· `.qap` 1.9 新增 `measurements.jsonl` ·
插件 API 2.1（`data_source` 能力 + 5s 超时 + 来源强制 + 坏数据隔离）·
PluginHost `submit_measurements` 原子注入 · 案例工作台四通道入口
（文件/连接器/插件/手工，事件写入步骤 `measurement_refs`）。B2 新增 48 例测试
（store 11 + intake 15 + plugin 15 + QAP 3 + UI 4）；四项适配器/插件专项测试全绿，
ruff 零告警。**全量逐文件回归 169 文件 / 2110 通过 / 56 跳过 / 0 失败（516.8s）**；
性能基线 8 项通过（冷启动 1.185s vs 基线 2.101s，tolerance ×4）。
已知边界：异步推送依赖插件自觉调用 `submit_measurements`（B4 账本
接线时统一补 `measurement_recorded` 事件）；连接器常驻采集默认不写项目集合
（`measurement_capture=False`，避免长时运行撑大 `.qap`），案例按最近窗口显式采集。

### B3 标准版本记录（6–8 人日）✅ 2026-10-08

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B3-1 ✅ | 标准注册表接入 `ProjectContext` 与 `.qap` 1.9 | `core/project_context.py`、`core/standard_record.py`、`core/project_manager.py` | 标准记录随项目保存/恢复；旧上下文迁移生成首版记录；共享保存补齐 standards/measurements |
| B3-2 ✅ | 规格限/控制限写入口：能力 Tab、SPC Tab | `ui/tabs/capability_tab.py`、`ui/tabs/spc_tab.py`、`core/project_context.py` | 改限生成新版本（同值幂等）；必填变更原因；上一条自动关闭 |
| B3-3 ✅ | 标准工时/作业组合票写入口：时间研究结果 → 标准版本 | `ui/tabs/time_study_tab.py`、`ui/tabs/std_work_combo_tab.py` | 逐工序标准工时 + 组合票版本；变更可查"谁在何时、为什么改" |
| B3-4 ✅ | 控制计划条目版本化 | `ui/tabs/control_plan_tab.py`、`core/project_context.py` | 条目编辑自动产生新版本（新增/修改/移除）；历史行可 as-of 还原 |
| B3-5 ✅ | as-of 复判：分析凭证记录 `standard_ref`；历史批次按当时标准复算 | `core/standard_record.py`、`ui/main_window.py` | `tests/test_standard_asof.py` 10 例：改限前后同一数据判定不同、追溯码随标准版本变化、`resolve_standard_context` 现行/as-of/记录 ID 三路解析 |

**出口标准（M3 门禁）**：任意历史批次可还原当时标准；标准变更在证据时间线上可见；
报告追溯码随标准版本变化。

**B3 完成记录（2026-10-08）**：`StandardRegistry.record_change`（幂等 + 毫秒级单调边界，
避免同秒连续变更出现零长度版本）· `resolve_standard_context`（现行 / as-of / 记录 ID）·
`ProjectContext` 五类写入口（规格限 / 控制限 / 标准工时 / 作业组合票 / 控制计划条目）
与旧上下文迁移 · 四个 Tab 写入口（能力 / SPC / 时间研究 / 作业组合票）· 控制计划编辑
自动版本化 · 工具菜单「标准版本记录」时间线（对象/生效区间/原因/变更人）·
分析凭证注入 `standard_ref`/`standard_as_of`（追溯码随标准变化）· `.qap` standards 段与
共享保存补齐 **standards/measurements**（顺带修复共享保存漏传 measurements 的潜在
TypeError）。B3 新增 20 例专项测试（as-of 10 + UI 接线 10）；全量逐文件回归
**171 文件 / 2130 通过 / 56 跳过 / 0 失败（512.0s）**，性能基线 8 项通过
（冷启动 1.192s vs 基线 2.101s，tolerance ×4），ruff 零告警。

### B4 证据视图与交换 v1（9–12 人日）✅ 2026-10-08

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B4-1 ✅ | 账本接线：导入、分析、案例步骤、标准变更、报告导出、案例关闭/重开、告警确认、数据清洗、证据/分享包导出 | `ui/main_window.py`、`core/project_context.py`、`core/measurement_store.py`、`core/streaming/alert_journal.py`、`core/case_workflow.py` | `tests/test_ledger_wiring.py` 9 例：关键动作事件、幂等、失败隔离计数、`.qap` 保存恢复 |
| B4-2 ✅ | 证据视图对话框：结论 → 凭证 → 账本事件 → 原始引用；指纹重算 + 账本链校验 + 复核 diff + 追溯码定位 | `ui/dialogs/evidence_view_dialog.py`（新）、`ui/main_window.py` | `tests/test_evidence_view.py` 6 例：追溯链完整、篡改标红、无凭证"不可复核"、追溯码定位、指纹一致/不一致 |
| B4-3 ✅ | 证据包导出：case + 账本 + 凭证 + 标准 + 测量 + manifest(哈希清单)，可独立校验 | `core/evidence_pack.py`（新）、`ui/dialogs/case_workflow_dialog.py` | `tests/test_evidence_pack.py` 11 例：导出即校验、篡改/缺文件/未登记文件/断链检出、默认不含原始数据 |
| B4-4 ✅ | 脱敏分享包 v1：参数化合成数据 + 统计等价声明 + 泄漏扫描，剥离标识 | `core/share_pack.py`（新）、`ui/dialogs/case_workflow_dialog.py` | `tests/test_share_pack.py` 12 例：统计等价、可复现、案例标识剥离、原始高精度值/表列名/禁用词检出 |
| B4-5 ✅ | HTML 报告追溯码 + 报告→事件回指（补 v4.2.0 遗留） | `output/html_export.py`、`core/evidence_ledger.py` | HTML 页脚可回读 12 位追溯码；报告事件以 `trace:<code>` 入账本，证据视图可定位 |

**出口标准（M4 门禁）**：报告每个结论数字可回指事件与原始引用；证据包可独立验证；脱敏包无原始值。

**B4 完成记录（2026-10-08）**：
- **账本所有权**：主窗口持有 `EvidenceLedger`，随 `.qap` `evidence/events.jsonl` 保存/恢复；
  测量/标准/告警三个旁路 sink（失败隔离 + `_ledger_failures` 计数）· 导入/分析/报告导出/
  数据清洗/证据包/分享包事件接线；案例创建/步骤/关闭/重开经 `CaseWorkflow` 自动入账；
  同一动作不重复记账（幂等测量/同值标准无事件）。
- **证据视图**：结论凭证 + 账本链状态 + 关联事件时间线 + 指纹重算 + 重跑 diff +
  追溯码定位；工具菜单与分析工作台双入口。
- **证据包**：`manifest.json` 逐文件 SHA-256 + 账本链 + 未登记文件检查；默认不含原始数据；
  工作台一键导出并即时校验；新增 `evidence_pack_exported` 事件类型。
- **脱敏分享包**：数值列按均值/标准差参数化合成（固定种子可复现）、分类列重标
  `Cat_n`、表列名统一 `C_n/sheet_n`；导出后自动泄漏扫描（原始高精度值、表列名、
  路径/人名等禁用词）；案例只保留 ID/状态/阶段，事件只输出计数与链状态。
- **HTML 报告**：页脚写入 12 位追溯码（Excel/PDF/Word 之外补齐最后一种格式）。
- B4 新增 40 例测试（证据包 11 + 分享包 12 + 证据视图 7 + 接线 9 + HTML 追溯 1）；
  全量逐文件回归 **175 文件 / 2170 通过 / 56 跳过 / 0 失败（520.4s）**，
  性能基线 8 项通过（冷启动 1.031s vs 基线 2.101s，tolerance ×4），ruff 零告警。

### B5 集成、性能与质量收口（4–6 人日）✅ 2026-10-08

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B5-1 ✅ | 端到端演示案例：导入 → 基线事件 → 分析 → 改善 → 改标准 → 复测 → 判定 → 关闭 → 证据包 → 脱敏包 | `tools/demo_v43_case.py`（新）、`tests/test_case_e2e_v43.py`（新） | 一条命令复现（18 条账本事件 / 8 阶段全带凭证）；每步有事件/凭证/标准引用 |
| B5-2 ✅ | 性能回归：账本追加/打开、导入链路上开销、冷启动 | `tools/benchmark.py`、`tools/perf_baseline.json`、`tests/test_evidence_perf.py` | 10 项基准全过（tolerance ×4）：`evidence_append_1k_s` 0.463s、`case_open_1k_events_s` 0.022s；单事件 <1ms、1 万事件 <5MB |
| B5-3 ✅ | 静态质量：新模块 ruff 零告警、core 无 Qt、时区守卫扩容 | `ruff.toml`、`tests/test_layering.py`、`tests/test_timezone_guard.py` | `ruff check .` 零告警；分层守卫通过；时区守卫覆盖 evidence_pack/share_pack |
| B5-4 ✅ | 文档同步：README 中英、guide.html（案例/证据/脱敏使用法）、发布说明草稿 | `README*.md`、`config/help/guide.html`、`docs/releases/v4.3.0.md` | guide 新增「改善案例与证据链」章节 + 目录锚点；README 增加开发文档入口 |
| B5-5 ✅ | 迁移手册：`.qap` 1.6–1.9、案例 v0→v1、插件 2.0→2.1、时区语义、图形依赖 | `docs/migration/v4.3.0.md`（新） | 兼容矩阵 + 升级步骤 + 回退说明 + FAQ 可复现 |
| B5-6 ✅ | **启动依赖修复**：matplotlib/seaborn 缺失不再阻塞主界面 | `main.py`、`ui/runtime_deps.py`、`ui/main_window.py` | 缺依赖时主窗口可启动；图表 Tab 一次性提示安装；5 例测试（含阻塞导入子进程）全绿 |

**出口标准（M5 门禁）**：E2E 演示一条命令复现；既有性能不退化；文档与迁移手册完成。

**B5 完成记录（2026-10-08）**：
- **端到端**：`python tools/demo_v43_case.py --output TEMP/demo_v43` 一键产出
  evidence.zip（独立校验通过）/ share.zip（泄漏扫描通过）/ report.html（追溯码可回读）
  / summary.json；账本 18 条事件、案例 8 阶段全部带凭证、as-of 还原到改善前标准。
- **性能**：基准从 8 项扩至 10 项；`evidence_append_1k_s 0.463s`（0.46ms/条）、
  `case_open_1k_events_s 0.022s`；导入路径每个文件仅 1 条事件（O(1)），单条开销 <5ms。
- **质量**：ruff 全库零告警；core 新模块无 Qt（分层守卫）；时区守卫扩至
  EvidencePack / SharePack。
- **文档**：guide.html 新增「改善案例与证据链」（案例/标准/账本/证据包/脱敏/插件数据源）；
  README 中英新增开发文档入口；发布说明草稿与迁移手册落盘。
- **启动健壮性**：移除 `main.py` 顶层 `import matplotlib`，改用 `MPLBACKEND` 环境变量延迟
  生效；图表预热与 seaborn 预热缺失时静默跳过；打开图表类 Tab 时一次性提示
  `pip install matplotlib seaborn`；阻断 matplotlib/seaborn 的子进程仍可导入主窗口（测试验证）。
- **最终门禁**：全量逐文件回归 **178 文件 / 2180 通过 / 56 跳过 / 0 失败（544.7s）**；
  性能基线 10 项通过（冷启动 1.258s vs 基线 2.101s，tolerance ×4）；ruff 零告警；
  版本一致性通过（本阶段不升版本号，B6 统一到 4.3.0）。

### B6 版本收尾与发布（2–3 人日）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| B6-1 | 版本四端一致：settings / version_info / Inno / 文档 | `config/settings.py`、`version_info.txt`、`packaging/AKIA-installer.iss`、README/ROADMAP/guide | `python tools/check_version.py` 通过 |
| B6-2 | 发布门禁：`python tools/release_check.py`（全量逐文件回归 + ruff + 性能） | — | 全绿并留存证据块 |
| B6-3 | 发布形态决策与执行：源码 / AppImage / Windows（发布时确认） | `docs/releases/v4.3.0.md` | Release 说明与资产一致；tag 与 HEAD 一致 |
| B6-4 | 插件 API 2.1 兼容声明 + 旧插件回归 | `docs/plugin-data-source.md`、`tests/test_plugin_api.py` | 2.0 插件全回归；API 版本文档更新 |

**出口标准（M6 门禁）**：`release_check.py` 全绿，版本四端一致，Release/tag 与 HEAD 一致。

---

## 5. 排期（8–10 周，含 20% 缓冲）

> 当前进度（2026-10-08）：**M0 ✅ 契约冻结 · M1 ✅ 案例闭环持久化 · M2 ✅ 数据源四通道 ·
> M3 ✅ 标准 as-of 复判 · M4 ✅ 证据链与交换 v1 · M5 ✅ 集成/性能/文档收口**；M6 待开工。

| 周 | 批次 | 里程碑 / 门禁 |
|----|------|----------------|
| W1 | B0 | **M0 契约冻结**：MEV/Standard/Ledger schema 定稿 + 契约测试全绿 |
| W2–W3 | B1 | **M1 案例闭环持久化**：UI 建案→保存→重开→关闭门禁通过 |
| W3–W5 | B2 ∥ B3 | **M2 数据源四通道** + **M3 标准 as-of 复判**（两条线可并行） |
| W6–W7 | B4 | **M4 证据链**：账本可验证 + 证据包/脱敏包导出 |
| W8 | B5 | **M5 集成门禁**：E2E 演示 + 性能不退化 + 文档完成 |
| W9–W10 | B6 + 缓冲 | **M6 发布**：`release_check.py` 全绿，版本四端一致 |

**最小可发布集（时间盒 6–7 周）**：B0 + B1 + B3 + B4 核心（账本/证据视图/证据包）；
B2 只保留连接器+文件+手工三条适配与插件能力契约（夹具插件验证），真实视觉适配与
脱敏分享包若超期顺延到 v4.3.1 补丁——顺延必须在 B4 中期显式评审，不允许静默缩水。

---

## 6. 测试与验收策略

### 6.1 新增测试文件（预计 +110~130 例）

| 文件 | 覆盖 | 预计 |
|------|------|------|
| `tests/test_measurement_event.py` | 契约/时间不变量/四类适配/异常 | 20 |
| `tests/test_standard_record.py` | 区间/as-of/diff/迁移 | 18 |
| `tests/test_evidence_ledger.py` | 哈希链/篡改/恢复/性能 | 15 |
| `tests/test_qap_evidence.py` | `.qap` 1.6–1.9 兼容往返 | 12 |
| `tests/test_case_lifecycle.py` | 状态机/关闭门禁/重开 | 15 |
| `tests/test_case_persistence.py` | UI 建案→保存→重开 | 10 |
| `tests/test_plugin_data_source.py` | API 2.1/信任/坏数据隔离 | 10 |
| `tests/test_standard_asof.py` | 历史标准复判 | 10 |
| `tests/test_evidence_view.py` | 追溯链/篡改标红（离屏） | 8 |
| `tests/test_evidence_pack.py` + `tests/test_share_pack.py` | 导出/校验/泄漏扫描 | 12 |
| `tests/test_case_e2e_v43.py` | 端到端演示 | 3 |
| `tests/test_timezone_guard.py` | 新模块无时区棘轮 | 2 |

### 6.2 兼容矩阵（必须全绿）

| 输入 | 期望 |
|------|------|
| `.qap` 1.6 / 1.7 / 1.8 | 可读；无 standards/evidence 段时视图显示"无账本"而非报错；保存升级为 1.9 |
| 案例 schema v0（裸 ImprovementCase） | 可读并按 v1 语义补默认值；不丢 steps |
| 插件 API 2.0（tab/agent_tools/settings） | 行为不变；不因新增 capability 被拒载 |
| 旧分析记录（无 ledger_seq / 无 standard_ref） | 证据视图显示"不可追溯"，diff 仍可比较凭证 |
| 无时区旧时间戳 | 按本机时区解释并标记；不静默改写 |

### 6.3 性能与质量门禁

- 既有 8 项基准不退化（冷启动 / 百万行导入 / 图表 / ML / SPC 10 万·100 万 / MSA / ML 10 万）；
- 新增：`evidence_append_1k_s`（1 千事件追加）、`case_open_1k_events_s`（证据视图打开）；
- 导入/分析主链路账本开销 < 5%；单事件 < 1ms；1 万事件文件 < 5MB；
- `python tools/release_check.py` 全绿；逐文件回归按仓库规则单文件执行。

---

## 7. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 数据模型反复（最大风险） | 返工、迁移链断裂 | B0 冻结 schema + 契约测试 + golden fixture；之后字段只增不减、版本号显式 |
| `.qap` 体积膨胀 | 项目文件不可用 | 账本只存引用/摘要；原始数据仍走 data/ 与 timeseries；B5 设体积预算并实测 |
| 账本拖慢导入/分析 | 性能回归 | 批量事件 + append 缓冲；导入只记批次事件；B5 基准设 <5% 开销 |
| 时区/时钟偏差 | 双时态不可信 | 事件时间与记录时间分离；设备 epoch 保留；偏差标记不拒绝；文档写明语义 |
| 案例关闭门禁过严 | 现场无法收尾 | 门禁只要求"复测 + 一个统计判定"；允许 abandoned 且必须写原因；不要求全部 8 阶段 |
| UI 范围蔓延 | 拖期 | 不新增 Tab；只允许 3 个对话框（案例中心/工作台升级/证据视图）；超期评审 |
| 插件数据源引入不可信数据 | 证据链被污染 | 仅信任插件可调用；schema 校验 + 事件标记 confidence/validity；原始值不直接入报告 |
| 脱敏不彻底 | 隐私泄漏 | 自动化泄漏扫描（原值/路径/人名）作为导出门禁；v1 只允许合成数据，不做"变换后原始数据" |
| 单人体量/排期 | 交付延期 | 定义最小可发布集与顺延项（B4 中期评审），批次之间保持可独立合并 |

---

## 8. 关键决策（默认值已给出，发布前需用户确认）

| # | 决策 | 默认建议 |
|---|------|----------|
| D1 | v4.3.0 发布形态 | 源码先行（tag + Release），AppImage/Windows 按需；沿用 v4.2.x 流程 |
| D2 | 案例范围 | 同一脊柱覆盖 IE 与质量案例；首个 E2E 用 IE 线；8D 自动立案留 v4.4.0 |
| D3 | 账本位置 | 项目内 `.qap` 证据段（随项目迁移）；本机审计日志保留为人类可读副本 |
| D4 | 脱敏方式 | v1 只出"合成数据 + 统计等价声明"，绝不出变换后的原始数据 |
| D5 | 是否新增 Tab | 不新增；案例中心/证据视图用 Home 卡片 + 对话框 |
| D6 | 时间语义 | ISO-8601 带偏移（默认 Asia/Shanghai）；设备 epoch 原样保留 |
| D7 | 哈希链强度 | sha256 前后链（可检测篡改）；HMAC/签名留后续版本，不引入密钥管理负担 |
| D8 | 视觉插件适配 | 主仓库只定义合同 + 夹具插件；真实适配在 Vision-expansion 仓库单独提交 |

---

## 9. 立即修复的小缺陷（本方案 B1/B2 顺带修复，均有测试）

1. ✅ 已修复（B1-3）：`_on_save_project` 未传 `cases=` → UI 案例保存即丢（G1）；
2. ✅ 已修复（B1-3）：`_apply_loaded_project` 未恢复 `project["cases"]` → 重开项目案例不可见（G2）；
3. ✅ 已修复（B1-4）：案例工作台只读 → 现可记录步骤/分析/结论/标准并受门禁关闭（G3）；
4. ✅ 已修复（B0/B1-2）：`owner/product` 已进 schema v1 并随 `CaseWorkflow.to_dict()` 落盘；
   共享项目保存顺带修复 cases 与 project_context 丢失；
5. ✅ 已修复（B2）：插件能力枚举新增 `data_source`，插件测量经校验/超时/来源强化后进入案例（G5）；
6. ✅ 已修复（B4）：HTML 报告已接 12 位追溯码，报告事件以 `trace:<code>` 入账本（G8）。
7. ✅ 已修复（B5 追加）：主入口缺依赖不再是裸报错 ——
   `ui/tabs/__init__.py` 包初始化曾急切导入全部 Tab、绕过懒加载，缺 matplotlib 时任意 Tab 都会连带失败；
   现改为 PEP 562 惰性导出，`ui/widgets/chart_icons.py` 延迟触碰 matplotlib，
   `main_window` 把缺依赖的 Tab 换成安装提示页且不打堆栈，
   `main.py` 增加核心依赖预检（缺 PySide6/numpy/pandas 时输出可执行提示、退出码 1）。

---

## 10. 执行入口（常用命令）

```bash
# 单文件回归（严禁一次传多文件：PySide6+scipy 同进程并发会死锁）
python tools/run_tests.py --quiet --files test_measurement_event.py

# 全量逐文件回归
python tools/run_tests.py --quiet

# 性能基线（新增两项后）
python tools/benchmark.py --tolerance 4

# 发布门禁
python tools/release_check.py
python tools/check_version.py
```

---

## 11. 交付物清单

- **核心契约**：`core/measurement_event.py` · `core/standard_record.py` · `core/evidence_ledger.py`
  · `core/evidence_pack.py` · `core/share_pack.py`；`ImprovementCase`/`CaseWorkflow` v1
- **接线**：`.qap` 1.9（standards + evidence）· 主线程序导入/分析/标准/报告/案例事件写入
  · 插件 API 2.1 `data_source` + 测试夹具插件
- **UI**：案例中心对话框 · 工作台可推进升级 · 证据视图（含账本校验与复核 diff）
- **文档**：本方案 + 迁移手册 + 插件数据源合同 + README/guide/ROADMAP 同步 + `docs/releases/v4.3.0.md`
- **质量**：新增 ≥110 例测试 · 兼容矩阵全绿 · 性能不退化 · ruff 零告警 · 发布门禁全绿
