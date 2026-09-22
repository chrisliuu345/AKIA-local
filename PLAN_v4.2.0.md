# QA-Tool v4.2.0 开发方案（执行版）

> 依据 `ROADMAP.md`「v4.2.0 — 算法可信度与深度」，把 P2–P6 拆成可直接排期的任务：
> 每项含**落点文件 / 验收方式 / 风险**。本文只描述执行路径，版本语义与设计决策仍以路线图为准。

**基线（2026-09-22 实测）**：144 个测试文件 / 1798 用例全绿（逐文件单进程执行）；ruff 全库零告警；
性能基线通过（冷启动 2.08s · 百万行导入 14.2s · 5k 图渲染 1.27s · 5k 行 ML 1.41s）；
Linux 发布形态为 **AppImage 单一格式**。

---

## 1. 现状盘点（P0–P6）

| 阶段 | 状态 | 证据 / 缺口 |
|------|------|-------------|
| **P0 契约基座** | ✅ 已交付 | `core/evidence.py`（`pd-hash-v1` 数据指纹 · 凭证 diff）· `core/improvement_case.py` · `.qap` 1.7 案例段 · `KNOWN_VALUES.md` |
| **P1 已知值矩阵** | ✅ 已交付 | `tests/known_values.py` 框架 + 13 个 `test_known_values_*.py`（SPC/能力/MSA/DOE/可靠性/时序/ML） |
| **P2 算法深度** | ❌ 未开工 | `analysis/spc/` 有 `hotelling.py`，**无 MEWMA / 广义方差 / 变点检测 / 自相关残差图**；`analysis/capability/non_normal_cap.py` 只有 percentile + Johnson，**无 Bootstrap 区间**；`analysis/time_series/arima.py::_auto_select` 已存在，需稳健性补强 |
| **P3 稳定性与大样本** | ❌ 未开工 | `tools/perf_baseline.json` 仅 4 项指标，无 10 万 / 100 万行档；无病态矩阵与极端值专项用例 |
| **P4 判定凭证接线** | ❌ 未开工 | `credential` 在 `core/evidence.py` 之外**零引用**——分析记录、报告、`.qap` 均未写入凭证 |
| **P5 闭环切片** | ❌ 未开工 | `ImprovementCase` 仅有 schema；Home（`ui/welcome_page.py`，已有卡片 + 最近项目）可直接复用为入口 |
| **P6 收尾** | ❌ 未开工 | — |

---

## 2. 任务分解

### P2 算法深度（≈1.5 周，只碰 `analysis/` + `tests/`）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P2-1 | **MEWMA 多元指数加权移动平均图** | 新增 `analysis/spc/mewma.py`（结构对齐 `hotelling.py`，判异复用 `_rules.py`） | 新增 `tests/test_known_values_spc_mewma.py`：NIST/文献已知值 ±1e-6；与 statsmodels 参考实现交叉验证（测试期可选依赖） |
| P2-2 | **广义方差控制图** | 新增 `analysis/spc/gen_var.py` | 已知值用例 + 与 `hotelling.py` 共用协方差估计路径 |
| P2-3 | **变点检测 PELT（纯 numpy）** | 新增 `analysis/spc/change_point.py` | 合成变点数据检出率 ≥95%、误报 ≤5%；超期则降级为二分分割 |
| P2-4 | **自相关残差控制图** | 新增 `analysis/spc/residual_chart.py`（ARIMA 残差 → I-MR） | 自相关数据上误报率显著低于裸 I-MR（对照用例） |
| P2-5 | **非正态能力 Bootstrap 置信区间** | 扩展 `analysis/capability/non_normal_cap.py` | 区间覆盖率蒙特卡洛检验（≥90% @95% CI）；固定随机种子保证可复现 |
| P2-6 | **可靠性区间补强** | `analysis/reliability/weibull.py`（已有 Fisher 信息 CI）→ 补 KM/Cox ALT/RBD 区间 | 与 `lifelines` 参考值交叉验证（测试期） |
| P2-7 | **ARIMA 自动选阶稳健性** | `analysis/time_series/arima.py` | 差分/季节场景不崩；候选网格失败可回退；已知值用例沿用 |

**P2 出口标准**：每个新算法都有 known-value 用例文件；`ruff` 零告警；全量逐文件回归全绿。

### P3 稳定性与大样本（≈1 周，可与 P2 并行）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P3-1 | 大样本基准扩展（10 万 / 100 万行 SPC·MSA·ML） | `tools/benchmark.py` + `perf_baseline.json` | 新指标入 CI（tolerance ×4）；单次运行不触发内存峰值（子进程隔离 + 线程上限） |
| P3-2 | 病态矩阵与极端值鲁棒性用例 | 新增 `tests/test_robustness_numeric.py` | 多重共线 / 常量列 / 全零 / NaN·Inf / 单点 / 重复值均返回结构化错误或降级结果，不抛未捕获异常 |
| P3-3 | **质量棘轮**：`BLE001`（盲除异常）纳入门禁 | `ruff.toml`（非 UI 范围 111 处，逐处 `# noqa: BLE001 + 理由` 或收窄异常类型） | `ruff check .` 零告警保持；CI 门禁不外溢到 `ui/`、`tests/` |
| P3-4 | 覆盖率补口 | 新增用例：`core/excel_utils.py` · `core/session_manager.py` · `core/audit.py` · `output/base_report_engine.py` · `analysis/capability/between_within_cap.py` · `analysis/hypothesis/variance_tests.py` · `analysis/quality/eight_d_engine.py` | 上述模块均有直接测试引用 |
| P3-5 | 遗留弃用清理 | `tests/test_live_dashboard.py`（websockets 旧式 `connect()`，50 条 DeprecationWarning）；`main.py` 全局 `RuntimeWarning` 屏蔽改为就地 `np.errstate` | 测试输出无自产 DeprecationWarning；数值告警不再被全局吞掉 |

### P4 判定凭证 + 方法文档（≈1 周，碰 `core/` + `ui/` + `output/`）

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P4-1 | **分析记录写入凭证**（当前最大缺口） | `ui/main_window.py::_store_analysis` + 各 `analysis/*` 返回结构 | 每次分析产出的记录含数据指纹 + 规则版本 + 参数；`verify_dataframe` 可校验 |
| P4-2 | 报告追溯码 | `output/pdf_report.py` · `word_report.py` · `excel_report.py` · `html_export.py` + `chart_engine` 脚注 | 报告页脚可解析出代码 → 凭证 |
| P4-3 | 重跑复核模式 | 复用 `core/evidence.py::diff_credentials` | 同数据两次运行 diff 为空；改参数后 diff 可见具体项 |
| P4-4 | guide.html「方法与参考」章节 | `config/help/guide.html` | 公式出处（NIST 优先）+ 已知值来源可溯源 |
| P4-5 | `.qap` 凭证段（1.7 → 1.8，向后兼容） | `core/project_manager.py` / `core/project_context.py` | 1.6/1.7 旧文件可读；新文件写出凭证段 |

### P5 首个改善闭环切片（≈1.5 周，时间盒，超期即缩范围）

流程：**基线测量 → 时间研究 → 线平衡瓶颈 → 改善方案 → 复测 → 配对检验 → 结论 → 标准草稿**

| 编号 | 任务 | 落点 | 验收 |
|------|------|------|------|
| P5-1 | Home 工作台入口（新建 / 继续案例） | `ui/welcome_page.py`（复用现有卡片结构） | 不新增 Tab；旧会话入口不受影响 |
| P5-2 | 案例脊柱驱动各步（每步挂时间戳 + 数据引用） | `core/improvement_case.py` + 相关 Tab 的数据交接 | 单案例端到端可复现；每步可回看输入数据 |
| P5-3 | 数据源：手动 / CSV（插件数据源预留接口） | `core/plugin_api.py` 预留贡献点 | 插件可实现数据源而不改核心 |
| P5-4 | 旧 `.qap` 零破坏 | `core/project_manager.py` | 旧文件回归用例通过 |
| P5-5 | E2E 演示 | 新增离屏 pytest E2E + 手动演示脚本 | 一键复现案例全流程 |

### P6 收尾（≈0.5 周）

- 版本 4.2.0 四端一致：`config/settings.py` · `version_info.txt` · `packaging/QA-Tool-installer.iss` · README/INSTALL/ROADMAP/guide → `tools/check_version.py` 通过
- 文档同步（中英）+ 全量逐文件回归 + ruff + 性能基线
- **发布形态**：Linux 仅 `build_appimage.sh` 产出 AppImage；Windows 安装包在 Windows 侧由 Inno 脚本构建

---

## 3. 排期与并行

| 周次 | 分析线 | 工程线 |
|------|--------|--------|
| W1 | P2-1 / P2-2（多元 SPC） | P3-1 大样本基准 |
| W2 | P2-3 / P2-4（变点 / 残差图） | P3-2 / P3-3（鲁棒性 + 质量棘轮） |
| W3 | P2-5 / P2-6 / P2-7（区间与稳健性） | P4-1 凭证接线 |
| W4 | P4-2 / P4-3 / P4-4（追溯与文档） | P3-4 / P3-5（覆盖率与弃用清理） |
| W5–W6 | P5 闭环切片（时间盒 1.5 周） | P6 收尾与发布 |

> 缓冲：整体 +20%。P2 与 P3 无文件冲突可并行；P5 依赖 P4-1 的凭证落地。

---

## 4. 每次提交的门禁（沿用 CI）

1. `ruff check .` 零告警
2. 逐文件 `pytest tests/test_xxx.py`（**严禁** `pytest tests/` 批量；conftest 有拦截器）
3. 新算法必须带 known-value 用例（`tests/known_values.py` 框架）
4. 性能敏感改动跑 `tools/benchmark.py --tolerance 4`
5. 发布前：`tools/check_version.py` + 打包冒烟（AppImage 启动 + 主窗口冷启动）

---

## 5. 技术债清单（2026-09-22 实测规模，按优先级）

| 项 | 规模 | 建议 | 归属 |
|----|------|------|------|
| 时间戳无时区（`datetime.now()`） | 56 处 | 与 v4.3.0 双时态一起定语义，勿单独改 | v4.3.0 |
| 遗留 `np.random` 全局随机 | 587 处 | 迁移 `np.random.Generator` + 显式种子（需同步已知值期望） | P3 |
| 盲除异常 `except Exception` | 271 处（非 UI 111） | 棘轮：`BLE001` 入门禁 + 逐处理由 | P3-3 |
| `except ...: pass` 静默吞异常 | 79 处（关键路径 6 处本次已补日志） | 按域补 `logger.debug/warning` | P3 |
| `PERF401` / `SIM105` | 37 / 22 处 | 机械清理（可自动修复） | P3 |
| `pathlib` 迁移（`PTH*`） | ≈250 处 | 低优先，禁止新增 `os.path` 用法 | 后续 |
| 全局 `RuntimeWarning` 屏蔽 | `main.py:24` | 改为就地 `np.errstate` | P3-5 |
| 全角标点告警（`RUF001/002/003`） | 4000+ | 中文语境噪声，不启用 | 不修 |

---

## 6. 风险与对策

| 风险 | 对策 |
|------|------|
| PELT 工程量超期 | 时间盒内降级为二分分割；先保证接口与用例 |
| 已知值来源与许可 | NIST 公有领域优先；文献值记录出处（进 guide「方法与参考」） |
| 闭环切片范围蔓延 | 只做单案例单模板，时间盒 1.5 周 |
| 性能回归 | P3 基线对比，超 tolerance ×4 即回退 |
| 大批量测试导致内存峰值/死锁 | 逐文件单进程执行 + `OMP/OPENBLAS/MKL_NUM_THREADS=2`；禁止多文件合并跑 |
| 沙箱/CI 无本地 socket | 服务端相关用例在具备 socket 的环境单独复跑（`test_dashboard_auth` 等 7 文件） |

---

## 7. 立刻可开工的前 5 件事

1. **P2-1 MEWMA**：以 `analysis/spc/hotelling.py` 为模板，先写已知值用例
2. **P2-5 非正态能力 Bootstrap CI**：改动面最小、用户可见价值高
3. **P3-1 大样本基准**：先加 10 万行档，跑通再上 100 万
4. **P4-1 凭证写入分析记录**：打通 `core/evidence.py` → `ui/main_window.py::_store_analysis`，是 P4/P5 的地基
5. **P3-3 质量棘轮**：`BLE001` 入门禁（非 UI 111 处）
