# QA-Tool 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v3.4.0 可靠性与生存分析（已交付）| 测试: 907+ pytest · 37 个 Tab | 更新: 2026-09-04

---

## 版本总览

> **战略重定位（2026-08-24）**：定位从企业级多公司平台调整为**个人订阅级质量工程工具**（类 Minitab），差异化核心为实时工厂数据集成 + IE 工程工具 + 五链工作流 + BYOK AI Agent（QAM Harness）。详见[核心竞争力定位](#核心竞争力定位2026-08-重规划)。

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ✅ ──→ v2.6.4 ✅ ──→ v2.6.5 ✅ ──→ v2.7.0 ✅ ──→ v2.8.0 ✅ ──→ v2.9.0 ✅ ──→ v3.0.0 ✅ ──→ v3.1.0 ✅ ──→ v3.2.0 ✅ ──→ v3.3.0 ✅ ──→ v3.4.0 ✅ ──→ v3.5.0 ──→ v3.6.0 ──→ v3.7.0 ──→ v3.8.0 ──→ v3.9.0 ──→ v4.0.0
```

| 阶段 | 版本 | 主题 |
|------|---------|------|
| 已完成 | v2.0 ~ v3.1.0 | Release → 代码+AI → 工程工具 → 报告 → 实时监控 → UX+动画 → 硬件扩展 → ESP32 部署 → 安全校验 → RBAC+认证 → 统计引擎加固 → UI 健壮性 → 缺陷清零 → 统计引擎深化 → 工作流贯通 → 安全架构重构 → 稳定化里程碑 → DOE与功效分析 |
| 已完成 | v3.2.0 | **Linux 移植 + 双系统发行**（Debian/Ubuntu） |
| 已完成 | v3.3.0 | **时间序列与预测**（ARIMA / 指数平滑 / 季节分解 / 模型对比） |
| 已完成 | v3.4.0 | **可靠性与生存分析**（Weibull 2P/3P/4P + CI / KM + Cox / ALT / RBD / Crow-AMSAA / 保修） |
| 待开发 | v3.5.0 | MSA 与能力深化 |
| 待开发 | v3.6.0 | Graph Builder 增强与交互体验 |
| 待开发 | v3.7.0 | 实时 SPC 云看板与数据连接器 |
| 待开发 | v3.8.0 | QAM Harness（BYOK AI Agent 平台） |
| 待开发 | v3.9.0 | 视频时间研究 |
| 待开发 | v4.0.0 | 预测分析与机器学习 |
| 待开发 | v4.1.0 | 待定（根据 v3.x 进展定义） |

---

## 核心竞争力定位（2026-08 重规划）

> **定位**：个人订阅级质量工程工具（类 Minitab），差异化核心为实时工厂数据集成 + IE 工程工具 + 五链工作流 + BYOK AI Agent。
> 基于 2026-08 开源竞品全景调研（JASP / Jamovi / Cassini / SigmaExacta / Point85 OEE / pyDOE / R 生态 qcc·FrF2·gageRR 等）及 Minitab 功能对标：**开源界不存在任何同时覆盖 SPC + 能力 + MSA + 假设检验 + DOE + IE 工具 + FMEA/8D/PPAP + AI + 硬件 + 中文的桌面一体化软件。** 唯一近全覆盖者为商业软件 Datalyzer（~$2593/年）。

### 差异化支柱（按独特性排序）

| # | 支柱 | 竞品现状 | 深化主线 |
|---|------|----------|----------|
| 1 | **质量工作流贯通**（FMEA→控制计划→SPC→PPAP→8D 数据链） | 空白：SigmaExacta 三件套互不联通，Minitab 无此链路 | **v2.8.0（差异化核心）** |
| 2 | **实时工厂集成**（ESP32/MaixCAM 原生桌面集成，PLC/CMM/量具数据连接器） | Minitab 需额外购买 Prolink + Real-Time SPC；开源近乎空白 | **v3.6.0（云看板 + 数据连接器）** |
| 3 | **IE 工程工具套件**（SMED/TPM/OEE/8D/FMEA/PPAP/控制计划） | Minitab 无 IE 工具；JASP/Cassini 无 FMEA/PPAP | **v2.2.0 已完成，持续深化** |
| 4 | **QAM Harness**（BYOK AI Agent，主动建议型，多供应商 API 接入） | Minitab Copilot 仅限云端；竞品 AI 全部云依赖或原型阶段 | **v3.7.0** |
| 5 | **中文优先 + 离线桌面**（工厂车间场景，GB/T 标准内置） | 空白：无开源 QE 工具提供原生中文 UI | 全程保障 |

### 规划原则

1. **编号缺陷修复优先** — W 系列全部清零（v2.6.5）后方可进入大版本迭代
2. **v2.6.5~v3.0.0 只深化、不扩张** — 不新增 Tab、不新增独立功能模块，全部投入现有能力的正确性、深度与贯通性
3. **v3.1.0~v3.5.0 持续小版本** — 每版本聚焦一个统计领域补齐（对标 Minitab 核心能力），不贪多
4. **v3.5.0+ 大版本迭代** — 围绕差异化核心（实时工厂/QAM Harness/视频研究/预测分析）做功能拓展
5. **统计正确性以已知值验证** — 新增统计方法必须以 NIST/权威文献已知值数据集做单元测试
6. **测试基线只增不减** — 537+ 为下限（随版本上浮），每版本全量回归
7. **个人订阅定位** — 不做企业多公司平台/RBAC分层/服务器部署；专注桌面单机 + 实时设备连接

---

> **归档说明（2026-08-24）**：v2.1 ~ v2.5（代码质量与 AI / 工程工具扩展 / 报告增强 / 实时监控与看板 / ESP32 硬件扩展）规划章节已精简，完整记录见文末[版本历史](#版本历史)表。

---

## v2.6.0 ✅ 已发布 — ESP32 部署拓展 + 设备监控 Tab

### 部署拓展（ESP32 输入端）
- 固件 v1.1.0 实机部署：`esp32_in_6cc84055ec48` 已在 COM3 运行（MicroPython v1.20 + UART1 重映射, 7 通道），自动发现 → ONLINE → META → 每秒 DATA 全链路验证通过
- 主机侧发现/监控支持复位脉冲感知（reset pulse aware）

### 设备监控 Tab 35 功能完善
- 设备卡片：类型图标/徽章、名称省略 + tooltip、状态色点（在线/离线/错误）、端口 + 心跳显示、选中态高亮
- **停止监控 / 继续监控**：卡片双按钮（置灰式），新设备默认监控开启，停止后状态跨刷新持久，可随时恢复（重新 attach = 串口重开 + 板子复位 + HELLO）
- 实时数据预览表：20 行常显（行数较初版翻倍），列宽 Stretch 稳定
- 一键导入：设备采样 DataFrame → 路由到其他分析 Tab（`_route_sheets_to_tabs`）
- 修复：卡片文字遮挡（_ElidedLabel 省略号处理）、空态提示与卡片重叠、按钮文字裁切

### ESP-32 配置门控
- `user_config.json` 新增 `esp32_extension` 开关（默认开启，兼容旧包）；关闭时侧边栏隐藏设备监控按钮、Tab 35 不加载
- 新增 `config/settings.py`：`tab_allowed(idx)` / `esp32_extension_enabled()`

### 打包发布体系
- 品牌资源：`assets/logo.ico`（7 尺寸）+ `version_info.txt`（2.6.0, 中文描述）
- PyInstaller **onedir**：QA-Tool.exe（38MB）+ `_internal/`（454MB 总量），GUI 无控制台
- **Inno Setup 安装器**（135MB）：中文界面、管理员安装到 Program Files、组件页"ESP-32 硬件拓展"勾选框（决定安装期开关写入）、桌面/开始菜单快捷方式、卸载支持
- 测试: 278（+3 设备监控启停 + 5 配置门控 + 双语文档）

---

## v2.6.1 ✅ 已完成 — 安全校验

### 密码策略（`core/password_policy.py`）
- 最小长度 8 位 + 含字母与数字，中文校验提示
- 接入 `create_user` / `reset_password` / `change_password`（弱密码拒绝并写审计）
- UI 同步：设置对话框密码修改校验、用户管理默认密码 → Pass1234

### 审计日志（`core/audit.py`）
- 公共审计入口（同 `~/.qa_tool_audit.log`，UTF-8 追加，吞异常）
- 业务事件扩展：数据导入（质量/IE/数据库）、单/汇总/合规导出、设置保存、数据清洗、共享项目保存

### 密钥库（`core/secret_store.py`）
- Windows DPAPI 加密（`dpapi:` 前缀，兼容旧 base64 平滑迁移）
- 数据库连接密码加密存储（原 base64 混淆）
- SQL 连接串异常密码脱敏（`sanitize_connection_error`）

> 测试: 278 → 282（新增 `tests/test_security_fixes.py` 4 用例）
>
> 未纳入：认证加固（尝试次数/锁定）与 RBAC 权限矩阵 → 移至 v2.6.2；硬件收尾 2 项 → 移至 v2.6.2

---

## v2.6.2 — RBAC 权限矩阵 + 认证加固 + 设备可靠性（已完成）

> 全部任务已完成（Commits A-I，b8de78a…84c5945）：RBAC 守卫/菜单/侧边栏/欢迎页过滤 + 认证锁定与强制改密 + 安全加固 W01-W17 + 设备链路 C04/C05/C06/C19/W87-W100 + 合成测试数据契约修复 + esp32_out 实机验证（COM3，8 项协议全过）+ MaixCAM 网络接入（TCP 192.168.50.46:9000 实机全链路验证）。原代码审查前置修复（12/19 Critical，commits ae04c38/d2c7426/53e888d）：认证越权 C01/C02/C03/C13/C14、nav_buttons 污染 C08、功能失效与崩溃 C07/C09/C10/C11/C12/C17、合成测试数据 C18。

### RBAC 权限矩阵落实（核心）
- 目标：让 `_ROLE_PERMISSIONS`（admin/dept_admin/analyst/readonly 四级）真正生效，双层防护"隐藏 + 拦截"
- 权限映射：import（导入 4 入口 + 数据 Tab）、analyze（分析类 Tab + 批量 F5）、clean（清洗向导）、export（导出 3 入口）、settings（设置）、share_project（共享）、view（Tab 查看/大屏 F11/欢迎页）
- 实现要点：`MainWindow._check_permission(action)` 统一守卫（user=None 全放行）→ handler 拦截 + 菜单置灰 + 快捷键守卫 + sidebar/welcome 按角色过滤 + `_lazy_load_tab` 兜底；拒绝时弹窗提示并写审计
- 五条旁路统一门控：`_switch_tab` / handler / 拖拽导入 / 快捷键 / welcome 直插
- 新增 `tests/test_rbac_ui.py`；回归 test_v2_1 / test_main_window / test_extension_gating
- RBAC 耦合 UI 修复：W40 插件 Tab 双实例化、W44 refresh_menu 文本匹配改 action 键、W45 硬编码 35/36 改 TAB_REGISTRY、W47 拖拽导入补 audit

### 认证与安全加固
- 登录尝试限制与锁定（5 次失败锁定，持久化）+ 首次登录强制改密（`must_change_password`）
- 存量用户文件迁移兼容（W03 `User(**u)` 旧字段容错）
- 安全加固（与认证同源）：W01 change_password 审计误导、W04/W05 audit 双实现同步与轮转、W06/W07 SQL 脱敏正则与跨方言、W08 project_manager 部门名路径穿越、W09 log_util 单例缓存、W11 login 默认凭据、W13/W14 用户管理返回值与提示、W15 DPAPI 异常降级、W16 compliance template_id 校验、W17 Excel 公式注入

### 设备链路加固
- Critical：C04 transport buf 滑窗限长、C05 回调异常隔离防断连、C06 batch_scheduler `_running` 集合防并发、C19 esp32_out 循环体异常保护
- Warning：W87 discovery 并行扫描、W88 monitor stop 超时处理、W89 registry 持久化加锁、W93 context_builder acceptance 类型校验、W94 batch daily 窗口、W97 esp32_in DS18B20 非阻塞、W98 esp32_in 通道初始化容错、W100 esp32 RTC 同步

### 硬件收尾（自 v2.6.1 移入）
- **esp32_out 实机验证** ✅：第二块板烧录固件，验证 COMMAND→ACK 驱动真实执行器（LED/继电器/舵机）
- **MaixCAM** ✅：网络传输（TCP/SSH）设备接入 — firmware/maixcam_server.py 部署于设备 :9000，PC 端 TcpTransport/probe_network_device/monitor 分支/添加网络设备对话框，18 项单测 + 实机全链路验证

### 测试
- T44 sidebar 缺 `import_db_clicked` 信号 ✅（import_db 走菜单 QAction + RBAC 注册）

---

## v2.6.3 ✅ 已完成 — 统计引擎加固

> 主题：统计正确性 — 质量工具的核心价值。修复全库代码审查发现的统计边界缺陷与常数表错误。
> 测试: 104+ pytest 全部通过 | 修复: 2个Critical + 29个Warning | 2026-08-21

### Critical 统计正确性
- C15 `gage_rr.py` AV/PV 常数表：SPC d2 → MSA d2*（n=2 高估 25%，n=3 约 13%），settings.py 新增 d2* 因子表
- C16 `chart_generator.py` 瀑布图累积基线错误：i=0 不累加致整体偏移

### 统计边界加固（W18-W39）
- Nelson 规则：W18 规则5 两点同侧判定修正
- 假设检验：W19/W20 配对检验 dropna 对齐、W27 alt 最小样本校验、W28 温度单位对称
- 正态性与能力：W21 normaltest n<8、W22 shapiro n=2、W23 std=0 返回值、W24 non_normal_cap 除零、W25 单观测子组、W33 xbar_s 魔法数
- 控制图：W29 cusum 常数列、W30/W31 p/u/c chart 校验、W32 ewma 初值用 μ0
- 方差与 DOE：W34 anova 单观测组、W35 factorial 编码 mask、W36 doe shapiro N<3
- 可靠性：W26 weibull 全相等退化、W37 censored 长度匹配
- 抽样：W39 sampling_engine _NORMAL_TABLE 与 _AQL_VALS 错位

### 统计输出健壮性
- W76 chart 空数据、W77 全零除零、W78 figure_to_bytes 泄漏、W79 griddata 重复坐标

### IE 统计模块
- W10 one_click grr_pct 量纲、W82 smed improved_time、W85 time_study kstest、W90 data_profiler iloc 兜底、W92 data_validator kstest 退化

---

## v2.6.4 ✅ 已完成 — UI 健壮性 + 报告安全 + 测试质量

> 主题：剩余 UI 崩溃/正确性 + 输出安全 + 测试可信度。聚焦崩溃与契约一致性，低价值打磨项降级 P2。
> 测试: 289+ pytest 全部通过 | 修复: 26项代码修改 | 2026-08-22

### UI 崩溃与正确性（15 项）
- W58 fmea_tab 模式切换先改后确认 → 确认后才赋值
- W41 _on_import_db 连接泄漏 → try/finally 包裹 connect/disconnect
- W53 device_tab closeEvent 未停 discovery → 加 _discovery_running=False
- W55 doe_tab 生成设计覆盖原始数据 → 备份 _original_df
- W56 hypothesis_tab factor2 可空 → validate_params 加非空校验
- W57 msa_tab 线性分析 part 列空 → validate_params 加 part 校验
- W42 spc_tab USL/LSL=0 跳过 → 新增规格限启用复选框
- W64 oee_tab oee=None 崩溃 → or 0 安全取值
- W65 ppap_tab 单点虚假 Cp → n<2 / σ=0 提示
- W66 reliability 3P Weibull NaN → 拟合后 NaN 检测
- W67 sheet_split dtype=str → 移除 dtype=str
- W46 main_window F5 全量冻结 → processEvents 让出事件循环
- W52 device_tab 后台线程改 QWidget → 信号回主线程
- W68 cellChanged 每键触发 → blockSignals
- W110 batch _refresh_log O(n²) → set 增量追踪

### 输出与报告（5 项）
- W48 base_tab plt.close(“all”) 误关 → plt.close(self.current_figure)
- W75 excel 无 try/finally → try/finally 包裹 wb.close()
- W80 word 图片溢出 A4 → min(width, 6.0) 等比缩放
- W71 8D PDF 未转义 → html escape
- W107 AnalyzeWorker 无 try/except → try/except + error dict

### 契约一致性（4 项）
- W59-W62 current_result 三件套统一 → smed/time_study 标准化
- W43 compliance load_template → try/except + fallback
- W109 root_cause KeyError → .get() 安全取值
- W111 llm closeEvent 阻塞 → 非阻塞等待

### 测试质量（4 项）
- W101 or True 恒真 → 删除
- W102 零断言 → 添加 assert
- W105 time.time 全局替换 → mock.patch
- W84 work_sampling z_value 硬编码 → scipy.stats.norm.ppf

### 已确认无需修改（7 项）
- W70 vsm 除零（已有守卫）、W83 tpm clamp（已有 clamp）、W95 sheet_splitter 截断（已有哈希后缀）、W96 kpi_formula 嵌套幂（已有深度限制）、W91 non_normal_cap skew（已处理）、W103 mtime flaky（无实际问题）、W104 import 期写文件（无实际问题）

---

## v2.6.5 ✅ 已完成 — 编号缺陷清零 + Info 一期

> 主题：W 系列编号缺陷全部清零（10 项）+ 技术债第一批。本版本不引入任何新功能，为后续深化版本建立干净基线。
> 测试: 450+ pytest 全部通过 | 修复: 10项W系列 + 6项Info | 2026-08-23

### W 系列清零（10 项，每项附回归测试）

| 编号 | 来源 | 问题摘要 | 处置 |
|------|------|----------|------|
| W49 | v2.6.4 降级 | 全量填充阻塞 | 修复（分块/异步处理） |
| W50 | v2.6.4 降级 | Grubbs 标签错误 | 修复 |
| W51 | v2.6.4 降级 | 均匀分布 μ 计算错误 | 修复 |
| W69 | v2.6.4 降级 | trend 分析无抽样（大数据卡顿） | 修复（自动抽样） |
| W72 | v2.6.4 降级 | sidebar 高度问题 | 修复 |
| W73 | v2.6.4 降级 | fishbone 迭代问题 | 修复 |
| W74 | v2.6.4 降级 | animate 动画清理缺失 | 修复 |
| W99 | v2.6.4 降级 | esp32 transport buf（与 C04 重复） | 复核后关闭并记录 |
| W86 | 未分配 | `utils/co401_analysis.py:5` / `co401_round2.py:5` 硬编码 `sys.path.insert(0, r"D:\...")` | 修复（移除硬编码路径；一次性脚本移出 `utils/`） |
| W106 | 未分配 | `ui/dialogs/import_dialog.py:155` `xl.parse(s, nrows=0)` 恒返回 0 行 | 修复（列名读取逻辑） |

### Info 清零一期（~50 项）
- 死代码清理 + 未使用 import（工具辅助扫描 + 人工复核）

### 验收标准
- W 系列未决项 = 0 ✅（W99 复核关闭记录在案）
- 新增回归测试 ≥ 10 ✅（27个W修复回归测试）
- 全量 pytest 通过且不低于 289 基线 ✅（450+ tests）

---

## v2.7.0 ✅ 已完成 — 统计引擎深化

> 主题：对标 Minitab 补齐统计方法缺口 — 强化"质量分析软件"的本体价值。缺口清单来自 2026-08 代码级审计（非臆测）。
> **质量铁律：每个新方法以 NIST StRD / AIAG 手册 / 权威文献已知值数据集做单元测试验证。**
> 状态（2026-08-23）：P1（7 项引擎）+ P2（6 项引擎与 UI 集成）+ 代码质量审查（9 项修复）完成 · 122 个新增测试 · 537+ tests
> 遗留：P1 中 5 项 UI 入口待接入（Type 1 / Hotelling T² / TOST / χ²·2比例 / 分布拟合；Cpm 与 Johnson 已随既有入口生效）→ 登记为 v2.8.0 前置收尾任务；Info 二期顺延

### 现状基线（已具备，不重复建设）
9 类控制图 + Nelson 8 规则 · Cp/Cpk/Pp/Ppk + Box-Cox + 组内组间能力 · Gage R&R（交叉/嵌套）+ 线性/偏倚 + 属性一致性 Kappa · t 检验/单双因素 ANOVA/正态性/方差齐性/非参数 3 种 · 全因子 + CCD + Box-Behnken · 线性/多元回归 · Weibull 2P/3P + MTBF + ALT（Arrhenius/IPL）· AQL 计数抽样（GB/T 2828.1）

### P1 核心缺口（7 项）— ✅ 引擎全部完成

| 领域 | 新增方法 | 实现位置（规划） |
|------|----------|------------------|
| MSA | **Type 1 量具研究**（Cg/Cgk，单量具×标准件） | `analysis/msa/type1_study.py` |
| 能力 | **真 Johnson 变换**（SU/SB 选型；现实现仅为 z-score 标准化，非真变换） | `analysis/capability/non_normal_cap.py` 重构 |
| 能力 | **Cpm**（田口能力指数；现仅在 time_study 内有零散计算，未进能力引擎） | `analysis/capability/normal_cap.py` |
| SPC | **Hotelling T² 多元控制图**（多特性联合监控，T² + Q 残差图） | `analysis/spc/hotelling.py` |
| 假设检验 | **等价检验 TOST**（1/2 样本均值等价） | `analysis/hypothesis/equivalence.py` |
| 假设检验 | **卡方拟合/独立性检验 + 2 比例检验** | `analysis/hypothesis/proportion.py` |
| 分布拟合 | **通用分布拟合**（正态/对数正态/指数/Gamma/Weibull MLE）+ AD/KS/卡方拟合优度 | 新 `analysis/distribution/fitting.py` |

> UI 接入状态：Cpm（目标值输入后随能力结果自动展示）✅ · Johnson（能力 Tab 既有方法选项）✅ · Type 1 / Hotelling T² / TOST / χ²·2比例 / 分布拟合 → 待接入（v2.8.0 前置收尾）

### P2 重要缺口（6 项，本版本尽量做，可溢出至 v2.9.0）

| 领域 | 新增方法 | 状态 |
|------|----------|------|
| SPC | Laney P'/U' 控制图（计数数据过度离散/欠离散场景） | ✅ 完成 |
| 能力 | 非正态百分位法能力指数（不依赖变换） | ✅ 完成 |
| 统计 | 公差区间（正态/非参数） | ✅ 完成 |
| 假设检验 | Mood 中位数检验 + Friedman 检验（完全区组） | ✅ 完成 |
| 抽样 | 计量型抽样（GB/T 6378 / ANSI/ASQ Z1.9） | ✅ 完成 |
| 抽样 | C=0 抽样方案（零缺陷接收） | ✅ 完成 |

### P3 溢出项（v2.9.0 收尾）
- I-MR-R/BW 组内组间控制图 · 部分因子/田口直交表设计 · Logistic 回归 · 回归残差诊断四图 · DOE 主效应/交互/等高线图接线（contour 生成器已存在但未接 DOE Tab）

### Info 清零二期（~50 项）— 顺延至 v2.8.0 周期
- 重复实现合并 + 单一数据源统一（如 variance_tests/normality 重复、audit 双实现）

### 验收标准
- 新方法 NIST 已知值验证测试全部通过 ✅
- 新方法 UI 接入对应现有 Tab（MSA/能力/SPC/假设检验/抽样/图表入口扩展，**不新增 Tab**）— P2 全部接入 ✅；P1 余 5 项入口顺延至 v2.8.0 前置收尾
- 全量 pytest 通过 ✅（537+ tests）

---

## v2.8.0 — 工作流贯通 ✅ 已完成（2026-08-25）

> 主题：打通 FMEA→控制计划→SPC→PPAP→8D 数据链 — 开源界无人实现的差异化壁垒。
> 完成内容：共享数据模型 + 五链贯通 + 魔法数字常量化 + 51 个回归测试。

### 前置收尾（v2.7.0 遗留）✅
- **P1 UI 入口接入（5 项）**：MSA Tab 增加 Type 1 量具研究入口 · SPC Tab 增加 Hotelling T² 入口 · 假设检验 Tab 增加 TOST 与 χ²·2比例检验入口 · 分布拟合入口（图表/能力 Tab 扩展）
- Info 清零二期：魔法数字常量化（RPN/Cpk/MSA/OEE 阈值统一）

### 共享数据模型（地基）✅
- 新建 `core/project_context.py`：`QualityCharacteristic` 数据类（特征 ID / 工序 / 规格限 / 单位 / 数据源绑定）+ `ProjectContext` 项目级上下文
- 替代 `MainWindow.analyses` 按 Tab 索引的扁平字典（保留兼容层渐进迁移）
- .qap 序列化扩展：FMEA / 控制计划 / 8D 工程数据纳入持久化

### 五链贯通 ✅

| # | 链路 | 实现 | 状态 |
|---|------|------|------|
| 1 | FMEA → 控制计划 | 高风险项（AP/RPN 阈值）一键生成 CP 行（特征/控制方法/反应计划） | ✅ |
| 2 | 控制计划 → SPC | CP 控制项生成 SPC 监控清单（特征 + 规格限 + 控制图类型预配置自动带入） | ✅ |
| 3 | 能力/MSA → PPAP | PPAP #8（MSA）/ #11（初始能力）自动拉取分析 Tab 最新结果，替代手输 | ✅ |
| 4 | FMEA → 8D D4 | 失效原因/机理注入鱼骨图骨架（替代硬编码 6M 默认值） | ✅ |
| 5 | 8D D7 → FMEA/CP | "标准已更新"驱动 FMEA/CP 复审提醒与修订标记 | ✅ |

### Info 清零三期
- 魔法数字常量化 ✅（RPN_CRITICAL=200, RPN_HIGH=100, RPN_MEDIUM=50, SIGNIFICANCE_LEVEL=0.05）
- i18n 一致性 → 推迟到 v2.9.0

### 验收标准 ✅
- 端到端场景测试：导入数据 → FMEA 识别高风险 → 生成 CP → SPC 监控 → PPAP 自动填充，一条链无手输中断
- .qap 打开/保存完整还原工程数据（含 FMEA/CP/8D）；旧 .qap 向后兼容加载
- 51 个回归测试全部通过（test_project_context 20 + test_generate_cp_rows 12 + test_qap_roundtrip 6 + test_five_chain 13）

---

## v2.9.0 — 安全架构重构 + 离线许可系统（待开发）

> 主题：移除 RBAC 角色权限系统 → 实现离线许可验证 → 构建方式切换 Nuitka。
> 定位：为未来许可商业化做准备，同时首次提升反破解能力。

### 阶段 1: 删除 Auth 系统 ✅ 已完成

**删除文件**：
- `core/auth.py` (408行) — AuthManager、User、4级角色权限矩阵
- `core/password_policy.py` (23行) — 密码复杂度校验
- `ui/dialogs/login_dialog.py` (239行) — 登录对话框
- `ui/dialogs/user_management_dialog.py` (276行) — 用户管理对话框
- `tests/test_auth_hardening.py` — auth 加固测试
- `tests/test_rbac_ui.py` — RBAC UI 测试
- `tests/test_security_fixes.py` — 安全修复测试
- `TEMP/qa-tool-security-fix-backup/` — 备份目录

**简化文件**：
- `core/audit.py` — 移除 auth 审计事件，保留通用审计
- `ui/main_window.py` — 移除 28 处 `_check_permission` 调用 + 角色逻辑
- `ui/dialogs/settings_dialog.py` — 移除账户标签页
- `ui/sidebar.py` — 移除 `set_permission_filter`
- `ui/welcome_page.py` — 移除 `set_permission_filter`
- `main.py` — 移除 AuthManager + LoginDialog，简化启动

**实际**：15 个文件，删除/简化 ~800 行（main_window.py -192行，settings_dialog.py -135行，main.py -13行，测试文件 -100行，5个文件全删 -1200行）

### 阶段 2: 离线许可系统（标准版安全方案） ✅ 已完成

**安全层级**：

| 层级 | 技术 | 作用 |
|------|------|------|
| L1 | Ed25519 非对称签名 | License 不可伪造（无私钥） |
| L2 | 硬件指纹绑定 | License 绑定特定机器（CPU+主板+磁盘+MAC） |
| L3 | AES-256-GCM 加密 | License 内容加密存储 |
| L4 | 运行时完整性校验 | 多点 SHA-256 校验防篡改 |
| L5 | 反调试检查 | 50+ 处分散检测（sys.gettrace/进程扫描/时序分析） |
| L6 | VM/模拟器检测 | 防止分析环境 |

**新建文件**：
- `core/license.py` — 主模块：硬件ID采集 + Ed25519验证 + 完整性校验
- `core/license_keys.py` — 内置公钥（Ed25519 Raw, 32 bytes）
- `core/anti_debug.py` — 分散式反调试（67 个检查点）
- `core/integrity.py` — 运行时完整性校验
- `tools/license_generator.py` — 离线签发工具（开发者用，含私钥）
- `ui/dialogs/license_dialog.py` — 激活对话框
- `tests/test_license.py` — license 单元测试

**实际**：7 个新建，+900 行

### 阶段 3: 构建方式切换 Nuitka

**Nuitka 编译**：
- Python → C → 原生机器码（不可逆向还原）
- 替代 PyInstaller（.pyc 可秒级反编译）
- 输出 10-50MB exe，启动速度提升 10-20%

**新建/修改文件**：
- `build_nuitka.py` — Nuitka 构建脚本（支持 --onefile / --standalone）
- `requirements.txt` — 添加 nuitka>=4.0

**构建命令**：
```bash
# 安装依赖
pip install nuitka ziglang

# 独立目录模式（推荐调试）
python build_nuitka.py --standalone

# 单文件模式（发布用）
python build_nuitka.py --onefile
```

**实际**：1 个新建，+150 行

### 验收标准
- 全量 pytest 通过
- Nuitka 构建成功，无 .pyc 文件泄漏
- License 签发 → 激活 → 验证 全流程通过 ✅
- 硬件指纹绑定验证：换机需重新激活 ✅
- 反调试检查分散验证（50+ 处） ✅

---

## v3.0.0 — 稳定化里程碑（已完成）

> 主题：Info 收尾 + 全量回归 + 性能基线 + 里程碑发布。
> 定位：v3.0.0 是"深化时代"的收官 — 本版本建立的性能基线自此成为后续所有版本（v3.1.0+）的回归门禁。

### 内容
- Info 系列清零收尾——无 TODO/FIXME/HACK 注释
- 性能基线已建立并记录在案（测试文件→ test_performance.py）
- 双语文档已同步，版本历史已更新至 v3.0.0
- Inno Setup 安装器版本已更新至 v3.0.0

### 验收标准
- C / W / Info 编号项全部清零
- 全量回归通过，测试数不低于 537 基线（只增不减）
- 性能基线达标并记录在案

---

## v3.1.0 ✅ 已完成 — DOE 与功效分析

> 主题：补齐实验设计全链路，对标 Minitab DOE 模块。
> 定位：v3.x 持续小版本序列第一弹，聚焦单一统计领域深度补齐。
> 完成日期：2026-08-28

### 核心内容（全部完成）
- **筛选设计**：Plackett-Burman 设计 ✅ · Definitive Screening 设计 ✅
- **全因子/部分因子**：2 水平全因子 ✅ · 2 水平部分因子（1/2, 1/4, 1/8）✅ · 中心点 ✅ · 区组化 ✅
- **田口设计**：Taguchi L4/L8/L9/L16/L18 ✅ · 望大/望小/望目特性 ✅ · SN 比计算 ✅
- **响应面设计**：中心复合设计(CCD) ✅ · Box-Behnken 设计 ✅ · 混合设计（Simplex Centroid/Lattice/Extreme Vertices）✅
- **功效与样本量**：t 检验/比例/方差/ANOVA 的 Power 分析 ✅ · 样本量计算器 ✅ · OC 曲线 ✅
- **DOE 向导 UI**：DOE Tab 扩展（10 种设计类型入口）+ Power & Sample Size 独立对话框 ✅

### 文件变更
- 新建 `analysis/doe/power_analysis.py` — Power & Sample Size 引擎（~350 行）
- 新建 `ui/dialogs/power_dialog.py` — Power 分析对话框（~250 行）
- 修改 `ui/tabs/doe_tab.py` — 集成新设计类型和 Power 入口
- 新建 `tests/test_power_analysis.py` — Power 单元测试（~200 行）
- 新建 `tests/test_doe_e2e.py` — DOE E2E 测试（~150 行）

### 验收标准
- Plackett-Burman / CCD / Box-Behnken / 部分因子 / 田口 / 混合设计生成正确性验证 ✅
- Power & Sample Size 计算与 Minitab 交叉验证 ✅
- DOE 全流程 E2E 测试：设计生成→数据录入→分析→响应曲面可视化 ✅
- 7 种检验类型的 Power 分析和样本量计算器 ✅
- OC 曲线可视化 ✅

---

## v3.2.0 ✅ 已完成 — Linux 移植 + 双系统发行

> 主题：跨平台移植 — 支持 Linux（Debian/Ubuntu 系），实现 Windows/Linux 双系统发行。
> 目标发行版：Debian 13 / elementary OS 8.1 / Ubuntu 22.04+
> 预计工期：8 天（1-2 周）
> 变更：v3.2.0 起取消许可证系统，仅保留代码本体加密防破译

### 核心问题分析

| 优先级 | 问题 | 影响 | 解决方案 |
|--------|------|------|----------|
| **P0** | `core/secret_store.py` DPAPI 加密 | Linux 凭证存储完全失效 | 替换为 keyring + cryptography |
| **P0** | `output/pdf_report.py` 硬编码 `C:/Windows/Fonts` | PDF 中文显示空白 | 添加 Linux 字体搜索路径 |
| **P1** | 100+ 处硬编码 `Microsoft YaHei` | UI 字体渲染异常 | 创建平台感知字体解析模块 |
| **P1** | `core/anti_debug.py:434` 引用 `WindowsError` | Linux 启动崩溃 | 替换为 `OSError` |
| **P2** | `build_nuitka.py` Windows 专属参数 | 构建脚本失败 | 添加平台检测 |
| **P2** | 无 Linux 打包方案 | 无法分发 | AppImage |

### 文件变更清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `ui/font_config.py` | **新建** | 平台感知 CJK 字体解析 |
| `core/secret_store.py` | 重写 | DPAPI → keyring + cryptography |
| `ui/theme.py` | 小改 | 使用 font_config |
| `main.py` | 小改 | 启动字体检测 |
| `output/pdf_report.py` | 小改 | Linux 字体路径 |
| `output/excel_report.py` | 小改 | 字体名称 |
| `output/word_report.py` | 小改 | 字体名称 |
| `output/html_export.py` | 小改 | 字体名称 |
| `core/report_templates.py` | 小改 | 字体名称 |
| `core/anti_debug.py` | 小改 | WindowsError → OSError |
| `build_nuitka.py` | 小改 | 平台检测 |
| `core/license.py` | 简化 | v3.2.0 起取消许可证 |

### 字体策略（平台感知）

```python
# ui/font_config.py — 核心逻辑
def get_cjk_font() -> str:
    """检测并返回最佳 CJK 字体"""
    if sys.platform == 'linux':
        # Linux: 检测 Noto Sans CJK SC / WenQuanYi
        return _detect_linux_font()
    elif sys.platform == 'darwin':
        return "PingFang SC"
    return "Microsoft YaHei"  # Windows
```

### 凭证存储（跨平台）

```python
# core/secret_store.py — Linux 替代方案
if sys.platform == 'win32':
    # 保留 DPAPI（Windows）
    from ._dpapi import encrypt_secret, decrypt_secret
else:
    # Linux/macOS: keyring + cryptography
    from cryptography.fernet import Fernet
    import keyring
    # ... 实现
```

### Linux 系统依赖

```bash
# PySide6 运行时依赖
sudo apt install libegl1 libgl1

# ESP32 串口访问
sudo usermod -aG dialout $USER

# 可选：CJK 字体
sudo apt install fonts-noto-cjk
```

### 打包方案：AppImage

- 单文件分发，无依赖
- 覆盖 Debian/Ubuntu 全系列
- 构建脚本：`build_linux.sh`

### 执行计划

| 阶段 | 时间 | 内容 | 交付物 |
|------|------|------|--------|
| **Phase 1** | Day 1-2 | 核心基础设施：字体解析模块 + 凭证存储 + 反调试修复 | font_config.py, secret_store.py, anti_debug.py |
| **Phase 2** | Day 3-4 | 输出系统：PDF/Excel/Word/HTML 字体 + matplotlib 清理 | 5 个输出模块 + 12 个文件清理 |
| **Phase 3** | Day 5-6 | UI 系统：核心 UI + 20 Tab + 10 对话框 | 30+ 文件字体更新 |
| **Phase 4** | Day 7-8 | 构建打包：Nuitka 适配 + AppImage + 许可证移除 + 测试 | build_linux.sh, qa-tool.desktop, 文档 |

### 测试策略

- 每阶段完成后运行全量 pytest 回归（688+ tests）
- Phase 4 完成后进行 Ubuntu/Debian 双平台集成测试

### 验收标准

- Ubuntu 22.04+ / Debian 13 应用正常启动
- 中文 UI 正常显示，无方块
- PDF/Excel/Word/HTML 中文导出正常
- ESP32 串口通信 Linux 下正常
- AppImage 单文件分发可用
- 全量 pytest 通过（688+ tests）

---

## v3.3.0 ✅ 已完成 — 时间序列与预测

> 主题：补齐全时间序列分析能力，支持趋势预测与季节性分解。

### 核心内容
- **ARIMA 建模**：自动 p/d/q 选择（AIC/BIC 最优）· 手动参数设置 · 残差诊断（ACF/PACF/Q-Q）
- **指数平滑**：单参数平滑 · 双参数平滑（Holt 线性趋势）· Holt-Winters（加法/乘法季节性）
- **ACF/PACF 图**：自相关/偏自相关可视化 · Ljung-Box 检验 · Durbin-Watson 统计量
- **季节性分解**：加法/乘法模型 · 趋势+季节+残差 分解图
- **预测 UI**：预测步数选择 · 置信区间可视化 · 多模型对比（AIC/BIC 排名）

### 验收标准
- ARIMA 自动选阶与 statsmodels 交叉验证
- Holt-Winters 预测结果与 Minitab 对比
- 时间序列全流程 E2E 测试：数据导入→ACF/PACF→建模→预测→可视化

---

## v3.4.0 ✅ 已完成 — 可靠性与生存分析

> 主题：补齐可靠性工程全链路，对标 Minitab Reliability 模块。

### 核心内容
- **Weibull 分析增强**：Weibull 3P/4P（MLE 估计）· 置信区间 · 拟合优度检验 · 概率图
- **生存分析**：Kaplan-Meier 生存曲线 · Log-rank 检验 · Cox 比例风险回归
- **加速寿命试验(ALT)**：Arrhenius / Power Law / Inverse Power Law · ALT 试验计划 · 寿命预测
- **保修分析**：首次失效预测 · 保修成本估算 · 寿命数据回归
- **可靠性框图(RBD)**：串联系统 · 并联系统 · 混合系统 · 系统可靠度计算
- **MTBF/MTTF**：置信区间估计 · 增长曲线（Crow-AMSAA）

### 验收标准
- Weibull 3P/4P MLE 估计与 Minitab 交叉验证
- Kaplan-Meier 曲线与 statsmodels 对比
- ALT 寿命预测与权威文献已知值验证

---

## v3.5.0 — MSA 与能力深化（待开发）

> 主题：深化测量系统分析与过程能力，补齐 Minitab 级高级功能。

### 核心内容
- **非参数能力分析**：不假设分布的能力评估（Edgeworth 近似 / 数据转换）
- **自动能力分析**：自动检测最佳拟合分布 → 选择最优变换 → 输出能力指标
- **Capability Sixpack**：六合图（控制图+能力直方图+概率图+统计量+不合格品率+能力图）
- **属性一致性分析**：Kappa 系数（Cohen's / Fleiss's）· 有效 Kappa · 偏差矩阵
- **EMP 方法量具研究**：Wheeler's EMP Crossed · 判异准则 · 分辨力分级
- **Gage R&R 增强**：方差分量图 · 型号×操作员交互效应图 · 不确定度预算

### 验收标准
- 非参数能力与 Minitab Nonparametric Capability 对比
- Capability Sixpack 六图联动正确性
- EMP 方法与 Wheeler 文献已知值验证

---

## v3.6.0 — Graph Builder 增强与交互体验（待开发）

> 主题：将现有图表工具升级为 Minitab Graph Builder 级交互体验。

### 核心内容
- **交互式图库**：缩略图预览面板（替代纯下拉框）· 按类别分组（基础统计/回归/DOE/时间序列/可靠性）
- **图表编辑增强**：参考线/目标线可拖拽 · 数据标签显示 · 图例自定义 · 坐标轴格式化
- **热力图与相关图**：相关系数矩阵热力图 · 散点矩阵图 · 相关系数显著性标记
- **表格构建器**：拖拽式描述统计表 · 交互式交叉表 · 分组统计摘要
- **一键导出**：Excel (.xlsx) · PowerPoint (.pptx) · Word (.docx) · 高分辨率 PNG/SVG
- **小多图(Faceting)**：分组变量 → 多图网格布局 · 行/列/封面 faceting

### 验收标准
- 图库面板加载时间 < 200ms
- 导出文件格式兼容性验证（Excel/PPT/Word 正常打开）
- 交互式编辑操作响应延迟 < 100ms

---

## v3.7.0 — 实时 SPC 云看板与数据连接器（待开发）

> 主题：将 ESP32/MaixCAM 设备框架升级为 Minitab Real-Time SPC 级实时监控能力。

### 核心内容
- **持续数据流**：ESP32/MaixCAM 设备持续采集 → 实时入数据库（SQLite/PostgreSQL）
- **Web 实时仪表板**：基于 FastAPI + WebSocket 的实时控制图 · 班次/产线/工位多维视图
- **OOC/OOS 告警**：控制限/规格限越界即时通知（邮件/webhook/桌面弹窗）· Nelson 规则实时检测
- **数据连接器框架（协议优先+插件化）**：OPC-UA 客户端（覆盖 95% 工厂 PLC）· Modbus TCP/RTU · MQTT 订阅（ESP32/Arduino Opta/Raspberry Pi 统一接入）· CMM DMIS · 量具 RS232/USB · 驱动插件架构（每种硬件一个插件，按需安装）
- **设备抽象层**：`DeviceDriver` 接口统一抽象 · 底层协议可替换 · 不绑定特定硬件
- **硬件推荐文档**：Arduino Opta WiFi（$185，工业级 CE/UL/DIN-rail，原生 MQTT/Modbus）或 ESP32（$10-20，原型验证）
- **产线可视化**：产线拓扑图 · 工位状态灯（绿/黄/红）· 实时 OEE 看板

### 验收标准
- 数据流延迟 < 500ms（设备→控制图）
- WebSocket 并发 50 连接无性能退化
- PLC/量具连接器 Mock 测试通过

---

## v3.8.0 — QAM Harness（BYOK AI Agent 平台）（待开发）

> 主题：打造工程分析专业化 AI Agent 平台，用户自带 API Key，主动建议型分析。

### 核心内容
- **BYOK 架构**：用户在设置面板配置自有 API Key（OpenAI / Anthropic / Google / DeepSeek / Z.ai / KIMI）· Key 加密存储（跨平台密钥库）· 连通性测试
- **主动建议型 Agent**：数据画像 → 自动推荐分析方法（如检测到偏态建议 Box-Cox）· 分析结果自动工程解读（结论/原因假设/建议动作）· 异常根因智能推荐
- **知识库 RAG**：内置质量工程知识库（IE/质量工程/精益生产方法论）· 用户可扩展 · TF-IDF 检索（后续升级向量检索）
- **多轮对话**：对话式分析引导 · 追问/澄清/深入 · 上下文保持（同一分析会话）
- **数据隐私**：首次 cloud API 调用隐私弹窗（明确告知数据发送至供应商）· 用户确认后持久化
- **统计结果人话解释**：P 值/Cp/Cpk 等指标自动口语化解读 · 非统计人员可读

### 验收标准
- 6 家供应商 API Key 配置 + 连通性测试全流程
- 主动建议准确率人工评审（工程师评分 ≥ 3.5/5）
- 数据隐私弹窗拦截率 100%

---

## v3.9.0 — 视频时间研究（待开发）

> 主题：引入基于视觉的动作分析与时间研究，独立 Tab 36。

### 核心内容
- **摄像头输入层**：USB/IP 摄像头统一抽象（OpenCV）· RTSP/HTTP/MJPEG 流支持 · 分辨率选择 · 实时预览
- **姿态估计**：MediaPipe Pose（33 关键点）· 帧级推理 · 置信度阈值可调
- **动作分类**：基于关键点角度/位移的 4 类判定（工作/空闲/走动/搬运）· 规则可配置
- **周期检测**：基于动作状态切换自动分割周期 · 周期时间实时计算 · 异常周期标记
- **分析引擎**：复用 `analysis/ie/time_study.py` · 周期时间异常值剔除 · 正态拟合 · 标准工时计算
- **Tab 36 上线**：摄像头选择/预览/标定/采集/分析/导出全流程 · UI 引导

### 验收标准
- 摄像头预览帧率 ≥ 15 FPS
- 手动标记延迟 < 100ms
- 视频分析全流程 E2E 测试通过

---

## v4.0.0 — 预测分析与机器学习（待开发）

> 主题：补齐 Minitab Predictive Analytics 级机器学习能力。

### 核心内容
- **CART 分类回归树**：树构建 · 剪枝（预剪枝/后剪枝）· 混淆矩阵 · ROC 曲线
- **Random Forests 随机森林**：Bagging + 特征随机 ·OOB 误差估计 · 特征重要性排序
- **Gradient Boosting (XGBoost)**：提升迭代 · 学习率/深度调参 · SHAP 特征解释
- **MARS 多元自适应回归**：分段线性回归 · 基函数选择 · 交互项检测
- **AutoML 模型选择**：自动尝试多种算法 · AIC/BIC/AUC 排名 · 最优模型推荐
- **特征工程**：缺失值填充 · 分箱 · 编码 · 特征交叉 · 标准化/归一化
- **模型评估**：交叉验证 · 学习曲线 · 过拟合诊断 · 残差分析

### 验收标准
- CART/Random Forests 与 scikit-learn 交叉验证
- AutoML 自动选模与人工选模对比一致性
- 预测分析全流程 E2E 测试：数据准备→特征工程→建模→评估→可视化

---

## v4.0.0 — 待定

> 主题：根据 v3.x 实际进展和市场反馈再定义。
> 方向候选：视频时间研究深化 · 数字孪生布局仿真 · 供应链质量协作 · 更多硬件集成

## 版本历史

| 日期 | 版本 | 内容 |
|------|---------|---------|
| 09-04 | v3.4.0 | 可靠性与生存分析完成：Weibull 2P/3P/4P + CI + KM + Cox + ALT + RBD + Crow-AMSAA + 保修分析 + 72个可靠性测试 |
| 09-01 | v3.3.0 | 时间序列与预测完成：ARIMA自动选阶 + 指数平滑 + 季节分解 + 预测 + E2E测试 |
| 09-01 | v3.2.0 | Linux移植完成：跨平台字体系统 + keyring凭证存储 + AppImage打包 + 双系统发行 |
| 08-28 | v3.1.0 | DOE与功效分析完成：筛选设计(PB/DSD) + 部分因子 + 田口 + 混合设计 + Power & Sample Size引擎 + 独立对话框 + E2E测试 |
| 08-28 | v3.2.0-planning | Linux移植规划：跨平台字体系统 + keyring凭证存储 + AppImage打包 + 双系统发行 |
| 08-24 | v3.x-planning | 战略重定位：从企业级多公司平台调整为个人订阅级质量工程工具（类 Minitab）；删除 v3.1~v3.6 旧规划（企业RBAC/跨平台/高可用/安全合规/双层治理）；重新设计 v3.1~v4.0 路线（DOE→时间序列→可靠性→MSA→Graph Builder→实时SPC→QAM Harness→视频研究→预测分析）；核心竞争力支柱从6个精简为5个（工作流贯通/实时工厂集成/IE工具套件/QAM Harness/中文本土化） |
| 08-24 | v3.x-AI-架构 | AI 架构决策：支柱 4 从"本地 LLM"调整为"AI 智能助手（云端 API + 本地模型分层）"；v3.1.0 新增 AI API 管理面板（6 家供应商 GUI 配置 + 数据隐私提示）；v3.2.0 服务端增加 AI 代理转发；v4.0.0 本地 LLM 定位为企业版专属功能 |
| 08-24 | v3.x-视频研究 | 视频时间研究方案确定：独立 Tab 36 · 标准 USB/IP 摄像头 + PC 端 OpenCV/MediaPipe 路线 · 穿插 v3.1~v3.5 三阶段交付（v3.1 摄像头输入层 + v3.3 姿态估计 + v3.5 完整分析上线）· MaixCAM 分阶段定位（当前 IoT 采集终端 → v4.0 条件触发升级视觉检测平台） |
| 08-23 | v2.7.0 | 已完成：P1期（7项核心功能+4项性能优化）+ P2期（6项功能）+ 代码质量审查（9项修复）+ UI集成（4个Tab：SPC/能力/假设检验/抽样） · 537+ tests |
| 08-23 | v2.6.5 | 已完成：W系列编号缺陷清零（W49/W50/W51/W69/W72/W73/W74/W86/W99/W106）+ Info一期（死代码/未使用import/状态漂移bug修复）· 450+ tests |
| 08-22 | v2.6.5-planning | 规划重构：v2.6.5~v3.0.0 从"功能扩张"转向"现有功能深化"（缺陷清零 → 统计引擎深化 → 工作流贯通 → 深化整合 → 稳定化）；旧功能项 P2-3/P2-4/P2-5/P3-1~P3-5 搁置至 3.0.0 后；基于开源竞品调研确立核心竞争力定位 |
| 08-21 | v2.6.2 | 已完成：RBAC 权限矩阵（守卫/菜单置灰/侧边栏/欢迎页过滤）+ 认证加固（登录锁定 + 强制改密）+ 安全修复 W01-W17 + 设备链路 C04/C05/C06/C19/W87-W100 + esp32_out 实机验证（COM3，LED/继电器/舵机 ACK）+ MaixCAM 网络接入（TCP :9000 全链路）· 296 tests |
| 08-19 | v2.6.1-review | 代码审查修复（12 Critical）：认证越权 C01/C02/C03/C13/C14 + nav_buttons C08 + 功能失效/崩溃 C07/C09/C10/C11/C12/C17 + 合成测试数据 C18 · 289 pytest · 44/45 冒烟 |
| 08-19 | v2.6.1 | 安全校验：密码策略（≥8 位+字母数字，auth 三处接线）+ 审计日志（core/audit.py 公共入口 + 9 类业务事件）+ 密钥库（DPAPI 加密存储 + SQL 连接串脱敏）· 282 tests |
| 08-18 | v2.6.0 | 已发布：ESP32-IN 部署拓展（固件 v1.1.0 实机验证）+ 设备监控 Tab 35（停止/继续监控、20 行预览、数据导入）+ ESP-32 配置门控 + PyInstaller onedir + Inno Setup 安装器 · 278 tests |
| 08-18 | v2.5-dev | H2 固件 v1.1.0 实机运行（MicroPython v1.20 + UART1 重映射, 7 通道）· H3 esp32_in 在 COM3 端到端验证（发现→META→DATA→导入）· 主机发现/监控支持复位脉冲 · 270+ tests |
| 08-17 | v2.5-dev | 硬件扩展：ESP32 设备框架恢复（core/devices + DeviceTab 35 + 21 测试）· QMenu GC 崩溃修复复检 · 内存泄漏审计（线程干净）· 264 tests |
| 08-15 | v2.4.1 | 已发布：自适应看板卡片 + 动画（fade/count-up/cross-fade）+ 显示模式宽高比与可读性修复 · 215 tests |
| 08-13 | v2.4 | 已发布：看板 E4 完成 — KPI 提取器 / 实时刷新 / 卡片布局 / 公式编辑器 / 车间看板 · 136 tests |
| 08-13 | v2.3.1 | 已发布：UI 文字显示修复 — 表头 / 状态栏省略 / 欢迎卡片 / 菜单 i18n |
| 08-13 | v2.4-dev | 看板阶段 1 完成（KPI 提取器 + 实时刷新 + 卡片布局）· 阶段 2 完成（公式编辑器 + 显示模式） |
| 08-12 | v2.3 | 已发布：报告模板引擎 + 对话框 + HTML 导出 + 菜单重构 |
| 08-10 | v2.3-dev | 阶段 B：报告模板引擎 + 对话框 + HTML 自包含导出 |
| 08-10 | v2.3-dev | 阶段 A：8D 鱼骨图嵌入 + PPAP 实时刷新 + 引擎包导出 |
| 08-10 | v2.2 | 已发布：32 tabs · SMED/8D/TPM/PPAP · 87 tests · lint-clean |
| 08-10 | v2.2-dev | 审查修复：3 Critical + 7 Warning（TPM 属性 / 动画 / 图表 tab） |
| 08-10 | v2.1 | 已发布：87 tests · AI 增强 · 懒加载 · 一键分析 · 列选择器修复 |
| 08-10 | v2.1-dev | 代码审计：5 bugs · 200+ imports · 60+ 死代码 · 15 重复分组 |
| 08-04 | v2.0 | 初始发布：28 tabs · 65 tests · AI 助手 · 插件系统 |

---

## 侧边栏演进

> **注**：v2.6.5 ~ v3.0.0 重规划期**不新增 Tab**（聚焦现有功能深化），35 Tab + 插件结构保持不变。
> v3.0.0 后新增能力优先以现有 Tab 内的入口/模式呈现，确需新增 Tab 的由对应版本规划单独定义。

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)   v3.0.0 (35)      v3.8.0 (36)
 Home (0)       Same           Same             Same           Same             Same                Same
 Quality (1-6)  Same           Same             Same           Same             Same                Same
 IE (7-11,21-22) Same          +SMED(29)+TPM(31)  Same         Same             Same                Same
 Charts (12,18-20) Same        Same             Same           Same             Same                Same
 Eng (13-17)     Same         +8D(30)+PPAP(32)   Same           Same             Same                Same
 Worksheet (23-25) Same        Same             Same           Same             Same                Same
 Sampling (26)   Same          Same             Same           Same             Same                Same
 Report (27)     Same          Same             Same           Same             Same                Same
 Data (28)       Same          Same             Same           Same             Same                Same
 —               —             —                Live Monitor (33) Same             Same                Same
 —               —             —                Multi-Plant (34)   Same             Same                Same
 —               —             —                —                 Device (35)      Same                Same
 —               —             —                —                 —                Video Time Study (36)
 Plugins (dynamic) Same        Same             Same             Same             Same                Same
```
