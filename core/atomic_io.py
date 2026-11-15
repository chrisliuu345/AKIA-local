"""把文件写到同目录临时文件，再用替换完成提交。

替换在同一文件系统上是原子的：读者要么看到旧文件，要么看到写完的新文件。
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def atomic_path(path: str) -> Iterator[str]:
    """产出临时路径。代码块成功结束后替换为目标文件，失败则删掉临时文件。"""
    target = os.path.abspath(path)
    directory = os.path.dirname(target) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix="." + os.path.basename(target) + ".",
        suffix=".tmp",
        dir=directory,
    )
    os.close(fd)
    try:
        yield temporary
        os.replace(temporary, target)
    except Exception:
        with contextlib.suppress(OSError):
            if os.path.exists(temporary):
                os.remove(temporary)
        raise


def atomic_write_text(path: str, text: str) -> None:
    with atomic_path(path) as temporary:
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
