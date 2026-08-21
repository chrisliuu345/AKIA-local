# QA-Tool 发展路线图

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> 当前: v2.6.1 + 代码审查修复 | 测试: 289 pytest · 44/45 冒烟 | 35 个 Tab + 插件 | 更新: 2026-08-19

---

## 版本总览

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ──→ v2.6.4 ──→ v2.6.5 ──→ v2.7.0 ──→ v2.7.5 ──→ v2.8.0 ──→ v2.8.5 ──→ v2.9.0 ──→ v2.9.5 ──→ v2.10.0
 Release   代码+AI    工程工具    报告      实时监控    UX+动画     硬件扩展    ESP32部署+    安全校验     RBAC+认证    统计引擎    UI健壮性    体验打磨    视频时间    宏录制      REST API   供应链      数字孪生    Web一期     Web二期
           (完成)    (完成)     (完成)    (完成)     (完成)     (完成)     设备监控Tab     (已完成)     +设备加固     加固        +报告+测试  +Info一期   时间研究   +Info二期   +Info三期   协作        布局仿真    看板/报告   +移动应用
                                                                           (已发布)                    (已完成)    (待开发)    (待开发)    (待开发)    (待开发)    (待开发)    (待开发)    (待开发)    (待开发)    (待开发)
```

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

## v2.6.3 — 统计引擎加固（待开发）

> 主题：统计正确性 — 质量工具的核心价值。修复全库代码审查发现的统计边界缺陷与常数表错误。

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

## v2.6.4 — UI 健壮性 + 报告安全 + 测试质量（待开发）

> 主题：剩余 UI 崩溃/正确性 + 输出安全 + 测试可信度。聚焦崩溃与契约一致性，低价值打磨项降级 P2。

### UI 崩溃与正确性
- 连接与线程：W41 _on_import_db 连接泄漏、W52 device_tab 后台线程改 QWidget、W53 closeEvent 未停 discovery
- 数据正确性：W42 USL/LSL=0 跳过、W43 compliance load_template、W55 doe 覆盖原始数据、W56 hypothesis factor2 可空、W57 msa part 列空、W58 fmea 先改后确认、W64 oee=None 崩溃、W65 ppap 单点虚假 Cp、W66 3P Weibull NaN、W67 sheet_split dtype、W70 vsm 除零
- 契约一致性：W59-W62 四个 Tab current_result 三件套 + 键名统一、W63 重建表清空备注
- 图表与交互：W48 base_tab plt.close 误关、W46 F5 全量冻结、W68 cellChanged 每键触发、W71 8D PDF 未转义

### 输出与报告
- W75 excel 无 try/finally 残缺文件、W80 word 图片溢出 A4

### 对话框
- W106 import_dialog nrows、W107 AnalyzeWorker 无 try/except、W108 conclusion 未转义、W109 root_cause KeyError、W110 batch _refresh_log O(n²)、W111 llm closeEvent 阻塞

### 测试质量
- W101 or True 恒真、W102 零断言、W103 mtime flaky、W104 import 期写文件、W105 time.time 全局替换

### IE/设备残留
- W83 tpm clamp、W84 work_sampling z_value、W86 co401 硬编码路径、W91 skewness 判定、W95 sheet_splitter 截断、W96 kpi_formula 嵌套幂

---

## v2.6.5 — 体验打磨 + Info 清零一期（待开发）

> 主题：清偿 v2.6.4 降级的 UI 打磨项 + 自定义图表模板 + 技术债第一批。原"长期积压 P2/P3"细化排期的第一个版本。

### P2-5 自定义控制图模板
- 控制图配置（规格线 / 颜色 / Nelson 规则集 / 图表样式）序列化为 JSON 模板
- 模板管理对话框：保存 / 加载 / 删除 / 重命名，user_config.json 持久化
- 控制图 Tab 一键应用模板

### P2-7 UI 打磨项（自 v2.6.4 降级，8 项）
- W49 全量填充阻塞、W50 Grubbs 标签、W51 均匀分布 μ、W69 trend 无抽样
- W72 sidebar 高度、W73 fishbone 迭代、W74 animate 清理、W99 esp32 buf（与 C04 重复，复核后关闭）

### P2-6 Info 清零一期（~50 项）
- 死代码清理 + 未使用 import（机械量大优先，工具辅助扫描 + 人工复核）

---

## v2.7.0 — 视频时间研究（待开发）

> 主题：P2-3 视频时间研究 — 帧级计时 + AI 动作识别。

### 核心功能
- 视频导入 → 抽帧 → Pose/Hands 关键点提取（OpenCV + MediaPipe）→ 动作分段（阈值 + 状态机）→ 工序节拍计时
- 新 Tab 36：时间轴 + 动作分段列表 + 节拍统计，与 time_study 数据互通
- 风险标注：MediaPipe 对 Python 3.14 兼容性未验证（官方支持通常滞后），备选方案 ONNX Runtime / OpenCV DNN
- 风险标注：PyInstaller 体积将显著增大（OpenCV 约 +60MB）

---

## v2.7.5 — 批量宏录制/回放 + Info 清零二期（待开发）

> 主题：P2-4 宏录制/回放 — 操作序列自动化。

### 核心功能
- 宏录制器：拦截关键 handler 记录 action + 参数 → JSON 宏脚本
- 宏管理对话框：保存 / 加载 / 编辑 / 删除
- 回放引擎：dry-run 预检 + 逐步确认模式；与 F5 批量分析整合

### P2-6 Info 清零二期（~50 项）
- 重复实现合并 + 单一数据源统一

---

## v2.8.0 — REST API 服务 + Info 清零三期（待开发）

> 主题：P3-3 REST API — 核心分析能力服务化，为供应链协作 / Web / 移动铺路（依赖链根节点）。

### 核心功能
- FastAPI 封装核心分析引擎：`/analyze/{tool}`（35 引擎）、`/kpi`、`/alerts`、`/devices`
- API Key 认证（复用 v2.6.2 RBAC 权限矩阵），OpenAPI 自动文档
- 架构决策（开发期确定）：桌面内嵌 uvicorn 线程（localhost）vs 独立 headless 进程
- 供 MES/ERP 系统消费

### P2-6 Info 清零三期（~51 项）
- i18n 一致性 + 魔法数字常量化 + 私有 API 替换

---

## v2.8.5 — 供应链质量协作（待开发）

> 主题：P3-1 供应链质量协作 — 复用 v2.8.0 REST API 层实现 P2P 数据共享。

### 核心功能
- 供应商数据包导出/导入（加密 JSON，密钥复用 DPAPI 密钥库）
- CPK 多层钻取：料号 → 批次 → 工序 → 参数
- 料号映射管理（自有料号 ↔ 供应商料号）
- 新增"供应链协作" Tab（索引 37）

---

## v2.9.0 — 数字孪生布局仿真（待开发）

> 主题：P3-2 数字孪生 — 2D 产线布局 + 离散事件仿真。

### 核心功能
- QGraphicsScene 2D 布局编辑器：工位 / 输送线 / 缓存区拖拽编排
- 工位属性绑定实数据（节拍 / 良率 / OEE，来源 KPI 提取器）
- 离散事件仿真：瓶颈识别 / 在制品堆积分析 / 改善前后对比
- 与 VSM / 产线平衡数据互通；新增 Tab（索引 38）

---

## v2.9.5 — Web 前端一期（待开发）

> 主题：P3-4 渐进式双端一期 — 看板与报告的 Web 只读视图（桌面端长期保留）。

### 核心功能
- React 脚手架（Vite + TypeScript），复用 REST API
- Web 看板：KPI 磁贴 + 图表轮播（对应桌面 display_mode）
- Web 报告查看：浏览已生成报告（PDF/HTML）
- 桌面内嵌静态文件服务（同端口提供 Web 资源）

---

## v2.10.0 — Web 二期 + 移动应用 + Info 收尾（待开发）

> 主题：P3-4 二期（分析交互）+ P3-5 移动应用 + P2-6 收尾。

### 核心功能
- Web 分析交互核心流程：选数据 → 跑分析 → 看结果（对应桌面主工作流）
- 移动应用（Flutter / React Native）：报告查看 + 预警推送（webhook / FCM），复用同一 REST API
- P2-6 剩余项清零 + 全量回归验证

---

## 原长期积压排期说明

> **注**: P2-1（低代码公式编辑器）与 P2-2（车间看板模式）已提前至 v2.4 E4（看板 UI 与控制增强）。
> 原"长期积压（P2/P3）"清单已全部分配至上述版本：P2-3→v2.7.0 · P2-4→v2.7.5 · P2-5/P2-7→v2.6.5 · P2-6 分三批贯穿 v2.6.5/v2.7.5/v2.8.0 + 收尾 v2.10.0 · P3-1→v2.8.5 · P3-2→v2.9.0 · P3-3→v2.8.0 · P3-4 一期→v2.9.5 二期→v2.10.0 · P3-5→v2.10.0。

---

## 侧边栏演进

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)
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
