"""v4.0.0 P4 — 预测分析 Tab（注册接线 / 训练 / 展示 / 模型保存加载）。"""

import os
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest
from PySide6.QtCore import Qt

pytest.importorskip("PySide6")

from ui.tabs.predictive_tab import PredictiveTab


@pytest.fixture
def frame():
    rng = np.random.default_rng(61)
    n = 160
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    return pd.DataFrame({
        "温度": x1,
        "压力": x2,
        "产线": rng.choice(["L1", "L2"], n),
        "强度": 2 * x1 + x2 + rng.normal(0, 0.4, n),
        "判定": np.where(x1 + x2 > 0, "PASS", "FAIL"),
    })


def test_registry_and_sidebar_wiring():
    from ui._tab_registry import INDEX_MAP, TAB_INDEX, TAB_COUNT
    from ui.main_window import _PLUGIN_TAB_START

    assert 37 in INDEX_MAP
    entry = INDEX_MAP[37]
    assert entry[2] == "PredictiveTab"
    assert entry[3] == "ui.tabs.predictive_tab"
    assert TAB_INDEX["predictive"] == 37
    assert TAB_COUNT >= 37
    assert _PLUGIN_TAB_START == 38       # 插件 Tab 自动顺延

    from ui.sidebar import CATEGORIES
    quality = next(c for c in CATEGORIES if c["key"] == "sidebar.quality_tools")
    # 时间序列与预测分析同属质量工具；侧栏清单与注册表、分析菜单必须一起出现。
    assert (36, "sidebar.time_series") in quality["items"]
    assert (37, "sidebar.predictive") in quality["items"]

    from core.i18n import i18n
    assert i18n.tr("sidebar.predictive") == "预测分析"


def test_tab_populates_controls(frame):
    tab = PredictiveTab()
    tab.set_data(frame)
    assert tab.target_combo.count() == len(frame.columns)
    assert tab.target_combo.currentText() == "判定" or tab.target_combo.currentText()
    assert tab.feature_list.count() == len(frame.columns) - 1
    checked = tab._selected_features()
    assert "温度" in checked and "压力" in checked
    assert "产线" not in checked            # 分类列默认不勾选
    tab.deleteLater()


def test_run_and_display_regression(frame):
    tab = PredictiveTab()
    tab.set_data(frame)
    tab.target_combo.setCurrentText("强度")
    tab.model_combo.setCurrentIndex(0)       # CART
    tab.cv_spin.setValue(3)
    result = tab.run_and_display()
    assert result is not None
    assert result["task"] == "regression"
    assert result["metrics"]["test"]["r2"] > 0.7
    assert tab.current_result["analysis_type"] == "ml.tree"
    assert tab.prediction_table.rowCount() > 0
    assert tab.canvas is not None
    # 结果必须可 JSON 序列化（项目保存 / 会话历史）
    assert json.dumps(tab.current_result, ensure_ascii=False)
    tab.deleteLater()


def test_run_and_display_classification(frame):
    tab = PredictiveTab()
    tab.set_data(frame)
    tab.target_combo.setCurrentText("判定")
    tab.model_combo.setCurrentIndex(1)       # 随机森林
    tab.cv_spin.setValue(3)
    result = tab.run_and_display()
    assert result is not None
    assert result["task"] == "classification"
    assert result["metrics"]["test"]["accuracy"] > 0.7
    assert tab.prediction_table.columnCount() >= 2
    tab.deleteLater()


def test_validation_and_model_roundtrip(frame, tmp_path):
    tab = PredictiveTab()
    tab.set_data(frame)
    for i in range(tab.feature_list.count()):
        tab.feature_list.item(i).setCheckState(Qt.Unchecked)
    ok, message = tab.validate_params()
    assert ok is False and "特征列" in message

    tab.set_data(frame)
    tab.target_combo.setCurrentText("强度")
    tab.model_combo.setCurrentIndex(0)
    tab.cv_spin.setValue(3)
    path = tab.save_model_to(str(tmp_path / "strength"))
    assert path.endswith(".qamodel")

    other = PredictiveTab()
    other.set_data(frame)
    bundle = other.load_model_from(path)
    assert bundle["target"] == "强度"
    predictions = other.predict_with_loaded()
    assert predictions is not None and len(predictions) == len(frame)
    assert other.prediction_table.rowCount() == len(frame)
    tab.deleteLater()
    other.deleteLater()
