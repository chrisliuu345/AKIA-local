# QA-Tool 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v2.6.5 编号缺陷清零 + Info 一期 | 测试: 450+ pytest · 35 个 Tab + 插件 | 更新: 2026-08-23

---

## 版本总览

> **规划重构（2026-08-22）**：v2.6.5 起的规划已全面重构 — 从"增加功能"转向"现有功能深化"，以核心竞争力为主线，编号缺陷修复优先。详见[核心竞争力定位](#核心竞争力定位2026-08-重规划)。

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ✅ ──→ v2.6.4 ✅ ──→ v2.6.5 ✅ ──→ v2.7.0 ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0
```

| 阶段 | 版本 | 主题 |
|------|---------|------|
| 已完成 | v2.0 ~ v2.6.5 | Release → 代码+AI → 工程工具 → 报告 → 实时监控 → UX+动画 → 硬件扩展 → ESP32 部署 → 安全校验 → RBAC+认证 → 统计引擎加固 → UI 健壮性 → 缺陷清零 |
| 待开发 | v2.6.5 | 编号缺陷清零 + Info 一期 |
| 待开发 | v2.7.0 | 统计引擎深化 + Info 二期 |
| 待开发 | v2.8.0 | 工作流贯通（差异化核心）+ Info 三期 |
| 待开发 | v2.9.0 | 深化整合与报告贯通 |
| 待开发 | v3.0.0 | 稳定化里程碑 + Info 收尾 |

---

## 核心竞争力定位（2026-08 重规划）

> 基于 2026-08 开源竞品全景调研（JASP / Jamovi / Cassini / SigmaExacta / Point85 OEE / pyDOE / R 生态 qcc·FrF2·gageRR 等）：**开源界不存在任何同时覆盖 SPC + 能力 + MSA + 假设检验 + DOE + IE 工具 + FMEA/8D/PPAP + AI + 硬件 + 中文的桌面一体化软件。** 最接近者各自缺口：Cassini（SPC 平台）缺 IE/FMEA/PPAP/中文；JASP 缺 IE/FMEA/硬件/中文；SigmaExacta 仅覆盖 FMEA/8D/PPAP（Web PWA）；唯一近全覆盖者为商业软件 Datalyzer。

### 差异化支柱（按独特性排序）

| # | 支柱 | 开源竞品现状 | 深化主线 |
|---|------|--------------|----------|
| 1 | **质量工作流贯通**（FMEA→控制计划→SPC→PPAP→8D 数据链） | 空白：SigmaExacta 三件套互不联通，无特征级数据模型 | **v2.8.0（差异化核心）** |
| 2 | **统计引擎深度对标 Minitab** | 分散：R 包方法全但无 GUI；JASP QC 覆盖窄 | **v2.7.0（本体价值）** |
| 3 | **中文优先 + 离线桌面**（工厂车间场景） | 空白：无开源 QE 工具提供原生中文 UI | 全程保障 |
| 4 | **本地 LLM AI**（Ollama + RAG，离线可审计） | 竞品 AI 全部云依赖或原型阶段 | v3.0.0 后 |
| 5 | **ESP32 硬件互联**（量具/传感器直采→SPC） | 近乎空白（仅 Cassini MQTT / Point85 OPC-UA，均在付费层） | v3.0.0 后 |

### 规划原则

1. **编号缺陷修复优先** — W 系列全部清零（v2.6.5）后方可进入大版本迭代
2. **只深化、不扩张** — v2.6.5~v3.0.0 不新增 Tab、不新增独立功能模块，全部投入现有能力的正确性、深度与贯通性
3. **统计正确性以已知值验证** — 新增统计方法必须以 NIST/权威文献已知值数据集做单元测试
4. **Info 分批穿插清偿** — 151 项技术债分四批（v2.6.5 / v2.7.0 / v2.8.0 / v3.0.0），不阻塞深化主线
5. **测试基线只增不减** — 289+ 为下限，每版本全量回归

---

## v2.1 ✅ 已完成 — 代码质量与 AI 增强

### 方向 A：代码质量与架构优化
- 5 个 P0 级 Bug 修复（p_chart 数据串位 / PDF 水印 / NameError ×3）
- 消除 12 处裸 except，2 处 iterrows 向量化
- Tab 懒加载（TAB_REGISTRY 32 项 + importlib 按需加载），启动时间减半
- 清理 200+ 未使用 import、60+ 死代码
- welcome_page 4 个失效功能修复、diagnostics apply_all 修复
- 测试: 65 → 87（+22）
- 关键修复：`pd.to_numeric` 替代 `select_dtypes`、`removeWidget` 防止 Stack 索引错位、`iloc` 保证重复列安全

### 方向 C：AI 智能增强
- 知识库 99 → 124 条（+25：SMED/8D/TPM/PPAP/AQL/Weibull/ALT/非参数）
- 混合检索：TF-IDF (0.5) + 关键词 (0.3) + 标题 (0.2)
- AI 对话 V2：8 个预设模板 + 20 轮历史 + MD 导出 + QSettings 持久化 + 流式刷新
- 一键分析：画像 → 推荐 → 执行 → AI 报告 → PDF/MD
- LLM 线程管理（closeEvent quit+wait）

### UX 改进
- 导入表格 → 自动路由到 21 个非 IE 工具（sheet_map 22 项）
- 欢迎页双入口（表格 / IE 数据）
- IE 识别 100+ 别名扩展；近常数列静默抑制
- 版本 → 2.1，构建 exe（36.8MB）带 logo + 知识库

---

## v2.2 ✅ 已完成 — 工程工具扩展

### 阶段 A：v2.1 遗留修复（9 项）
插件索引 33、LLM 流式刷新、validate_params 补全、动画清理、欢迎页最近项目、diagnostics apply_all、Chart Tab 控件清理、数据校验、profile_result

### 阶段 B：新工程工具（4 个模块）

| 索引 | 模块 | 引擎 | Tab |
|:--:|------|------|------|
| 29 | SMED | `analysis/ie/smed.py` | `ui/tabs/smed_tab.py` |
| 30 | 8D 问题解决 | `analysis/quality/eight_d_engine.py` | `ui/tabs/eight_d_tab.py` |
| 31 | TPM | `analysis/ie/tpm.py` | `ui/tabs/tpm_tab.py` |
| 32 | PPAP | `analysis/quality/ppap_engine.py` | `ui/tabs/ppap_tab.py` |

**侧边栏**: 32 个 Tab（+4 新增）· 插件起始索引 33

---

## v2.3 ✅ 已完成 — 报告增强

### 阶段 A：v2.2 遗留修复（4 项）
- A1: 8D D4 页嵌入 FishboneCanvas（6M 骨架、render_fishbone）
- A2: PPAP 状态变更实时完成度刷新
- A3: PPAP 完成度统一到引擎 `completion_pct`（基于提交层级）
- A4: `analysis/ie/__init__.py` 与 `analysis/quality/__init__.py` 导出新模块

### 阶段 B：报告系统（4 项）

| # | 模块 | 文件 | 说明 |
|:--:|------|------|------|
| D1 | 模板引擎 | `core/report_templates.py` | string.Template，5 套内置 HTML 模板 |
| D2 | 模板对话框 | `ui/dialogs/template_dialog.py` | 选择 → 预览 → 导出 PDF/Word/HTML |
| D3 | 合规报告 | `output/compliance_report.py` | 框架带 IATF/ISO 条款引用 |
| D4 | HTML 导出 | `output/html_export.py` | matplotlib→base64 内联，自包含离线 HTML |

### 菜单重构
6 个菜单：文件 | 分析 | AI | 工具 | 视图 | 帮助 —— 分类子菜单覆盖全部 32 个 Tab

---

## v2.4 ✅ 已完成 — 实时监控与集成（方向 E）

### E1. 文件监视实时 SPC ✅（1.5 天）
- 文件变更 → 自动导入 → 更新控制图 → 超规格预警
- 实现：`core/file_watcher.py`（轮询 FileMonitor 守护线程 + 稳定态确认，Qt-free）、`ui/tabs/monitor_tab.py`（索引 33）

### E2. 多工厂/多线体对比 ✅（1 天）
- 同指标多线并排 · Cp/Cpk 对比 · 违规汇总
- 实现：`core/plant_compare.py`（summarize_plant / build_comparison）、`ui/tabs/multi_plant_tab.py`（索引 34）

### E3. 预警通知系统 ✅（0.5 天）
- 多渠道预警（弹窗 / 声音 / 日志）· 可配置规则 · 预警聚合/去重
- 实现：`core/alert_rules.py`（AlertTracker NEW/ONGOING/CLEARED 状态机 + AlertLog 环形缓冲 + user_config 规则配置）、MonitorTab 预警横幅 + 弹窗 + 蜂鸣 + 日志面板

### E4. 看板 UI 与控制增强 ✅（3 天）— P2-1/P2-2 自 v2.5 提前

**阶段 1：**
- F0: 统一 KPI 提取器 `core/kpi_extractor.py` — 修复 3 个错误卡片指标（OEE / %GRR / SPC 违规键路径错误），为公式引擎提供变量命名空间
- F1: 实时刷新 — 信号驱动（`analysis_completed` → `_notify_dashboard`）+ QTimer(5s) 轮询兜底 + 自动刷新开关
- F2: 自定义卡片布局 — 显示/隐藏 + 排序对话框（`ui/dialogs/layout_dialog.py`），QSettings 持久化

**阶段 2：**
- F3: 低代码公式编辑器（P2-1）— `core/kpi_formula.py` AST 白名单解析器（拒绝 23 类攻击用例，长度/深度防护）+ `ui/dialogs/formula_dialog.py`，自定义 KPI 卡片实时求值
- F4: 车间看板模式（P2-2）— 全屏看板 `ui/dialogs/display_mode.py`，大数字 KPI 磁贴（FONT_36B），图表轮播（QTimer 8s），ESC/方向键，F11 快捷键

**状态**: 方向 E 全部实现 — E1/E2/E3 完成（Tab 33-34、预警系统、215 测试）

**估算**: 6 天总计（E1 1.5 + E2 1 + E3 0.5 + E4 3）| 新增 Tab 33-34 | 侧边栏 32→34

---

## v2.4.1 ✅ 已完成 — 看板与显示模式视觉增强

- **自适应卡片网格**: ≤3 卡片 → 1 列（560×260）/ ≤6 → 2 列（330×220）/ 更多 → 3 列（240×170）；多卡片滚动溢出保留
- **卡片详情**: 更新时间戳（HH:MM）、状态色点（Cpk/OEE/GRR/违规 红/橙/绿分级）、按列数动态字号
- **动画基础设施** `ui/widgets/animate.py`: fade_in / count_up / cross_fade（QPropertyAnimation/QVariantAnimation, InOutCubic），设置开关（默认开，user_config.json）
- **大屏**: KPI 数字滚动 + 磁贴淡入 + 轮播交叉淡化
- **大屏图表渲染**: 按图表区宽高比渲染（deepcopy + set_size_inches，300ms 防抖重绘）— 修复拉伸/压缩变形与裁切
- **大屏可读性**: 图表 PNG 白底（原深色底黑字）
- **修复**: F5 批量分析 DataFrame 真值歧义；批量分析跳过不可运行 Tab（Dashboard 等）；显示模式窗口防重复
- 测试: 201 → 215

---

## v2.5 ✅ 已完成 — 硬件扩展（ESP32）

### H1. ESP32 设备框架 ✅（core/devices + Tab 35）
- JSON-lines 串口协议（utf-8, `\n` 结尾）：HELLO→ACK→READY 握手 · PING/PONG 心跳（3s/9s）· DATA/COMMAND/RECOGNITION 消息
- `core/devices/`: protocol.py（encode/decode/HandshakeProtocol/Heartbeat）、transport.py（SerialTransport 守护读线程）、discovery.py（comport 扫描 + HELLO 探测）、registry.py（状态机 + user_config.json 持久化）、device.py（Device / Esp32InputDevice / Esp32OutputDevice / MaixcamVisionDevice）
- `ui/tabs/device_tab.py`（索引 35）：设备卡片 + 详情页（事件 / 数据预览 / 输出控制台 / 识别记录）+ 自动发现（3s）+ 设备数据导入分析
- 侧边栏"监控"组：实时监控 (33) / 多工厂 (34) / 设备监控 (35) · 插件起始索引 36
- 测试: test_devices.py 30（全部 mock，无硬件依赖）

### H2. MicroPython 固件 ✅（firmware/esp32_in.py + esp32_out.py, v1.1.0）
- 板载 MicroPython **v1.20.0**（官方 v1.21+ 破坏 `machine.UART(0)`：REPL UART 驱动未安装 → `ESP_ERR_INVALID_STATE`/128B-TX-FIFO 停滞）
- 两份固件均使用 **UART1 重映射到板载桥接芯片**（`machine.UART(1, tx=1, rx=3)`, 115200）+ 开机自上报（HELLO + META）供 PC 自动发现
- `esp32_in.py`: 7 个可配置通道（DS18B20 温度 @GPIO4 + 6× ADC 32/33/34/35/36/39, ATTN_11DB）→ 每秒 DATA · 应答 HELLO/PING
- `esp32_out.py`: COMMAND `<name>:on/off|duty>` 语法（led GPIO2 / 继电器 GPIO25 数字, 舵机 GPIO13 PWM）→ ACK 应答
- REPL 逃生舱：上电时按住 BOOT（GPIO0 低电平）→ 固件退出，REPL 保持可用（维护通道）
- 协议仿真测试（`TEMP/fw_proto_test.py`, 伪 machine + UART 管道）：开机上报 / META / HELLO 应答 / PONG / DATA / COMMAND+ACK 全部通过
- 烧录：复制到板子为 `main.py`（esptool.py 仅安装 MicroPython 镜像；板子：ESP32-D0WD-V3, 4MB, 无 SPIRAM, DTR/RTS 复位脉冲由主机代码处理）

### H3. 实机验证（部分完成）
- ✅ **esp32_in 在 COM3 实测**（`esp32_in_6cc84055ec48`, FW 1.1.0）：自动发现（HELLO 探测 + 开机上报）→ ONLINE → META 7 通道 → 每秒 DATA · 经 `TEMP/e2e_hw_check.py`（hello+pong+meta+data PASS）与设备页冒烟（预览表含通道名/单位、一键导入 → 多列 DataFrame）端到端验证
- ⏳ **esp32_out**: 固件 + 协议仿真测试通过；第二块板烧录并验证 COMMAND→ACK 真实执行器 → **移入 v2.6.1**
- ⏳ **MaixCAM**: 网络传输（TCP/SSH，非串口）→ **移入 v2.6.1**

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

## v2.7.0 — 统计引擎深化（待开发）

> 主题：对标 Minitab 补齐统计方法缺口 — 强化"质量分析软件"的本体价值。缺口清单来自 2026-08 代码级审计（非臆测）。
> **质量铁律：每个新方法以 NIST StRD / AIAG 手册 / 权威文献已知值数据集做单元测试验证。**

### 现状基线（已具备，不重复建设）
9 类控制图 + Nelson 8 规则 · Cp/Cpk/Pp/Ppk + Box-Cox + 组内组间能力 · Gage R&R（交叉/嵌套）+ 线性/偏倚 + 属性一致性 Kappa · t 检验/单双因素 ANOVA/正态性/方差齐性/非参数 3 种 · 全因子 + CCD + Box-Behnken · 线性/多元回归 · Weibull 2P/3P + MTBF + ALT（Arrhenius/IPL）· AQL 计数抽样（GB/T 2828.1）

### P1 核心缺口（7 项，本版本必做）

| 领域 | 新增方法 | 实现位置（规划） |
|------|----------|------------------|
| MSA | **Type 1 量具研究**（Cg/Cgk，单量具×标准件） | `analysis/msa/type1_study.py` |
| 能力 | **真 Johnson 变换**（SU/SB 选型；现实现仅为 z-score 标准化，非真变换） | `analysis/capability/non_normal_cap.py` 重构 |
| 能力 | **Cpm**（田口能力指数；现仅在 time_study 内有零散计算，未进能力引擎） | `analysis/capability/normal_cap.py` |
| SPC | **Hotelling T² 多元控制图**（多特性联合监控，T² + Q 残差图） | `analysis/spc/hotelling.py` |
| 假设检验 | **等价检验 TOST**（1/2 样本均值等价） | `analysis/hypothesis/equivalence.py` |
| 假设检验 | **卡方拟合/独立性检验 + 2 比例检验** | `analysis/hypothesis/proportion.py` |
| 分布拟合 | **通用分布拟合**（正态/对数正态/指数/Gamma/Weibull MLE）+ AD/KS/卡方拟合优度 | 新 `analysis/distribution/fitting.py` |

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

### Info 清零二期（~50 项）
- 重复实现合并 + 单一数据源统一（如 variance_tests/normality 重复、audit 双实现）

### 验收标准
- 新方法 NIST 已知值验证测试全部通过
- 新方法 UI 接入对应现有 Tab（MSA/能力/SPC/假设检验/抽样/图表入口扩展，**不新增 Tab**）
- 全量 pytest 通过

---

## v2.8.0 — 工作流贯通（待开发，差异化核心）

> 主题：打通 FMEA→控制计划→SPC→PPAP→8D 数据链 — 开源界无人实现的差异化壁垒。
> 现状（2026-08 审计）：五个工程 Tab 完全孤岛化 — 无共享特征 ID 数据模型；PPAP 的 Cp/Cpk 靠手输文本解析而非调用能力分析引擎；FMEA/CP/8D 数据不进 .qap 序列化（仅统计 Tab 1-6 结果序列化）；报告模板不能自动拉取分析结果。

### 共享数据模型（地基）
- 新建 `core/project_context.py`：`QualityCharacteristic` 数据类（特征 ID / 工序 / 规格限 / 单位 / 数据源绑定）+ `ProjectContext` 项目级上下文
- 替代 `MainWindow.analyses` 按 Tab 索引的扁平字典（保留兼容层渐进迁移）
- .qap 序列化扩展：FMEA / 控制计划 / 8D 工程数据纳入持久化

### 五链贯通

| # | 链路 | 实现 |
|---|------|------|
| 1 | FMEA → 控制计划 | 高风险项（AP/RPN 阈值）一键生成 CP 行（特征/控制方法/反应计划） |
| 2 | 控制计划 → SPC | CP 控制项生成 SPC 监控清单（特征 + 规格限 + 控制图类型预配置自动带入） |
| 3 | 能力/MSA → PPAP | PPAP #8（MSA）/ #11（初始能力）自动拉取分析 Tab 最新结果，替代手输 |
| 4 | FMEA → 8D D4 | 失效原因/机理注入鱼骨图骨架（替代硬编码 6M 默认值） |
| 5 | 8D D7 → FMEA/CP | "标准已更新"驱动 FMEA/CP 复审提醒与修订标记 |

### Info 清零三期（~51 项）
- i18n 一致性 + 魔法数字常量化 + 私有 API 替换

### 验收标准
- 端到端场景测试：导入数据 → FMEA 识别高风险 → 生成 CP → SPC 监控 → PPAP 自动填充，一条链无手输中断
- .qap 打开/保存完整还原工程数据（含 FMEA/CP/8D）；旧 .qap 向后兼容加载

---

## v2.9.0 — 深化整合与报告贯通（待开发）

> 主题：跨模块结果复用 + 报告自动聚合 + v2.7.0 P3 溢出收尾。

### 报告贯通
- 报告模板自动聚合：一键拉取最新 Cpk / %GRR / SPC 违规 / 8D 状态 / PPAP 完成度等填充模板上下文（当前需调用方手动传 context dict）

### 跨 Tab 结果复用
- SPC ↔ 能力分析共享 σ（同一数据一次计算，控制态/汇总态统一）
- MSA 测量误差注入能力分析（测量不确定度修正的 Cpk，可选开关）

### v2.7.0 P3 收尾
- I-MR-R/BW 控制图 · 部分因子/田口设计 · Logistic 回归 · 残差诊断四图

### 验收标准
- 集成测试覆盖全部贯通链路（v2.8.0 五链 + 报告聚合）
- 全量 pytest 通过

---

## v3.0.0 — 稳定化里程碑（待开发）

> 主题：Info 收尾 + 全量回归 + 性能基线 + 里程碑发布。

### 内容
- Info 系列清零收尾（剩余项）+ 全量回归验证
- 性能基线与回归门禁：启动时间 / 大文件（10 万行级）导入耗时 / 内存占用峰值
- 双语文档同步（README / ROADMAP）+ 版本历史表归档
- PyInstaller + Inno Setup 安装器发布

### 验收标准
- C / W / Info 编号项全部清零
- 全量回归通过，测试数不低于 289 基线（只增不减）
- 性能基线达标并记录在案

---

## 3.0.0 后 Backlog（仅登记，不排期）

### 核心竞争力延伸（3.0.0 后评估启动）
- **AI 深化**：本地 LLM 从"对话助手"升级为"全分析解读引擎" — 每个分析结果自动生成工程解读、异常诊断建议、知识库联动（保持离线可审计）
- **硬件深化**：ESP32 设备直采 → 实时 SPC 闭环（采集→控制图→预警→COMMAND 反馈）、量具无线采集、更多传感器类型

### 搁置的旧规划项（2026-08-22 重规划决策）
- P2-3 视频时间研究（MediaPipe/OpenCV 姿态估计）
- P2-4 批量宏录制/回放
- P2-5 自定义控制图模板（注：v2.8.0 工作流贯通的"CP→SPC 预配置"覆盖其核心场景）
- P3-1 供应链质量协作 · P3-2 数字孪生布局仿真 · P3-3 REST API 服务 · P3-4 Web 前端 · P3-5 移动应用

---

## 侧边栏演进

> **注**：v2.6.5 ~ v3.0.0 重规划期**不新增 Tab**（聚焦现有功能深化），35 Tab + 插件结构保持不变。

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)   v2.6.5~3.0.0 (35)
 Home (0)       Same           Same             Same           Same
 Quality (1-6)  Same           Same             Same           Same
 IE (7-11,21-22) Same          +SMED(29)+TPM(31)  Same         Same
 Charts (12,18-20) Same        Same             Same           Same
 Eng (13-17)     Same         +8D(30)+PPAP(32)   Same           Same
 Worksheet (23-25) Same        Same             Same           Same
 Sampling (26)   Same          Same             Same           Same
 Report (27)     Same          Same             Same           Same
 Data (28)       Same          Same             Same           Same
 —               —             —                Live Monitor (33) Same
 —               —             —                Multi-Plant (34)   Same
 —               —             —                —                 Device (35)
 Plugins (dynamic) Same        Same             Same             Same
```

---

## 版本历史

| 日期 | 版本 | 内容 |
|------|---------|---------|
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
