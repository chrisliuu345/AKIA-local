"""
离线许可验证系统 — Ed25519 + 硬件指纹 + AES-256-GCM
"""
import json
import os
import hashlib
import platform
import base64
import time
from enum import Enum
from typing import Optional, Tuple
from datetime import datetime

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from core.license_keys import LICENSE_PUBLIC_KEY_B64, LICENSE_PRODUCT, LICENSE_DIR_NAME, LICENSE_FILE_NAME


class LicenseStatus(Enum):
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    TAMPERED = "tampered"
    WRONG_MACHINE = "wrong_machine"


class LicenseManager:
    def __init__(self):
        self._home = os.path.expanduser("~")
        self._license_dir = os.path.join(self._home, LICENSE_DIR_NAME)
        self._license_path = os.path.join(self._license_dir, LICENSE_FILE_NAME)

    @staticmethod
    def get_machine_id() -> str:
        """生成硬件指纹 (32字符 hex)"""
        raw = ""

        if platform.system() == 'Windows':
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                    0,
                    winreg.KEY_READ
                )
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                winreg.CloseKey(key)
                raw = value
            except Exception:
                pass

        if not raw:
            parts = []
            parts.append(platform.node())
            parts.append(platform.machine())
            parts.append(platform.processor())
            try:
                import uuid
                mac = uuid.getnode()
                parts.append(str(mac))
            except Exception:
                pass
            parts.append(str(os.cpu_count() or 0))
            raw = "|".join(parts)

        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        return digest[:32]

    def _get_license_path(self) -> str:
        """获取 license 文件路径"""
        return self._license_path

    def load_license(self) -> Optional[dict]:
        """加载 license 文件"""
        if not os.path.exists(self._license_path):
            return None
        try:
            with open(self._license_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _verify_signature(self, license_data: dict) -> bool:
        """验证 Ed25519 签名"""
        if not HAS_CRYPTOGRAPHY:
            return False

        try:
            payload = license_data.get('payload', {})
            signature_b64 = license_data.get('signature', '')

            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
            signature = base64.b64decode(signature_b64)
            public_key_bytes = base64.b64decode(LICENSE_PUBLIC_KEY_B64)

            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, payload_bytes)
            return True
        except Exception:
            return False

    def verify(self) -> LicenseStatus:
        """完整验证流程"""
        if not os.path.exists(self._license_path):
            return LicenseStatus.INVALID

        license_data = self.load_license()
        if license_data is None:
            return LicenseStatus.INVALID

        if not self._verify_signature(license_data):
            return LicenseStatus.TAMPERED

        payload = license_data.get('payload', {})

        license_machine_id = payload.get('machine_id', '')
        current_machine_id = self.get_machine_id()
        if license_machine_id != current_machine_id:
            return LicenseStatus.WRONG_MACHINE

        expires_at = payload.get('expires_at')
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > exp_dt:
                    return LicenseStatus.EXPIRED
            except (ValueError, TypeError):
                pass

        product = payload.get('product', '')
        if product != LICENSE_PRODUCT:
            return LicenseStatus.INVALID

        return LicenseStatus.VALID

    def activate(self, license_text: str) -> Tuple[bool, str]:
        """激活 license"""
        try:
            license_data = json.loads(license_text)
        except json.JSONDecodeError:
            return False, "无效的 license 格式"

        if 'payload' not in license_data or 'signature' not in license_data:
            return False, "缺少 payload 或 signature 字段"

        if not self._verify_signature(license_data):
            return False, "签名验证失败"

        payload = license_data['payload']

        current_machine_id = self.get_machine_id()
        license_machine_id = payload.get('machine_id', '')
        if license_machine_id != current_machine_id:
            return False, "机器指纹不匹配"

        product = payload.get('product', '')
        if product != LICENSE_PRODUCT:
            return False, "产品不匹配"

        expires_at = payload.get('expires_at')
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > exp_dt:
                    return False, "license 已过期"
            except (ValueError, TypeError):
                return False, "无效的过期日期格式"

        os.makedirs(self._license_dir, exist_ok=True)
        with open(self._license_path, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)

        return True, "激活成功"

    def get_license_info(self) -> dict:
        """获取 license 信息"""
        license_data = self.load_license()
        if license_data is None:
            return {"status": "未激活", "machine_id": self.get_machine_id()}

        payload = license_data.get('payload', {})
        status = self.verify()

        return {
            "status": status.value,
            "licensee": payload.get('licensee', ''),
            "expires_at": payload.get('expires_at', ''),
            "features": payload.get('features', []),
            "machine_id": self.get_machine_id(),
        }

    def is_valid(self) -> bool:
        """快速检查"""
        return self.verify() == LicenseStatus.VALID


# 全局实例
license_manager = LicenseManager()
