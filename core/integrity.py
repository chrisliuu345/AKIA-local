"""
运行时完整性校验 — 多点 SHA-256 校验防篡改
"""
import hashlib
import os
import json
from typing import Tuple, List

CRITICAL_FILES = [
    "core/license.py",
    "core/license_keys.py",
    "core/anti_debug.py",
    "core/integrity.py",
    "main.py",
]

# 基线哈希存储路径
_BASELINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".integrity_baseline.json"
)


def compute_file_hash(filepath: str) -> str:
    """计算文件 SHA-256"""
    try:
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (IOError, OSError):
        return None


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


def save_baseline(base_dir: str = None) -> bool:
    """保存当前哈希作为基线（开发者用）"""
    hashes = compute_all_hashes(base_dir)
    # 过滤掉 None 值
    valid = {k: v for k, v in hashes.items() if v is not None}
    try:
        with open(_BASELINE_PATH, 'w', encoding='utf-8') as f:
            json.dump(valid, f, indent=2)
        return True
    except (IOError, OSError):
        return False


def _load_baseline() -> dict:
    """加载基线哈希"""
    try:
        with open(_BASELINE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, OSError, json.JSONDecodeError):
        return {}


def verify_integrity(base_dir: str = None) -> Tuple[bool, List[str]]:
    """校验完整性，返回 (是否通过, 问题列表)
    
    验证逻辑:
    1. 检查关键文件是否存在
    2. 比对当前哈希与基线哈希（如果基线存在）
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    issues = []
    hashes = compute_all_hashes(base_dir)
    baseline = _load_baseline()

    for file_path, file_hash in hashes.items():
        if file_hash is None:
            issues.append(f"Critical file missing: {file_path}")
        elif file_path in baseline:
            # 基线存在时比对哈希
            if baseline[file_path] != file_hash:
                issues.append(f"File tampered: {file_path}")

    return (len(issues) == 0, issues)
