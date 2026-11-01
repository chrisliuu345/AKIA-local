"""数据资产主窗口入口与项目恢复回归。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QFileDialog, QMessageBox


def test_main_window_exports_and_imports_qda(tmp_path, monkeypatch, _qt_application):
    from core.project_context import QualityCharacteristic
    from ui.main_window import MainWindow

    target = tmp_path / "assets.qda"
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a: (_ for _ in ()).throw(AssertionError(a[-1]))))
    window = MainWindow()
    try:
        window.current_data = {"raw_data": {"Sheet1": pd.DataFrame({"x": [1, 2]})}}
        window.project_context.add_characteristic(QualityCharacteristic(id="QC-1", name="x"))
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            staticmethod(lambda *a, **k: (str(target), "qda")))
        window._on_export_data_asset()
        assert target.exists()

        window.current_data = {}
        window.project_context.characteristics.clear()
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, **k: (str(target), "qda")))
        window._on_import_data_asset()
        assert window.current_data["raw_data"]["Sheet1"]["x"].tolist() == [1, 2]
        assert window.project_context.characteristics[0].id == "QC-1"
    finally:
        window.close()


def test_data_asset_actions_registered(_qt_application):
    from PySide6.QtGui import QAction
    from ui.main_window import MainWindow

    window = MainWindow()
    try:
        assert window.findChild(QAction, "exportDataAssetAction") is not None
        assert window.findChild(QAction, "importDataAssetAction") is not None
        labels = [entry["label"] for entry in window._build_command_entries()]
        assert "导出本地数据资产" in labels
        assert "导入本地数据资产" in labels
    finally:
        window.close()
