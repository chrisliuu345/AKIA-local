"""数据库导入被行数上限截断时：弹警告，并把截断事实写进导入证据。"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

import pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture
def window(_qt_application):
    from ui.main_window import MainWindow

    win = MainWindow()
    QApplication.processEvents()
    yield win
    win.close()
    win.deleteLater()


def _patch_db(monkeypatch, truncated: list[str]):
    config = {"db_type": "mysql", "host": "h", "port": 3306,
              "database": "demo", "user": "u", "password": "p"}

    class _Dialog:
        def __init__(self, parent=None):
            pass

        def exec(self):
            return True

        def get_selection(self):
            return config, ["readings"]

    class _Loader:
        def __init__(self):
            self.metadata = {}

        def connect(self, cfg):
            return True

        def load(self, names):
            self.metadata = {"total_rows": 3, "truncated_tables": list(truncated),
                             "row_limit": 3}
            return {"readings": pd.DataFrame({"x": [1.0, 2.0, 3.0]})}

        def disconnect(self):
            pass

    monkeypatch.setattr("ui.dialogs.db_connection_dialog.DbConnectionDialog", _Dialog)
    monkeypatch.setattr("core.sql_loader.SqlLoader", _Loader)


def test_truncated_import_warns_and_records_evidence(window, monkeypatch):
    _patch_db(monkeypatch, ["readings"])
    warnings, recorded = [], []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a[2])))
    monkeypatch.setattr(window, "_record_data_imported",
                        lambda *a, **k: recorded.append(k))
    window._on_import_db()
    assert warnings and "readings" in warnings[0] and "3" in warnings[0]
    assert recorded[0]["extra"] == {"truncated_tables": ["readings"], "row_limit": 3}


def test_complete_import_does_not_warn(window, monkeypatch):
    _patch_db(monkeypatch, [])
    warnings, recorded = [], []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))
    monkeypatch.setattr(window, "_record_data_imported",
                        lambda *a, **k: recorded.append(k))
    window._on_import_db()
    assert warnings == []
    assert recorded[0]["extra"] is None
