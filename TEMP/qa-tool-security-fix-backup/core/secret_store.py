"""
凭据加密存储 — Windows DPAPI (CryptProtectData/CryptUnprotectData)
机器 + 当前用户绑定，密钥由操作系统托管，不在磁盘落明文密钥。
纯标准库实现 (ctypes)，无新增依赖。

存储格式: "dpapi:<base64>"; 旧版 base64 数据 (无前缀) 视为过期格式可读。
"""

import base64
import ctypes
import sys

_PREFIX = "dpapi:"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.c_void_p)]


def _protect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI 仅在 Windows 可用")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    in_blob = _DATA_BLOB(len(data), ctypes.cast(
        ctypes.create_string_buffer(data), ctypes.c_void_p
    ))
    out_blob = _DATA_BLOB()
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise RuntimeError(f"DPAPI 加密失败 (error {ctypes.get_last_error()})")
    try:
        out = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return out


def _unprotect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("DPAPI 仅在 Windows 可用")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    in_blob = _DATA_BLOB(len(data), ctypes.cast(
        ctypes.create_string_buffer(data), ctypes.c_void_p
    ))
    out_blob = _DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise RuntimeError(f"DPAPI 解密失败 (error {ctypes.get_last_error()})")
    try:
        out = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)
    return out


def encrypt_secret(text: str) -> str:
    """加密明文 → 'dpapi:<base64>'。非 Windows 环境退化为 base64 (不可用, 抛错)。"""
    if not text:
        return ""
    return _PREFIX + base64.b64encode(_protect(text.encode("utf-8"))).decode()


def decrypt_secret(stored: str) -> str:
    """解密存储值 → 明文。支持旧版无前缀 base64 (平滑迁移)。失败返回 ''。"""
    if not stored:
        return ""
    try:
        if stored.startswith(_PREFIX):
            raw = base64.b64decode(stored[len(_PREFIX):])
            return _unprotect(raw).decode("utf-8")
        # 旧版 base64 兼容
        return base64.b64decode(stored).decode("utf-8")
    except Exception:
        return ""
