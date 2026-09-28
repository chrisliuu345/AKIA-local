# 2026-09-28 中间质量审查与算法优化（无版本号）

> 范围：全库代码质量审查 + 算法正确性/性能优化。**不新增版本号**（交付时为 4.2.0 源码更新），
> 不发布安装包；每个阶段独立提交，便于回溯与回滚。
> 触发：v4.2.0 发布后的一次中间质量活动，重点是"发现真实缺陷"而非堆砌规则。

## 1. 阶段与提交

| 阶段 | 主题 | 提交 |
|------|------|------|
| P1 | 静态质量棘轮扩容 + 死代码/冗余 noqa 清理 | `33f46e8` |
| P2 | 静默失败治理 + 批量调度执行器修复 | `957b20d` |
| P3 | 数值鲁棒性：非有限值/缺失输入统一净化 | `f9a8f44` |
| P4 | 性能热点向量化（Nelson 判异 / 解析逐格回调） | `d1e0806` |
| P5 | 全量逐文件回归 + 文档同步（本文件） | 见 git log |

## 2. 真实缺陷清单（本次发现并修复）

### 2.1 功能级缺陷

| 缺陷 | 现象 | 影响 | 修复 |
|------|------|------|------|
| 批量调度必然失败 | `ui/dialogs/batch_dialog.py` 创建 `BatchScheduler()` 未注入执行器，所有任务抛 `NotImplementedError` | 「工具 → 批量调度」定时任务永远不会成功，只在日志里看到失败 | 新增无 Qt 依赖执行器 `core/batch_scheduler.py::run_task_headless`（数据源 → 分析 → docx/pdf/xlsx/Markdown 报告），对话框注入 |
| 8D Tab 初始化崩溃 | PLW0108 自动修复把 `lambda r: self._stack.setCurrentIndex(r)` 改为直接绑定方法 → 立即求值 `self._stack`（晚于连接创建） | `EightDTab` 构造抛 `AttributeError`，懒加载失败（5 例 UI 用例失败） | 先创建 `_stack` 再连接；未用 noqa 掩盖 |
| 保修分析删失标记错位 | `T = failure_times.dropna()` 后 `censored.reindex(T.index)` 在索引重置场景下按位置错配 | 删失标记与时间行错位 → 失效点数量统计错误 | 改为 `sanitize_pairs` 成对净化（按行剔除，标记与时间严格对齐） |

### 2.2 数值鲁棒性缺陷（底层报错直达用户）

| 模块 | 输入 | 旧行为 | 新行为 |
|------|------|--------|--------|
| `analysis/time_series/exponential_smoothing.py` | 含缺失值 | `ValueError: No supported index is available.` | 净化后正常拟合（与 ARIMA 同款修复对齐） |
| `analysis/spc/{c,np,p,u}_chart.py` | 缺失/±inf | `cannot convert float NaN to integer` / `OverflowError` | 剔除无效子组；不足 2 个给结构化中文错误 |
| `analysis/spc/residual_chart.py`、`analysis/time_series/arima.py` | 含 ±inf | `IndexError: index 0 is out of bounds`（Ljung-Box 空序列） | 净化 + 「残差有效点不足」守卫 |
| `analysis/capability/{sixpack,non_normal_cap}.py` | 含 ±inf | `autodetected range ... is not finite` / `boxcox_normmax ...` | 净化后正常出结果 |
| `analysis/spc/xbar_s.py` | 全常量序列 | 报错文案无法定位原因 | 文案点明"常量序列 / 量具分辨率不足" |

统一入口：`analysis/_sanitize.py`（`sanitize_series/array/pairs/groups/frame`）+
`analysis/spc/_validation.py`（计数图专用）。

### 2.3 可观测性缺陷

- `core/audit.py`：审计写入失败此前**静默**（审计链可无声缺失）→ 现计数
  `write_failures()` + warning 日志（导入/导出/告警确认等合规事件依赖此路径）。
- `core/session_manager.py`：损坏会话文件被静默跳过 → warning 带文件名。
- `core/batch_scheduler.py`：`target_time` 非法 / 任务配置读取失败 → warning。
- `core/one_click_analyzer.py`：AI 结论失败退回本地模板 → warning（结论来源变化需可见）。
- `config/settings.py`：旧版 `user_config.json` 迁移失败 → warning（否则用户无声丢配置）。
- 31 处 `except ...: pass` 全部补齐"为什么可以宽异常"的理由注释（AST 扫描口径 100%）。

### 2.4 死代码

- `core/sampling_engine.py::sequential_decision`：`total` 只写不读。
- `ui/tabs/smed_tab.py::run_analysis`：甘特图 `y` 只写不读。

## 3. 算法与性能

### 3.1 Nelson 判异向量化（`analysis/spc/_rules.py`）

- 旧实现逐窗口 `np.sum`/`np.all`：100 万点约 400 万次 NumPy 调用，占 I-MR 分析 99% 时间。
- 新实现前缀和滑窗计数；规则 8「报告后跳过整段」语义保留。
- **等价性验证**：随机 + 构造数据（常量 · 锯齿 · 趋势 · 与均值相等点）2100 项逐点对照，**0 差异**。

### 3.2 解析逐格回调向量化（`core/data_parser.py`）

- 旧实现 `df.map(_is_blank / _is_invalid_cell)`：百万行表约 1200 万 + 600 万次 Python 调用。
- 新实现按列分派：数值/布尔/时间列只判缺失，文本列用 pandas 字符串向量化 + 原正则。
- **等价性验证**：混合类型表（文本/数值/布尔/时间/混合对象列 + `NA`/`None`/空串/星号/问号/`ERR`）
  逐格掩码一致、剔除行数一致（176 = 176）；重名列按位置遍历保持兼容。

### 3.3 基准（`tools/benchmark.py`，2026-09-28 实测）

| 指标 | v4.2.0 基线 | 本次 | 变化 |
|------|-------------|------|------|
| 冷启动 | 2.296s | 2.101s | −8% |
| 百万行导入 | 14.269s | **5.188s** | **−64%（2.7×）** |
| 5k 图渲染 | 1.732s | 0.972s | −44% |
| 5k 行 ML | 1.588s | 1.481s | −7% |
| SPC 10 万点 | 3.292s | **1.303s** | **−60%（2.5×）** |
| SPC 100 万点 | 21.956s | **1.622s** | **−93%（13.5×）** |
| MSA 10 万行 | 1.044s | 1.058s | ≈ |
| ML 10 万行 | 3.936s | 4.081s | ≈（噪声） |

`tools/perf_baseline.json` 已按本次实测收紧，锁定收益（门禁 tolerance ×4 通过）。

## 4. 门禁与复现

```bash
ruff check .                      # 全库零告警（含 2026-09-28 新增 11 条规则棘轮）
python tools/run_tests.py         # 逐文件全量回归（单进程/文件）
python tools/benchmark.py         # 8 项性能基线
python tools/release_check.py     # 版本一致性 + ruff + 回归 + 基准（一键）
```

## 5. 未处理项（明确边界，避免误解为"全部干净"）

- `np.random` 全局随机（约 587 处）：本轮未迁移到 `Generator`（需同步已知值期望），
  分析层入口已做确定性净化，但随机性来源仍受全局状态影响。
- `core/` 与 `ui/` 的宽异常存量（core 90 · ui 128）：本轮只治理**可观测性**与理由注释，
  未逐处收敛捕获范围（收敛顺序见 `ruff.toml` 注释）。
- `PERF401` 存量 60 处未入闸（自动修复 51 处）；`pathlib` 迁移（≈250 处）与
  无时区时间戳（56 处）按原计划延后（后者随 v4.3.0 双时态定语义）。
- 复核模式 UI 弹窗、HTML 导出追溯码、时间研究/线平衡引擎类型化接入案例工作流
  等 v4.2.0 已知功能遗留（见 `docs/releases/v4.2.0.md`）。
