"""预测分析页（v4.0.0）— 数据准备 / 训练 / 评估 / 预测。

模型: 线性/逻辑回归 · CART · 随机森林 · 梯度提升 · MARS（仅回归）
训练在后台线程执行（按钮触发），run_and_display() 为同步入口（批量分析/测试）。
"""

from typing import Any

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from analysis.ml import boosting, forest, mars, persist, train as ml_train, trees
from ui.font_config import get_ui_font
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY

MODEL_OPTIONS = [
    ("CART 决策树", "tree"),
    ("随机森林", "forest"),
    ("梯度提升", "boosting"),
    ("MARS（仅回归）", "mars"),
    ("线性 / 逻辑回归", "linear"),
]
TASK_OPTIONS = [("自动判定", "auto"), ("回归", "regression"), ("分类", "classification")]
_NON_SERIALIZABLE = {"pipeline", "X_train", "X_test", "y_train", "y_test"}


class _TrainWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, job, parent=None):
        super().__init__(parent)
        self._job = job

    def run(self):
        try:
            self.done.emit(self._job())
        except Exception as exc:  # noqa: BLE001 - 主线程统一展示错误
            self.failed.emit(str(exc))


class PredictiveTab(BaseAnalysisTab):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df: pd.DataFrame | None = None
        self.parsed_info: dict[str, Any] = {}
        self.current_result: dict[str, Any] = {}
        self.current_figure = None
        self.canvas = None
        self._worker: _TrainWorker | None = None
        self._model_bundle: dict[str, Any] | None = None
        self._setup_ui()

    # ---------------- UI ----------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("预测分析（机器学习）")
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)

        top_layout = QHBoxLayout()
        config_group = QGroupBox("建模配置")
        config_layout = QFormLayout(config_group)
        config_layout.setContentsMargins(10, 10, 10, 10)

        self.target_combo = QComboBox()
        self.target_combo.currentTextChanged.connect(self._refresh_feature_list)
        config_layout.addRow("目标列:", self.target_combo)

        self.task_combo = QComboBox()
        for label, value in TASK_OPTIONS:
            self.task_combo.addItem(label, value)
        config_layout.addRow("任务类型:", self.task_combo)

        self.model_combo = QComboBox()
        for label, value in MODEL_OPTIONS:
            self.model_combo.addItem(label, value)
        config_layout.addRow("模型:", self.model_combo)

        self.cv_spin = QSpinBox()
        self.cv_spin.setRange(2, 10)
        self.cv_spin.setValue(5)
        config_layout.addRow("交叉验证折数:", self.cv_spin)

        self.test_spin = QDoubleSpinBox()
        self.test_spin.setRange(0.1, 0.5)
        self.test_spin.setSingleStep(0.05)
        self.test_spin.setValue(0.2)
        config_layout.addRow("测试集比例:", self.test_spin)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 99999)
        self.seed_spin.setValue(42)
        config_layout.addRow("随机种子:", self.seed_spin)

        self.run_btn = QPushButton("开始训练")
        self.run_btn.setFont(QFont(get_ui_font(), 12, QFont.Bold))
        self.run_btn.setMinimumHeight(42)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.run_btn.clicked.connect(self._on_run_clicked)
        config_layout.addRow(self.run_btn)

        self.save_model_btn = QPushButton("保存模型 (.qamodel)")
        self.save_model_btn.setMinimumHeight(38)
        self.save_model_btn.setStyleSheet(BUTTON_SECONDARY)
        self.save_model_btn.clicked.connect(self._on_save_model)
        config_layout.addRow(self.save_model_btn)

        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.setMinimumHeight(38)
        self.load_model_btn.setStyleSheet(BUTTON_SECONDARY)
        self.load_model_btn.clicked.connect(self._on_load_model)
        config_layout.addRow(self.load_model_btn)

        self.predict_btn = QPushButton("用已加载模型预测")
        self.predict_btn.setMinimumHeight(38)
        self.predict_btn.setStyleSheet(BUTTON_SECONDARY)
        self.predict_btn.clicked.connect(self.predict_with_loaded)
        config_layout.addRow(self.predict_btn)

        self.export_btn = QPushButton("导出预测结果")
        self.export_btn.setMinimumHeight(38)
        self.export_btn.setStyleSheet(BUTTON_SECONDARY)
        self.export_btn.clicked.connect(self._on_export_predictions)
        config_layout.addRow(self.export_btn)
        top_layout.addWidget(config_group)

        feature_group = QGroupBox("特征列")
        feature_layout = QVBoxLayout(feature_group)
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QAbstractItemView.NoSelection)
        feature_layout.addWidget(self.feature_list)
        top_layout.addWidget(feature_group)

        info_group = QGroupBox("结果摘要")
        info_layout = QVBoxLayout(info_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont(get_ui_font(), 12))
        info_layout.addWidget(self.result_text)
        self.status_label = QLabel("请选择目标列与特征后开始训练")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self.status_label)
        top_layout.addWidget(info_group, 1)

        layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Vertical)
        chart_container = QWidget()
        self.chart_layout = QVBoxLayout(chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_container = chart_container
        chart_container.setMinimumHeight(300)
        splitter.addWidget(chart_container)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.prediction_table = QTableWidget()
        self.prediction_table.horizontalHeader().setStretchLastSection(True)
        self.prediction_table.setAlternatingRowColors(True)
        self.prediction_table.setStyleSheet("QTableWidget { font-size: 12px; }")
        table_layout.addWidget(self.prediction_table)
        splitter.addWidget(table_container)
        layout.addWidget(splitter, 1)

    # ---------------- 数据 ----------------

    def set_data(self, df: pd.DataFrame, parsed_info: dict[str, Any] | None = None):
        self.df = df
        self.parsed_info = parsed_info or {}
        if hasattr(self, "_hide_empty_state"):
            self._hide_empty_state()
        columns = list(df.columns) if df is not None else []
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItems(columns)
        self.target_combo.blockSignals(False)
        if columns:
            numeric = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
            self.target_combo.setCurrentText(numeric[-1] if numeric else columns[-1])
        self._refresh_feature_list()

    def _refresh_feature_list(self):
        self.feature_list.clear()
        if self.df is None:
            return
        target = self.target_combo.currentText()
        numeric_cols = [c for c in self.df.columns
                        if pd.api.types.is_numeric_dtype(self.df[c])]
        for col in self.df.columns:
            if col == target:
                continue
            item = QListWidgetItem(str(col))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if col in numeric_cols else Qt.Unchecked)
            item.setData(Qt.UserRole, col)
            self.feature_list.addItem(item)

    def _selected_features(self):
        features = []
        for i in range(self.feature_list.count()):
            item = self.feature_list.item(i)
            if item.checkState() == Qt.Checked:
                features.append(item.data(Qt.UserRole))
        return features

    def validate_params(self) -> tuple:
        if self.df is None or len(self.df) == 0:
            return False, "请先导入数据"
        if not self.target_combo.currentText():
            return False, "请选择目标列"
        if not self._selected_features():
            return False, "请至少勾选一个特征列"
        return True, ""

    # ---------------- 训练 ----------------

    def _task_value(self):
        value = self.task_combo.currentData()
        return None if value == "auto" else value

    def _make_job(self):
        df = self.df
        target = self.target_combo.currentText()
        features = self._selected_features()
        model = self.model_combo.currentData()
        task = self._task_value()
        cv = int(self.cv_spin.value())
        test_size = float(self.test_spin.value())
        seed = int(self.seed_spin.value())

        def job() -> dict[str, Any]:
            common = dict(task=task, cv=cv, test_size=test_size, random_state=seed)
            if model == "tree":
                return trees.analyze(df, target, features, auto_prune=True, **common)
            if model == "forest":
                return forest.analyze(df, target, features, n_estimators=120, **common)
            if model == "boosting":
                return boosting.analyze(df, target, features, max_iter=150, **common)
            if model == "mars":
                return mars.analyze(df, target, features, **common)
            fit = ml_train.fit_pipeline(df, target, features, model="linear", **common)
            return {k: v for k, v in fit.items() if k not in _NON_SERIALIZABLE}
        return job

    def _on_run_clicked(self):
        ok, message = self.validate_params()
        if not ok:
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.status_label.setText(message)
            return
        self.run_btn.setEnabled(False)
        self.status_label.setStyleSheet("color: #888;")
        self.status_label.setText("训练中，请稍候...")
        self._worker = _TrainWorker(self._make_job(), self)
        self._worker.done.connect(self._on_worker_done)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def _on_worker_done(self, result):
        self.run_btn.setEnabled(True)
        self.display_result(result)
        self.analysis_completed.emit()

    def _on_worker_failed(self, message):
        self.run_btn.setEnabled(True)
        self.status_label.setStyleSheet("color: #e74c3c;")
        self.status_label.setText(f"训练失败: {message}")

    def run_and_display(self) -> dict[str, Any] | None:
        """同步入口（批量分析/测试）——后台按钮走 _on_run_clicked。"""
        ok, message = self.validate_params()
        if not ok:
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.status_label.setText(message)
            return None
        try:
            result = self._make_job()()
        except Exception as exc:  # noqa: BLE001
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.status_label.setText(f"训练失败: {exc}")
            return None
        self.display_result(result)
        self.analysis_completed.emit()
        return result

    # ---------------- 展示 ----------------

    def display_result(self, analysis: dict[str, Any] | None = None):
        source = analysis or self.current_result
        payload = source.get("result", source)
        self.current_result = {
            "analysis_type": payload.get("analysis_type", "ml.model"),
            "params": {"target": self.target_combo.currentText(),
                       "features": self._selected_features(),
                       "model": self.model_combo.currentData(),
                       "task": payload.get("task")},
            "result": payload,
            "chart_data": payload,
        }
        task = payload.get("task", "regression")
        test = (payload.get("metrics") or {}).get("test", {})
        cv = payload.get("cv", {})
        lines = [payload.get("summary_text", "")]
        if task == "regression":
            lines.append(f"测试集 R²={_num(test.get('r2'))}，"
                         f"RMSE={_num(test.get('rmse'))}，"
                         f"MAE={_num(test.get('mae'))}")
        else:
            lines.append(f"测试集准确率={_num(test.get('accuracy'))}，"
                         f"F1={_num(test.get('f1_weighted'))}"
                         + (f"，AUC={_num(test.get('auc'))}" if test.get("auc") else ""))
        importances = (payload.get("importances") or [])[:8]
        if importances:
            lines.append("")
            lines.append("特征重要性:")
            lines.extend(f"  {item['feature']}: {item['importance']:.4f}"
                         for item in importances)
        rules = payload.get("rules") or payload.get("terms") or []
        if rules:
            lines.append("")
            lines.append("规则 / 基函数:")
            lines.extend(f"  {rule}" for rule in rules[:8])
        self.result_text.setPlainText("\n".join(lines))
        self.status_label.setStyleSheet("color: #2e7d32;")
        self.status_label.setText(
            "训练完成" + (f"（CV {cv.get('folds')} 折）" if cv else ""))
        self._fill_predictions(payload.get("predictions") or [])
        self._render_chart(payload)

    def _fill_predictions(self, rows):
        self.prediction_table.clear()
        if not rows:
            self.prediction_table.setRowCount(0)
            self.prediction_table.setColumnCount(0)
            return
        columns = list(rows[0])
        headers = {"actual": "实际值", "predicted": "预测值",
                   "probability": "预测概率", "行号": "行号"}
        self.prediction_table.setColumnCount(len(columns))
        self.prediction_table.setHorizontalHeaderLabels(
            [headers.get(c, c) for c in columns])
        self.prediction_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(columns):
                value = row[key]
                text = f"{value:.4f}" if isinstance(value, (int, float)) else str(value)
                self.prediction_table.setItem(i, j, QTableWidgetItem(text))
        self.prediction_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)

    def _render_chart(self, analysis: dict[str, Any]):
        try:
            import matplotlib.pyplot as plt
            from config.settings import CHART_DPI
            from output.chart_engine import setup_chinese_font
            setup_chinese_font()

            rows = analysis.get("predictions") or []
            task = analysis.get("task")
            if not rows or task is None:
                return
            if task == "regression":
                actual = np.asarray([r.get("actual") for r in rows], dtype=float)
                predicted = np.asarray([r.get("predicted") for r in rows], dtype=float)
                fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=CHART_DPI)
                axes[0].scatter(actual, predicted, alpha=0.6, color="#1b5faa",
                                edgecolors="k", linewidth=0.3)
                lo = float(min(actual.min(), predicted.min()))
                hi = float(max(actual.max(), predicted.max()))
                axes[0].plot([lo, hi], [lo, hi], "r--", linewidth=1)
                axes[0].set_xlabel("实际值")
                axes[0].set_ylabel("预测值")
                axes[0].set_title("预测 vs 实际", fontweight="bold")
                axes[0].grid(True, alpha=0.3)
                axes[1].scatter(predicted, actual - predicted, alpha=0.6,
                                color="#e07b39", edgecolors="k", linewidth=0.3)
                axes[1].axhline(0, color="red", linestyle="--", linewidth=1)
                axes[1].set_xlabel("预测值")
                axes[1].set_ylabel("残差")
                axes[1].set_title("残差诊断", fontweight="bold")
                axes[1].grid(True, alpha=0.3)
            else:
                test = analysis.get("metrics", {}).get("test", {})
                matrix = np.asarray(test.get("confusion_matrix", []), dtype=float)
                labels = list(test.get("labels", []))
                if matrix.size == 0:
                    return
                fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=CHART_DPI)
                axes[0].imshow(matrix, cmap="Blues")
                axes[0].set_xticks(range(len(labels)), labels)
                axes[0].set_yticks(range(len(labels)), labels)
                axes[0].set_xlabel("预测")
                axes[0].set_ylabel("实际")
                axes[0].set_title("混淆矩阵", fontweight="bold")
                for i in range(len(labels)):
                    for j in range(len(labels)):
                        axes[0].text(j, i, int(matrix[i, j]), ha="center",
                                     va="center",
                                     color="white" if matrix[i, j] > matrix.max() / 2
                                     else "black")
                roc = analysis.get("roc")
                if roc:
                    axes[1].plot(roc["fpr"], roc["tpr"], color="#1b5faa",
                                 label=f"AUC={roc['auc']:.3f}")
                    axes[1].plot([0, 1], [0, 1], "k--", linewidth=1)
                    axes[1].set_xlabel("假阳性率")
                    axes[1].set_ylabel("真阳性率")
                    axes[1].set_title("ROC 曲线", fontweight="bold")
                    axes[1].legend(loc="lower right")
                    axes[1].grid(True, alpha=0.3)
            fig.tight_layout()
            self._render_figure(fig)
        except Exception as exc:  # noqa: BLE001 - 图表失败不影响结果
            self.status_label.setText(f"训练完成（图表渲染失败: {exc}）")

    # ---------------- 模型文件 ----------------

    def save_model_to(self, path: str) -> str:
        if self.df is None:
            raise ValueError("请先导入数据")
        target = self.target_combo.currentText()
        fit = ml_train.fit_pipeline(
            self.df, target, self._selected_features(), task=self._task_value(),
            model=self.model_combo.currentData(), cv=int(self.cv_spin.value()),
            test_size=float(self.test_spin.value()),
            random_state=int(self.seed_spin.value()))
        saved = persist.save_model(
            path, fit["pipeline"], task=fit["task"], target=target,
            features=fit["features"], model=fit["model"], params=fit["params"],
            metrics=fit["metrics"])
        self.status_label.setStyleSheet("color: #2e7d32;")
        self.status_label.setText(f"模型已保存: {saved}")
        return saved

    def load_model_from(self, path: str) -> dict[str, Any]:
        self._model_bundle = persist.load_model(path)
        self.status_label.setStyleSheet("color: #2e7d32;")
        self.status_label.setText(
            f"已加载模型: {self._model_bundle.get('model', '')}"
            f"（{self._model_bundle.get('task', '')}，目标列 "
            f"{self._model_bundle.get('target', '')}）")
        return self._model_bundle

    def predict_with_loaded(self) -> pd.DataFrame | None:
        if self._model_bundle is None:
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.status_label.setText("请先加载模型（.qamodel）")
            return None
        if self.df is None:
            return None
        try:
            predictions = persist.predict_frame(self._model_bundle, self.df)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "预测失败", str(exc))
            return None
        self._loaded_predictions = predictions
        preview = predictions.reset_index().rename(
            columns={"index": "行号", "预测值": "predicted",
                     "预测概率": "probability"})
        self._fill_predictions(preview.head(200).to_dict(orient="records"))
        self.status_label.setStyleSheet("color: #2e7d32;")
        self.status_label.setText(f"预测完成: {len(predictions)} 行")
        return predictions

    def _on_save_model(self):
        if self.df is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存模型", "model.qamodel",
                                              "QA-Tool 模型 (*.qamodel)")
        if not path:
            return
        try:
            self.save_model_to(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "保存失败", str(exc))

    def _on_load_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载模型", "",
                                              "QA-Tool 模型 (*.qamodel)")
        if not path:
            return
        try:
            self.load_model_from(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "加载失败", str(exc))

    def _on_export_predictions(self):
        rows = getattr(self, "_loaded_predictions", None)
        if rows is None:
            payload = self.current_result.get("result", self.current_result)
            rows = pd.DataFrame(payload.get("predictions") or [])
        if rows.empty:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出预测结果", "predictions.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        if path.endswith(".csv"):
            rows.to_csv(path, index=False, encoding="utf-8-sig")
        else:
            rows.to_excel(path, index=False)
        self.status_label.setText(f"预测结果已导出: {path}")

    def refresh_texts(self):
        self.title_label.setText("预测分析（机器学习）")


def _num(value) -> str:
    try:
        return f"{float(value):.4g}"
    except (TypeError, ValueError):
        return "-"
