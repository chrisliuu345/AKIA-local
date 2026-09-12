# QA-Tool 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v3.7.2 实时监控对标优化（8 项）（✅ 2026-09-10）| 进行中: **v3.8.0 P1/P2 ✅ + 插件接口 v2 ✅（视觉迁至独立项目，待发布）** | 测试: 1500+ pytest · 36 个分析 Tab | 更新: 2026-09-12

---

## 版本总览

> **战略重定位（2026-08-24）**：定位从企业级多公司平台调整为**个人订阅级质量工程工具**（类 Minitab），差异化核心为实时工厂数据集成 + IE 工程工具 + 五链工作流 + BYOK AI Agent（QAM Harness）。详见[核心竞争力定位](#核心竞争力定位2026-08-重规划)。

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ✅ ──→ v2.6.4 ✅ ──→ v2.6.5 ✅ ──→ v2.7.0 ✅ ──→ v2.8.0 ✅ ──→ v2.9.0 ✅ ──→ v3.0.0 ✅ ──→ v3.1.0 ✅ ──→ v3.2.0 ✅ ──→ v3.3.0 ✅ ──→ v3.4.0 ✅ ──→ v3.5.0 ✅ ──→ v3.6.0 ✅ ──→ v3.6.1 ✅(并入 3.6.0) ──→ v3.7.0 ✅ ──→ v3.7.1 ✅ ──→ v3.7.2 ✅ ──→ v3.8.0 ──→ v4.0.0
```

| 阶段 | 版本 | 主题 |
|------|---------|------|
| 已完成 | v2.0 ~ v3.1.0 | Release → 代码+AI → 工程工具 → 报告 → 实时监控 → UX+动画 → 硬件扩展 → ESP32 部署 → 安全校验 → RBAC+认证 → 统计引擎加固 → UI 健壮性 → 缺陷清零 → 统计引擎深化 → 工作流贯通 → 安全架构重构 → 稳定化里程碑 → DOE与功效分析 |
| 已完成 | v3.2.0 | **Linux 移植 + 双系统发行**（Debian/Ubuntu） |
| 已完成 | v3.3.0 | **时间序列与预测**（ARIMA / 指数平滑 / 季节分解 / 模型对比） |
| 已完成 | v3.4.0 | **可靠性与生存分析**（Weibull 2P/3P/4P + CI / KM + Cox / ALT / RBD / Crow-AMSAA / 保修） |
| 已完成 | v3.5.0 | **MSA 与能力深化**（属性一致性增强 / EMP 方法 / Gage R&R 增强 / Capability Sixpack / 自动能力分析 / Edgeworth 近似） |
| 已完成 ✅ | v3.6.0 | **Graph Builder 增强与交互体验**（图表编辑架构 / 饼图·帕累托实时交互 / 热力图·散点矩阵 / 小多图 Faceting / PPT·PNG·SVG 导出+缩略图图库 / 帮助中心+菜单重构 / 集成测试）— 2026-09-06 代码验收通过；构建链 2026-09-07 切 PyInstaller+Inno |
| 已完成 | v3.6.1 | **全量代码质量审查**（7 处潜在崩溃修复 / 缺陷隐患清理 / ruff 全库扫描 / 72 文件全量回归） |
| 已完成 ✅ | v3.7.0 | **实时 SPC 云看板与数据连接器**（实时数据流/Web 看板/连接器插件/告警中心 — 2026-09-08 开发完成）|
| 已完成 ✅ | v3.7.1 | **五链贯通修复 + 数据语义与工程一致性加固**（FMEA→CP→SPC 桥接修复 + ProjectContext 单一事实源 / 列类型值优先判定（测量值·时长列）+ 清洗后重算 / 打包隔离本机配置 + 敏感配置加密 / APP_VERSION 单一事实源 + CI 版本门禁 / 僵尸模块清理与分层归位）— 2026-09-10 |
| 已完成 ✅ | v3.7.2 | **实时监控对标优化 8 项**（实时图 USL/LSL + 缩放 / plant.json 可视化配置 / 告警分级·确认·审计·联动 / 成本损失核算 / OEE 节拍真实 P + 停机原因码 + 班次日历 / 分钟降采样与分档保留 / 连接器健康页与自动重连 / 看板可选鉴权）— 2026-09-10 |
| 开发中 ✅ | v3.8.0 | Industrial AI Agent（QAM Harness + BYOK；视觉能力移至独立插件项目）— 待发布 |
| 独立项目 | QA-Tool-Vision-expansion | 视频时间研究插件（动作识别/作业周期/标准工时），基于主应用插件接口 v2 |
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
> ⚙️ 2026-09-07 更新：构建链由 Nuitka 切换回 **PyInstaller (onedir)**（`build_pyinstaller.py`），Inno/AppImage/.deb 打包保留并复用 `build/<name>.dist` 产物；`build_nuitka.py` 与 nuitka 依赖已移除。
- 品牌资源：`assets/logo.ico`（7 尺寸）+ `version_info.txt`（Windows 版本资源，PyInstaller --version-file 复用）
- PyInstaller **onedir**：QA-Tool.exe（38MB）+ `_internal/`（454MB 总量），GUI 无控制台
- **Inno Setup 安装器**（135MB）：中文界面、管理员安装到 Program Files、组件页"ESP-32 硬件拓展"勾选框（决定安装期开关写入）、桌面/开始菜单快捷方式、卸载支持
- Linux：`build_appimage.sh` → AppImage；`build_deb.sh` → .deb（版本号从 APP_VERSION 动态注入）
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

## v3.5.0 ✅ 已完成 — MSA 与能力深化

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

## v3.6.0 ✅ 已完成 — Graph Builder 增强与交互体验（代码验收通过 2026-09-06 · 构建链切 PyInstaller+Inno 2026-09-07）

> 主题：将现有图表工具升级为 Minitab Graph Builder 级交互体验。
> 进度：P1 图表编辑架构 ✅ · P2 饼图/帕累托实时交互 ✅ · P3 热力图/散点矩阵 ✅ · P4 小多图(Faceting) ✅ · P5 一键导出+缩略图图库 ✅ · P6 集成测试+性能优化 ✅ · 质量审查+稳定性加固 ✅ · 帮助中心+菜单重构 ✅（2026-09-06 代码验收通过；发布打包另行执行）

### 核心内容
- **交互式图库**：缩略图预览面板（替代纯下拉框）· 按类别分组（基础统计/回归/DOE/时间序列/可靠性）✅
- **图表编辑增强**：参考线/目标线可拖拽 · 数据标签显示 · 图例自定义 · 坐标轴格式化（未实现，顺延后续版本候选）
- **热力图与相关图**：相关系数矩阵热力图 · 散点矩阵图 · 相关系数显著性标记 ✅
- **表格构建器**：拖拽式描述统计表 · 交互式交叉表 · 分组统计摘要（未实现，顺延后续版本候选）
- **一键导出**：Excel (.xlsx) ✅(原有) · PowerPoint (.pptx) ✅ · Word (.docx) ✅(原有) · 高分辨率 PNG/SVG ✅
- **小多图(Faceting)**：分组变量 → 多图网格布局 · 行/列/封面 faceting ✅
- **帮助中心（增补 2026-09-06）**：使用指南由 docx 迁移为离线 HTML（`config/help/guide.html`，浏览器打开，商业帮助页布局：固定侧栏导航 + FAQ 折叠 + 打印样式；过时内容按当前事实修订）✅ · **菜单栏整体重构**：去 emoji 前缀、AI/工具/帮助归位（报告模板→工具、HTML 导出→文件导出、模板说明→帮助、删重复知识库检索）、视图补显示模式 F11 入口、帮助新增使用指南(F1) ✅

### 稳定性修复（图形渲染链路，手动回归驱动）
- 实时调参重绘：canvas 换新（QtAgg 禁止跨 figure 复用 canvas）· 编辑面板行保持原位 · 隐藏工具条不再入布局/不再闪现 ✅
- 页面高度同步改为显式累加布局行最小高（绕开 Qt 对刚替换 canvas 的 minimumSizeHint 缓存失效 → 消除刷新后画布溢出乱码）✅
- SPC 显示网格/显示控制限开关真正生效（`show_limits` 曾完全未被引擎读取；UCL/LCL/EWMA/CUSUM 全类型支持）✅
- hypothesis/msa/doe 三 Tab 渲染入口补模块级 import（曾依赖函数内局部 import 巧合而静默 NameError）✅

### 验收标准
- 图库面板加载时间 < 200ms ✅（实测展开即时，无阻塞渲染）
- 导出文件格式兼容性验证（Excel/PPT/Word 正常打开）✅（python-pptx/docx/openpyxl 生成，PPTX 重开断言通过；人工双击抽查一次）
- 交互式编辑操作响应延迟 < 100ms ✅（小数据即时；8000 行大网格防抖合并后约 0.3–0.6s 单次重绘）
- 连续 5 次实时刷新滚动位置零漂移、画布像素完整 ✅（集成测试守护）

---

## v3.6.1 — 全量代码质量审查与静态缺陷修复（已完成 · 并入 v3.6.0 发布，不单独发版）

> 触发：吸取 v3.6.0 图形链路多轮回归教训，全量 ruff(F/E/B) + 语义审查 + 72 个测试文件单线程全量回归。

### 修复清单
- **潜在运行时崩溃（静默/条件触发）**
  - `analysis/doe/taguchi.py`：噪声因子双水平内表调用不存在的 `_build_plackett_burman`（NameError）→ 补 Sylvester-Hadamard 实现；三水平内表对 list 做 `[:, :n]` 元组切片（TypeError）→ 转 np.array。新增 TestNoiseFactors 3 用例 ✅
  - `core/report_templates.py`：`_BUILTIN_TEMPLATES` 是函数内局部却被类方法引用（NameError）→ 模块级全局化 ✅
  - `core/sampling_engine.py`：注解用 `Dict/Any` 未导入（3.14 延迟求值才未立即崩溃）→ 补 typing 导入 ✅
  - `core/anti_debug.py`：`else` 分支内层 `import subprocess` 使 Windows 路径 UnboundLocalError → 删除局部导入 ✅
  - `ui/tabs/tpm_tab.py`：`_display` 尾部局部 `import matplotlib.pyplot` 令函数头引用局部化（UnboundLocalError）→ 删除局部导入 ✅
  - `ui/tabs/msa_tab.py`：Type 1 校验引用未定义 `reference` → 校验处读取 ref_spin ✅
  - `ui/tabs/doe_tab.py`：Pareto 渲染用 run_analysis 局部导入的 `create_pareto_chart`（跨方法 NameError）→ 模块级导入 ✅
- **缺陷隐患**
  - 循环内 lambda 未绑定循环变量（`auto_cap.py`/`data_validator.py` kstest 回调）→ 默认参数绑定 ✅
  - `secret_store.py`/`sql_loader.py`：except 内 raise 补异常链 `from` ✅
  - 冗余赋值清理（mixture `p_model`、gage_rr `grr=ev`、factorial `df_factors`、johnson `kurt`、power `df1`、regression `actual`、chart_icons `base`、fishbone 两处、analysis_card `MplFigure` 导入）✅
- **工程卫生**
  - 171 处未用 import/f-string 自动清理；`analysis/ie` 与 `analysis/quality` 包根补 `__all__` 语义化导出 ✅
  - TEMP/ 临时脚本目录移出 git 跟踪并加入 .gitignore（含误入的乱码文件名垃圾文件）✅
  - 复查确认：无裸 except、无硬编码密钥、无遗留调试探针/FIXME、无可变默认参数缺陷 ✅
- **全量回归**：72 个 pytest 文件 + tests/test_integration.py 脚本断言全部通过（约 1300 用例，单线程逐文件执行防 PySide6 死锁）✅

### 遗留（风格债，不影响运行 — ✅ 已于 2026-09-07 全部清零，见下方【v3.7.0 前置】）
- F841 65 处 / E701·E702 568 处 / E402 20 处 / B 类 72 处 — 全部清理完毕
- ruff 已入 dev-requirements + ruff.toml + ci.yml 门禁（全库零告警）

---

## v3.7.0 — 实时 SPC 云看板与数据连接器（✅ 2026-09-08 开发完成）

### 【v3.7.0 前置】开发前必须先清零的遗留清单 ✅（2026-09-07 全部完成）
- [x] F841 未用赋值清理并复核（65 处：绘图中间量删绑定留调用 / anti_debug decoy 保留调用副作用）
- [x] E701/E702 单行多语句（568 处 / 23 文件）经 `ruff format` 批量规范化
- [x] E402 延迟模块级导入 20 处整改（可移顶移顶；main.py 导入链重构后无需 noqa）
- [x] ruff 引入开发流程：`ruff.toml`（F,E9,B,E701,E702,E402）+ dev-requirements + ci.yml 门禁，全库零告警
- [x] B 类清零：B007×38 / B905×31（29 处 strict=True + 2 处外部数据 strict=False）/ B028×2 / B008×1
- [x] 清理后全量回归通过（73 测试文件单线程 + tests/test_integration.py 脚本断言，零失败）

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

### 开发记录（2026-09-08, P1→P6）
- P1 ✅ 设备驱动抽象（DeviceDriver/Mock/MonitorAdapter）+ 数据流总线 + SQLite 时序层 + 采集编排（延迟<500ms 验收通过）
- P2 ✅ 实时 SPC：LiveSPC 滚动窗口引擎（I-MR/XBar-R, 增量 Nelson/OOC/OOS）+ spc_tab 实时监控模式（>500ms 检出验收通过）
- P3 ✅ 实时看板：FastAPI+WebSocket 独立服务（/api/devices /api/history /ws/stream, SQLite 优先+总线回退）+ 浏览器仪表板 + 菜单「工具→实时看板」（50 并发 WS 验收通过）
- P4 ✅ 数据连接器 SPI 插件化（按需安装）：Modbus TCP / MQTT / OPC-UA / CMM DMIS / RS232 量具（Mock 测试通过）
- P5 ✅ 产线拓扑（data/plant.json）+ 工位状态灯（绿/黄/红, 离线>5s）+ 实时 OEE（10min 滑动窗口）+ 告警中心（去抖/冷却 + 邮件/webhook/桌面，测试通过）
- P6 ✅ 版本 3.7.0 四端一致 + guide.html 实时看板章节 + 文档 + 全量回归

## v3.7.2 ✅ 已完成 — 实时监控对标优化（2026-09-10 开发完成）

> 本节源自 2026-09-08 竞品对标调研（9 项），原 v3.7.1 候选位被缺陷修复版占用后
> 顺延；本次落地 **1-8 项**（发布为 v3.7.2 小版本），第 9 项「多站点/多语言」
> 仍留待 v3.8.0 或后续版本。全部批次交付含回归用例，版本 3.7.2 四端一致。

> 对标来源（官方页面 2026-09-08 抓取）：
> [Minitab Real-Time SPC](https://www.minitab.com/en-us/products/real-time-spc/) ·
> [WinSPC(Advantive)](https://www.advantive.com/products/winspc/) ·
> [InfinityQS Enact](https://www.advantive.com/products/infinity-qs-enact/) ·
> [DataLyzer](https://datalyzer.com/)（Minitab 首选 URL 404，改用 /en-us/products/real-time-spc/ 成功）

### 功能对照（竞品 vs QA-Tool v3.7.0）

| 能力 | Minitab RTSPC | WinSPC | Enact | DataLyzer | QA-Tool 现状 |
|---|---|---|---|---|---|
| 实时控制图 | I-MR/Xbar-R/S/I-MR-R/S/EWMA/P·NP·Laney/C·U·Laney | 全套 | ✓ | ✓ | 实时仅 I-MR/XBar-R（批量分析已齐全） |
| 实时看板 | 云仪表板自动更新 | Plant monitor 单屏汇总 | 角色化仪表板 | 看板/报告 | 浏览器仪表板（WS 广播） |
| 数据接入 | 全链路 | RS232/USB/文件/CSV/Excel/ODBC/OPC/DDE/API 500+ 方法 | 机/设备/操作员实时 | 设备/CMM/DB/PLC 自动采集 | 插件 Modbus/MQTT/OPC-UA/DMIS/量具RS232 |
| 告警 | 邮件/短信定制 | 邮件/自定义程序/停机/双向指令 | 邮件/短信/应用内+自动工单 | 早期预警 | 邮件/webhook/桌面（去抖冷却），无确认/联动/短信 |
| 配置方式 | **Autoconfigure 电子表格**（站/工序/规格/流程图一次配置） | 三步连接向导 | 向导 | 模块化 | data/plant.json 手工 JSON |
| 角色/权限 | 按角色分配 | 多用户 | 角色仪表板 | 用户+站点授权 | 无 |
| 成本/效益 | 六位数字节约案例 | **Cost Inspector**（$ / 单位） | 净含量控制 MAV/TNE | 9% 成本降低 | 无 |
| 系统集成 | SAP DM 等 | MES/ERP/HMI/LIMS | 多厂区云平台 | OEE/LIMS/API/DLL/Python | WS/HTTP 自建 |

### v3.7.2 交付清单（原候选 9 项，落地 1-8）

1. ✅ **实时图表增强**：`LiveSPC.spec_limits()` + `chart_engine._draw_spec_lines`（USL/LSL 品红虚线，I-MR/XBar/P·NP·C·U 均生效）；看板页面滚轮缩放 / 拖拽平移 / 双击复位 + 超规格点标红；桌面实时图 `ui/widgets/chart_zoom.py` 滚轮缩放（Shift 纵向）与双击复位，规格限自动读 plant.json。**看板视觉重设计**：调色板与 `ui/theme.py` 令牌一致（bg #181822/#262632、accent #1b5faa/#4da6ff、状态色 #27ae60/#ffa726/#e74c3c）、基准字号 15px 起并可 A−/A/A+ 调节（localStorage 持久化，车间大屏用）、HiDPI 画布 + Y 轴刻度/网格/时间轴、悬停十字线数值提示、KPI 汇总条、工位状态色点+文字双编码（色弱友好）、OEE 进度条与班次外提示、成本卡片
2. ✅ **plant.json 可视化配置**：`ui/dialogs/plant_config_dialog.py` 表格编辑器（增删行 / USL·LSL / 节拍 / 成本 / 班次）+ Excel·CSV 模板导入导出；`core/plant.py` 新增 `plant_to_rows` / `rows_to_plant` / `rows_from_excel` / `reload()` 热重载（对象标识不变，看板/OEE/实时图即时生效）
3. ✅ **告警补全**：等级 `info/warning/critical`（预告/警告/严重，规则可覆盖，按类型与超限幅度自动判定）+ `core/streaming/alert_journal.py` JSONL 留存与确认（ack/ack_by/note）+ 审计 `alert_fired`/`alert_ack` + `ui/dialogs/alert_center_dialog.py`（等级筛选/仅未确认/确认/导出 CSV）+ 联动动作 `make_action_handler`（默认 `alert_actions_enabled=false` 绝不执行）；**顺带修复** v3.7.0 遗留缺陷：邮件/webhook 处理器为函数而引擎按 `h.notify` 调用，导致两类通道在引擎路径下静默失效
4. ✅ **成本分析**：`core/streaming/cost.py` 超规格量 × 单件损失（废品成本优先，缺省回退单位成本）+ 停机分钟 × 停机费率；`/api/cost` 与看板「成本损失」卡片（对标 Cost Inspector）
5. ✅ **实时 OEE 真人化**：`core/plant.py` 节拍字段（工位优先、回退产线，瓶颈工位取最大）+ 班次日历（`parse_shift` / `shift_seconds_in_window`，支持跨零点）+ `core/streaming/downtime.py` 停机原因码追踪；`LiveOEEComputer` 输出 A/P/Q 真实口径与 defects / downtime_s / run_time_s / 原因码，向后兼容无节拍·无班次旧配置（P=1.0、A 沿用样本口径）
6. ✅ **数据保留与降采样**：`measurements_1m` 分钟聚合表（avg/min/max/count，幂等重算）+ `maintain()` 分档保留（原始/聚合独立）+ `IngestRunner` 周期维护 + `/api/history?agg=1m`
7. ✅ **连接器健康页 + 自动重连**：`connectors/health.py` 状态机（unknown/online/degraded/error/stopped）+ 指数退避（base×2ⁿ 封顶）+ `IngestRunner` 退避跳过与到期自动重连 + `ui/dialogs/connector_health_dialog.py`（运行时状态 / 插件依赖可用性 / 手动重连）+ `connectors/registry.specs_from_settings` / `create_drivers` 接线 user_config.connectors 到 StreamBus（此前桌面端总线无数据源）
8. ✅ **看板可选鉴权**：`server/app.py` API token（`Authorization: Bearer` 或 `?token=`，HTTP 与 WS 同时校验，WS 未授权 1008 关闭）+ `dashboard_config()` host 绑定（非回环且无令牌时强制回退回环，需显式 `dashboard_allow_lan_without_token` 才放行）+ 看板页面自动透传令牌 + CLI `--token`
9. ⏳ **多站点/多语言**：多站点拓扑合并视图 + 界面多语言（对标 Enact 多站点 / DataLyzer 11 语言）→ 顺延

> **附带缺陷修复**（2026-09-10）：
> ① 「帮助 → 模板格式说明」弹窗自 v3.6.0 起崩溃 — 帮助文本用 f-string 拼接，
> JSON 示例中的 `{` 被当成格式化字段（`ValueError: Invalid format specifier`）；
> 改为普通字符串 + 占位符替换，并让分析类型/必填/可选字段由
> `TemplateParser` 常量自动生成（文档与解析器不再漂移，历史误报的
> cusum/ewma/linear_regression 等不支持类型已清除）。
> ② 使用指南 HTML 同步至最新支持：新增「分析模板与批量」章节（JSON 三种写法、
> Excel 格式、25 种分析类型、字段说明）并补全目录与工具菜单说明。
> ③ PPAP Tab 切换提交等级崩溃 — `_refresh_matrix` 对 `range(3)` 无条件
> `matrix.item(row, c).setForeground(...)`，而第 2 列是 `setCellWidget` 状态下拉框
> （没有 QTableWidgetItem），必然抛 `AttributeError: 'NoneType' object has no
> attribute 'setForeground'`；现跳过空单元格、以 Qt 数据角色还原默认样式，并补上
> 原本 `pass` 未实现的"必交项高亮"，构造后即渲染初始等级样式。同类"空单元格"
> 隐患全库扫描（`.item(...).属性` / `.cellWidget(...).属性`）后确认其余调用点
> 均有 None 保护或位于 try/except 内；尺寸报告空行改为显式提示"缺少 USL/LSL"。

> 与 v3.8.0 AI Agent 不冲突，可将 1/3 与其对话式分析联动（告警事务与图表上下文已可编排）。


---

## v3.8.0 — Industrial AI Agent（QAM Harness + 插件接口）（开发中）

> 主题：打造工业级 AI Agent 平台（LLM 智能分析 + BYOK + 工具调用）。
> **2026-09-12 架构调整**：机器视觉不进入主软件，改为独立插件项目
> `QA-Tool-Vision-expansion`；主应用只提供插件接口 v2（Tab / Agent 工具 /
> 设置页 / 能力依赖声明 / 信任模型）。

### 架构设计

```
QA-Tool v3.8.0 Industrial AI Agent
    |
    ├── Core Agent Layer
    │   ├── LLM Client (Ollama/OpenAI/DeepSeek)  [已有]
    │   ├── Knowledge Base (TF-IDF RAG)           [已有]
    │   ├── Conversation Manager (多轮对话)
    │   └── Tool Registry (工具注册)
    |
    ├── Plugin API v2 (主应用只保留接口)
    │   ├── IQAToolPlugin (manifest / 能力 / 依赖探测)
    │   ├── 贡献点: Tab · Agent 工具 · 设置页
    │   └── 分发: plugins/ · ~/.qa_tool_plugins/ · pip entry point
    │        └── 外部项目 QA-Tool-Vision-expansion（视觉能力）
    |
    ├── Analysis Tools (Agent 可调用)
    │   ├── Quality Analysis (SPC/Capability/MSA)
    │   ├── Time Study (手动；视觉由插件贡献)
    │   ├── IE Tools (OEE/SMED/TPM)
    │   └── Root Cause (SHAP) [已有]
    |
    └── Output Layer
        ├── Natural Language Response
        ├── Chart Generation
        └── Report Export
```

### 核心内容

**Phase 1: Agent Core (Day 1-2) — ✅ 已完成 2026-09-11**
- `core/agent/engine.py` — Agent 主循环（LLM 调用 + 工具调度）
- `core/agent/tools.py` — 工具注册与调度框架
- `core/agent/conversation.py` — 多轮对话管理 + 上下文保持
- `ui/dialogs/agent_dialog.py` — Agent 对话 UI

> **Phase 1 实际交付（2026-09-11）**
> - `core/agent/tools.py` — `ToolRegistry` / `AgentContext` / `ToolResult` +
>   **16 个面向本软件能力的工具**（真引擎接线，非壳）:
>   数据清单 / 列统计描述 / SPC 控制图（imr·xbar_r·xbar_s·p·np·c·u·cusum·ewma）/
>   过程能力（正态·非正态）/ Gage R&R（交叉·嵌套）/ 假设检验（正态·t·配对·ANOVA）/
>   OEE（IE 资源解析）/ 实时 OEE 快照 / 成本损失 / 告警查询 / 连接器健康 /
>   五链上下文 / 产线配置 / 已运行分析 / 知识库检索 / 指标解读
> - `core/agent/engine.py` — 在线（LLM 输出 `{"tool":...,"args":...}` → 执行 →
>   结果回灌 → 最多 3 步）与**离线（关键词规则路由 + explain 判定阈值 + 改善建议）**
>   双路径；LLM 异常自动降级离线；工具异常不中断主循环
> - `core/agent/conversation.py` — 多轮裁剪 / 工具记录 / Markdown 导出
> - `core/agent/explain.py` — Cp/Cpk/Pp/Ppk/PPM/σ/GRR/ndc/OEE/A·P·Q/p 值/RPN/
>   平衡率/不良率的工程解读（离线也能给判定与建议）
> - `ui/agent_bridge.py` — UI→core 适配（主窗口数据表/分析结果/五链/产线/告警/
>   停机追踪/实时 OEE/连接器健康/知识库 → AgentContext）
> - `ui/dialogs/llm_dialog.py` — 在既有 Ollama 对话框上升级为 QAM Harness：
>   聊天气泡（左右分栏）/ Markdown 轻渲染 / 工具调用卡片（参数·耗时·状态）/
>   上下文条（数据表·分析数·告警数·工具数）/ 8 个 Agent 预设 / 离线工具模式提示
> - 流式渲染修复（2026-09-11）: token 更新由"逐块删尾"改为**锚点整段替换**，
>   每个回答始终在同一气泡内逐字增长（原实现 `StartOfBlock` 只能删掉表格气泡的
>   最后一段，导致每个字残留新框刷屏）；工具卡片到达时结束当前气泡避免覆盖，
>   收尾/失败/清空同步复位锚点；新增 4 例 UI 回归（直接 token + 真实 Worker
>   信号链路）
> - 对话窗口交互升级（2026-09-11）: 模型选择下拉框（含刷新/自定义项）改为
>   **「模型名称」完全自定义输入框**（回车/失焦生效，QSettings 记忆）；
>   窗口改为独立非模态顶层窗口（可自由移动/缩放/最大化/全屏），
>   初始尺寸按屏幕可用区域自适应并居中，双行头布局保证 860px 宽度下无遮挡
> - 命名统一: 侧边栏与菜单「AI 助手」→ **QAM Harness**（`sidebar.llm` / `menu.ai`，
>   `LLMDialog` 保留为兼容别名）
> - 测试: `tests/test_agent_tools.py`(12) + `tests/test_agent_engine.py`(15) +
>   `tests/test_agent_ui.py`(14)，覆盖真引擎数值、工具异常兜底、离线路由、
>   LLM 工具协议解析、步数上限、UI 端到端对话
> - P0 收尾同步完成: 路线图数字订正（36 分析 Tab / 1400+ 测试）、`.gitignore`
>   增加运行产物（data/、analysis_report.*、chat_history.md）、remote URL 明文
>   token 清理、`requirements-vision.txt` Vision 可选依赖占位

> **P2 实际交付（BYOK 云供应商 + 隐私门，2026-09-11 ✅）**
> 说明: 编号沿用 P0→P4（P2=BYOK、P3=Vision），与本文件原先的 "Phase 2: Vision"
> 对应关系为 P3 = Phase 2。
> - `core/agent/providers.py` — BYOK 注册表：**OpenAI / Anthropic / Google Gemini /
>   DeepSeek / Z.ai(GLM) / KIMI** + **自定义 OpenAI 兼容端点**（vLLM/LM Studio/
>   OneAPI/企业网关）；协议映射（openai / anthropic / gemini 原生 / ollama）、
>   本地端点识别（localhost·127.x·10.x·192.168.x·172.16-31.x·::1）、密钥脱敏
> - `core/llm_client.py` 重构 — 三套协议适配器：OpenAI 兼容 SSE、
>   **Anthropic 原生**（x-api-key + anthropic-version + content_block_delta）、
>   **Gemini 原生**（streamGenerateContent + alt=sse）；统一 SSE 解析、
>   **错误归一化**（401/403/404/429/5xx/超时/DNS → 中文可读 + 密钥脱敏）、
>   `from_config()`（读加密配置）与 `test_connection()`（延迟 + 模型数）
> - **隐私门**（路线图验收项）: `core/agent/privacy.py` fail-closed 策略 +
>   `ui/dialogs/privacy_dialog.py`「同意并继续 / 仅用本地工具 / 取消」，
>   按供应商**只拦一次**（`llm_privacy_ack_<id>`，设置页可撤销），外发预览列出
>   问题 + 工具结果摘要（截断 400 字）+ 数据列名提示与规模估算，明确声明
>   不上传原始数据表/路径/密钥
> - 设置面板新增「QAM Harness」标签页: 供应商 / 模型（可自定义）/ API Key
>   （密码框 + 显示切换 + 保存即加密 + 清除）/ 接口地址覆盖 / **连通性测试**
>   （后台线程，显示延迟与模型数）/ 隐私授权状态与撤销 / 云调用总开关
> - 对话窗口: 供应商下拉（8 项，未配密钥置灰标注）、模型联动、隐私提示条；
>   云调用关闭或未授权时自动降级本地工具模式
> - API 接入快捷补配: 在对话窗口点击/切换到未配置密钥的云供应商时直接弹出
>   密钥输入框（密码回显 + 空值校验 + 保存即加密 `_enc`），已有密钥静默接入；
>   取消则回退原供应商，不改变当前连接
> - 测试: `test_agent_providers.py`(7) + `test_llm_client_protocols.py`(18) +
>   `test_agent_privacy.py`(11) + `test_settings_ai_tab.py`(8) + 对话 UI 扩展(5)
>   + API 接入快捷补配(6) = **55 用例**，全部离线（mock urlopen），覆盖协议请求体/请求头/SSE 解析、
>   错误归一化、密钥加密落盘与不回显、隐私门三出口

> **评审 O1/O2 修复（2026-09-11 ✅）**
> - **O1 工具覆盖补齐**：新增 `core/agent/tools_ext.py`，工具数 16 → **30**，
>   覆盖全部 36 个分析 Tab 的主要能力——Laney P′/U′、Hotelling T²、能力 Sixpack、
>   组间组内能力、Johnson 变换、容差区间、属性一致性、Type 1、线性·偏倚、EMP、
>   双因素 ANOVA、卡方、两比例、TOST、Mann-Whitney/Kruskal、DOE 分析（因子/部分因子/
>   响应曲面/BBD/PB/DSD/田口/混料）+ 设计生成 + 功效与样本量、线性回归、可靠性
>   （Weibull/KM/Cox/Crow-AMSAA/保修/RBD）、时间序列（ARIMA/指数平滑/季节分解/
>   ACF·PACF）、IE（标准工时/线平衡/VSM/工作抽样/SMED/TPM）、AI 根因分析。
>   实现遵循"真引擎"原则并逐一对齐真实返回结构；DOE 引擎参数差异用
>   `_call_with_supported` 自适应
> - **O2 流式防泄漏**：模型输出工具 JSON 时不再把 JSON 打到界面——
>   以 `{`/``` 开头则全缓冲；正文中出现 `{"tool"` 则只放行其之前正文；
>   并保留 6 字符尾部防止分块切断泄漏；非工具 JSON 回答不丢内容
> - **顺带发现（未修，待定）**：`analysis/spc/hotelling.py` 在**未提供子组列**时
>   `sample_sizes=[1]*n` 使 `_compute_ucl` 的 `(ni-1)` 项为 0 → **T² UCL=0、
>   100% 点被判越限**（提供 subgroup_column 后 UCL=2.447、越限 0，实测对照）。
>   当前工具已改为显式告警并建议提供 subgroup_column；引擎公式修复需另行确认
>   （个体观测的正确形式为 UCL = p(m+1)(m-1)/(m(m-p))·F(α;p,m-p)）
> - 测试: `tests/test_agent_tools_ext.py`(15) + `test_agent_engine.py` 新增 4 例
>   = **19 用例**（每个扩展工具都用真实引擎跑通合成数据）

**Phase 2: Vision Infrastructure (Day 3-4)**
- `analysis/vision/camera.py` — 相机输入抽象（USB/IP/RTSP/MJPEG）
- `analysis/vision/processor.py` — 帧处理流水线
- `analysis/vision/pose.py` — MediaPipe 姿态估计（33 关键点）
- `analysis/vision/action.py` — 动作分类（工作/空闲/走动/搬运）

**Phase 3: Integration (Day 5-6)**
- Agent 调用 Vision 能力（视频时间研究）
- Agent 调用 Quality/IE 工具
- 自然语言响应生成（统计结果口语化解读）

**Phase 4: Testing & Polish (Day 7)**
- E2E 测试：Agent 对话 → 工具调用 → 结果返回
- 性能优化：帧处理延迟 < 100ms
- 文档更新

> **P3 历史交付（Vision AI 视频时间研究，2026-09-11 ✅ → 2026-09-12 迁出）**
> **状态更新**：以下视觉代码已整体迁出主库，作为独立插件项目
> `QA-Tool-Vision-expansion`（pip entry point `qa_tool.plugins`）；
> 主库不再包含 `analysis/vision`、Tab 37、`tools_vision` 与 Vision 依赖。
> 说明: 编号 P3 = Phase 2/3/4（Vision 基础设施 → Agent 集成 → 验收），
> V0 为实施中发现并先行修复的工时研究计时列缺陷。
> - **V0 前置修复**: `analysis/ie/time_study.py` 旧实现误用 `cycle`（循环序号）
>   当观测时间，3 次 11/12/13s 的观测会算成均值 2s；已改为
>   `observation_time > 0` 优先、否则回退 `cycle`（兼容旧数据），
>   整体统计同步修正；新增 `tests/test_ie_time_study.py`(8)
> - **V1 核心引擎** `analysis/vision/`（无 Qt，cv2/mediapipe 全惰性导入）:
>   - `camera.py` — 文件/USB/RTSP/MJPEG/合成源统一 `FrameSource` 接口 +
>     `open_source()` 解析；文件源帧序号时间戳可复现，实时源墙钟
>   - `processor.py` — 缩放/ROI/MOG2 前景 ∪ 帧差活动特征/最大前景块质心与
>     包围盒/位移速度/延迟统计（P95）
>   - `pose.py` — MediaPipe **Tasks API**（1.0 起已移除旧 `mp.solutions`）
>     PoseLandmarker VIDEO 模式 33 关键点 + 手腕摆动/搬运姿态特征；
>     模型缺失/校验失败/依赖缺失自动降级 OpenCV 运动特征并给出提示
>   - `model_store.py` — `pose_landmarker_lite.task`（5.6MB，SHA256
>     `59929e1d…574d`）按需下载 + 校验，默认 `~/.qa_tool_models/`，
>     支持 `QA_TOOL_MODELS_DIR` / `QA_TOOL_POSE_MODEL` 离线放置
>   - `action.py` — 工作/空闲/走动/搬运/离岗规则状态机 + 最短驻留迟滞，
>     输出状态段/时长占比；`VISION_STATUSES` 供工作抽样引擎直接复用
>   - `session.py` — 采样节拍（固定步进，容忍浮点时间戳）/周期切分
>     （合并小间隔、过滤过短）/`to_time_observations()`/
>     `to_work_sampling_labels()`/逐帧回调（UI 预览）
> - **V2 Agent 工具** `core/agent/tools_vision.py`: 工具数 30 → **34** —
>   `vision_status`（依赖/模型探测）· `vision_analyze_video`（状态占比+周期，
>   默认 5FPS/10 分钟，上限 30 分钟）· `vision_time_study`（周期 →
>   标准工时，接 TimeStudyEngine）· `vision_work_sampling`（接
>   WorkSamplingEngine，含置信区间与工时利用率）；无依赖时返回安装指引
> - **V3 UI** `ui/tabs/vision_tab.py`（**Tab 37「视频时间研究」**，
>   registry/sidebar/i18n/IE 菜单四处接线）: 视频源与参数区 · QThread 分析
>   线程逐帧预览叠加状态徽标 · 状态占比/周期表 · 「发送到工时研究」
>   （主窗口路由到 Tab 7 `set_ie_data`）· 结果 JSON 导出 · 姿态模型一键下载
>   （进度 + SHA256）· 依赖缺失显示安装指引
> - **V4 验收**: `tools/vision_benchmark.py`（标注 CSV 时长加权一致率 +
>   混淆统计；`--demo` 合成自检 **99.0%**；现场片段 `--min-accuracy` 门禁）。
>   实测（640×480，30fps 合成源采样 15fps）: OpenCV 路径 **15.1 FPS**、
>   单帧均值 3.6ms / P95 2.9ms；MediaPipe 路径 **15.1 FPS**、
>   均值 12.8ms / P95 14.1ms（均 <100ms 验收线）。
>   新增测试 53 例（时间研究 8 + Vision 引擎 25 + Agent 工具 10 +
>   Tab 6 + 基准 4），全部离线/合成数据；最终全量逐文件回归
>   **115 文件 / 1594 通过 / 2 跳过 / 0 失败**，ruff 零告警
> - **文档与打包**: guide.html 新增「视频时间研究」章节与模块/工具数订正
>   （37 Tab / 34 工具）；README 中英同步；`requirements-vision.txt`
>   统一 `opencv-contrib-python>=4.9,<5` + `mediapipe>=1.0`（避免双 cv2
>   发行版冲突）；PyInstaller 默认排除 `cv2/mediapipe`（可选能力，
>   随包分发需移除 excludes 后重建）
> - **遗留（需真机验收）**: 沙箱无 `/dev/video*`，摄像头实拍与现场动作
>   准确率需在用户机器上跑 `tools/vision_benchmark.py --video … --labels …`；
>   合成自检达标不等于现场达标，真机素材到位后补验收记录

> **插件接口 v2 实际交付（v3.8.1，2026-09-12 ✅）**
> 定位：主应用不再内置具体能力插件，只提供稳定接口；视觉由独立项目承载。
> - `core/plugin_api.py` — `PLUGIN_API_VERSION=2.0` · `PluginManifest`
>   （id/版本/API 版本/兼容主程序/可选依赖/能力项，非法声明拒绝加载）·
>   `IQAToolPlugin`（is_available / create_tab / register_agent_tools /
>   create_settings_page / on_load / on_unload）· `PluginToolRegistry`
>   （工具自动加 `<插件id>_` 前缀避免冲突）· 版本表达式与 API 大版本兼容校验
> - `core/plugin_manager.py` v2 — 三级发现（随包 `plugins/` → 用户目录
>   `~/.qa_tool_plugins/`（`QA_TOOL_PLUGIN_DIRS` 可覆盖）→ pip entry point
>   `qa_tool.plugins`）；**信任模型**（随包默认信任，用户/pip 插件首次只解析
>   manifest，不导入不执行，设置页信任后加载）；依赖探测返回"不可用 + 安装
>   指引"；旧式单文件 `IPlugin` 经 `LegacyPluginAdapter` 兼容
> - `ui/plugin_host.py` — 插件只读门面（数据表/分析结果/项目上下文/主题字体/
>   通知/跳转），避免插件直接操作主窗口内部状态
> - 主应用接线：插件 Tab 进入侧栏「插件」分类（索引动态分配）· 插件工具并入
>   QAM Harness 工具注册表 · 「设置 → 插件」页展示状态/信任/插件设置页 ·
>   插件 Tab 的 `send_to_time_study` 信号可回传工时研究（通用路由）
> - 首个外部插件 **QA-Tool-Vision-expansion**（独立项目，pip entry point）：
>   视觉引擎/动作识别/视频 Tab/4 个 Agent 工具/基准脚本/模型下载全部迁出，
>   主库删除 `analysis/vision`、Tab 37、`tools_vision`、`requirements-vision.txt`
>   与对应测试；插件侧 44 通过 / 1 跳过，主库插件契约 7 例 + 现有 UI/引擎回归通过
> - 主库工具数回到 30（插件工具按安装情况追加，如视觉插件提供 vision_* 四个）；
>   Tab 数 36 + 插件 Tab；PyInstaller 默认排除插件依赖 cv2/mediapipe

### BYOK 架构
- 用户在设置面板配置自有 API Key（OpenAI / Anthropic / Google / DeepSeek / Z.ai / KIMI）
- Key 加密存储（跨平台密钥库）
- 连通性测试

### 知识库 RAG
- 内置质量工程知识库（IE/质量工程/精益生产方法论）
- 用户可扩展
- TF-IDF 检索（后续升级向量检索）

### 数据隐私
- 首次 cloud API 调用隐私弹窗（明确告知数据发送至供应商）
- 用户确认后持久化

### 验收标准
- 6 家供应商 API Key 配置 + 连通性测试全流程
- Agent 对话：自然语言问答 → 工具调用 → 结果返回
- Vision AI（已迁出）：摄像头预览帧率 ≥ 15 FPS、动作分类准确率 ≥ 85%
  → 由独立插件项目 `QA-Tool-Vision-expansion` 验收；主库验收插件接口契约
- 主动建议准确率人工评审（工程师评分 ≥ 3.5/5）
- 数据隐私弹窗拦截率 100%
- 统计结果人话解释（P 值/Cp/Cpk 自动口语化解读）

---

## v3.9.0 — 已合并至 v3.8.0 / 独立插件项目

> ⚠️ 本版本规划的「视频时间研究（Vision AI）」不再进入主软件，
> 已迁至独立插件项目 `QA-Tool-Vision-expansion`（主应用仅保留插件接口 v2）。

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

## 版本历史

| 日期 | 版本 | 内容 |
|------|---------|---------|
| 09-12 | v3.8.1-plugin-api | **插件接口 v2 + 视觉迁移**：`core/plugin_api.py`（manifest/能力/依赖/工具前缀代理/API 版本门禁）+ `core/plugin_manager.py` 三级发现与信任模型 + `ui/plugin_host.py` 只读门面；主应用接线插件 Tab/Agent 工具/设置页；迁移出 `analysis/vision`、Tab 37、`tools_vision`、`requirements-vision.txt` 与视觉测试到独立项目 `QA-Tool-Vision-expansion`（README/pyproject/entry point/44 用例）；插件契约测试 7 例，主库保留 36 Tab/30 工具 + 插件贡献 |
| 09-11 | v3.8.0-P3 | **Vision AI 视频时间研究完成**：V0 修复工时研究误用 cycle 计时列；新增 `analysis/vision/`（文件/USB/RTSP/MJPEG/合成源、MOG2∪帧差流水线、MediaPipe Tasks 33 关键点 + OpenCV 降级、工作/空闲/走动/搬运/离岗迟滞状态机、周期切分与 TimeObservation/工作抽样输出、姿态模型按需下载+SHA256）；QAM Harness 工具 30→34（vision_status/analyze_video/time_study/work_sampling，离线关键词路由含视频路径提取）；新增 Tab 37「视频时间研究」（QThread 实时预览、占比/周期表、发送到工时研究、JSON 导出、模型下载）；`tools/vision_benchmark.py` 合成自检 99.0%，640×480 采样 15fps 实测 15.1 FPS、P95 ≤14.1ms；新增 53 例测试；文档/README/guide 同步，PyInstaller 默认排除 cv2/mediapipe；摄像头实拍验收待用户侧素材 |
| 09-11 | v3.8.0-P1 | **QAM Harness Agent Core 完成**：`core/agent/{tools,engine,conversation,explain}.py` + `ui/agent_bridge.py` + 对话 UI 升级（气泡/Markdown/工具卡片/上下文条）；16 个工具全部接真实分析引擎（SPC/能力/MSA/假设检验/OEE/成本/告警/连接器/五链/产线/实时/已跑分析/知识库/指标解读）；在线 LLM 工具协议 + 离线规则路由双路径（断网可用），LLM 异常自动降级；「AI 助手」更名 QAM Harness（侧栏+菜单+i18n+文档）；新增 3 个测试文件 41 用例；顺带完成 P0（路线图数字订正、.gitignore 运行产物、remote 明文 token 清理、requirements-vision.txt 占位） |
| 09-10 | v3.7.2 | 实时监控对标优化 8 项落地：**实时图表增强**（LiveSPC 规格限输出 + chart_engine USL/LSL 参考线 + 看板滚轮缩放/拖拽/双击复位 + 桌面实时图 chart_zoom 与 plant 规格自动注入）；**看板视觉重设计**（主题令牌对齐 ui/theme.py、基准字号 15px + A−/A/A+ 可调、HiDPI 坐标轴/网格/悬停提示、KPI 汇总条、状态色点+文字双编码）；**plant.json 可视化配置**（表格编辑器 + 模板导入导出 + reload 热重载 + 默认路径 off-by-one 修复与旧位置迁移）；**告警补全**（info/warning/critical 分级 + AlertJournal JSONL 留存与确认 + 审计 + 告警中心 UI + 联动动作默认禁用；顺带修复邮件/webhook 处理器派发缺陷）；**成本损失**（超规格×单件损失 + 停机×费率，/api/cost + 看板卡片）；**OEE 真人化**（节拍→真实性能 P、停机原因码、班次日历、P/OEE 截断至 100%、班次外不计入、向后兼容旧配置）；**数据保留**（measurements_1m 分钟聚合 + 分档保留 + agg=1m 查询）；**连接器健康**（状态机 + 指数退避自动重连 + 健康页 + user_config.connectors 接线 StreamBus）；**看板鉴权**（API token HTTP/WS 双校验 + host 绑定安全回退）；**文档同步**（修复「模板格式说明」弹窗 f-string 崩溃、类型清单改由解析器常量生成；使用指南新增「分析模板与批量」章节并补全目录/工具菜单说明）。新增 10 个测试文件（约 90 用例），ruff 零告警，全量逐文件回归通过 |
| 09-10 | v3.7.1 | 缺陷修复与加固：**五链贯通三段桥接修复**（FMEA→CP 索引错配静默失效 / CP→SPC 懒加载时序错 + 监控清单无 UI 承载 / 8D 绕过上下文直读缓存）+ ProjectContext 确立为链路唯一事实源；**数据识别语义修复**（measurement 关键词列不进 numeric_columns 导致导入误报与 DOE 空因子；"时间"关键词把可用时间/停机时间/观测时间误判为 timestamp；清洗后 select_dtypes 重算恒空）+ DataParser.refresh_info 公共 API；**工程一致性**（打包不再夹带本机 user_config.json，改发 user_config.default.json + 敏感配置 <key>_enc 加密；APP_VERSION 单一事实源 + tools/check_version.py 入 CI；退出统一清理告警引擎/看板线程/实时订阅；Linux 无 keyring 显式提示不落明文）；**结构清理**（删除 anti_debug/integrity/license_keys/license_generator/license_dialog 约 950 行僵尸代码，保留 core/license.py 兼容 shim；字体工具下沉 core/fonts.py + 分层守卫测试；插件侧栏显示 IPlugin.name；test_integration 转为真 pytest 用例，run_all_tests 迁至 tools/） |
| 09-08 | v3.7.0-review | 新增代码质量审查：9 处缺陷修复（B1-B9, 见 fix commit 2381c46）+ 竞品对标（Minitab RTSPC / WinSPC / Enact / DataLyzer 官方页）→ v3.7.1 候选清单 9 项入档 |
| 09-08 | v3.7.0 | 实时 SPC 云看板与数据连接器开发完成：P1 驱动抽象/流总线/SQLite时序/PollRunner（<500ms）→ P2 LiveSPC 实时控制图（跳变<500ms 检出）→ P3 FastAPI+WS 浏览器看板（50并发）→ P4 连接器插件 SPI（Modbus/MQTT/OPC-UA/DMIS/量具 按需安装）→ P5 产线拓扑/状态灯/实时OEE/告警中心（邮件/webhook/桌面, 去抖）→ P6 版本 3.7.0 四端一致+文档；74+ 测试文件全绿；构建链 PyInstaller+Inno+AppImage+deb 维持
| 09-07 | v3.7.0-前置 | 风格债全量清零（F841 65 / E701·E702 568 / E402 20 / B 类 72）；ruff 入 ruff.toml+dev-requirements+CI 门禁零告警；构建链 Nuitka → PyInstaller(onedir)（build_pyinstaller.py），Inno/AppImage/.deb 保留；73 测试文件全绿 |
| 09-06 | v3.6.0 | Graph Builder 增强与交互体验完成并通过代码验收：图表编辑架构/实时交互/热力图·散点矩阵/小多图 Faceting/导出增强/帮助中心(guide.html)+菜单重构；全量质量审查并入（7 处潜在崩溃修复+ruff 清理）；73 个测试文件全绿；版本号统一 3.6.0；发布打包另行执行 |
| 09-05 | v3.5.0 | MSA与能力深化完成：属性一致性增强(Fleiss's Kappa + 有效Kappa + 偏差矩阵) + EMP方法量具研究 + Gage R&R增强(方差分量图 + 交互效应图 + 不确定度预算) + Capability Sixpack + 自动能力分析 + Edgeworth近似 + 100+ 测试 |
| 09-04 | v3.8.0-planning | 架构调整：v3.8.0 + v3.9.0 合并为 Industrial AI Agent（AI + Vision 融合平台）；v3.9.0 视频时间研究作为 Agent Vision 能力在 v3.8.0 Phase 2 实现 |
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
> v3.8.0 Industrial AI Agent 以对话式交互为主，不新增独立 Tab。

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)   v3.0.0 (35)      v3.8.0 (35+Agent)
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
 Plugins (dynamic) Same        Same             Same           Same             Same                Same
 —               —             —                —                 —                Agent Dialog (new)
```
