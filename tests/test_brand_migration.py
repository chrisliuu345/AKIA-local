"""旧版数据兼容层测试 — 旧格式仍可读，新格式写入生效。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import joblib


def test_legacy_user_config_env_still_honoured(monkeypatch):
    import config.settings as settings

    monkeypatch.delenv("AKIA_USER_CONFIG", raising=False)
    monkeypatch.setenv("QA_TOOL_USER_CONFIG", "/tmp/legacy-user-config.json")
    assert settings._default_user_config_path() == "/tmp/legacy-user-config.json"


def test_new_user_config_env_wins_over_legacy(monkeypatch):
    import config.settings as settings

    monkeypatch.setenv("AKIA_USER_CONFIG", "/tmp/new.json")
    monkeypatch.setenv("QA_TOOL_USER_CONFIG", "/tmp/legacy.json")
    assert settings._default_user_config_path() == "/tmp/new.json"


_STORE: dict = {}


class _FakeQSettings:
    """QSettings 替身 — 沙箱内 ~/.config 只读，用内存存储做确定性单测。"""

    def __init__(self, organization: str, application: str):
        self.data = _STORE.setdefault((organization, application), {})

    def value(self, key, default=None, type=None):
        value = self.data.get(key, default)
        return bool(value) if type is bool else value

    def allKeys(self):
        return list(self.data)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        pass


def test_qsettings_migration_copies_legacy_org(monkeypatch):
    from core import settings_migration

    _STORE.clear()
    monkeypatch.setattr(settings_migration, "QSettings", _FakeQSettings)
    _FakeQSettings("QA-Tool", "LLM").setValue("model", "legacy-model")

    migrated = settings_migration.migrate_legacy_qsettings(("LLM",))
    current = _FakeQSettings("AKIA", "LLM")
    assert current.value("model") == "legacy-model"
    assert migrated == 1

    # 新组已有数据时不覆盖（第二次调用因迁移标记直接跳过）
    assert settings_migration.migrate_legacy_qsettings(("LLM",)) == 0


def test_legacy_model_format_still_loads(tmp_path):
    from analysis.ml import persist

    payload = {
        "format": "qa-tool-model",
        "format_version": 1,
        "pipeline": None,
        "task": "regression",
        "target": "y",
        "features": ["x"],
    }
    path = tmp_path / "legacy.qamodel"
    joblib.dump(payload, path)

    bundle = persist.load_model(path)
    assert bundle["format"] == "qa-tool-model"
    assert persist.FORMAT_NAME == "akia-model"
    assert persist.MODEL_EXT == ".qamodel"


def test_plugin_api_legacy_entry_point_group_and_alias():
    from core import plugin_api

    assert plugin_api.PLUGIN_ENTRY_POINT_GROUP == "akia.plugins"
    assert plugin_api.LEGACY_PLUGIN_ENTRY_POINT_GROUP == "qa_tool.plugins"
    assert plugin_api.IQAToolPlugin is plugin_api.IAKIAPlugin


def test_user_plugin_dirs_include_legacy_dir(monkeypatch):
    from core import plugin_manager

    monkeypatch.delenv("AKIA_PLUGIN_DIRS", raising=False)
    monkeypatch.delenv("QA_TOOL_PLUGIN_DIRS", raising=False)
    dirs = {str(p) for p in plugin_manager._user_plugin_dirs()}
    assert any(d.endswith(".akia_plugins") for d in dirs)
    assert any(d.endswith(".qa_tool_plugins") for d in dirs)


def test_default_runtime_paths_use_new_brand():
    from core import audit, batch_scheduler, project_manager, settings_migration

    assert audit.LOG_FILE.endswith(".akia_audit.log")
    assert batch_scheduler.BatchScheduler.TASKS_FILE.endswith(
        os.path.join(".akia_batch", "tasks.json"))
    assert project_manager.SHARED_DIR.endswith(".akia_shared")
    assert set(settings_migration.LEGACY_GROUPS) >= {
        "MainWindow", "RecentProjects", "Dashboard",
        "DBConnections", "Formulas", "LLM",
    }
