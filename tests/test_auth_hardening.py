"""
认证加固测试 — 登录锁定 / must_change_password / W01/W03/W04/W05
"""

import os
import json
import pytest


def _setup_auth(tmp_path, monkeypatch):
    """通用 setup：重定向 USERS_FILE 和 LOG_FILE 到临时目录"""
    import core.auth as auth_mod
    import core.audit as audit_mod
    monkeypatch.setattr(auth_mod.AuthManager, "USERS_FILE", str(tmp_path / "users.json"))
    monkeypatch.setattr(audit_mod, "LOG_FILE", str(tmp_path / "audit.log"))
    return auth_mod, audit_mod, auth_mod.AuthManager()


# ── 登录锁定 ──────────────────────────────────────────
class TestLoginLockout:
    def test_lockout_after_5_failures(self, tmp_path, monkeypatch):
        """5 次失败后锁定，正确密码也无法登录"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            assert am.authenticate("alice", "wrong") is None
        assert am.is_account_locked("alice") is True
        assert am.authenticate("alice", "Pass1234") is None  # 正确密码也被拒

    def test_lockout_persists_across_instances(self, tmp_path, monkeypatch):
        """锁定状态持久化到 users.json"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("bob", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("bob", "wrong")
        # 重新创建 AuthManager 实例
        am2 = auth_mod.AuthManager()
        assert am2.is_account_locked("bob") is True

    def test_failed_attempts_reset_on_success(self, tmp_path, monkeypatch):
        """成功登录后 failed_attempts 归零"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("carol", "Pass1234", role="analyst")
        am.authenticate("carol", "wrong")  # 1 次失败
        am.authenticate("carol", "Pass1234")  # 成功
        users = am._load_users()
        u = next(x for x in users if x["username"] == "carol")
        assert u["failed_attempts"] == 0

    def test_4_failures_no_lockout(self, tmp_path, monkeypatch):
        """4 次失败不锁定，第 5 次正确密码仍可登录"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("dave", "Pass1234", role="analyst")
        for _ in range(4):
            am.authenticate("dave", "wrong")
        assert am.is_account_locked("dave") is False
        user = am.authenticate("dave", "Pass1234")
        assert user is not None


# ── 解锁 ──────────────────────────────────────────────
class TestUnlock:
    def test_admin_unlock(self, tmp_path, monkeypatch):
        """admin 可以解锁锁定账户"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        assert am.is_account_locked("alice")
        admin = am.authenticate("admin", "admin")
        assert am.unlock_user("alice", caller=admin) is True
        assert am.is_account_locked("alice") is False
        # 解锁后可以登录
        user = am.authenticate("alice", "Pass1234")
        assert user is not None

    def test_dept_admin_cannot_unlock_admin(self, tmp_path, monkeypatch):
        """dept_admin 不能解锁 admin 账户"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        # admin 默认密码是 admin，先改密
        am.create_user("boss", "Pass1234", role="dept_admin")
        boss = am.authenticate("boss", "Pass1234")
        # 锁定 admin（需要先知道 admin 的密码来改它，但我们可以直接操作文件）
        users = am._load_users()
        for u in users:
            if u["username"] == "admin":
                u["locked"] = True
        am._save_users(users)
        assert am.is_account_locked("admin")
        assert am.unlock_user("admin", caller=boss) is False
        assert am.is_account_locked("admin") is True

    def test_unlock_nonexistent_user(self, tmp_path, monkeypatch):
        """解锁不存在的用户返回 False"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        admin = am.authenticate("admin", "admin")
        assert am.unlock_user("ghost", caller=admin) is False


# ── must_change_password ──────────────────────────────
class TestMustChangePassword:
    def test_default_admin_has_flag(self, tmp_path, monkeypatch):
        """默认 admin 的 must_change_password=True"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        users = am.list_users()
        admin = next(u for u in users if u.username == "admin")
        assert admin.must_change_password is True

    def test_reset_password_sets_flag(self, tmp_path, monkeypatch):
        """管理员重置密码后 must_change_password=True"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        admin = am.authenticate("admin", "admin")
        am.reset_password("alice", "NewPass1234", caller=admin)
        users = am._load_users()
        u = next(x for x in users if x["username"] == "alice")
        assert u["must_change_password"] is True

    def test_force_change_password_clears_flag(self, tmp_path, monkeypatch):
        """force_change_password 成功后 must_change_password=False"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        admin = am.authenticate("admin", "admin")
        assert admin.must_change_password is True
        assert am.force_change_password("admin", "NewPass1234") is True
        users = am._load_users()
        u = next(x for x in users if x["username"] == "admin")
        assert u["must_change_password"] is False

    def test_change_password_clears_flag(self, tmp_path, monkeypatch):
        """change_password 成功后 must_change_password=False"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.force_change_password("admin", "Admin1234")  # 先改掉默认密码
        am.reset_password("admin", "TempPass1234")  # 重置 → flag=True
        # 用旧密码（重置后的）改密
        assert am.change_password("admin", "TempPass1234", "FinalPass1234") is True
        users = am._load_users()
        u = next(x for x in users if x["username"] == "admin")
        assert u["must_change_password"] is False

    def test_new_user_no_flag(self, tmp_path, monkeypatch):
        """新建用户的 must_change_password=False"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        users = am.list_users()
        alice = next(u for u in users if u.username == "alice")
        assert alice.must_change_password is False


# ── W03: from_dict 迁移兼容 ───────────────────────────
class TestFromDictMigration:
    def test_old_json_without_new_fields(self, tmp_path, monkeypatch):
        """旧 JSON（无 must_change_password/failed_attempts/locked）能正确加载"""
        auth_mod, _, _ = _setup_auth(tmp_path, monkeypatch)
        # 模拟旧格式数据
        old_data = [{
            "username": "legacy_user",
            "password_hash": "$pbkdf2-sha256$150000$aaa$bbb",
            "role": "analyst",
            "department": "质量部",
            "team": "一组",
            "display_name": "老用户",
            "created_at": "2024-01-01T00:00:00",
        }]
        (tmp_path / "users.json").write_text(json.dumps(old_data), encoding="utf-8")
        am = auth_mod.AuthManager()
        users = am.list_users()
        u = next(x for x in users if x.username == "legacy_user")
        assert u.must_change_password is False  # 默认值
        assert u.failed_attempts == 0
        assert u.locked is False

    def test_json_with_extra_fields(self, tmp_path, monkeypatch):
        """JSON 含未知字段时不崩溃"""
        auth_mod, _, _ = _setup_auth(tmp_path, monkeypatch)
        data = [{
            "username": "test",
            "password_hash": "$pbkdf2-sha256$150000$aaa$bbb",
            "role": "analyst",
            "department": "",
            "team": "",
            "display_name": "test",
            "created_at": "2024-01-01",
            "future_field": "something",  # 未知字段
        }]
        (tmp_path / "users.json").write_text(json.dumps(data), encoding="utf-8")
        am = auth_mod.AuthManager()
        users = am.list_users()
        assert any(u.username == "test" for u in users)


# ── W01: change_password 不产生误导性 login 审计 ──────
class TestChangePasswordAudit:
    def test_no_misleading_login_audit(self, tmp_path, monkeypatch):
        """change_password 不产生 login 成功审计"""
        _, audit_mod, am = _setup_auth(tmp_path, monkeypatch)
        am.force_change_password("admin", "Admin1234")  # 先改默认密码
        am.change_password("admin", "Admin1234", "NewPass1234")
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "change_password" in log_content
        # W01: 不应出现 "admin: login 成功"
        assert "admin: login 成功" not in log_content

    def test_verify_credentials_no_audit(self, tmp_path, monkeypatch):
        """_verify_credentials 不写审计日志"""
        _, audit_mod, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        log_before = (tmp_path / "audit.log").read_text(encoding="utf-8") if (tmp_path / "audit.log").exists() else ""
        am._verify_credentials("alice", "Pass1234")
        log_after = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert log_before == log_after  # 无新增审计


# ── W05: 审计日志轮转 ─────────────────────────────────
class TestAuditRotation:
    def test_log_rotates_when_exceeds_5mb(self, tmp_path, monkeypatch):
        """日志超过 5MB 时轮转归档"""
        _, audit_mod, am = _setup_auth(tmp_path, monkeypatch)
        # 写入超过 5MB 的日志
        log_path = tmp_path / "audit.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("x" * (5 * 1024 * 1024 + 1))
        # 再写一条审计记录，触发轮转
        audit_mod.audit("test_action", "tester", "rotation test")
        # 原日志应被轮转为 .1
        assert (tmp_path / "audit.log.1").exists()
        # 新日志应包含刚写入的记录
        new_content = log_path.read_text(encoding="utf-8")
        assert "test_action" in new_content


# ── W04: 统一审计实现 ─────────────────────────────────
class TestUnifiedAudit:
    def test_auth_uses_core_audit(self, tmp_path, monkeypatch):
        """auth.py 的审计写入 core.audit.LOG_FILE"""
        auth_mod, audit_mod, am = _setup_auth(tmp_path, monkeypatch)
        # 确认 auth_mod 不再有 _LOG_FILE 属性
        assert not hasattr(auth_mod, "_LOG_FILE")
        # 审计记录写入 core.audit.LOG_FILE
        am.create_user("alice", "Pass1234", role="analyst")
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "alice: create_user" in log_content


# ── Commit F: force_change_password 授权校验 (P1-1) ───

class TestForceChangePasswordGuard:
    def test_reject_non_owner_caller(self, tmp_path, monkeypatch):
        """caller 非本人 → 拒绝且不修改密码"""
        auth_mod, audit_mod, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        # 构造 admin 作为 caller
        admin = am.authenticate("admin", "admin")
        assert am.force_change_password("alice", "NewPass99", caller=admin) is False
        assert am.authenticate("alice", "NewPass99") is None  # 密码未变
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "force_change_password_failed" in log_content

    def test_reject_when_not_must_change(self, tmp_path, monkeypatch):
        """非强制改密状态的账户调用 → 拒绝"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("bob", "Pass1234", role="analyst")
        bob = am.authenticate("bob", "Pass1234")  # 新用户无 flag
        assert bob.must_change_password is False
        assert am.force_change_password("bob", "NewPass99", caller=bob) is False

    def test_owner_can_change_when_flagged(self, tmp_path, monkeypatch):
        """本人 + must_change_password → 成功并清除 flag"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        # 手工构造 must_change 用户
        users = am._load_users()
        users.append({"username": "carol", "password_hash": auth_mod._hash_password("Pass1234"),
                      "role": "analyst", "must_change_password": True})
        am._save_users(users)
        carol = am.authenticate("carol", "Pass1234")
        assert carol.must_change_password is True
        assert am.force_change_password("carol", "NewPass99", caller=carol) is True
        assert am.authenticate("carol", "NewPass99") is not None


# ── Commit F: 存量默认密码迁移 (P1-2) ─────────────────

class TestDefaultAdminMigration:
    def test_legacy_admin_default_pw_migrated(self, tmp_path, monkeypatch):
        """存量 admin 仍用默认密码 → 启动时强制改密"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        # 手工构造"旧版" admin 记录（无 must_change_password 字段 = 未改密）
        users = am._load_users()
        u = next(x for x in users if x["username"] == "admin")
        u.pop("must_change_password", None)
        am._save_users(users)
        # 重新构造 AuthManager 触发 _ensure_file → 迁移
        am2 = auth_mod.AuthManager()
        u2 = next(x for x in am2._load_users() if x["username"] == "admin")
        assert u2["must_change_password"] is True

    def test_changed_admin_not_migrated(self, tmp_path, monkeypatch):
        """已改密的 admin → 迁移不动"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        users = am._load_users()
        u = next(x for x in users if x["username"] == "admin")
        u["password_hash"] = auth_mod._hash_password("NewAdmin99")
        u["must_change_password"] = False
        am._save_users(users)
        am2 = auth_mod.AuthManager()
        u2 = next(x for x in am2._load_users() if x["username"] == "admin")
        assert u2["must_change_password"] is False

    def test_migrated_admin_requires_password_change_on_login(self, tmp_path, monkeypatch):
        """迁移后 admin 登录须先改密 (auth 返回 flag)"""
        auth_mod, _, am = _setup_auth(tmp_path, monkeypatch)
        users = am._load_users()
        u = next(x for x in users if x["username"] == "admin")
        u.pop("must_change_password", None)
        am._save_users(users)
        am2 = auth_mod.AuthManager()
        admin = am2.authenticate("admin", "admin")
        assert admin is not None
        assert admin.must_change_password is True


# ── Commit F: unlock caller 必填 + 审计 (P1-3/P2-1) ───

class TestUnlockCallerRequired:
    def test_unlock_without_caller_rejected(self, tmp_path, monkeypatch):
        """caller=None → 拒绝解锁"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        assert am.is_account_locked("alice")
        assert am.unlock_user("alice", caller=None) is False
        assert am.is_account_locked("alice") is True

    def test_unlock_audit_records_operator(self, tmp_path, monkeypatch):
        """解锁审计记录 by=执行者"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        admin = am.authenticate("admin", "admin")
        assert am.unlock_user("alice", caller=admin) is True
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "unlock_user" in log_content and "by=admin" in log_content

    def test_unlock_resets_failed_attempts(self, tmp_path, monkeypatch):
        """解锁后 failed_attempts 归零 (G2 前置)"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        admin = am.authenticate("admin", "admin")
        am.unlock_user("alice", caller=admin)
        users = am._load_users()
        u = next(x for x in users if x["username"] == "alice")
        assert u["failed_attempts"] == 0


# ── Commit F: 边界补充 (G1/G2/G3) ────────────────────

class TestLockoutBoundaries:
    def test_locked_account_attempts_frozen(self, tmp_path, monkeypatch):
        """G1: 锁定后再失败 → 计数冻结 + login_locked 审计"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        am.authenticate("alice", "wrong")  # 第 6 次
        users = am._load_users()
        u = next(x for x in users if x["username"] == "alice")
        assert u["failed_attempts"] == 5  # 冻结
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "login_locked" in log_content

    def test_unlock_then_4_failures_no_relock(self, tmp_path, monkeypatch):
        """G2: 解锁后 4 次失败不锁，第 5 次才锁"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        admin = am.authenticate("admin", "admin")
        am.unlock_user("alice", caller=admin)
        for _ in range(4):
            am.authenticate("alice", "wrong")
        assert am.is_account_locked("alice") is False
        am.authenticate("alice", "wrong")  # 第 5 次
        assert am.is_account_locked("alice") is True

    def test_unknown_user_audit(self, tmp_path, monkeypatch):
        """G3: 用户不存在 → login_failed 用户不存在 审计"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.authenticate("ghost", "x")
        log_content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "用户不存在" in log_content


# ── Commit F: from_dict 容错 / change_password 锁检查 ──

class TestFromDictTolerant:
    def test_list_users_skips_invalid_records(self, tmp_path, monkeypatch):
        """P3-6: 缺 password_hash 的记录被跳过，不崩溃"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        users = am._load_users()
        users.append({"username": "ghost", "role": "analyst"})  # 无 password_hash
        am._save_users(users)
        names = [u.username for u in am.list_users()]
        assert "ghost" not in names
        assert "admin" in names


class TestChangePasswordLocked:
    def test_locked_account_cannot_change_password(self, tmp_path, monkeypatch):
        """P3-5: 锁定账户 change_password 失败"""
        _, _, am = _setup_auth(tmp_path, monkeypatch)
        am.create_user("alice", "Pass1234", role="analyst")
        for _ in range(5):
            am.authenticate("alice", "wrong")
        assert am.change_password("alice", "Pass1234", "NewPass99") is False
