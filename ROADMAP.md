# QA-Tool 产品路线图

> 最后更新：2026-08-01 | 版本：v1.6 | 历史完成记录见 `D:\AI-agent\Output\CHANGELOG.md`

---

## 一、产品定位

**AI 工业质量 + IE 分析平台** — 面向质量工程师 / IE 工程师 / 六西格玛从业者的桌面分析工具。

| 维度 | 说明 |
|------|------|
| 技术栈 | Python 3.14, PySide6, pandas 3.x, matplotlib, scipy, statsmodels, scikit-learn, shap |
| UI 主题 | **仅暗色模式** |
| 输出格式 | Excel (.xlsx), Word (.docx), PDF (.pdf), PNG |
| 合规模板 | FDA 21 CFR Part 11 / ISO 9001 & IATF 16949 / GB/T 4091 |
| 分析模块 | 25+ 种质量分析 + 5 种 IE 分析 |
| AI 能力 | 数据画像 · LLM 问答 · 知识库 RAG（99 条目）· AI 根因分析（SHAP 三路融合） |
| 企业特性 | **.qap 项目文件** · **SQL 数据库直连** · **批量调度** · **多用户权限+企业协同** |
| 语言 | 中文（zh.json 389 key）/ 英文（en.json 389 key）完全匹配 |

---

## 二、当前整体架构

### 2.1 分层架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                          QA-Tool (v1.6)                               │
├──────────────────────────────────────────────────────────────────────┤
│  UI 层 (ui/)                                                         │
│  ├─ MainWindow: 导入分流 / Sheet路由 / 分析调度 / 信号总线             │
│  │   + .qap项目保存/打开/最近项目 + 共享项目 + 批量调度入口            │
│  ├─ Sidebar: 12 导航项 + 智能诊断 + AI助手 + 分类折叠动画             │
│  ├─ Tabs (12): Welcome·SPC·Cap·MSA·Hypo·DOE·Reg │                    │
│  │              TimeStudy·WorkSampling·LineBalance·OEE·VSM·Chart     │
│  ├─ Dialogs: login·import·settings(含账户标签)·llm(事件过滤器修复)    │
│  │           ·diagnosis·cleaner·chart_viewer·root_cause·compliance    │
│  │           ·db_connection·batch_dialog·user_management              │
│  └─ Theme: 暗色专用 + BUTTON_* 常量 + 填色状态按钮                    │
├──────────────────────────────────────────────────────────────────────┤
│  分析引擎层 (analysis/)                                               │
│  ├─ 质量引擎: spc(9) · capability(3) · msa(3) ·                       │
│  │            hypothesis(4) · doe(4) · regression(1)                  │
│  ├─ IE 引擎: time_study · work_sampling · line_balance(LPT)           │
│  │            · oee(A×P×Q+损失分解) · vsm(拓扑+VA/NVA)                │
│  ├─ AI 引擎: ai/root_cause (SHAP+RF+相关性+异常联动)                  │
│  └─ 共享模块: spc/_rules.py (8条Nelson规则统一实现)                   │
├──────────────────────────────────────────────────────────────────────┤
│  AI 智能层 (core/)                                                    │
│  ├─ DataProfiler: 列画像 + 分析推荐(含置信度评分+健康指标)              │
│  ├─ LLMClient: Ollama REST (qwen2.5:7b) 流式问答                     │
│  ├─ ContextBuilder: 分析结果 → prompt，多轮记忆                       │
│  └─ KnowledgeBase: TF-IDF RAG (99条目), 在线增强+离线检索             │
├──────────────────────────────────────────────────────────────────────┤
│  报告引擎层 (output/)                                                 │
│  ├─ 图表引擎: 智能系统抽样(>300点自动抽样+判异点强制保留+动态图宽)     │
│  └─ BaseReportEngine ← Word/Excel/PDF Reporter + ComplianceReporter   │
├──────────────────────────────────────────────────────────────────────┤
│  企业特性层 (core/)                                                   │
│  ├─ ProjectManager: .qap zip项目保存/加载/最近项目                    │
│  ├─ SharedProjectManager: 部门共享项目目录                            │
│  ├─ SqlLoader: MySQL/PostgreSQL/SQL Server (SQLAlchemy)              │
│  ├─ BatchScheduler: QTimer+QThread批量任务调度                        │
│  └─ AuthManager: PBKDF2认证 · 四级角色 · 部门/班组 · 权限矩阵         │
├──────────────────────────────────────────────────────────────────────┤
│  数据接入层 (core/)                                                   │
│  ├─ 质量通道: DataLoader → DataParser(增强表头检测) → Tabs 1-6+12     │
│  ├─ IE 通道:  DataLoader.load_ie_data → IEDataParser(三维列推断)     │
│  └─ 统一数据模型: 5个@dataclass (含FIELD_ALIASES/format_example)       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 三、Phase 8 企业特性 — ✅ 全部完成

| 子任务 | 状态 | 关键交付 |
|--------|:---:|---------|
| 8.1 .qap 项目文件 | ✅ | `core/project_manager.py` (zip打包) + 主窗口菜单集成 + 最近项目 |
| 8.2 SQL 数据库直连 | ✅ | SqlLoader完整 + DbConnectionDialog + 菜单入口 |
| 8.3 批量调度 | ✅ | `core/batch_scheduler.py` + `ui/dialogs/batch_dialog.py` |
| 8.4 多用户权限 | ✅ | `core/auth.py` (PBKDF2+四级角色) + LoginDialog + UserManagementDialog |
| 8.4+ 企业协同 | ✅ | 部门/班组组织 + 共享项目目录 + SharedProjectManager |

---

## 四、Phase 8.5 质量与体验完善 — 部分完成

### ✅ 已完成
- APP_VERSION → "1.5", en.json 补齐 (389 key), test_integration 路径修复
- Nelson 规则 8/8 全部实现 → `analysis/spc/_rules.py` 共享模块
- IE Tab (7-11) + ChartTab export_clicked 信号连接
- `analysis/__init__.py` 导出 ie/ai/charts
- SqlLoader `__del__` 析构; xbar_r 违规键名统一
- 图表智能系统抽样 (>300点自动抽样+判异点保留)
- 控制图动态图宽 + QScrollArea 滚动
- `ui/tabs/__init__.py` 统一导入
- 一键分析: 三维列推断 + 表头自动检测 + 置信度评分 + 健康指标
- AI助手: eventFilter 修复回车发送 + 线程保护
- ChartTab: 质量导入路径自动加载数据

### ⬜ 待完成
- 测试体系升级 (run_all_tests 迁移 + SPC 单元测试 + pytest)
- OEE 阈值 / LLM URL / 根因分析权重 配置化

---

## 五、Phase 12-14 靶向工具 — 下一迭代 ★

> 贴近 IE/质量工程师日常高频需求。详见 `下一步开发进度.md`

| Phase | 内容 | 估算 |
|-------|------|:--:|
| 12 图表工具扩展 | 11 种 QC/IE 专用图表（工序能力对比、MSA雷达、OEE瀑布等） | 4-6天 |
| 13 数据工具 | 随机数据生成器 + 格式转换器 + AQL抽样工具 | 3-5天 |
| 14 工作表工具 | 合并/拆分 + 分层审核表单(LPA) | 3-4天 |

---

## 六、下阶段规划 — v1.7+

> 详细规划见 `下一步开发进度.md`

| 阶段 | Phase | 内容 | 估算 |
|------|-------|------|:--:|
| **短期** | Bug修复 | 8 bugs (P0-P2) 数据正确性/安全/体验 | 1-2天 |
| **中期** | 9 | 工程工具: 可靠性(Weibull/MTBF)·鱼骨图·FMEA·人机配合 | 2-3周 |
| | 10 | UX体验: 动画过渡·拖拽导入·空状态引导·视觉抛光 | 1-2周 |
| | 11 | 工作表工具: 合并/拆分/LPA分层审核表 | 1-2周 |
| | 12 | 抽样检验: GB/T 2828.1 AQL·序贯抽样·随机抽样器 | 1周 |
| **长期** | 13 | 报告增强: 模板自定义·PDF水印·批量导出·邮件 | 2-3周 |
| | 14 | 数据工具: 随机生成器·格式转换·异常值检测 | 1-2周 |
| | 15 | 插件化: IPlugin接口·加载器·管理器UI | 2-3周 |

---

### Phase 14 数据工具详解

> 质量/IE 工程师日常需要生成测试数据、转换格式、检测异常——侧栏新增「数据工具」分类。

#### 14.1 随机数据生成器

| 功能 | 说明 | 用户场景 |
|------|------|---------|
| **分布生成** | 正态 / 对数正态 / 指数 / 均匀 / 威布尔 / 二项 / 泊松 | "生成 100 组 μ=10, σ=0.5 的数据做 SPC 教学演示" |
| **分组生成** | 指定子组数 + 子组大小，含随机偏移 | "生成 25 组×5 个 = 125 个点的 XBar-R 样本数据" |
| **带规格限** | 可设 USL/LSL，自动计算理论不合格率 | "模拟 Cp=1.33 的过程数据验证能力分析" |
| **MSA 模板** | 零件×操作员×重复次数 三因子交叉设计 | "生成 10 零件×3 操作员×2 重复 = 60 行 MSA 数据" |
| **DOE 模板** | 因子名称 + 水平数 → 全因子/部分因子表格 | "生成 A(2)×B(3)×C(2) 的 DOE 实验表" |
| **时间序列** | 含趋势 + 周期 + 噪声的可控时间序列 | "生成带上升趋势的月度良率数据做演示" |

**新建**: `core/data_generator.py` + `ui/tabs/data_gen_tab.py`

#### 14.2 数据格式转换器

| 功能 | 说明 |
|------|------|
| CSV ↔ Excel | 批量互转，保留编码检测 |
| 宽表 ↔ 长表 | 透视/逆透视 (melt/pivot) |
| 编码转换 | UTF-8 / GB2312 / Shift-JIS 自动检测和转换 |
| 列拆分/合并 | 按分隔符拆分列，多列拼接为单列 |

**新建**: `core/data_converter.py` + `ui/tabs/data_converter_tab.py`

#### 14.3 异常值检测与处理

| 方法 | 说明 |
|------|------|
| **IQR 法** | Q1-1.5×IQR / Q3+1.5×IQR |
| **Z-Score** | |z| > 3 标记异常 |
| **Grubbs 检验** | 单异常值统计检验 |
| **处理建议** | 删除/替换均值/保留标记 + 原因分析 |

**新建**: `core/outlier_detector.py`

#### 14.4 侧栏集成

```python
CATEGORIES 新增:
{
    "key": "sidebar.data_tools",
    "items": [
        (13, "sidebar.data_generator"),    # 随机数据生成器
        (14, "sidebar.data_converter"),    # 格式转换器
        (15, "sidebar.outlier_detector"),  # 异常值检测
    ],
}
```

**舍弃**: MES/ERP 全接口 · Dashboard 大屏 · 移动端 · PLC/SCADA 实时采集 · AI 自动报告生成

---

## 七、变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-08-01 | **v1.6** | **Phase 8 企业特性全部完成**: .qap 项目文件 (ProjectManager+SharedProjectManager)、SQL 直连验收、批量调度 (BatchScheduler+BatchDialog)、多用户权限+企业协同 (AuthManager PBKDF2四级角色/部门班组/UserManagementDialog/设置账户标签页/LoginDialog)。**质量完善**: Nelson 规则 8/8 共享模块 `_rules.py`、控制图智能系统抽样+动态图宽+QScrollArea、一键分析三维列推断+置信度评分+健康指标、AI助手 eventFilter 修复回车+线程保护、ChartTab 数据路由修复、工作抽样填色状态按钮、侧栏 UI 重构(分类折叠动画/分割线消除/按钮迁移菜单)。**Bug修复**: APP_VERSION、en.json 补齐、IE Tab 信号连接、SqlLoader析构、违规键名统一、预览表全量数据、保存PNG按钮样式、分类组按钮间距 |
| 2026-07-30 | v1.5.1 | 交接审计: 版本号/翻译/测试路径修复; Phase 8 优先级重排; Phase 8.5 规划; ROADMAP 结构更新 |
| 2026-07-28 | v1.5 | Phase 7 IE工具扩展 (线平衡/OEE/VSM) |
| 2026-07-28 | v1.4 | Phase 6 AI深化 (SHAP根因分析/知识库RAG) |
| 2026-07-27 | v1.3 | Phase 4+5 (报告引擎/IE工具前两个/暗色主题) |
| 2026-07-22 | v1.2 | Phase 2+3 |
| 2026-07-21 | v1.1 | Phase 1 完成 |
| 2026-07-19 | v1.0 | 项目初始 |
