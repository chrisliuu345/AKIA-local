"""test_settings_config.py — 配置文件分层与敏感键加密

覆盖 v3.7.1 S1:
- user_config.default.json（随包公共默认）+ user_config.json（本机）叠加
- save_config 只写本机文件，不把默认值落盘
- 敏感键（*_password/_secret/_token/_api_key）自动改存 <key>_enc
- get_secret 优先解密，兼容旧版明文
"""

import json

import pytest


@pytest.fixture(scope="module", autouse=True)
def _restore_real_config():
    """模块结束后恢复真实配置路径下的状态（函数级 monkeypatch 已还原路径）"""
    yield
    from config import settings
    settings.load_config()


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    """隔离配置路径的 settings 模块，测试后恢复真实配置"""
    from config import settings

    default_path = tmp_path / "user_config.default.json"
    user_path = tmp_path / "user_config.json"
    monkeypatch.setattr(settings, "_DEFAULT_CONFIG_PATH", str(default_path))
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(user_path))
    yield settings, default_path, user_path


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


class TestConfigLayering:
    def test_defaults_used_when_user_file_missing(self, cfg):
        settings, default_path, user_path = cfg
        _write(default_path, {"chart_dpi": 150, "esp32_extension": False})

        merged = settings.load_config()

        assert merged["chart_dpi"] == 150
        assert settings.get_setting("chart_dpi") == 150
        assert settings.get_setting("missing_key", "fallback") == "fallback"
        assert settings.esp32_extension_enabled() is False

    def test_user_file_overrides_defaults(self, cfg):
        settings, default_path, user_path = cfg
        _write(default_path, {"chart_dpi": 120, "msa_ndc_threshold": 5})
        _write(user_path, {"chart_dpi": 200})

        settings.load_config()

        assert settings.get_setting("chart_dpi") == 200
        assert settings.get_setting("msa_ndc_threshold") == 5

    def test_corrupted_json_falls_back_to_defaults(self, cfg):
        settings, default_path, user_path = cfg
        _write(default_path, {"chart_dpi": 120})
        user_path.write_text("{ not json", encoding="utf-8")

        merged = settings.load_config()

        assert merged["chart_dpi"] == 120

    def test_save_config_writes_user_file_only(self, cfg):
        settings, default_path, user_path = cfg
        _write(default_path, {"chart_dpi": 120, "esp32_extension": True})
        settings.load_config()

        settings.save_config({"chart_dpi": 180})

        saved = json.loads(user_path.read_text(encoding="utf-8"))
        assert saved == {"chart_dpi": 180}
        assert "esp32_extension" not in saved, "默认值不应写入本机配置"


class TestSecretProtection:
    def test_secret_key_saved_encrypted(self, cfg, monkeypatch):
        settings, default_path, user_path = cfg
        _write(default_path, {})
        settings.load_config()

        import core.secret_store as secret_store
        monkeypatch.setattr(secret_store, "encrypt_secret",
                            lambda text: f"enc({text})")
        monkeypatch.setattr(secret_store, "decrypt_secret",
                            lambda stored: stored[4:-1] if stored.startswith("enc(") else "")

        settings.save_config({"alert_smtp_password": "S3cret!"})

        saved = json.loads(user_path.read_text(encoding="utf-8"))
        assert "alert_smtp_password" not in saved
        assert saved["alert_smtp_password_enc"] == "enc(S3cret!)"
        assert settings.get_secret("alert_smtp_password") == "S3cret!"

    def test_plaintext_secret_still_readable(self, cfg):
        """旧版本明文配置保持可读（向后兼容）"""
        settings, default_path, user_path = cfg
        _write(default_path, {})
        _write(user_path, {"alert_smtp_password": "legacy-pw"})

        settings.load_config()

        assert settings.get_secret("alert_smtp_password") == "legacy-pw"

    def test_is_secret_key_suffixes(self, cfg):
        settings, _default_path, _user_path = cfg
        assert settings.is_secret_key("alert_smtp_password")
        assert settings.is_secret_key("openai_api_key")
        assert settings.is_secret_key("webhook_token")
        assert not settings.is_secret_key("chart_dpi")
        assert not settings.is_secret_key("alert_smtp_host")
