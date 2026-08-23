"""
多用户认证 — PBKDF2-SHA256 哈希 + 四级角色权限
"""

import json
import os
import hashlib
import base64
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.password_policy import validate_password
from core.audit import audit as _audit  # W04: 统一审计实现


# 简易 bcrypt-lite: 使用 PBKDF2-SHA256 替代 bcrypt（无额外依赖）
# 格式: $pbkdf2-sha256$rounds$salt_base64$hash_base64
_PBKDF2_ROUNDS = 150000
_MAX_FAILED_ATTEMPTS = 5  # 连续登录失败锁定阈值


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
    must_change_password: bool = False   # 首次登录/重置后强制改密
    failed_attempts: int = 0             # 连续登录失败次数
    locked: bool = False                 # 账户锁定状态

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        """从字典构造 User，忽略未知字段，缺失字段用默认值（W03 迁移兼容）
        缺 password_hash 视为非法记录 (P3-6)，由调用方捕获跳过"""
        if not d.get("password_hash"):
            raise ValueError("缺少 password_hash")
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "department": self.department,
            "team": self.team,
            "display_name": self.display_name or self.username,
            "created_at": self.created_at,
            "must_change_password": self.must_change_password,
            "failed_attempts": self.failed_attempts,
            "locked": self.locked,
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
    "admin":       {"import", "analyze", "clean", "export", "view", "account",
                    "manage_users", "settings", "share_project", "view_shared"},
    "dept_admin":  {"import", "analyze", "clean", "export", "view", "account",
                    "manage_dept_users", "share_project", "view_shared"},
    "analyst":     {"import", "analyze", "clean", "export", "view", "account",
                    "share_project", "view_shared"},
    "readonly":    {"export", "view", "view_shared", "account"},
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
            return
        self._migrate_default_admin()

    def _migrate_default_admin(self):
        """存量部署迁移 (P1-2): admin 仍使用默认密码时强制改密"""
        try:
            users = self._read_users_file()
        except Exception:
            return
        changed = False
        for u in users:
            if u.get("username") == "admin" and not u.get("must_change_password", False):
                if _verify_password("admin", u.get("password_hash", "")):
                    u["must_change_password"] = True
                    changed = True
        if changed:
            try:
                self._save_users(users)
                _audit("auth_migrate", "system", "检测到 admin 默认密码，已启用强制改密")
            except OSError:
                pass

    def _init_default_admin(self):
        admin = User(
            username="admin",
            password_hash=_hash_password("admin"),
            role="admin",
            department="",
            team="",
            display_name="系统管理员",
            created_at=datetime.now().isoformat(),
            must_change_password=True,  # 首次登录强制改密
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

    def _verify_credentials(self, username: str, password: str) -> Optional[dict]:
        """验证凭据但不审计、不修改失败计数（W01: 供 change_password 内部调用）"""
        users = self._load_users()
        for u in users:
            if u["username"] == username and _verify_password(password, u["password_hash"]):
                return u
        return None

    def authenticate(self, username: str, password: str) -> Optional[User]:
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                if u.get("locked", False):
                    _audit("login_locked", username, "账户已锁定，拒绝登录")
                    return None
                if _verify_password(password, u["password_hash"]):
                    if u.get("failed_attempts", 0) > 0:
                        u["failed_attempts"] = 0
                        self._save_users(users)
                    _audit("login", username, "成功")
                    return User.from_dict(u)
                else:
                    u["failed_attempts"] = u.get("failed_attempts", 0) + 1
                    if u["failed_attempts"] >= _MAX_FAILED_ATTEMPTS:
                        u["locked"] = True
                        _audit("login_locked", username, f"连续失败{u['failed_attempts']}次，已锁定")
                    else:
                        _audit("login_failed", username, f"失败{u['failed_attempts']}次")
                    self._save_users(users)
                    return None
        _audit("login_failed", username, "用户不存在")
        return None

    def is_account_locked(self, username: str) -> bool:
        """检查账户是否已锁定（供登录界面区分提示）"""
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                return u.get("locked", False)
        return False

    def unlock_user(self, username: str, caller: User) -> bool:
        """管理员解锁用户账户 (P1-3: caller 必填, 拒绝隐式放行)"""
        if caller is None:
            _audit("unlock_user_failed", username, "缺少操作者身份")
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                if not _can_manage(caller, u.get("role", "")):
                    _audit("unlock_user_failed", username, "无权限解锁该用户")
                    return False
                u["locked"] = False
                u["failed_attempts"] = 0
                self._save_users(users)
                _audit("unlock_user", username, f"by={caller.username}")
                return True
        return False

    def force_change_password(self, username: str, new_password: str,
                              caller: Optional[User] = None) -> bool:
        """强制修改密码（must_change_password 场景，不需要旧密码）
        P1-1: 仅允许账户本人且处于 must_change_password 状态时执行"""
        if caller is not None and caller.username != username:
            _audit("force_change_password_failed", username, "仅限账户本人修改")
            return False
        ok, reason = validate_password(new_password)
        if not ok:
            _audit("force_change_password_failed", username, reason)
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                if not u.get("must_change_password", False):
                    _audit("force_change_password_failed", username, "账户不处于强制改密状态")
                    return False
                u["password_hash"] = _hash_password(new_password)
                u["must_change_password"] = False
                self._save_users(users)
                _audit("force_change_password", username)
                return True
        return False

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
                u["must_change_password"] = True  # 重置后强制改密
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
        all_users = []
        for u in self._load_users():
            try:
                all_users.append(User.from_dict(u))
            except ValueError:
                # P3-6: 跳过缺 password_hash 的非法记录，避免列表崩溃
                continue
        if department:
            return [u for u in all_users if u.department == department]
        return all_users

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        ok, reason = validate_password(new_password)
        if not ok:
            _audit("change_password_failed", username, reason)
            return False
        # P3-5: 锁定账户不允许改密（后端守卫一致性）
        if self.is_account_locked(username):
            _audit("change_password_failed", username, "账户已锁定")
            return False
        # W01: 使用 _verify_credentials 而非 authenticate，避免产生误导性 login 审计
        user_dict = self._verify_credentials(username, old_password)
        if not user_dict:
            _audit("change_password_failed", username, "旧密码错误")
            return False
        users = self._load_users()
        for u in users:
            if u["username"] == username:
                u["password_hash"] = _hash_password(new_password)
                u["must_change_password"] = False
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
