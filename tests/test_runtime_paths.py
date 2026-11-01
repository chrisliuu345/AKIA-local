"""源码/冻结安装包的数据目录与旧文件迁移回归。"""
import sys
from pathlib import Path

from core import runtime_paths


def _clear_overrides(monkeypatch):
    monkeypatch.delenv("AKIA_DATA_DIR", raising=False)
    monkeypatch.delenv("QA_TOOL_DATA_DIR", raising=False)


def test_source_run_keeps_repository_data_dir(monkeypatch):
    _clear_overrides(monkeypatch)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert runtime_paths.default_data_dir() == runtime_paths._PACKAGED_DATA_DIR


def test_frozen_linux_uses_xdg_data_home(monkeypatch, tmp_path):
    _clear_overrides(monkeypatch)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert runtime_paths.default_data_dir() == tmp_path / "AKIA"


def test_frozen_windows_uses_local_appdata(monkeypatch, tmp_path):
    _clear_overrides(monkeypatch)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert runtime_paths.default_data_dir() == tmp_path / "AKIA"


def test_data_dir_override_supports_portable_install(monkeypatch, tmp_path):
    monkeypatch.setenv("AKIA_DATA_DIR", str(tmp_path))
    assert runtime_paths.default_data_dir() == tmp_path


def test_packaged_file_is_migrated_without_deleting_original(monkeypatch, tmp_path):
    legacy_dir = tmp_path / "installed" / "data"
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "plant.json"
    legacy.write_text('{"lines": []}', encoding="utf-8")
    target_dir = tmp_path / "user" / "data"
    monkeypatch.setattr(runtime_paths, "_PACKAGED_DATA_DIR", legacy_dir)
    monkeypatch.setenv("AKIA_DATA_DIR", str(target_dir))

    target = runtime_paths.default_data_path("plant.json")

    assert target == target_dir / "plant.json"
    assert target.read_text(encoding="utf-8") == '{"lines": []}'
    assert legacy.exists()


def test_data_filename_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("AKIA_DATA_DIR", str(tmp_path))
    try:
        runtime_paths.default_data_path("../outside.db")
    except ValueError as exc:
        assert "不能包含目录" in str(exc)
    else:
        raise AssertionError("目录穿越文件名必须被拒绝")


def test_runtime_components_share_user_data_dir(monkeypatch, tmp_path):
    from core.plant import default_plant_path
    from core.storage.timeseries import default_store_path
    from core.streaming.alert_journal import default_journal_path

    monkeypatch.setenv("AKIA_DATA_DIR", str(tmp_path))
    assert default_plant_path() == tmp_path / "plant.json"
    assert default_journal_path() == tmp_path / "alerts.jsonl"
    assert default_store_path() == tmp_path / "timeseries.db"


def test_timeseries_migration_includes_sqlite_sidecars(monkeypatch, tmp_path):
    from core.storage.timeseries import default_store_path

    legacy_dir = tmp_path / "installed" / "data"
    legacy_dir.mkdir(parents=True)
    for suffix in ("", "-wal", "-shm"):
        (legacy_dir / f"timeseries.db{suffix}").write_bytes(suffix.encode() or b"db")
    target_dir = tmp_path / "user" / "data"
    monkeypatch.setattr(runtime_paths, "_PACKAGED_DATA_DIR", legacy_dir)
    monkeypatch.setenv("AKIA_DATA_DIR", str(target_dir))

    target = default_store_path()

    assert target.read_bytes() == b"db"
    assert Path(f"{target}-wal").read_bytes() == b"-wal"
    assert Path(f"{target}-shm").read_bytes() == b"-shm"
