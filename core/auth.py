"""
多用户认证 — PBKDF2-SHA256 哈希 + 四级角色权限
"""

import json
import os
import hashlib
import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from core.password_policy import validate_password

_LOG_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_audit.log")
def _audit(action: str, operator: str, detail: str = ""):
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {operator}: {action} {detail}\n")
    except Exception: pass


# 简易 bcrypt-lite: 使用 PBKDF2-SHA256 替代 bcrypt（无额外依赖）
# 格式: $pbkdf2-sha256$rounds$salt_base64$hash_base64
_PBKDF2_ROUNDS = 150000


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return (
        f"$pbkdf2-sha256${_PBKDF2_ROUNDS}$"
        f"{base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(dk).decode()}"
    )


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        parts = password_hash.split("$")
        if len(parts) != 5:
            return False
        algo, rounds, salt_b64, dk_b64 = parts[1], int(parts[2]), parts[3], parts[4]
        rounds = min(rounds, 1_000_000)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
        return dk == expected
    except Exception:
        return False


@dataclass
class User:
    username: str
    password_hash: str
    role: str            # "admin" / "dept_admin" / "analyst" / "readonly"
    department: str = ""  # 质量部 / 生产部 / IE部 / 研发部 / ...
    team: str = ""        # 一组 / 二组 / 白班 / 夜班 / ...
    display_name: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "department": self.department,
            "team": self.team,
            "display_name": self.display_name or self.username,
            "created_at": self.created_at,
        }

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def can_manage_users(self) -> bool:
        return self.role in ("admin", "dept_admin")


# 预设部门/班组
_DEPARTMENTS = ["质量部", "生产部", "IE部", "研发部", "供应链", "其他"]
_TEAMS = ["一组", "二组", "三组", "白班", "夜班", "A班", "B班", "C班"]

# 四级角色权限矩阵
_ROLE_PERMISSIONS = {
    "admin":       {"import", "analyze", "clean", "export", "view",
                    "manage_users", "settings", "share_project", "view_shared"},
    "dept_admin":  {"import", "analyze", "clean", "export", "view",
                    "manage_dept_users", "share_project", "view_shared"},
    "analyst":     {"import", "analyze", "clean", "export", "view",
                    "share_project", "view_shared"},
    "readonly":    {"export", "view", "view_shared"},
}


def _can_manage(caller: Optional[User], target_role: str) -> bool:
    """判断 caller 是否有权管理 target_role 的用户（后端越权防护）"""
    if caller is None:
        return True
    if caller.role == "admin":
        return True
    if caller.role == "dept_admin":
        return target_role in ("analyst", "readonly")
    return False


class AuthManager:
    """用户认证与权限管理器"""

    USERS_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_users.json")

    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.USERS_FILE):
            self._init_default_admin()

    def _init_default_admin(self):
        admin = User(
            username="admin",
            password_hash=_hash_password("admin"),
            role="admin",
            department="",
            team="",
            display_name="系统管理员",
            created_at=datetime.now().isoformat(),
        )
        self._save_users([admin.to_dict()])

    def _read_users_file(self) -> List[dict]:
        with open(self.USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("用户文件格式错误: 不是列表")
        return data

    def _load_users(self) -> List[dict]:
        try:
            return self._read_users_file()
        except (json.JSONDecodeError, ValueError):
            # 用户文件损坏：备份后重建默认 admin，避免系统锁死
            try:
                os.replace(self.USERS_FILE, self.USERS_FILE + ".corrupt")
                _audit("auth_corrupt", "system", "用户文件损坏，已备份并重建默认管理员")
            except OSError:
                pass
            self._init_default_admin()
            try:
                return self._read_users_file()
            except Exception:
                return []
        except Exception:
            return []

    def _save_users(self, users: List[dict]):
        os.makedirs(os.path.dirname(self.USERS_FILE), exist_ok=True)
        with open(self.USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    def authenticate(self, username: str, password: str) -> Optional[User]:
        users = self._load_users()
        for u in users:
            if u["username"] == username and _verify_password(password, u["password_hash"]):
                _audit("login", username, "成功")
                return User(**u)
        _audit("login_failed", username)
        return None

    def create_user(self, username: str, password: str, role: str = "analyst",
                     department: str = "", team: str = "", display_name: str = "") -> Optional[User]:
        if role not in _ROLE_PERMISSIONS:
            raise ValueError(f"无效角色: {role}")
        ok, reason = validate_password(password)
        if not ok:
            _audit("create_user_failed", username, reason)
            return None
        users = self._load_users()
        if any(u["username"] == username for u in users):
            _audit("create_user_failed", username, "用户已存在")
            return None
        user = User(
            username=username,
            password_hash=_hash_password(password),
            role=role,
            department=department,
            team=team,
            display_name=display_name or username,
            created_at=datetime.now().isoformat(),
        )
        users.append(user.to_dict())
        self._save_users(users)
        _audit("create_user", username, f"角色={role}")
        return user

    def update_user(self, username: str, caller: Optional[User] = None, **kwargs) -> bool:
        """更新用户属性（角色/部门/班组/显示名称），不修改密码"""
        if "role" in kwargs and kwargs["role"] not in _ROLE_PERMISSIONS:
            raise ValueError(f"无效角色: {kwargs['role']}")
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                if not _can_manage(caller, u.get("role", "")):
                    _audit("update_user_failed", username, "无权限修改该用户")
                    return False
                if "role" in kwargs and not _can_manage(caller, kwargs["role"]):
                    _audit("update_user_failed", username, "无权限设置该角色")
                    return False
                for k in ("role", "department", "team", "display_name"):
                    if k in kwargs and kwargs[k] is not None:
                        u[k] = kwargs[k]
                self._save_users(users)
                _fields = ','.join(k for k in ("role", "department", "team", "display_name")
                                    if k in kwargs and kwargs[k] is not None)
                _audit("update_user", username, f"字段={_fields}")
                return True
        return False

    def reset_password(self, username: str, new_password: str, caller: Optional[User] = None) -> bool:
        """管理员重置用户密码"""
        ok, reason = validate_password(new_password)
        if not ok:
            _audit("reset_password_failed", username, reason)
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                if not _can_manage(caller, u.get("role", "")):
                    _audit("reset_password_failed", username, "无权限重置该用户密码")
                    return False
                u["password_hash"] = _hash_password(new_password)
                self._save_users(users)
                _audit("reset_password", username)
                return True
        _audit("reset_password_failed", username, "用户不存在")
        return False

    def delete_user(self, username: str, caller: Optional[User] = None) -> bool:
        if username == "admin":
            _audit("delete_user_failed", username, "禁止删除admin")
            return False
        users = self._load_users()
        target = next((u for u in users if u["username"] == username), None)
        if target is None:
            _audit("delete_user_failed", username, "用户不存在")
            return False
        if not _can_manage(caller, target.get("role", "")):
            _audit("delete_user_failed", username, "无权限删除该用户")
            return False
        new_users = [u for u in users if u["username"] != username]
        self._save_users(new_users)
        _audit("delete_user", username)
        return True

    def list_users(self, department: str = "") -> List[User]:
        all_users = [User(**u) for u in self._load_users()]
        if department:
            return [u for u in all_users if u.department == department]
        return all_users

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        ok, reason = validate_password(new_password)
        if not ok:
            _audit("change_password_failed", username, reason)
            return False
        user = self.authenticate(username, old_password)
        if not user:
            _audit("change_password_failed", username, "旧密码错误")
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                u["password_hash"] = _hash_password(new_password)
                self._save_users(users)
                _audit("change_password", username)
                return True
        return False

    @staticmethod
    def check_permission(user: User, action: str) -> bool:
        allowed = _ROLE_PERMISSIONS.get(user.role, set())
        return action in allowed

    @staticmethod
    def get_permissions(role: str) -> set:
        return _ROLE_PERMISSIONS.get(role, set())
