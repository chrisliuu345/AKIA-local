"""
多用户认证 — bcrypt 哈希 + 三级角色权限
"""

import json
import os
import hashlib
import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

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

    def _load_users(self) -> List[dict]:
        try:
            with open(self.USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
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
                return User(**u)
        return None

    def create_user(self, username: str, password: str, role: str = "analyst",
                     department: str = "", team: str = "", display_name: str = "") -> Optional[User]:
        if role not in _ROLE_PERMISSIONS:
            raise ValueError(f"无效角色: {role}")
        users = self._load_users()
        if any(u["username"] == username for u in users):
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
        return user

    def update_user(self, username: str, **kwargs) -> bool:
        """更新用户属性（角色/部门/班组/显示名称），不修改密码"""
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                for k in ("role", "department", "team", "display_name"):
                    if k in kwargs and kwargs[k]:
                        u[k] = kwargs[k]
                self._save_users(users)
                return True
        return False

    def reset_password(self, username: str, new_password: str) -> bool:
        """管理员重置用户密码"""
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                u["password_hash"] = _hash_password(new_password)
                self._save_users(users)
                return True
        return False

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            return False
        users = self._load_users()
        new_users = [u for u in users if u["username"] != username]
        if len(new_users) == len(users):
            return False
        self._save_users(new_users)
        return True

    def list_users(self, department: str = "") -> List[User]:
        all_users = [User(**u) for u in self._load_users()]
        if department:
            return [u for u in all_users if u.department == department]
        return all_users

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        user = self.authenticate(username, old_password)
        if not user:
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                u["password_hash"] = _hash_password(new_password)
                self._save_users(users)
                return True
        return False

    @staticmethod
    def check_permission(user: User, action: str) -> bool:
        allowed = _ROLE_PERMISSIONS.get(user.role, set())
        return action in allowed

    @staticmethod
    def get_permissions(role: str) -> set:
        return _ROLE_PERMISSIONS.get(role, set())
