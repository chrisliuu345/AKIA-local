# QA-Tool v2.6.1 全库代码审查报告

**审查日期**：2026-08-19
**审查基线**：v2.6.1 工作树（HEAD=`051d021`，git clean），约 204 个 .py 文件、3.2 万行
**审查方法**：8 组 `review` 子代理并行只读审查（G1-G8），覆盖 core/ui/tabs/dialogs/analysis/output/config/tests/firmware 全量代码；分级标准 Critical（必须修）/ Warning（应修）/ Info（建议）
**报告生成**：主模型整合 8 组结果，分级去重、按优先级排序

---

## 一、统计总览

| 组 | 范围 | 文件数 | Critical | Warning | Info |
|----|------|--------|----------|---------|------|
| G1 | core/（含 devices/） | 45 | 6 | 21 | 20 |
| G2 | ui/ 主文件 + widgets/ | 11 | 2 | 11 | 18 |
| G3 | ui/tabs/ 前半（分析类） | 18 | 1 | 14 | 24 |
| G4 | ui/tabs/ 后半（监控/设备/数据/报告） | 19 | 3 | 20 | 16 |
| G5 | ui/dialogs/ | 19 | 2 | 12 | 18 |
| G6 | analysis/ 统计引擎 | 38 | 1 | 20 | 20 |
| G7 | analysis/ie+quality+ai+charts + output/ + config/ + plugins/ + utils/ | 27 | 2 | 14 | 24 |
| G8 | tests/ + firmware/ | 26 | 2 | 9 | 11 |
| **合计** | — | **203** | **19** | **121** | **151** |

> 部分条目跨组重复（如 device_tab 跨线程操作 UI 在 G3/G4 均报，本报告去重后计入一次）。

---

## 二、P0 Critical 清单（必须修，功能/安全缺陷）

### C01 · `core/auth.py:174-177` — `update_user` 无角色白名单校验（提权路径）
`create_user`（:145）校验 role 合法性，但 `update_user` 没有。任何绕过 UI 的调用（代码/脚本）可直接把任意用户（含自己）提权为 `"admin"`。
**修复**：在 `update_user` 中复用 `create_user` 相同的 `role in _ROLE_PERMISSIONS` 校验，并拒绝越权提权。
**归属**：v2.6.2 RBAC 前置必修（RBAC 接线后此洞从"内部"扩大到"接口层"）。

### C02 · `core/auth.py:43-47` — `_verify_password` rounds 无上限（CPU DoS）
PBKDF2 迭代次数取自哈希串中攻击者可控的 `rounds`（`int(parts[2])`），用户文件被篡改为 `rounds=10**9` 时每次登录触发数十亿次哈希。
**修复**：clamp rounds 至合理上限（如 1_000_000），或校验 `rounds == _PBKDF2_ROUNDS` 不匹配即拒绝。

### C03 · `core/auth.py:122-127` — 用户文件损坏后系统锁死无恢复
`_load_users` 对 JSON 解析异常静默返回 `[]`，`_ensure_file` 仅在文件不存在时重建。文件损坏（断电/手编）时所有账号不可登录且无恢复路径。
**修复**：解析失败时备份损坏文件并重建默认 admin，或至少记录告警。

### C04 · `core/devices/transport.py:117` — 读线程 `_buf` 无界增长（内存耗尽）
设备数据流长时间不含 `\n`（波特率不匹配噪声/错误固件/二进制）时 `_buf` 无限增长，`protocol.py` 的 `MAX_LINE_LEN` 只对 `decode_message` 生效不对 `_buf`。
**修复**：`_buf` 超过 `MAX_LINE_LEN` 时丢弃并重置（滑窗保留尾部）。

### C05 · `core/devices/transport.py:127-130` — 回调异常导致读线程永久退出（设备离线无重连）
`except Exception` 同时兜底 `on_message` 回调异常：`monitor.py:101` 的 `device.add_data(msg.get("values",[]))` 在畸形 `values`（dict/str）时抛 `TypeError`，被捕获后 `break`，设备永久离线无重连。
**修复**：回调调用单独 try/except（与 `on_event` 一致），与串口 I/O 异常分离，I/O 错误保留重连。

### C06 · `core/batch_scheduler.py:138-142` — `_execute_task` 无 in-flight 检查（重复并发执行）
`once` 任务执行期间 `last_run` 为空、`enabled` 仍 True，执行耗时超过轮询周期（30s）时同一任务被重复启动并发执行，多 worker 写同一输出文件；hourly 同理。
**修复**：维护 `_running: set[str]`，启动前判重，`_on_task_finished` 中移除。

### C07 · `ui/widgets/fishbone_canvas.py:356,387` — 根分支 >12 时 IndexError 崩溃
`M6_COLORS[:n]`（n≤6）否则 `M6_COLORS * 2`（恒 12 项），n≥13 时 `colors[i]` 必然 IndexError，`render_fishbone` 抛异常导致鱼骨 Tab 无法渲染。
**修复**：`colors = M6_COLORS * (n // len(M6_COLORS) + 1)` 或循环取色。

### C08 · `ui/main_window.py:114` — `nav_buttons` 被 Tab 控件覆盖（v2.6.2 RBAC 踩雷）
`self.sidebar.nav_buttons[idx] = tab` 用 Tab 控件覆盖 `add_plugin_entry` 注册的按钮引用。当前无读取方无即时故障，但 v2.6.2 若按 `nav_buttons` 置灰会拿到 QWidget 而非 QPushButton。
**修复**：删除此行；插件按钮已由 `add_plugin_entry` 注册。

### C09 · `ui/tabs/monitor_tab.py:32,172` — `update_received` 信号未连接，实时监控刷新失效
`update_received = Signal(object)` 定义后从未 `.connect()`，后台线程 `FileMonitor(on_change=self.update_received.emit)` 发出的信号无接收者，`_on_update` 永不执行。只有启动时 `check_once()` + 直接调 `_on_update(initial)` 显示一次，**文件后续变化不刷新**，"实时监控"核心功能失效。
**修复**：`__init__`/`_setup_ui` 中加 `self.update_received.connect(self._on_update)`（跨线程信号自动 QueuedConnection）。

### C10 · `ui/tabs/pareto_tab.py:225` — 钻取后"还原全部数据"永久失效
`_on_item_clicked` 调 `self.set_data(filtered)`，重写的 `set_data`（:36）把 `self._full_df = df` 覆盖为过滤后子集；`_reset_data`（:228）再用 `_full_df` 还原时仍是过滤数据。
**修复**：`set_data` 仅在 `self._full_df is None` 时赋值，或钻取走独立过滤路径不经 `set_data`。

### C11 · `ui/tabs/multi_plant_tab.py:184` — `setSpan` 跨次运行残留
`QTableWidget.setRowCount()` 不清理旧 span；错误行 `setSpan(row,1,1,5)` 第二次运行行数变化后合并单元格错位。
**修复**：`_fill_table` 开头 `self.table.clearSpans()`。

### C12 · `ui/tabs/monitor_tab.py:269-280` — 实时刷新 matplotlib Figure 泄漏
`create_control_chart` 内部 `plt.subplots` 注册到 Gcf，`_render_figure` 仅 `deleteLater()` 旧 canvas 从不 `plt.close`；监控 1-2 秒/次更新，数小时累积数百个 figure。
**修复**：替换旧图前 `plt.close(self.current_figure)` 或 `plt.close("all")`。

### C13 · `ui/dialogs/user_management_dialog.py:165` — dept_admin 编辑同级 dept_admin 被静默降级
`_role_keys` 仅 `["analyst","readonly"]`，目标角色 `dept_admin` 不在其中时回退 `idx=0` 显示"分析师"，保存后 `update_user` 写入 `"analyst"`——同级管理员被越权降级，UI 无提示。
**修复**：编辑模式下目标角色不在白名单时禁用角色下拉框并回传原角色；dept_admin 编辑目标应限定为本部门 analyst/readonly。

### C14 · `ui/dialogs/user_management_dialog.py:186-195` — dept_admin 可对 admin 角色用户重置密码/删除
按钮可见条件只检查 `target.username != "admin"`（:191），未校验目标角色：admin 创建的第二个管理员（如 "supervisor"）出现在 dept_admin 部门列表时，dept_admin 可重置其密码或删除。
**修复**：非 admin 操作者一律禁止操作 `target.role == "admin"` 用户（按钮隐藏 + 后端双重校验）。

### C15 · `analysis/msa/gage_rr.py:45-46,51-52` — AV/PV 用错 d2 常数表（系统性高估 25%）
AV 与 PV 用 `CONTROL_CHART_CONSTANTS[d2]`（操作员数/零件数 → d2，n=2 时 1.128），但 AIAG MSA 手册要求用 **d2\* 表**（K2/K3 倒数）：n=2 时 d2*=1.41。导致 AV、PV 系统性高估约 25%，GRR%TV、NDC（`1.41*PV/GRR`）全部失真。
**修复**：AV 用 AIAG K2 表（2→0.7086, 3→0.5231, 4→0.4467, 5→0.4030），PV 用 K3 表；EV 用 d2(r) 正确，仅 AV/PV 有误。

### C16 · `analysis/charts/chart_generator.py:554-557` — 瀑布图累积基线错误
`bottom` 只在 `i > 0` 时累加，首根柱 v0 从未计入基线，从第二根柱起所有柱底与连接线整体下移 v0。柱间相对高度正确但绝对位置错误，v0 较大或为负时图形明显失真。
**修复**：`bottom += v` 改为每轮绘制前无条件累加（首柱 bottom=0+v0），同步调整连接线。

### C17 · `output/pdf_report.py:146,194,252` — 用户文本未转义进 `Paragraph`（XML 解析失败）
atype/title 含 `<`（如列名"温度<100"）、`&` 时 reportlab 解析 XML 标记抛异常，**整个 PDF 生成失败**。
**修复**：对插入 `Paragraph` 的用户数据先 `html.escape()`，P-value 拼接同样转义。

### C18 · `tests/run_all_tests.py:41` — 冒烟脚本依赖的 `公司仪器测试数据.xlsx` 缺失
该文件经全仓库递归搜索**不存在**，T06、T07、T42、T43 四个用例必然 FAIL，冒烟测试体系实际不可用。
**修复**：将 fixture 纳入仓库，或改为测试内置合成数据生成器（与 T01-T05 一致）。

### C19 · `firmware/esp32_out.py:118-143` — main() 无异常保护（单条畸形消息打死设备）
`esp32_in.py:162-193` 有 try/except 而本文件没有：USB 拔出时 `uart.write` 抛 OSError、`command` 字段非字符串（:135 `msg.get("command","")` 未校验类型 → :83 `":" not in command` 抛 TypeError）都会让设备静默死机。
**修复**：循环体包 try/except 并向 PC 输出 `ERR` 行（对齐 esp32_in），`run_command` 入口 `isinstance(command, str)` 校验。

---

## 三、P1 Warning 清单（应修，边界/健壮性/性能）

### 认证与安全
- W01 `core/auth.py:222` — `change_password` 内部调 `authenticate` 产生误导性 `login 成功` 审计。修复：提取 `_verify_credentials` 复用。
- W02 `core/auth.py:175` — `if k in kwargs and kwargs[k]` truthy 判断，空串无法清空 department/team/display_name。修复：用 `is not None`。
- W03 `core/auth.py:139/212` — `User(**u)` 解包 JSON，v2.6.2 新字段无默认值时旧文件 `TypeError` 崩溃。修复：新字段带默认值或 `from_dict` 兼容构造。
- W04 `core/audit.py:10-17` + `core/auth.py:16-20` — `_audit` 与公共 `audit()` 双实现不同步。修复：auth 内部改调 `core.audit.audit`，删除重复实现。
- W05 `core/audit.py:10-17` — 审计日志无轮转/大小上限，无限增长。修复：超 5MB 轮转归档。
- W06 `core/sql_loader.py:17-19` — 脱敏正则 `[^@\s/]+` 假设密码不含 `@`，含 `@` 时只打码首个 `@` 前片段。修复：URL 解码后整体打码或用 SQLAlchemy URL 解析。
- W07 `core/sql_loader.py:92-95` — 回退路径 `f'SELECT * FROM "{safe_name}"'` 双引号在 MySQL/SQL Server 跨方言语义不一致。修复：回退走 `pd.read_sql_table` 或方言化引用。
- W08 `core/project_manager.py:197` — 部门名无净化，`../..` 可写出共享目录。v2.6.2 部门维度扩大后风险升级。修复：校验 `os.path.basename(department) == department` 且白名单内。
- W09 `core/log_util.py:9-19` — `_logger` 单例缓存使 `name` 参数失效，所有模块共享第一个调用者 logger 名。修复：直接 `logging.getLogger(name)`。
- W10 `core/one_click_analyzer.py:326` — `_fallback_synthesis` 对 `grr_pct` 按 0-100 阈值判定，而 `kpi_extractor.py:74` 归一化为 0-1，量纲不一致致误判。修复：统一量纲约定。
- W11 `ui/dialogs/login_dialog.py:68` — 默认凭据 `admin/admin` 明文展示。修复：首次登录后移除提示。
- W12 `ui/dialogs/login_dialog.py:73-85` — 登录失败无次数限制/锁定/冷却。修复：连续失败 N 次锁定。
- W13 `ui/dialogs/user_management_dialog.py:112-113` — `reset_password` 返回值未检查，不合规密码仍弹"已重置"虚假成功。修复：检查返回值。
- W14 `ui/dialogs/user_management_dialog.py:96-99` — `create_user` 失败提示笼统（重名 vs 密码不合规混为一条）。修复：UI 层先校验密码并区分失败原因。
- W15 `ui/dialogs/db_connection_dialog.py:23-29` — DPAPI 异常时静默降级 base64（≈明文）写入 QSettings。修复：降级时警告用户或拒绝保存，仅保留 base64 读旧数据。
- W16 `output/compliance_report.py:56` — `load_template` 对 `template_id` 无校验，`../` 或绝对路径可逃逸模板目录读任意 JSON。修复：校验不含路径分隔符或 realpath 断言。
- W17 `output/excel_report.py:107-117,128,142-143,156,161` — Excel 公式注入：`=+-@` 开头字符串被当公式执行。修复：非数值字符串用 `write_string()` 或加 `'` 前缀。

### 统计正确性（数值边界）
- W18 `analysis/spc/_rules.py:95-100` — 规则 5（连续 3 点中 2 点超 2σ 同侧）实现要求**全部 3 点同侧**，标准规则只要求超 2σ 的两点同侧。如 [+2.2σ, −0.2σ, +2.2σ] 应判异但被漏报。修复：改为"超 2σ 的点中 ≥2 点同侧"。
- W19 `analysis/hypothesis/t_tests.py:99-100` — 配对检验先各自 `dropna()` 再按位置截断对齐，NaN 位置不一致时配对静默错位，t 统计量与结论全错。修复：按索引对齐后 dropna。
- W20 `analysis/hypothesis/nonparametric.py:30-32` — 同 W19，`clean_a[:n]`/`clean_b[:n]` 位置截断错位。修复：按索引对齐。
- W21 `analysis/hypothesis/normality.py:29` — `stats.normaltest` 要求 n≥8，此处 n≥3 即调用，n∈[3,7] 崩溃。修复：n<8 跳过。
- W22 `analysis/capability/normal_cap.py:88` — n≥2 允许但 `stats.shapiro` 要求 n≥3，n=2 崩溃。修复：n<3 跳过 shapiro。
- W23 `analysis/capability/normal_cap.py:41-49` — std=0 时返回 `inf`，0/0 得 NaN，`json.dumps` 抛异常 UI 无法序列化。修复：用 None 或大有限值。
- W24 `analysis/capability/non_normal_cap.py:64-74` — std_t=0 除零无保护（normal_cap 有保护）。修复：补 `if std_t > 0` 守卫。
- W25 `analysis/capability/between_within_cap.py:27,32` — 单观测子组 `groups.std(ddof=1)` 为 NaN 全链路 NaN。修复：子组 n=1 跳过。
- W26 `analysis/reliability/weibull.py:146` — 失效时间全部相等时 scipy 拟合退化，产出 β=0.2/η=1e-6 垃圾参数无告警。修复：try/except + eta>0 校验。
- W27 `analysis/reliability/alt.py:42-44` — 无最小样本校验，n=2 除零、n=1 linregress 抛异常。修复：入口校验 n≥3 且数值>0。
- W28 `analysis/reliability/alt.py:23,27` — 温度单位不对称：use_temp 自动 +273.15，stress_temp 不转换不校验，传摄氏度静默全错。修复：统一入口约定。
- W29 `analysis/spc/cusum.py:24-26` — 常数列 σ=0 → k_abs=h_abs=0，凡偏离 target 全判违规，满屏伪违规。修复：σ==0 返回稳定态。
- W30 `analysis/spc/p_chart.py:18,24` / `analysis/spc/u_chart.py:16,19,24` — 未校验 ss/u_sizes 为正，含 0 或负时 inf/NaN 静默污染。修复：入口校验 >0。
- W31 `analysis/spc/c_chart.py:18-19` — 未校验缺陷数非负，c̄<0 时 sqrt NaN。修复：校验非负整数。
- W32 `analysis/spc/ewma.py:26` — 初值用首观测，Montgomery/Minitab 以 μ0 起始，σ 大时首点误报。修复：`ewma[0] = mean`。
- W33 `analysis/spc/xbar_s.py:23` — `s[s==0]=1e-10` 魔法数掩盖零标准差，污染 s̄。修复：剔除并告警。
- W34 `analysis/hypothesis/anova.py:39,43` — 单观测组过滤后 df/SS 自相矛盾（grand mean/df 仍含被过滤行）。修复：统一基于过滤集计算。
- W35 `analysis/doe/factorial.py:45-47` — 非 ±1 编码（实际水平值/中心点 0）时 mask 空 → NaN 静默。修复：校验或按 >0/<0 分组。
- W36 `analysis/doe/doe_analysis.py:55` — `stats.shapiro(residuals)` 无下限，N<3 崩溃。修复：`len>=3` 才调用。
- W37 `analysis/reliability/weibull.py:83` — censored 长度不匹配时 IndexError 无校验。修复：入口校验等长。
- W38 `analysis/charts/chart_generator.py` 见 C16。
- W39 `core/sampling_engine.py:16-32` — `_NORMAL_TABLE` 除 A/B 外字码 Ac-Re 列表 20 项而 `_AQL_VALS` 21 项，最后一个 AQL（100）永远落入兜底且中段错位风险，抽样判定可能错误放行/误收。修复：对照 GB/T 2828.1 表 2-A 逐码核对补全。

### UI 正确性与契约
- W40 `ui/main_window.py:108-114,1014-1025` — 插件 Tab 双实例化：`__init__` 急切 `create_tab()` + 首次导航 `_lazy_load_tab` 又 `create_tab()`，旧实例 removeWidget 后不 deleteLater，`create_tab()` 有副作用（定时器/线程/监控）会重复启动。修复：init 不创建实例只占位，统一懒加载。
- W41 `ui/main_window.py:646-649,675-680` — `_on_import_db` 仅成功路径 disconnect，`load()` 抛异常时连接泄漏。修复：try/finally disconnect。
- W42 `ui/main_window.py:1681-1684,1696-1699` — `_apply_diagnosis` 用 `if params.get("usl")` 真值判断，USL/LSL=0（合法规格限）被静默跳过；`_on_load_session`(:1410) 与 `_apply_template_to_tab`(:858) 已用 `is not None`，三处不一致。修复：统一 `is not None`。
- W43 `ui/main_window.py:1162-1188` — `_on_export_compliance` 中 `load_template`/`t.get` 在 try 之外，模板 id 失效时异常冒泡到 Qt 槽无提示。修复：移入 try 或先判 None。
- W44 `ui/main_window.py:1476-1512` — `refresh_menu_for_user` 靠菜单标题文本匹配定位插入点，语言切换后文本不匹配。修复：构建时 QAction 存实例属性，刷新只 enable/disable。
- W45 `ui/main_window.py:167,1071,107,173` — 硬编码 35/36 共 4 处，与 `_tab_registry.TAB_COUNT`（全库无消费方）脱节，"单一数据源"不成立。修复：改用 `len(TAB_REGISTRY)`。
- W46 `ui/main_window.py:973-1006` — `_on_run_all_analyses`（F5）UI 线程同步全量加载 35 Tab 逐个 run，大数据冻结分钟级；无 `current_result` 的 Tab 也计成功。修复：结果为空不计成功，考虑 QThreadPool/QTimer 分片。
- W47 `ui/main_window.py:1748-1757` — `_load_and_route`（拖拽导入）唯一无 audit 的导入路径，失败仅状态栏无日志无提示。修复：补 audit + 异常反馈。
- W48 `ui/tabs/base_tab.py:42-43` — `_clear_canvas()` 调 `plt.close("all")` 关闭全局所有 figure，误关其它 Tab 持有的图。修复：仅关闭本布局内 canvas 持有的 figure。
- W49 `ui/tabs/base_tab.py:113-122` — `_populate_preview_table` 默认全量填充，10 万行逐 cell setItem 阻塞 UI。修复：默认限 500 行。
- W50 `ui/tabs/data_tools_tab.py:129-133` — Grubbs 检验仅最大值方向且标错行（`outliers.iloc[-1]` 标最后位置非最大值行）。修复：max/min 分别算 G，用 `idxmax/idxmin`。
- W51 `ui/tabs/data_tools_tab.py:60` — 均匀分布 μ 负值时 high<low 抛 ValueError 无 try。修复：校验参数非负。
- W52 `ui/tabs/device_tab.py:418-426` — `_on_refresh` 后台线程直接 `refresh_btn.setEnabled/setText`（跨线程改 QWidget）。修复：经信号回传。
- W53 `ui/tabs/device_tab.py:594-597` — `closeEvent` 停 monitor/registry 但未停 discovery 线程，daemon 继续 emit 信号触发 "wrapped C/C++ object deleted"。修复：`_discovery_running = False`。
- W54 `ui/tabs/device_tab.py:197-212` — `esp32_extension` 门控缺失：`_tab_registry` 无条件注册 DeviceTab，Tab 内未检查设置，关闭硬件拓展后设备发现仍执行。修复：注册或 `__init__` 处门控。
- W55 `ui/tabs/doe_tab.py:246-247` — 生成 2^k 设计矩阵 `self.df = design_df` 覆盖用户原始数据。修复：design 仅存 result。
- W56 `ui/tabs/hypothesis_tab.py:217-223,275` — 双因素 ANOVA factor2 可空 → `anova.two_way(df,col1,factor,"")`。修复：强制校验 factor2 非空。
- W57 `ui/tabs/msa_tab.py:209-216,264-265` — 线性分析 part 列空不拦截。修复：把"线性"加入强制 part 分支。
- W58 `ui/tabs/fmea_tab.py:97-102` — `_on_mode_changed` 先改 `_mode` 再弹确认，用户选"否"后 combo 已切但数据旧。修复：确认通过后再赋值，拒绝回滚 combo。
- W59 `ui/tabs/cap_comparison_tab.py:155-194` — `_run` 未写 `current_result`，三件套缺失致导出/dashboard 取空。修复：补三件套。
- W60 `ui/tabs/time_study_tab.py:206-207` — 引擎无异常兜底；`current_result` 键名不一致（引擎返回 `results` 复数而非 `result`）。修复：try/except + 包装三件套。
- W61 `ui/tabs/work_sampling_tab.py:311` — 同 W60 契约问题。修复：包装后赋值。
- W62 `ui/tabs/std_work_combo_tab.py:70-111` + `worker_machine_tab.py:75-116` + `summaries_panel_tab.py` + `trend_tab.py` — 只 `emit()` 不写 `current_result`，违反基类契约。修复：补三件套。
- W63 `ui/tabs/work_sampling_tab.py:281-295` — `_rebuild_obs_rows` 重建全表时备注列写空串，已输入备注被清空。修复：保留第 2 列既有文本。
- W64 `ui/tabs/oee_tab.py:228-229` — `oee=None` 时 `f"{oee:.1%}"` TypeError 崩溃（其它三个 KPI 有 isinstance 保护）。修复：统一 None 防护。
- W65 `ui/tabs/ppap_tab.py:142-144` — 单点样本硬编码 `sigma=0.001` 产虚假大 Cp/Cpk（100+）。修复：<2 标注"数据不足"。
- W66 `ui/tabs/reliability_tab.py:316-319` — 3P Weibull 时 `t_range` 起点 `min*0.5` 可能 <gamma，`z**beta`（非整数）产 NaN 曲线断裂。修复：起点改 `max(min*0.5, gamma)`。
- W67 `ui/tabs/sheet_split_tab.py:41` — `dtype=str` 全列读字符串，拆分后数值列变文本。修复：去掉 dtype=str。
- W68 `ui/tabs/std_work_combo_tab.py:67-68` + `worker_machine_tab.py:72-73` — `cellChanged` 每键触发完整 `_run`（重建图+emit），输入工序名逐字符重绘。修复：col==0 防抖 300ms。
- W69 `ui/tabs/trend_tab.py:134` — 大数据全量绘制无抽样，n=1 万行图宽 200 英寸。修复：等距抽样。
- W70 `ui/tabs/vsm_tab.py:252` — `steps` 为空时除零。修复：n==0 提前 return。
- W71 `ui/tabs/eight_d_tab.py:239-245` — PDF 导出 `str(step.__dict__)` 直接塞 `Paragraph`，含 `<`/`&` 时解析异常。修复：`xml.sax.saxutils.escape`。
- W72 `ui/sidebar.py:289-303` — 语言切换后不重算 `_expanded_height`，长文本分组裁切。修复：刷新路径重算。
- W73 `ui/widgets/fishbone_canvas.py:486-493` — `for c in self._causes` 迭代中 `remove`，删中途元素跳项 + 脏引用。修复：先收集待删再移除。
- W74 `ui/widgets/animate.py:14-15,74-75` — `_ACTIVE` 以 `id(stack)` 为键无清理钩子，stack 销毁后条目永久滞留。修复：connect destroyed 信号清理或 WeakKeyDictionary。

### 输出与报告
- W75 `output/excel_report.py:20-36` — `generate()` 无 try/finally，中途抛异常 `wb.close()` 不执行产出残缺文件。修复：try/finally。
- W76 `output/chart_engine.py:396,468` — `create_capability_chart`/`create_histogram` 空数据崩溃（`bins=0`/`min([])`)。修复：入口判空返回占位图。
- W77 `output/chart_engine.py:445` — `create_pareto_chart` 全零值 `sum==0` 除零 NaN。修复：sum==0 跳过百分比曲线。
- W78 `output/chart_engine.py:483-487` — `figure_to_bytes` 不 `plt.close(fig)`，批量导出循环每个 figure 泄漏。修复：末尾 close。
- W79 `output/chart_engine.py:375,408` — `griddata(method="cubic")` 重复坐标抛 QhullError。修复：drop_duplicates 或降级 linear。
- W80 `output/word_report.py:102` — 图片 `Inches(CHART_FIGSIZE[0])`=10 英寸溢出 A4。修复：`Cm(16)` 固定页内宽度。
- W81 `output/pdf_report.py:252` — `p_value` 非数值时 `:.4f` 抛异常。修复：float 转换失败回落原值。
- W82 `analysis/ie/smed.py:47,55,57` — `improved_time == 0` 无法表达"改善为 0 秒"（当未设置回退原时间），SMED 典型"作业消除"场景算错。修复：用 None 哨兵区分。
- W83 `analysis/ie/tpm.py:45` — `quality_rate` 未 clamp，good>total 时良品率>100% OEE>1。修复：`min(good/total,1.0)`。
- W84 `analysis/ie/work_sampling.py:21-26` — `_z_value` 对 confidence<0.90 静默返回 1.645。修复：补档位或抛 ValueError。
- W85 `analysis/ie/time_study.py:69` — kstest std=0 除零 NaN。修复：std==0 跳过。
- W86 `utils/co401_analysis.py:5` + `utils/co401_round2.py:5` — 硬编码 `sys.path.insert(0, r"D:\AI-agent\projects\ie-quality-analyzer")` 指向旧项目目录。修复：相对本仓库路径。

### 设备与固件
- W87 `core/devices/discovery.py:27` — 每端口强制串行扫描 ≥4s，多串口机器发现耗时 80s+ 阻塞 UI。修复：限制端口数或后台扫描可取消。
- W88 `core/devices/monitor.py:47-48` — `stop()` join(3) 超时后 detach 读线程仍运行。修复：确认读线程退出或允许重试。
- W89 `core/devices/registry.py:71-88` — `save_persistent` 读改写 user_config.json 无锁，多实例并发丢数据。修复：原子写+锁。
- W90 `core/data_profiler.py:228-230` — `iloc[0]` 无空值兜底，规格列全文本/全空时 `IndexError` 崩 profile()。修复：dropna 后判空。
- W91 `core/data_profiler.py:403` — "skewness 差值<0.1"判列间高相关错误（偏度相近≠相关）。修复：用 `df[cols].corr()`。
- W92 `core/data_validator.py:126-128` — n>5000 时 kstest 在 std≈0 时退化。修复：复用 std 守卫跳过。
- W93 `core/context_builder.py:38` — `acceptance` 非 dict 时 `AttributeError`，LLM 对话构建崩溃。修复：isinstance 检查。
- W94 `core/batch_scheduler.py:126-129` — daily 30s 窗口与默认 30s 轮询周期相等，抖动即错过。修复：窗口放宽 ≥2×interval。
- W95 `core/sheet_splitter.py:15` — 列值截断 `[:50]` 后同名覆盖丢数据。修复：追加哈希后缀。
- W96 `core/kpi_formula.py:70` — `evaluate` 双 `ast.parse`；嵌套幂（500 字符内可达 70 层）MemoryError。修复：缓存 parse + Pow 深度/指数上限。
- W97 `firmware/esp32_in.py:138-139` — DS18B20 `sleep_ms(750)` 同步阻塞，ping/hello 响应最长停顿 750ms。修复：两阶段采集。
- W98 `firmware/esp32_in.py:69-94` — adc/digital 通道初始化失败整体崩溃。修复：逐通道 try/except 跳过。
- W99 `firmware/esp32_in.py:160-168` + `esp32_out.py:117-124` — 接收 buf 无上限，噪声字节流耗尽堆内存。修复：限制上限截断丢弃。
- W100 `firmware/esp32_in.py:185` — `time.time()` 无 RTC 同步，PC 端按 Unix epoch 解析错位。修复：协议明确 timestamp 语义。

### 测试质量
- W101 `tests/test_v2_1.py:96-97` — `assert "NotImplementedError" in ... or True` 恒真，A1-13 回归形同虚设。修复：删 `or True`。
- W102 `tests/test_v2_1.py:166-173` — `try/except: pass` 零断言，任何异常都算通过。修复：断言确定行为。
- W103 `tests/test_monitor.py:83-95` — 依赖真实 mtime + sleep(0.6) flaky。修复：缩短 interval + deadline 轮询。
- W104 `tests/test_integration.py:93` — import 期写残留文件 `_tmp_test_report.xlsx` 且无 test_* 函数，collection error 拖垮 pytest。修复：改正式 pytest 函数 + tmp_path。
- W105 `tests/test_devices.py:85-90` — 裸赋值 `time.time` 全局替换（非 monkeypatch），与 xdist 互踩。修复：`monkeypatch.setattr`。

### 对话框
- W106 `ui/dialogs/import_dialog.py:155` — `xl.parse(s, nrows=0)` 恒 0 行，"估算总行数"永远 0。修复：用 `ws.max_row` 或删除。
- W107 `ui/dialogs/one_click_dialog.py:26-31` — `AnalyzeWorker.run` 无 try/except，异常时 QThread 静默终止 finished 永不发出，UI 永久卡"分析中"。修复：整体 try/except emit error。
- W108 `ui/dialogs/one_click_dialog.py:261` — `conclusion.replace("\n","<br>")` 未 HTML 转义，含 `<` 破坏渲染/注入。修复：`html.escape` 后 replace。
- W109 `ui/dialogs/root_cause_dialog.py:198` — `self.df[cols]` 列不存在 KeyError + `_run_analysis` 无 except，对话框构造崩溃。修复：except 兜底 + 列过滤。
- W110 `ui/dialogs/batch_dialog.py:232-235` — `_refresh_log` 每 2s 全量 split + `not in` 检查 O(n²)。修复：游标追加。
- W111 `ui/dialogs/llm_dialog.py:466-470` — closeEvent `wait(3000)` 失败后 `terminate()`，阻塞 4s + 解释器状态损坏风险。修复：协作式停止 + 非阻塞。

---

## 四、P2 Info 清单（建议，可读性/一致性，精简）

> 共 151 项，此处列代表性条目，完整清单见各子代理原始输出。

- `core/auth.py:47` — `dk == expected` 非恒定时间比较，建议 `hmac.compare_digest`。
- `core/auth.py:143-167` — `create_user` 密码失败与重名均返回 None，调用方只能笼统提示。
- `core/secret_store.py:75-86` — `decrypt_secret` 吞异常返回 ""，凭据损坏与未设置无法区分。
- `core/sql_loader.py:47` — mssql driver 硬编码 ODBC Driver 17，仅装 Driver 18 时失败。
- `core/data_loader.py:82` — `load_chunked = load_head` 别名误导。
- `core/data_parser.py:233` — `type_key.replace("_col","")` 无效操作死代码。
- `core/data_objects.py:110-115` — `if d[k] is None: d[k] = None` 死代码。
- `core/session_manager.py:21` — 秒级时间戳 session_id，同秒创建互相覆盖。
- `core/plugin_manager.py:54` — `isinstance(p, IPlugin)` 拒绝鸭子类型插件。
- `ui/main_window.py:299-349` — "分析"菜单缺 Tab 35（device），且是 Tab 清单第 3 份平行副本。
- `ui/main_window.py:1084-1096` — `_collect_charts` 永久改 Tab 内图表尺寸并重绘。
- `ui/welcome_page.py:237-244` — `hasattr(parent,'_load_project_by_path')` 直插父窗口私有方法，破坏封装。
- `ui/tabs/chart_tab.py:300` — `options["dark_mode"]=True` 硬编码不随主题切换。
- `ui/tabs/msa_tab.py:190-191` — `measure_col` 填全部列而非仅数值列。
- `ui/tabs/line_balance_tab.py:135-136` — `set_raw_data` 覆写为 pass，导入数据静默丢弃。
- `ui/tabs/fmea_tab.py:145-154` — S/O/D clamp 不回写单元格，显示 11 而 RPN 用 10。
- `analysis/hypothesis/variance_tests.py` — 与 `normality.py:56-93` `variance_test` 完全重复实现。
- `analysis/regression/linear_regression.py:50,67` — p 值序列化为字符串，与全库 float 约定不一致。
- `analysis/reliability/mtbf.py:145` — `mean_ratio` 死代码。
- `analysis/reliability/alt.py:14` — `activation_energy` 参数声明后从未使用（Ea 由回归拟合）。
- `output/compliance_report.py:63-85` — 模板 sections 仅用于筛选分析项，正文占位符未参与渲染。
- `output/chart_engine.py:27` — 用 matplotlib 私有 API `_load_fontmanager`，跨版本可能失效。
- `config/settings.py:120-144` — `save_config` 更新模块常量而 `load_config` 不重放，双通道状态漂移。
- `tests/pytest.ini:8-9` — slow/gui marker 声明但全仓无用例使用，死配置。
- `firmware/esp32_out.py:86` — value 做 strip 而 name 未 strip，"led :on" 误报 unknown。

---

## 五、v2.6.2 RBAC 专项风险点

RBAC 接线（让 `_ROLE_PERMISSIONS` 真正生效）是 v2.6.2 核心，审查发现以下必须先行处理或同步处理的风险点：

### RBAC 前置必修（接线前必须封堵）
1. **C01 `auth.py:174-177` update_user 提权** — RBAC 接线后此洞从"内部"扩大到"接口层"，必须先封堵。
2. **C13/C14 `user_management_dialog.py` 同级降级 + 越权操作 admin 用户** — 两处直接破坏 RBAC 权限模型的 Critical，必须修复。
3. **C08 `main_window.py:114` nav_buttons 污染** — RBAC 若按 nav_buttons 置灰会拿到 QWidget 而非 QPushButton，必须先清。

### RBAC 接线要点（审查发现的多旁路问题）
4. **"菜单置灰即可"是错觉** — `_switch_tab`（:471-509，所有导航唯一漏斗）、handler 入口（`_on_import_quality` 等 9 个）、拖拽导入（`:1748-1757`）、快捷键（Ctrl+O/F5/F11/Ctrl+Shift+S 等 7 个）、welcome 卡片（信号直连 handler）**五条旁路**全部绕过菜单，权限校验必须收敛在 handler 入口与 `_switch_tab` 单点，并加拒绝审计。
5. **`refresh_menu_for_user` 靠文本匹配定位**（:1476-1512）— 语言切换后失效，且当前仅管用户管理菜单。RBAC 扩展时建议：构建时给 QAction 挂 `setProperty("rbac_action",...)` + 存实例引用，按角色矩阵统一 enable/disable。
6. **`_lazy_load_tab` 角色切换后缓存失效** — 已缓存 Tab 不会重新校验；插件路径双实例化（W40）放大权限泄漏面。
7. **sidebar 在登录前构建** — CATEGORIES/CategoryGroup 在 `current_user=None` 时构建仅按 `tab_allowed` 过滤，无角色概念；`_rebuild_history` 的 `navigation_changed` 可直接切无权限 Tab，属绕过点。
8. **两套权限模型并行** — `_ROLE_PERMISSIONS`（死代码）与 `User.can_manage_users`（:76）+ `SharedProjectManager.list_shared` 的 `role=="admin"`（project_manager.py:216）三套语义，需统一入口，否则 dept_admin 在矩阵中无 `settings` 权限但 UI 设置对话框对 dept_admin 可见可改。
9. **`readonly` 含 `export` 权限**（auth.py:94）— 需产品确认是否符合"只读"语义。
10. **audit 现状全部为成功后记录** — RBAC 需增加"权限拒绝"审计事件；项目/会话加载路径无 audit（:1190-1213/:1297-1360），建议随 RBAC 补全。
11. **`delete_user` 仅保护 admin 用户名**（auth.py:198-201）— dept_admin 可删除本部门其他 dept_admin；后端无归属校验（纵深防御缺失）。RBAC 需定义 dept_admin 能否管理同角色用户。
12. **User dataclass 无 disabled/password_expired/last_login 字段**（:52-79）— v2.6.2 如需账号禁用/密码过期，新增字段必须带默认值（`User(**u)` 解包旧 JSON 会 TypeError，见 W03）。
13. **认证加固依赖** — RBAC 部署后 `authenticate` 无失败计数/锁定（C 级风险，登录入口无暴力破解防护），底层已有 `_audit("login_failed")` 可扩展。

---

## 六、测试覆盖率盲区

现有 282 个测试的覆盖盲区（v2.6.2 应补）：

| 模块/功能 | 现状 | 建议 |
|-----------|------|------|
| `core/auth.py` RBAC 权限判定 | 仅 hash 往返 + 角色结构 + 审计日志；权限检查函数与 UI 门控执行路径无测试 | 补 require_permission/角色拒绝场景（test_rbac_ui.py） |
| `ui/main_window.py` handler 层 | 仅 2 个纯函数（_tab_has_data/_tab_is_runnable） | 补懒加载 + 数据流（分析完成→结果注册） |
| `output/` 报告引擎 | pdf_report 零用例，excel_report 仅冒烟（且 xlsx 缺失），chart_engine 仅 waterfall | 补 excel/pdf 生成与图嵌入 |
| `config/settings.py` 持久化 | 仅操作内存 _user_overrides | 补 user_config.json save/load/损坏恢复/schema 迁移 |
| `ui/tabs/` 34 个 Tab | 仅 5 个有测试（monitor/multi_plant/dashboard/smed/display_mode） | spc/capability/fmea/tpm/trend/8D/鱼骨/PPAP/抽样/合并/拆分/工时/OEE/VSM/device_tab 均无 |
| `core/` 业务模块 | plugin_manager/project_manager/one_click_analyzer/context_builder/audit/report_templates/excel_utils/log_util/knowledge_base 无覆盖 | 补核心模块 |
| 设备命令链路 | Esp32OutputDevice command 编码/发送/ack 解析无测试（test_devices.py:228 空断言） | 补 PC 侧命令链路 |
| i18n | 仅校验 zh.json 4 个 key | 补全量 key 一致性 + 切换行为 |

---

## 七、修复优先级建议

### P0 — v2.6.2 开工前必修（19 项 Critical）
- **认证安全（4 项）**：C01 update_user 提权、C02 rounds DoS、C03 文件损坏锁死、C13/C14 用户管理对话框越权
- **功能缺陷（8 项）**：C09 monitor 信号未连接、C10 pareto 钻取还原、C11 multi_plant span 残留、C12 monitor figure 泄漏、C15 Gage R&R 常数表、C16 瀑布图基线、C17 PDF 转义、C07 鱼骨 >12 分支
- **设备/固件（3 项）**：C04 transport buf 无界、C05 回调异常断连、C19 esp32_out 无异常保护
- **调度（1 项）**：C06 batch 重复执行
- **RBAC 前置（1 项）**：C08 nav_buttons 污染
- **测试（1 项）**：C18 冒烟数据缺失

### P1 — v2.6.2 期间逐步修（W01-W111，按模块分批）
- **统计边界（W18-W39）**：配对错位、规则 5 漏报、shapiro/normaltest 下限、std=0/inf/NaN 序列化、采样表错位 — 建议与 v2.6.2 并行做一轮"统计引擎边界加固"
- **RBAC 同步（W40-W47）**：插件双实例化、DB 连接泄漏、USL/LSL=0、菜单文本匹配、硬编码 35/36、拖拽无 audit — 与 RBAC 接线同步修
- **契约一致性（W59-W62）**：4 个 Tab 缺 current_result 三件套 + 2 个键名不一致 — RBAC 后台化时一并修
- **输出安全（W75-W81）**：Excel 公式注入、资源泄漏、空数据崩溃、图片溢出
- **设备/固件（W87-W100）**：discovery 阻塞、user_config 无锁、固件 buf 上限
- **测试质量（W101-W105）**：恒真断言、零断言、flaky、残留文件

### P2 — 长期优化（151 项 Info）
- 重复实现合并（variance_tests/normality、audit 双实现）
- 死代码清理
- i18n 一致性（welcome 硬编码中文）
- 魔法数字常量化
- 私有 API 替换（chart_engine matplotlib 私有 API）
- 单一数据源（TAB_REGISTRY 消费、角色映射统一）

---

## 八、结论

**总体评价：需修改后合并。**

QA-Tool v2.6.1 架构清晰（Qt-free 业务层、统一日志/审计入口、AST 白名单公式引擎、模块化 Tab 注册），v2.6.1 新增的密码策略/密钥库/审计方向正确。但全库审查发现 **19 项 Critical** 需在 v2.6.2 开工前修复：

1. **认证安全是首要**：`update_user` 提权路径（C01）+ 用户管理对话框两处越权（C13/C14）直接破坏 RBAC 权限模型，必须在 RBAC 接线前封堵；`rounds` DoS（C02）与文件损坏锁死（C03）影响可用性。
2. **统计正确性有系统性缺陷**：Gage R&R AV/PV 常数表错误（C15）导致 %GRR/NDC 系统性失真（高估 25%），配对检验位置截断错位（W19/W20）静默产出错误统计结论 — 建议做一轮统计引擎边界加固。
3. **设备框架健壮性集中在线程边界**：transport buf 无界（C04）+ 回调异常断连（C05）+ esp32_out 无异常保护（C19）。
4. **功能缺陷**：monitor 信号未连接（C09）致实时监控失效、pareto 钻取还原失效（C10）、PDF 未转义（C17）致生成崩溃。
5. **RBAC 接线最大风险是"菜单置灰即可"的错觉** — `_switch_tab`/handler/拖拽/快捷键/welcome 五条旁路必须统一门控，且 nav_buttons 污染（C08）需在 RBAC 消费前清除。

建议修复顺序：P0 认证安全 4 项 → P0 功能缺陷 8 项 → P0 设备/固件 3 项 → P0 调度/测试 2 项 → P0 RBAC 前置 1 项 → 启动 v2.6.2 RBAC 接线 → P1 统计边界加固与契约一致性同步推进 → P2 长期优化。

---

*报告结束。修复决策等待用户逐项确认。*
