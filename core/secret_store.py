"""
跨平台凭据加密存储

Windows:  DPAPI (CryptProtectData/CryptUnprotectData) — 机器+用户绑定
Linux:    keyring (系统密钥环) + cryptography (AES-256-Fernet)
macOS:    keyring (系统钥匙串)

存储格式:
  Windows: "dpapi:<base64>"
  Linux/macOS: "keyring:<base64>" 或旧版 "dpapi:<base64>"（向后兼容）
"""

import base64
import logging
import sys

logger = logging.getLogger("QA-Tool.SecretStore")

_PREFIX_DPAPI = "dpapi:"
_PREFIX_KEYRING = "keyring:"


def _encrypt_dpapi(data: bytes) -> bytes:
    """Windows DPAPI 加密"""
    import ctypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.c_void_p)]

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
        raise RuntimeError(f"DPAPI encryption failed (error {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _decrypt_dpapi(data: bytes) -> bytes:
    """Windows DPAPI 解密"""
    import ctypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.c_void_p)]

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
        raise RuntimeError(f"DPAPI decryption failed (error {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _encrypt_keyring_fernet(data: bytes) -> bytes:
    """Linux/macOS: Fernet 加密（AES-128-CBC + HMAC-SHA256）"""
    import os

    try:
        import keyring
    except ImportError:
        raise RuntimeError("keyring package required on Linux/macOS")

    SERVICE_NAME = "qa-tool"
    KEY_NAME = "master-key"

    key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if key is None:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        keyring.set_password(SERVICE_NAME, KEY_NAME, key)

    from cryptography.fernet import Fernet
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(data)


def _decrypt_keyring_fernet(data: bytes) -> bytes:
    """Linux/macOS: Fernet 解密"""
    try:
        import keyring
    except ImportError:
        raise RuntimeError("keyring package required on Linux/macOS")

    from cryptography.fernet import Fernet

    SERVICE_NAME = "qa-tool"
    KEY_NAME = "master-key"

    key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if key is None:
        raise RuntimeError("No encryption key found in keyring")

    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(data)


def encrypt_secret(text: str) -> str:
    """加密明文 → 平台特定存储格式"""
    if not text:
        return ""

    data = text.encode("utf-8")

    if sys.platform == "win32":
        encrypted = _encrypt_dpapi(data)
        return _PREFIX_DPAPI + base64.b64encode(encrypted).decode()
    else:
        encrypted = _encrypt_keyring_fernet(data)
        return _PREFIX_KEYRING + base64.b64encode(encrypted).decode()


def decrypt_secret(stored: str) -> str:
    """解密存储值 → 明文。支持旧版格式（向后兼容）。失败返回 ''。"""
    if not stored:
        return ""

    try:
        if stored.startswith(_PREFIX_DPAPI):
            raw = base64.b64decode(stored[len(_PREFIX_DPAPI):])
            if sys.platform == "win32":
                return _decrypt_dpapi(raw).decode("utf-8")
            else:
                # 旧版 dpapi 数据在非 Windows 平台无法解密
                logger.warning("Cannot decrypt dpapi data on non-Windows platform")
                return ""
        elif stored.startswith(_PREFIX_KEYRING):
            raw = base64.b64decode(stored[len(_PREFIX_KEYRING):])
            return _decrypt_keyring_fernet(raw).decode("utf-8")
        else:
            # 旧版无前缀 base64（兼容）
            return base64.b64decode(stored).decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed: {e}")
        return ""
