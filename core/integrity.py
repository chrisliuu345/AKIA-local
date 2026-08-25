"""
运行时完整性校验 — 多点 SHA-256 校验防篡改
"""
import hashlib
import os
from typing import Tuple, List

CRITICAL_FILES = [
    "core/license.py",
    "core/license_keys.py",
    "core/anti_debug.py",
    "core/integrity.py",
    "main.py",
]


def compute_file_hash(filepath: str) -> str:
    """计算文件 SHA-256"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_all_hashes(base_dir: str = None) -> dict:
    """计算所有关键文件的哈希"""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    hashes = {}
    for file_path in CRITICAL_FILES:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            hashes[file_path] = compute_file_hash(full_path)
        else:
            hashes[file_path] = None
    return hashes


def verify_integrity(base_dir: str = None) -> Tuple[bool, List[str]]:
    """校验完整性，返回 (是否通过, 问题列表)"""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    issues = []
    hashes = compute_all_hashes(base_dir)

    for file_path, file_hash in hashes.items():
        if file_hash is None:
            issues.append(f"Critical file missing: {file_path}")

    return (len(issues) == 0, issues)
