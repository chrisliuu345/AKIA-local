# QA-Tool 版本路线图 (ROADMAP)

> 当前: v2.3 | 测试: 87/87 | 32 Tab + 插件 | 更新: 2026-08-10

---

## 版本路线图总览

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 🔨 ──→ v2.4 ──→ v2.5
 发布     代码+AI    工程工具    报告增强    实时监控    长期规划
          (完成)     (完成)     (进行中)    (3天)      (待定)
```

---

## v2.1 ✅ 已完成 — 代码质量与 AI 智能增强

### 方向A: 代码质量与架构优化
- 5个P0 Bug修复 (p_chart数据写反/pdf水印/NameError×3)
- 12处裸except消除, 2处iterrows向量化
- Tab懒加载 (TAB_REGISTRY 32项 + importlib按需创建), 启动时间减半
- 200+未使用导入清理, 60+死代码删除
- welcome_page 4个死功能修复、诊断apply_all修复
- 测试: 65→87 (+22)
- 关键修复: pd.to_numeric替代select_dtypes, removeWidget防止Stack错位, iloc防重名列

### 方向C: AI智能增强
- 知识库 99→124条目 (+25: SMED/8D/TPM/PPAP/AQL/Weibull/ALT/非参数)
- 混合检索: TF-IDF(0.5)+关键词(0.3)+标题(0.2)
- AI对话V2: 8预设模板 + 20轮历史 + 导出MD + QSettings持久化 + 流式刷新
- 一键智能分析: 画像→推荐→执行→AI撰写→PDF/MD
- LLM线程管理 (closeEvent quit+wait)

### 体验提升
- 导入工作表→自动分发21个非IE工具 (sheet_map 22条目)
- 欢迎页双入口 (工作表/IE数据)
- IE识别100+别名扩展; 数据校验近常数列静默
- 版本号→2.1, 构建 exe (36.8MB) 含 logo+knowledge

---

## v2.2 ✅ 已完成 — 工程工具扩展

### Phase A: v2.1 遗留修复 (9项)
插件索引33、LLM流式刷新、validate_params完整、动画清理、欢迎页最近项目、诊断apply_all、Chart Tab控件清理、数据校验、profile_result

### Phase B: 新工程工具 (4个)

| 索引 | 模块 | 引擎 | Tab |
|:--:|------|------|------|
| 29 | SMED 快速换模 | `analysis/ie/smed.py` | `ui/tabs/smed_tab.py` |
| 30 | 8D 问题解决 | `analysis/quality/eight_d_engine.py` | `ui/tabs/eight_d_tab.py` |
| 31 | TPM 全面维护 | `analysis/ie/tpm.py` | `ui/tabs/tpm_tab.py` |
| 32 | PPAP 生产件批准 | `analysis/quality/ppap_engine.py` | `ui/tabs/ppap_tab.py` |

**侧栏**: 32 Tab (4新增) · 插件起点 33

---

## v2.3 🔨 报告增强（当前版本）

### Phase A: v2.2 遗留修复 (4项) ✅
- A1: 8D D4页嵌入 FishboneCanvas (6M骨架, render_fishbone)
- A2: PPAP状态变更实时刷新完成度
- A3: PPAP完成度统一使用引擎 completion_pct (按提交等级)
- A4: analysis/ie/__init__.py 和 analysis/quality/__init__.py 导出新模块

### Phase B: 报告系统 (4项)

| # | 模块 | 文件 | 说明 |
|:--:|------|------|------|
| D1 | 模板引擎 | `core/report_templates.py` (新建) | string.Template, 5种内置HTML模板 |
| D2 | 模板对话框 | `ui/dialogs/template_dialog.py` (新建) | 选模板→预览→导出PDF/Word/HTML |
| D3 | 合规报告 | `output/compliance_report.py` | 框架已有, IATF/ISO条款引用 |
| D4 | HTML导出 | `output/html_export.py` (新建) | matplotlib→base64内嵌, 自包含离线HTML |

**菜单**: 工具 → 报告模板 / 导出HTML报告

---

## v2.4 — 实时监控与集成（方向E）

### E1. 文件监控实时SPC（1.5天）
- QFileSystemWatcher 监控文件夹
- 新文件/变更 → 自动导入 → 更新控制图 → 超限告警
- 新建: `core/file_watcher.py`, `ui/tabs/monitor_tab.py` (index 33)

### E2. 多工厂/多产线对比（1天）
- 同指标多线并排 · Cp/Cpk雷达图 · OEE多柱图 · 不良率叠加趋势
- 新建: `ui/tabs/multi_plant_tab.py` (index 34)

### E3. 告警通知系统（0.5天）
- 多通道告警（弹窗/声音/日志）· 可配置规则 · 告警聚合/去重

### E4. 数据看板增强（0.5天）
- 实时刷新Dashboard(27号Tab, QTimer轮询)
- 自定义KPI卡片布局

**预估**: 3天 | 新建 Tab 33-34 | 侧栏 32→34

---

## v2.5 — 长期规划 (P2/P3)

| 优先级 | 功能 | 说明 |
|:--:|------|------|
| P2-1 | 低代码公式编辑器 | 用户自定义KPI公式 (类似JMP Formula Editor) |
| P2-2 | 车间大屏模式 | 全屏仪表盘·自动轮播·适配1920×1080 |
| P2-3 | 视频工时分析 | 视频帧级计时·AI动作识别 (OpenCV+MediaPipe) |
| P2-4 | 批量宏录制/回放 | 录制操作序列→保存为宏→一键回放 |
| P2-5 | 自定义控制图模板 | 用户保存/加载图表配置 (JSON) |
| P3-1 | 供应链质量协同 | P2P供应商数据共享·CPK穿透·物料号映射 |
| P3-2 | 数字孪生Layout | 拖拽工站模拟线平衡·2D Canvas产线布局 |
| P3-3 | REST API服务 | FastAPI包装核心分析→供MES/ERP调用 |
| P3-4 | Web前端迁移 | 逐步从PySide6迁移到FastAPI+React |
| P3-5 | 移动端App | Flutter/React Native查看报告+告警推送 |

---

## 侧栏演进路线

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)
 首页(0)       同左          同左             同左
 质量(1-6)     同左          同左             同左
 IE(7-11,21-22) 同左         +SMED(29)+TPM(31)  同左
 图表(12,18-20) 同左         同左             同左
 工程(13-17)    同左         +8D(30)+PPAP(32)   同左
 工作表(23-25)  同左         同左             同左
 抽样(26)       同左         同左             同左
 报告(27)       同左         同左             同左
 数据(28)       同左         同左             同左
 —              —            —               实时监控(33)
 —              —            —               多工厂对比(34)
 插件(动态)     同左         同左             同左
```

---

## 版本历史

| 日期 | 版本 | 内容 |
|------|------|------|
| 08-10 | v2.3-dev | Phase B: 报告模板引擎 + 对话框 + HTML自包含导出 |
| 08-10 | v2.3-dev | Phase A: 8D鱼骨图嵌入 + PPAP实时刷新 + 引擎包导出 |
| 08-10 | v2.2 | 发布: 32Tab·SMED/8D/TPM/PPAP·87测试·lint干净 |
| 08-10 | v2.2-dev | 审查修复: 3 Critical + 7 Warning (TPM属性/动画/图表) |
| 08-10 | v2.1 | 发布: 87测试·AI增强·懒加载·一键分析·列选择器修复 |
| 08-10 | v2.1-dev | 代码审计: 5Bug·200+导入·60+死代码·15组重复 |
| 08-04 | v2.0 | 正式发布: 28Tab·65测试·AI助手·插件化 |
