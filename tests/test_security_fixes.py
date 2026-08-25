"""v2.6.1 安全校验回归测试: 密码策略 / DPAPI 凭据存储 / SQL 连接串脱敏"""


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
