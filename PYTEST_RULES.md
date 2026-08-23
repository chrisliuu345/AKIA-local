# ⚠️ pytest 运行规则

**绝对禁止**: `pytest tests/` 批量运行
**正确方式**: `pytest tests/test_xxx.py` 逐文件执行

## 死机原因

PySide6 + scipy + numpy 并发初始化在 Windows + Python 3.14 下触发线程死锁，导致系统无响应。

## 技术拦截

- `tests/conftest.py`: 超过 30 个测试自动中断
- `run_tests.ps1`: 强制单文件执行入口
- 绕过方式: `$env:QA_TOOL_ALLOW_BATCH=1`（仅 CI 使用）
