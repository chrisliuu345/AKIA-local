"""v4.1.0 打包就绪 — 用户配置路径（源码 / 打包 / 环境变量）与迁移。"""

import json
import os
import sys

import config.settings as settings


def test_source_run_uses_repo_root(monkeypatch):
    monkeypatch.delenv("QA_TOOL_USER_CONFIG", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    path = settings._default_user_config_path()
    assert path.endswith("user_config.json")
    assert not path.endswith("user_config.default.json")
    assert os.path.basename(os.path.dirname(path)) == "QA-Tool"


def test_frozen_linux_uses_xdg_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("QA_TOOL_USER_CONFIG", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = settings._default_user_config_path()
    assert path == str(tmp_path / "QA-Tool" / "user_config.json")


def test_frozen_windows_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("QA_TOOL_USER_CONFIG", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = settings._default_user_config_path()
    assert path == str(tmp_path / "QA-Tool" / "user_config.json")


def test_env_override_wins(monkeypatch, tmp_path):
    target = tmp_path / "portable.json"
    monkeypatch.setenv("QA_TOOL_USER_CONFIG", str(target))
    assert settings._default_user_config_path() == str(target)


def test_save_config_creates_missing_parent(monkeypatch, tmp_path):
    target = tmp_path / "nested" / "dir" / "user_config.json"
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_user_overrides", {})
    settings.save_config({"chart_dpi": 111})
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["chart_dpi"] == 111


def test_legacy_config_migrates_to_user_dir(monkeypatch, tmp_path):
    app_dir = tmp_path / "app"
    (app_dir / "config").mkdir(parents=True)
    legacy = app_dir / "user_config.json"
    legacy.write_text('{"chart_theme": "light"}', encoding="utf-8")
    monkeypatch.setattr(settings, "_CONFIG_DIR", str(app_dir / "config"))
    target = tmp_path / "user" / "user_config.json"

    settings._migrate_legacy_user_config(str(target))
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["chart_theme"] == "light"

    # 已存在目标文件时不覆盖
    target.write_text('{"chart_theme": "dark"}', encoding="utf-8")
    settings._migrate_legacy_user_config(str(target))
    assert json.loads(target.read_text(encoding="utf-8"))["chart_theme"] == "dark"
