"""
许可证系统 — v3.2.0 起已移除

保留接口以保持向后兼容，但所有方法变为空操作。
"""

from enum import Enum
from typing import Tuple


class LicenseStatus(Enum):
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"
    TAMPERED = "tampered"
    WRONG_MACHINE = "wrong_machine"


class LicenseManager:
    """许可证管理器 — 空操作实现（v3.2.0+）"""

    def __init__(self):
        pass

    @staticmethod
    def get_machine_id() -> str:
        """返回机器ID（用于向后兼容）"""
        import platform
        import hashlib
        raw = f"{platform.node()}|{platform.machine()}|{platform.processor()}"
        return hashlib.md5(raw.encode()).hexdigest()[:32]

    def verify(self) -> Tuple[bool, LicenseStatus]:
        """验证许可证 — 始终返回有效"""
        return True, LicenseStatus.VALID

    def activate(self, license_data: str) -> bool:
        """激活许可证 — 空操作"""
        return True

    def get_license_info(self) -> dict:
        """获取许可证信息"""
        return {
            "status": "active",
            "message": "v3.2.0+ 不需要许可证",
            "machine_id": self.get_machine_id(),
        }


def _ensure_license_dir():
    """确保许可证目录存在 — 空操作"""
    pass


def verify_license() -> Tuple[bool, LicenseStatus]:
    """验证许可证 — 始终返回有效"""
    return True, LicenseStatus.VALID


def get_machine_id() -> str:
    """获取机器ID"""
    return LicenseManager.get_machine_id()
