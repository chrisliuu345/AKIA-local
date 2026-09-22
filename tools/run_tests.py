#!/usr/bin/env python3
"""run_tests.py — 逐文件测试运行器（单一进程跑一个文件）

为什么需要它：PySide6 + scipy + numpy 在同一进程内并发初始化会死锁甚至 OOM
（2026-09-22 实测），因此本项目规定「一个文件一个进程」。手工 for 循环容易写错，
本脚本把正确姿势固化成一条命令，并顺带做三件事：

1. 每个文件独立子进程 + 单文件超时（默认 900s，超时即判失败并继续）
2. 限制 BLAS/OpenMP 线程数（``--max-as-gb`` 可额外限制地址空间，但**默认关闭**：
   RLIMIT_AS 约束的是虚拟地址空间，numpy/Qt 常映射 20–40 GB 虚拟内存，实测 12 GB 上限
   会让 test_devices 直接 MemoryError；如确需限制请给足余量，例如 ``--max-as-gb 32``）
3. 失败日志集中留存（默认 ``/tmp/qa_tool_test_logs/``，便于 CI 上传产物）

用法::

    python tools/run_tests.py                    # 全量逐文件
    python tools/run_tests.py --quiet            # 只打印失败与汇总（CI 用）
    python tools/run_tests.py --files test_a.py  # 只跑指定文件（可多次）
    python tools/run_tests.py --timeout 300      # 单文件超时（秒）
    python tools/run_tests.py --max-as-gb 32     # 可选：单进程地址空间上限（Linux）
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"
LOG_DIR = Path(os.environ.get("QA_TOOL_TEST_LOG_DIR", "/tmp/qa_tool_test_logs"))


def _test_files(pattern: str | None) -> list[Path]:
    return sorted(TESTS_DIR.glob(pattern or "test_*.py"))


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    cache = Path(env.get("TMPDIR", "/tmp")) / "qa_tool_mplcache"
    cache.mkdir(parents=True, exist_ok=True)
    env.setdefault("MPLCONFIGDIR", str(cache))
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        env.setdefault(key, "2")
    return env


def _limiter(max_as_gb: float | None):
    """返回 preexec_fn：限制子进程地址空间（Linux/macOS 有效）。"""
    if not max_as_gb or os.name != "posix":
        return None

    def _apply():  # pragma: no cover - 子进程内执行
        import resource

        limit = int(max_as_gb * 1024 ** 3)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    return _apply


def _summary_line(text: str) -> str:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    for line in reversed(text.strip().splitlines()):
        cleaned = ansi.sub("", line).strip()
        if any(token in cleaned for token in ("passed", "failed", "error", "skipped")):
            return cleaned.strip("= ")
    return ""


def run(files: list[Path], timeout: float, quiet: bool,
        max_as_gb: float | None) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = _child_env()
    failures: list[tuple[str, str]] = []
    total_passed = total_skipped = 0
    started = time.time()

    for path in files:
        stage = path.stem
        log_path = LOG_DIR / f"{stage}.log"
        cmd = [sys.executable, "-m", "pytest", str(path), "-q", "--tb=line",
               "-p", "no:cacheprovider"]
        try:
            proc = subprocess.run(cmd, cwd=ROOT, env=env, timeout=timeout,
                                  capture_output=True, text=True,
                                  preexec_fn=_limiter(max_as_gb), check=False)
            output, code = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            code = 124
        log_path.write_text(output, encoding="utf-8", errors="replace")
        line = _summary_line(output)
        if code == 0:
            if not quiet:
                print(f"ok   {stage:38s} {line}")
        else:
            reason = "超时" if code == 124 else f"退出码 {code}"
            print(f"FAIL {stage:38s} {reason} | {line}")
            print(f"     日志: {log_path}")
            failures.append((stage, reason))
        for token, counter in (("passed", "passed"), ("skipped", "skipped")):
            if token in line:
                part = line.split(token)[0].strip().split()[-1]
                if part.isdigit():
                    if counter == "passed":
                        total_passed += int(part)
                    else:
                        total_skipped += int(part)

    elapsed = time.time() - started
    print(f"\n文件: {len(files)} | 通过用例: {total_passed} | 跳过: {total_skipped} "
          f"| 失败文件: {len(failures)} | 用时: {elapsed:.1f}s")
    if failures:
        print("失败文件清单:")
        for stage, reason in failures:
            print(f"  - {stage}（{reason}）")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="逐文件运行 pytest（一个文件一个进程）")
    parser.add_argument("--files", nargs="*", default=None,
                        help="只跑指定文件（支持 basename 或相对 tests/ 的路径）")
    parser.add_argument("--pattern", default=None, help="文件通配（默认 test_*.py）")
    parser.add_argument("--timeout", type=float, default=900.0, help="单文件超时秒数")
    parser.add_argument("--max-as-gb", type=float, default=None,
                        help="单进程地址空间上限（GB，Linux 有效；默认不限制 —— 该上限约束"
                             "虚拟内存，给太小会让 numpy/Qt 抛 MemoryError，建议 ≥32）")
    parser.add_argument("--quiet", action="store_true", help="只打印失败与汇总")
    args = parser.parse_args()

    if args.files:
        files = []
        for name in args.files:
            candidate = Path(name)
            if not candidate.is_absolute():
                # 支持三种写法：文件名 / tests/xxx.py / 完整相对路径
                if candidate.parent == Path("."):
                    candidate = TESTS_DIR / candidate.name
                else:
                    candidate = ROOT / candidate
            if not candidate.exists() and candidate.suffix != ".py":
                candidate = candidate.with_suffix(".py")
            if not candidate.exists():
                print(f"[error] 文件不存在: {name}", file=sys.stderr)
                return 2
            files.append(candidate)
    else:
        files = _test_files(args.pattern)
    if not files:
        print("[error] 未找到测试文件", file=sys.stderr)
        return 2
    return run(files, args.timeout, args.quiet, args.max_as_gb)


if __name__ == "__main__":
    sys.exit(main())
