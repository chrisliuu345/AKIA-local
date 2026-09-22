# pytest 运行规则

**绝对禁止**: `pytest tests/` 批量运行，或一次传多个文件（会被自动拦截）
**正确方式**: `pytest tests/test_xxx.py` 逐文件执行，或 `python tools/run_tests.py`

## 一键逐文件（推荐）

```bash
python tools/run_tests.py                 # 全量逐文件（失败汇总 + 日志留存）
python tools/run_tests.py --quiet         # CI 用法：只打印失败与汇总
python tools/run_tests.py --timeout 600   # 单文件超时保护
```

脚本为每个文件拉起独立子进程，默认把 BLAS 线程数限为 2，日志写到
`/tmp/qa_tool_test_logs/`（CI 失败时作为 artifact 上传）。

> `--max-as-gb` 会限制**虚拟地址空间**（非 RSS）：numpy/Qt 常映射 20–40 GB 虚拟内存，
> 给小了会直接 MemoryError（实测 12 GB 会让 `test_devices` 失败）。默认不限制，
> 确需限制时建议 ≥ 32。

## 死机原因

PySide6 + scipy + numpy 并发初始化触发线程死锁，导致系统无响应（尤其 Windows + Python 3.14）。

## 技术拦截

- `tests/conftest.py`: **一次传入多个 `.py` 文件参数即中断**（`pytest.exit`）；
  无文件参数且收集数 > 30（目录批量）同样中断
- 绕过方式: `QA_TOOL_ALLOW_BATCH=1`（仅在明确知道风险时使用；Windows 仍可能冻机）

## 环境能力标记（2026-09-22 新增）

需要外部能力的用例必须打标记，能力缺失时**自动跳过**而不是失败：

| 标记 | 含义 | 缺失时 |
|------|------|--------|
| `requires_socket` | 需绑定本地回环端口（看板 / 设备 / 服务端） | 自动 `skip` |
| `requires_keyring` | 需可用系统密钥环后端 | 自动 `skip`（CI 用 `keyrings.alt` 提供） |
| `requires_server` | 需 FastAPI/uvicorn（`requirements-server.txt`） | 自动 `skip` |

CI 已安装 `requirements-server.txt` 并为密钥环提供 CI 专用后端，这三类用例在 CI 中会
真实执行；本地受限沙箱里则显式显示 skipped（不再伪装成失败）。

## CI 推荐

GitHub Actions 已拆分为 `lint` / `tests` / `benchmark` 三个 job（tag 上追加
`package-appimage` 打包冒烟），其中 `tests` 直接调用 `python tools/run_tests.py --quiet`。
