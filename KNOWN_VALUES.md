# 已知值测试规范（v4.2.0 P0 契约）

> 目的：把「算法可信」变成 CI 可执行的证据。v4.2.0 P1 起，每个关键算法至少 1 个已知值用例；
> 用例的来源、容差与出处必须随测试代码入库，不允许只写断言不写出处。

## 1. 来源优先级

1. **NIST StRD**（Statistical Reference Datasets，公有领域）
2. **NIST/SEMATECH e-Handbook of Statistical Methods**
3. **标准与文献**（GB/T、ISO、Montgomery、Box 等；记录章节 / 页码 / 表号）
4. **参考实现交叉验证**（statsmodels / scipy / R；仅作补充，不作为唯一来源）

## 2. 容差政策

| 预设 | rel_tol | abs_tol | 适用 |
|------|---------|---------|------|
| `closed_form` | 1e-9 | 1e-12 | 闭式解（均值 / 极差 / Cp / 回归系数等） |
| `rounded_6dp` | 1e-9 | 5.1e-7 | 引擎输出四舍五入到 6 位小数 |
| `rounded_4dp` | 1e-9 | 5.1e-5 | 引擎输出四舍五入到 4 位小数（能力指数等） |
| `iterative` | 1e-6 | 1e-9 | 迭代求解（MLE / ARIMA / 优化） |
| `bootstrap` | 1e-3 | 1e-3 | 随机模拟（Bootstrap / 蒙特卡洛；必须固定 seed） |

- 每个用例用 `KnownValueCase(rel_tol=..., abs_tol=...)` 或 `KnownValueCase.with_preset(...)` 显式声明容差；
- 期望值为 0 时必须给 `abs_tol`；
- 容差比默认更宽时，必须在 `notes` 写明理由（如「算法为迭代解，收敛判据 1e-8」）。

## 3. 文件与命名

- 测试文件：`tests/test_known_values_<domain>_<method>.py`
  （domain：`spc` / `capability` / `msa` / `doe` / `reliability` / `timeseries` / `ml`）
- 测试函数：`test_<method>_<case_id>`
- 每个用例一个 `KnownValueCase`，`case_id` 全局唯一，建议 `nist-<dataset>-<stat>` 形式
- 数据点 ≤ 50 内联在测试文件；更大数据集放 `tests/data/known_values/`（CSV，文件头或同名 `.md` 记录来源）

## 4. 框架用法

```python
from tests.known_values import KnownValueCase, assert_close

CASE = KnownValueCase.with_preset(
    "nist-norris-mean", "NIST StRD Norris",
    preset="closed_form", reference="Norris dataset, column 1 mean",
)

def test_mean_norris():
    assert_close(actual=computed_mean, expected=0.5, case=CASE)
```

## 5. CI 与回归

- 文件匹配 `tests/test_*.py`，自动进入逐文件回归与 CI，无需改工作流；
- 新增用例必须同时通过 `ruff check .` 门禁；
- 严禁在此目录使用 `pytest tests/` 批量运行（见 `PYTEST_RULES.md`）。
