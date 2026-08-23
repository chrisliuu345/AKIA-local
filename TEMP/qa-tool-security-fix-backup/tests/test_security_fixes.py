"""安全修复回归测试: 权限矩阵 / 强制改密 / 锁定 / 密码策略 / DPAPI / 脱敏"""

# ── 权限矩阵 ──

def test_permission_matrix_admin_full():
    from core.auth import AuthManager, User
    admin = User(username="a", password_hash="x", role="admin")
    for perm in ("import", "analyze", "clean", "export", "view",
                 "manage_users", "settings", "share_project", "view_shared"):
        assert AuthManager.check_permission(admin, perm), f"admin 缺 {perm}"


def test_permission_matrix_readonly_restricted():
    from core.auth import AuthManager, User
    ro = User(username="r", password_hash="x", role="readonly")
    for perm in ("export", "view", "view_shared"):
        assert AuthManager.check_permission(ro, perm), f"readonly 缺 {perm}"
    for perm in ("import", "analyze", "clean", "manage_users", "settings", "share_project"):
        assert not AuthManager.check_permission(ro, perm), f"readonly 不应有 {perm}"


def test_permission_dept_admin():
    from core.auth import AuthManager, User
    da = User(username="d", password_hash="x", role="dept_admin")
    assert AuthManager.check_permission(da, "manage_dept_users")
    assert not AuthManager.check_permission(da, "manage_users")
    assert not AuthManager.check_permission(da, "settings")


# ── 密码策略 ──

def test_password_policy():
    from core.password_policy import validate_password, MIN_PASSWORD_LEN
    assert MIN_PASSWORD_LEN == 8
    ok, _ = validate_password("abc12345")
    assert ok
    ok, _ = validate_password("Abc12345")
    assert ok
    # 长度不足
    ok, _ = validate_password("a1b2c3")
    assert not ok
    # 纯字母
    ok, _ = validate_password("abcdefgh")
    assert not ok
    # 纯数字
    ok, _ = validate_password("12345678")
    assert not ok
    # 空
    ok, _ = validate_password("")
    assert not ok


# ── 强制改密 / 锁定 / 密码策略 (AuthManager, 隔离用户文件) ──

def _fresh_manager(tmp_path, monkeypatch):
    import core.auth as auth
    monkeypatch.setattr(auth.AuthManager, "USERS_FILE",
                        str(tmp_path / "users.json"))
    monkeypatch.setattr(auth, "_LOCKOUT_FILE", str(tmp_path / "lockout.json"))
    monkeypatch.setattr(auth, "_login_attempts", {})
    from core.auth import AuthManager
    return AuthManager()


def test_default_admin_must_change(tmp_path, monkeypatch):
    am = _fresh_manager(tmp_path, monkeypatch)
    u = am.authenticate("admin", "admin")
    assert u is not None
    assert u.must_change_password is True


def test_auth_lockout_after_5_failures(tmp_path, monkeypatch):
    import time
    import core.auth as auth
    am = _fresh_manager(tmp_path, monkeypatch)
    for _ in range(5):
        am.authenticate("admin", "wrong")
    assert auth.lockout_remaining("admin") > 0
    # 锁定期内即使密码正确也拒绝
    assert am.authenticate("admin", "admin") is None


def test_lockout_resets_after_window(tmp_path, monkeypatch):
    import time
    import core.auth as auth
    am = _fresh_manager(tmp_path, monkeypatch)
    for _ in range(5):
        am.authenticate("admin", "wrong")
    auth._login_attempts["admin"]["until"] = time.time() - 1
    assert am.authenticate("admin", "admin") is not None


def test_lockout_uses_normalized_key(tmp_path, monkeypatch):
    """M2: 大小写/空白变体共享同一锁定计数，防多键绕过"""
    import core.auth as auth
    am = _fresh_manager(tmp_path, monkeypatch)
    for i in range(5):
        am.authenticate("Admin", "wrong")
    assert auth.lockout_remaining("  admin ") > 0


def test_lockout_persists_across_instances(tmp_path, monkeypatch):
    """M1: 锁定状态持久化到文件，重启/新实例不清零"""
    import core.auth as auth
    _fresh_manager(tmp_path, monkeypatch)
    am = auth.AuthManager()
    for _ in range(5):
        am.authenticate("admin", "wrong")
    # 新实例(如同重启)重新加载
    auth._login_attempts = {}
    am2 = auth.AuthManager()
    assert auth.lockout_remaining("admin") > 0


def test_default_admin_migration_forces_change(tmp_path, monkeypatch):
    """S2: 存量 admin 默认弱口令被标记强制改密"""
    import core.auth as auth
    from core.auth import User
    _fresh_manager(tmp_path, monkeypatch)
    # 手工构造"存量"用户文件: admin 用默认弱口令且 must_change_password=False
    legacy = [User(
        username="admin",
        password_hash=auth._hash_password("admin"),
        role="admin",
        must_change_password=False,
    ).to_dict()]
    with open(tmp_path / "users.json", "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(legacy, f)
    am = auth.AuthManager()  # __init__ 触发迁移
    u = am.authenticate("admin", "admin")
    assert u is not None
    assert u.must_change_password is True


def test_create_user_forces_change(tmp_path, monkeypatch):
    """M3: 新建用户首次登录强制改密"""
    am = _fresh_manager(tmp_path, monkeypatch)
    u = am.create_user("newbie", "Pass1234", role="analyst")
    assert u is not None
    assert u.must_change_password is True


def test_lockout_expired_record_cleaned(tmp_path, monkeypatch):
    """M4: 过期且无计数的记录被清理，防内存膨胀"""
    import time
    import core.auth as auth
    _fresh_manager(tmp_path, monkeypatch)
    auth._login_attempts["ghost"] = {"count": 0, "until": time.time() - 10}
    assert auth.lockout_remaining("ghost") == 0
    assert "ghost" not in auth._login_attempts
    # 若有未完成计数则保留(等待下一次失败到阈值)
    auth._login_attempts["half"] = {"count": 3, "until": time.time() - 10}
    assert auth.lockout_remaining("half") == 0
    assert "half" in auth._login_attempts


def test_create_user_policy_violation_rejected(tmp_path, monkeypatch):
    am = _fresh_manager(tmp_path, monkeypatch)
    assert am.create_user("u1", "weak", role="analyst") is None
    u = am.create_user("u1", "Pass1234", role="analyst")
    assert u is not None and u.username == "u1"


def test_reset_password_forces_change(tmp_path, monkeypatch):
    am = _fresh_manager(tmp_path, monkeypatch)
    assert am.reset_password("admin", "NewPass1") is True
    u = am.authenticate("admin", "NewPass1")
    assert u is not None and u.must_change_password is True


def test_change_password_clears_flag(tmp_path, monkeypatch):
    am = _fresh_manager(tmp_path, monkeypatch)
    u = am.authenticate("admin", "admin")
    assert u.must_change_password is True
    assert am.change_password("admin", "admin", "NewPass1") is True
    u2 = am.authenticate("admin", "NewPass1")
    assert u2 is not None and u2.must_change_password is False


# ── DPAPI 密码存储 ──

def test_secret_store_roundtrip():
    from core.secret_store import encrypt_secret, decrypt_secret
    enc = encrypt_secret("S3cret@!db")
    assert enc.startswith("dpapi:")
    assert decrypt_secret(enc) == "S3cret@!db"


def test_secret_store_garbage_returns_empty():
    from core.secret_store import decrypt_secret
    assert decrypt_secret("not-valid-base64-###") == ""
    assert decrypt_secret("") == ""


# ── SQL 连接串脱敏 ──

def test_sanitize_connection_error_masks_password():
    from core.sql_loader import sanitize_connection_error
    err = Exception("(sqlite3.OperationalError) near '...' / connection string: "
                    "mysql://root:secret123@127.0.0.1:3306/db")
    out = sanitize_connection_error(err)
    assert "secret123" not in out
    assert "root" in out or "******" in out