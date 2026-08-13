# QA-Tool 项目交接文档（面向 opencode 接管）

> **给 opencode 的说明**：本文件是项目交接的核心文档。opencode 会自动读取 `AGENTS.md` —
> 建议在仓库根目录创建 `AGENTS.md` 内容为 `参考 HANDOVER.md 了解项目`，
> 或将本文件直接重命名为 `AGENTS.md`。开发约定（第四节）为强制条款。

---

## 一、项目概要与速览

### 1.1 定位与状态

| 项 | 值 |
|----|----|
| 名称 | QA-Tool (IE Quality Analyzer) |
| 定位 | 质量工程 + 工业工程分析桌面软件（Minitab 风格） |
| 技术栈 | Python 3.14 + PySide6 + pandas/numpy/scipy/matplotlib/seaborn/sklearn + reportlab/python-docx/openpyxl + Ollama/OpenAI 兼容 API |
| 当前版本 | **v2.4**（2026-08-13 发布，GitHub Release 含 36.9MB exe） |
| 测试状态 | **136/136 通过**（pytest，10 个测试文件） |
| 规模 | 32 个分析 Tab + 插件系统；analysis 53 文件 / core 31 / ui 64 / output 8 |
| 仓库 | https://github.com/chrisliuu345/QA-Tool （main @ `2beaf72`） |
| 打包产物 | `dist/QA-Tool/QA-Tool.exe`（PyInstaller 单目录 ~36.9MB） |

### 1.2 架构分层

```
main.py                 # 入口: Splash → 进度 → MainWindow → 登录 (admin/admin)
analysis/               # 统计引擎层 (纯计算, 无 Qt 依赖)
├── spc/                # 控制图: XBar-R/S, I-MR, P/NP/C/U, CUSUM, EWMA + Nelson 8 规则
├── capability/         # 过程能力: 正态/非正态(Box-Cox/Johnson)/组间组内
├── msa/                # 量具 R&R (交叉/嵌套), 偏倚/线性, 属性一致性
├── hypothesis/         # t检验/ANOVA/正态性/方差齐性/非参数
├── doe/                # 全因子/2^k, CCD, Box-Behnken
├── regression/         # 线性/多元回归
├── ie/                 # 工时/工作抽样/线平衡/OEE/VSM/SMED/TPM
├── reliability/        # Weibull/MTBF/ALT 加速寿命
├── quality/            # 8D 引擎, PPAP 引擎, 鱼骨图
├── charts/             # 15 种图表生成器
└── ai/                 # SHAP 根因分析
core/                   # 业务核心层 (31 文件)
├── data_loader.py      # Excel/CSV 读取 (注意: pandas 默认 header=0 读入)
├── data_parser.py      # 表头检测/列分类/规格限提取 (header 双路径逻辑, 见坑 #1)
├── kpi_extractor.py    # v2.4 统一 KPI 提取器 (结构探测)
├── kpi_formula.py      # v2.4 AST 白名单公式引擎 (安全红线)
├── i18n.py             # 翻译引擎 (当前仅中文生效, en 为预留)
├── auth.py             # 4 级角色 + PBKDF2 认证
├── knowledge_base.py   # TF-IDF RAG 知识库 (124 条目, 5 类 JSON)
├── llm_client.py       # Ollama + OpenAI 双后端
├── plugin_manager.py   # 插件发现 (Tab 索引从 33 起)
└── session_manager.py / project_manager.py / data_profiler.py ...
ui/                     # PySide6 界面层
├── main_window.py      # 主窗口 (~1600 行): 懒加载/菜单/状态栏/导入路由
├── sidebar.py          # 侧栏: 分类折叠 + 历史记录
├── _tab_registry.py    # TAB_REGISTRY: 32 Tab 单一数据源 (index→模块映射)
├── tabs/               # 32 个分析 Tab (继承 base_tab.BaseAnalysisTab)
├── dialogs/            # 18 个对话框 (含 v2.4 新增 formula/layout/display_mode)
└── widgets/            # ElidedLabel (自动省略号标签), Toast, 鱼骨图画布
output/                 # 报告引擎: excel/word/pdf/html/compliance/chart
config/                 # settings.py (版本号/Nelson规则/控制图常数) + knowledge/ (5 JSON) + templates/ (5 HTML + 3 合规模板)
locales/                # zh.json (540 键) / en.json (524 键, 缺 16 键 — 见遗留 #1)
plugins/                # example_plugin.py + 插件接口
tests/                  # 136 测试 (10 文件)
utils/                  # 一次性开发脚本 (generate_test_data.py 等)
```

### 1.3 核心机制（必须理解）

1. **Tab 懒加载**：`ui/_tab_registry.py` 的 `TAB_REGISTRY` 是 32 个 Tab 的唯一数据源
   `(index, i18n_key, class_name, module_path, category_key)`。主窗口首次访问时
   `importlib` 动态导入并替换 QStackedWidget 占位符。**新增 Tab 必须同时注册
   TAB_REGISTRY + 侧栏 CATEGORIES + locales 三处**（见第四节约定）。

2. **current_result 三件套包装**：每个 Tab 分析完成后必须写：
   ```python
   self.current_result = {
       "analysis_type": "显示名",   # 中文, 侧栏历史/Dashboard 卡片标题
       "params": {...},            # 本次分析参数
       "result": {...},            # 引擎原始输出 dict
   }
   ```
   主窗口 `_on_analysis_finished` 读取该属性存入 `self.analyses[idx]` 并通知
   Dashboard 刷新（`_notify_dashboard` → `refresh_if_changed` 指纹去重）。

3. **引擎输出形状多样**：各引擎返回结构互不相同（capability 嵌套 `capability`、
   OEE 嵌套 `overall`、MSA 嵌套 `percentages.grr_pct_tv`、P 图顶层 `violations`、
   回归顶层 `r_squared`、TPM 顶层 `avg_oee`）。`core/kpi_extractor.py` 用**结构探测**
   （顶层特征键）而非名称匹配提取指标。**修改引擎输出形状时须同步更新提取器与
   `tests/test_kpi_extractor.py`**。

4. **公式引擎安全**：`core/kpi_formula.py` 是 AST 白名单解析器（禁止 Call/Attribute/
   Subscript），带 500 字符长度上限、200 求值深度上限、复数/inf/nan 结果拒绝。
   23 个攻击用例测试覆盖。**白名单不可放宽**（见安全红线）。

5. **标度约定**：所有百分比指标统一 0-1 分数（OEE/GRR 等）；MSA 引擎输出
   `grr_pct_tv` 是 0-100 百分数，由提取器 `/100` 归一化。公式变量、Dashboard
   卡片、大屏 KPI 都基于归一化后的值。

### 1.4 上手必读的 5 个坑

| # | 坑 | 说明与避免方法 |
|---|----|----|
| 1 | **表头双路径** | `DataLoader` 用 pandas 默认 `header=0` 读入（列名已是表头），而 `DataParser._apply_header` 历史上会把数据第一行重赋为列名（v2.4.1 已修：仅列名为默认数字时才提取首行）。测试构造 df 时注意两种输入形态 |
| 2 | **QSettings 作用域分离** | 布局设置存 `QSettings("QA-Tool", "Dashboard")`，公式存 `QSettings("QA-Tool", "Formulas")`，主窗口几何存 `("QA-Tool", "MainWindow")`。传错 settings 对象会静默读不到数据（F3 曾踩坑） |
| 3 | **空态 widget 叠加** | `QGridLayout.takeAt(0)` 只移除布局项**不销毁 widget**，孤儿 widget 仍显示。清空网格必须 `item.widget().setParent(None) + deleteLater`，空态标签要纳入统一管理列表 |
| 4 | **en.json 键缺口** | zh 540 键 / en 524 键。`i18n.tr()` 缺键时回退显示键名。新增文案必须同时加 zh + en 两个文件 |
| 5 | **离屏测试模态框** | `QT_QPA_PLATFORM=offscreen` 下 `QMessageBox.information/warning` 会永久阻塞（无人点击）。离屏验证脚本需 `QMessageBox.warning = staticmethod(lambda *a, **k: None)` 打补丁 |

---

## 二、操作清单

### 2.1 环境搭建

```bash
# Python 3.14 (本项目环境: C:\Python314)
cd D:\AI-agent\projects\ie-quality-analyzer
pip install -r requirements.txt    # 20 项依赖, 全部 >= 版本下限
```

### 2.2 日常运行

```bash
python main.py          # 无 CLI 参数; Splash → 主窗口 → 登录
# 登录: admin / admin (4 级角色: admin/dept_admin/analyst/readonly)
```

语言：仅中文生效（`core/i18n.py` 只加载 zh.json；en.json 为预留，`set_language("en")` 未接线）。

### 2.3 测试

```bash
python -m pytest tests/ -q          # 136 项全量 (pytest.ini: testpaths=tests, -v --tb=short)
python -m pytest tests/test_kpi_formula.py -q    # 单文件
python tests/run_all_tests.py       # 独立跑法, 报告写入 D:\AI-agent\Output\QA-Tool\test_report.md
```

测试文件与覆盖：
- `test_integration.py` — 全分析模块集成（模块级断言，收集失败即报错）
- `test_kpi_extractor.py` / `test_kpi_formula.py` — v2.4 新增（真实引擎形状/注入安全）
- `test_display_mode.py` — 大屏模式（offscreen QApplication）
- `test_v2_1.py` / `test_core_modules.py` / `test_nelson_rules.py` / `test_reliability.py` / `test_alt_nonparametric.py` — 历史回归

### 2.4 打包

```bash
# 前置: config/templates/*.html 必须已生成 (core/report_templates.py 运行时生成,
# 若不存在先执行: python -c "from core.report_templates import _ensure_templates; _ensure_templates()")
python -m PyInstaller QA-Tool.spec --noconfirm
# 产物: dist/QA-Tool/QA-Tool.exe (~36.9MB, 单目录模式)
# 注意: *.spec 在 .gitignore 中, 不入库; 修改打包配置需改 spec 文件本身
```

### 2.5 GitHub 发布流程（已验证）

```bash
git add -A && git commit -m "feat: ..." && git push origin main
git tag -a vX.Y -m "vX.Y: 英文描述" && git push origin vX.Y
# 创建 Release 并上传 exe (gh CLI 经 git credential-manager 取 token):
gh release create vX.Y --repo chrisliuu345/QA-Tool --title "vX.Y — 英文标题" --notes "<英文 notes>"
gh release upload vX.Y "D:\AI-agent\projects\ie-quality-analyzer\dist\QA-Tool\QA-Tool.exe" --repo chrisliuu345/QA-Tool --clobber
```

**发布要求（用户明确规定）**：README、ROADMAP、Release notes、更新日志必须为英文。
代码提交信息用中文（`<type>: <description>` 格式）。

### 2.6 手动测试

- 测试数据：`D:\AI-agent\Output\QA-Tool手动测试数据.xlsx`（7 Sheet：首件数据/过程数据/OEE数据/TPM记录/MSA数据/假设检验/回归数据），生成脚本 `generate_test_data.py` 同目录
- 测试路径：首页 → 导入工作表 → Sheet 自动匹配 → 各 Tab 运行 → Dashboard 卡片 → F11 大屏 → ESC 退出
- 离屏 UI 验证模式（无人工目检时的替代）：
  ```python
  os.environ["QT_QPA_PLATFORM"] = "offscreen"
  # 实例化 MainWindow → 注入 mock analyses → _switch_tab(idx) → grab() 截图 / findChildren 断言
  # 注意 QMessageBox 打补丁 (坑 #5)
  ```

### 2.7 常见故障

| 症状 | 处理 |
|------|------|
| .xls 读取失败 | DataLoader 回退 calamine → xlrd；确认 `python-calamine` 已装 |
| 图表中文乱码 | 依赖 Microsoft YaHei；Linux 需装文泉驿并改 `config/settings.py FONT_FAMILY` |
| PyInstaller 找不到 templates | 先运行 `_ensure_templates()` 生成 config/templates/*.html |
| 测试收集失败 | `pytest.ini` 的 pythonpath=`.` 依赖项目根目录执行；test_integration 为模块级断言 |
| MCP 服务器异常 | 检查编辑器 MCP 服务器配置与日志（工作区问题，与项目无关） |

---

## 三、历史记录

### 3.1 版本史

| 日期 | 版本 | 内容要点 |
|------|------|---------|
| 2026-08-04 | v2.0 | 首发：28 Tab · 65 测试 · AI 助手 · 插件系统 |
| 2026-08-10 | v2.1 | 代码审计（5 P0 bug + 200 导入清理）· AI 增强（知识库 124 条/混合检索/一键分析）· Tab 懒加载（启动减半）· 测试 87 |
| 2026-08-10 | v2.2 | 4 个工程工具：SMED(29)/8D(30)/TPM(31)/PPAP(32) · 32 Tab · 审查修复 3 Critical |
| 2026-08-12 | v2.3 | 报告模板引擎（5 内置模板）· 模板对话框 · HTML 自包含导出 · 菜单栏重构（6 菜单 i18n） |
| 2026-08-13 | v2.3.1 | UI 文字显示修复：表头裁切（TPM/PPAP）· ElidedLabel 组件 · 欢迎页卡片 · 菜单 i18n |
| 2026-08-13 | **v2.4** | **Dashboard 增强（长期规划 P2-1/P2-2 提前）**：F0 统一 KPI 提取器（修复 3 项坏指标）· F1 实时刷新 · F2 卡片布局 · F3 公式编辑器（AST 白名单）· F4 车间大屏（F11 轮播）· 136 测试 |

关键 commit（v2.4 主线）：`69be89f` F0-F2 → `6254770` F3 → `b0eab05` F4 → `c7aaafe` DataParser 修复 → `f28d246` 大屏裁切修复 → `2beaf72` 发布文档。

### 3.2 重要 Bug 修复记录（含避免方法）

| Bug | 根因 | 修复与教训 |
|-----|------|-----------|
| P 图数据写反（v2.1） | `total_inspected` 用了错误的聚合 | 写引擎时核对字段语义，单测覆盖字段级断言 |
| Dashboard 3 项指标从未显示（v2.4 F0） | 键路径写错：OEE 在 `overall.oee`、GRR 在 `percentages.grr_pct_tv`、SPC 违规在 `xbar_chart.violations` | 测试必须用**真实引擎输出形状**，捏造形状会给假信心 |
| %GRR 显示 100 倍（v2.4 审查） | 引擎输出 0-100 百分数，格式化又乘 100 | 提取层归一化为 0-1 分数，单一标度约定 |
| DataParser 列名丢失（v2.4.1） | `header=0` 读入后仍把数据首行重赋为列名 | header 双路径判定（默认数字列名才提取首行） |
| 空态"请先运行分析"叠加（v2.4.1） | `takeAt` 不销毁 widget + 空态下指纹早退失效 | 清理网格必须销毁 widget；空态纳入统一管理 |
| 大屏图表裁切（v2.4） | QLabel 按原始像素 1:1 显示 150dpi 大图 | ScaledPixmapLabel：KeepAspectRatio + resize 重缩放 |
| 公式长链逃逸 RecursionError | 深度无限制的递归求值 | 长度 500 + 深度 200 + 三重异常捕获，只抛 FormulaError |
| 列名 sanitize 碰撞（"A/B" vs "A B"） | 不同列名 sanitize 后同名静默覆盖 | 冲突列追加序号后缀 |
| 公式读不到（F3） | 传了 Dashboard 作用域的 QSettings 读 Formulas 数据 | 不同用途用不同 QSettings 组织名，读取方必须匹配 |
| 可靠性结果进不了 analyses | `reliability_tab` 只发信号不设 `current_result` | 所有 Tab 统一三件套包装（v2.4 已修 reliability/TPM 两处） |

### 3.3 架构决策记录

1. **结构探测优于名称匹配**：分析类型显示名随语言/图表类型变化，而引擎结果有稳定顶层特征键 — `kpi_extractor` 据此设计。
2. **指纹去重**：Dashboard 刷新用轻量内容签名（深度受限的 `_sig`，O(1) 不遍历大数组）避免 N+1 次全量重绘与 5 秒轮询空转。
3. **df 缓存**：公式变量列统计的 `DataParser.prepare` 是重清洗（50k 行约 1 秒），按 `(id(df), len(df))` 缓存。
4. **零依赖公式引擎**：stdlib `ast` 白名单而非 eval/第三方解析器 — 安全且无新依赖。
5. **ElidedLabel 统一省略**：状态栏/侧栏历史/欢迎页路径/卡片指标行共用，自动省略号 + tooltip 全文。

### 3.4 遗留事项与已知限制

1. **en.json 缺 16 键**（524 vs zh 540）— 英文模式为预留功能，如需启用先补齐键并接线 `i18n.set_language("en")` + UI 刷新。
2. **v2.4 方向 E 未完成**：E1 文件监控实时 SPC（`core/file_watcher.py` + monitor_tab 33）、E2 多工厂对比（multi_plant_tab 34）、E3 告警通知系统 — ROADMAP 已标注待排期。
3. **会话加载与 analyses 不一致**：`_on_load_session` 只恢复 Tab 参数不恢复 `self.analyses`；`session_manager.add_analysis` 仅在 `_on_run_analysis` 调用（`_on_analysis_finished` 未调用）。
4. **SMED Gantt y 轴标签**：预设名较长时 matplotlib 标签可能重叠（图表侧，tight_layout 部分缓解）。
5. **LLM 线程**：llm_dialog 的 closeEvent quit+wait(2000) 为兜底方案，长时间流式响应关闭可能延迟。
6. **大屏图表无交互**：轮播为静态位图（150dpi），不支持缩放/平移 — 设计取舍。
7. **`_on_load_recent`/`_on_load_project`/`_on_load_session` 三处加载逻辑重复**，可重构合并。
8. **user_config.json 在根目录**且被 gitignore（用户本地配置，非版本化）。

### 3.5 未来规划

**v2.4 剩余（方向 E）**：E1 文件监控实时 SPC（1.5 天）→ E2 多工厂/多产线对比（1 天）→ E3 告警通知（0.5 天），新建 Tab 33-34。

**v2.5 长期（P2/P3）**：P2-3 视频工时分析 · P2-4 批量宏录制 · P2-5 自定义控制图模板；P3-1 供应链协同 · P3-2 数字孪生 Layout · P3-3 REST API · P3-4 Web 前端迁移 · P3-5 移动端。
（P2-1 公式编辑器 / P2-2 大屏模式已于 v2.4 提前完成。）

---

## 四、开发约定（opencode 必须遵守）

### 4.1 编码规范

- **中文注释与文档，英文代码标识符**（项目一贯风格，勿混用）
- 所有用户可见文字走 `i18n.tr(key)` — **zh.json 与 en.json 必须同时添加**（缺 en 会回退显示键名）
- 遵循既有代码风格：简洁、函数式倾向、docstring 中文
- 提交信息 `<type>: <description>`（中文描述）

### 4.2 结构性约定（破坏即回归）

1. **新 Tab 三处注册**：`ui/_tab_registry.py` TAB_REGISTRY → `ui/sidebar.py` CATEGORIES → `locales/zh.json` + `en.json`（`sidebar.xxx` 键）。插件 Tab 索引从 33 起，不占用 1-32。
2. **current_result 三件套**：所有 Tab 完成分析必须写 `{"analysis_type", "params", "result"}` 包装并 emit `analysis_completed`（见 1.3-2）。
3. **引擎输出形状变更**：同步更新 `core/kpi_extractor.py` 结构探测 + `tests/test_kpi_extractor.py`（用真实引擎输出断言）。
4. **公式引擎白名单不可放宽**：任何允许 Call/Attribute/Subscript 的修改都构成安全回归，测试必须保持 23 攻击用例全拒。
5. **QSettings 作用域**：新持久化数据用独立组织名，读取方不得混用（见坑 #2）。
6. **QGridLayout/QStackedWidget 清理**：移除布局项必须销毁 widget（坑 #3）。

### 4.3 修改后验证（每次改动必做）

```bash
python -m pytest tests/ -q     # 全量必须 100% 通过 (当前 136)
```
- UI 改动附加：离屏实例化 + 截图/断言（坑 #5 的 QMessageBox 补丁）
- 引擎改动附加：真实输出形状单测 + Dashboard 卡片渲染验证
- 发布前附加：README/ROADMAP 英文更新 + 版本号 `config/settings.py` + tag

### 4.4 发布红线

- GitHub 上的 README/ROADMAP/Release notes/提交文档语言为**英文**
- 发布前由用户手动测试确认后才推送（v2.4 流程）
- Release 流程见 2.5，exe 上传至对应 tag

---

*交接文档生成于 2026-08-13 · 项目版本 v2.4 · 136/136 测试通过 · 仓库 main @ 2beaf72*
