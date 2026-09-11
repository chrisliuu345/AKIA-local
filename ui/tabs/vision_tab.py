"""视频时间研究 Tab（v3.8.0 P3，Tab 37）— 视频 → 动作分析 → 标准工时。

线程模型: QThread 内运行 analysis/vision 会话，逐帧回传预览信号；
主线程只做渲染与表格更新。无摄像头/无依赖时给出安装与降级提示，不崩溃。
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from ui.font_config import get_ui_font
from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY, BUTTON_SECONDARY, colors as theme_colors

SOURCE_TYPES = (
    ("本地视频文件", "file"),
    ("USB 摄像头", "usb"),
    ("RTSP 流", "rtsp"),
    ("MJPEG / HTTP 流", "mjpeg"),
    ("合成演示源", "synthetic"),
)

_DISABLED_SUFFIX = (
    "QPushButton:disabled { background-color: #2c2c38; color: #6e7080;"
    " border: 1px solid #3a3a48; }")


class VisionWorker(QThread):
    """后台执行视频分析，逐帧回传预览（processed 帧 + 当前状态）。"""

    frame_ready = Signal(object, object)
    progressed = Signal(object)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, source, config):
        super().__init__()
        self.source = source
        self.config = config
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        from analysis.vision.session import run_vision_session

        try:
            result = run_vision_session(
                self.source, self.config,
                progress=lambda payload: self.progressed.emit(payload),
                should_stop=lambda: self._stop,
                frame_callback=lambda processed, pose, state:
                    self.frame_ready.emit(processed, state))
        except Exception as e:                      # 兜底: 异常不冒到 Qt 事件循环
            self.failed.emit(f"{type(e).__name__}: {e}")
            return
        self.succeeded.emit(result)


class _ModelDownloadWorker(QThread):
    progressed = Signal(int, int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self._cancel = False

    def stop(self):
        self._cancel = True

    def _on_progress(self, done: int, total: int):
        if self._cancel:
            raise RuntimeError("已取消")
        self.progressed.emit(done, total)

    def run(self):
        from analysis.vision.model_store import download_pose_model

        try:
            path = download_pose_model(progress=self._on_progress)
        except Exception as e:
            self.failed.emit(str(e))
            return
        self.succeeded.emit(str(path))


class VisionTab(BaseAnalysisTab):
    send_to_time_study = Signal(object)         # list[TimeObservation]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: VisionWorker | None = None
        self.download_worker: _ModelDownloadWorker | None = None
        self.result = None
        self._setup_ui()
        self._refresh_backend_status()

    # ------------------------------------------------------------ UI
    def _setup_ui(self):
        tc = theme_colors(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("视频时间研究")
        title.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        title.setStyleSheet(f"color: {tc['text_primary']};")
        layout.addWidget(title)

        subtitle = QLabel("摄像头/视频 → 动作识别（工作·空闲·走动·搬运·离岗）→ "
                          "作业周期 → 标准工时；与 Agent 工具、工时研究 Tab 同引擎")
        subtitle.setStyleSheet(f"color: {tc['text_muted']}; font-size: 10pt;")
        layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_config_panel(tc))
        splitter.addWidget(self._build_result_panel(tc))
        splitter.setSizes([220, 560])
        layout.addWidget(splitter, 1)

    def _build_config_panel(self, tc) -> QWidget:
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        group = QGroupBox("视频源与参数")
        form = QFormLayout(group)
        form.setContentsMargins(10, 10, 10, 10)
        form.setSpacing(6)

        self.source_combo = QComboBox()
        for label, key in SOURCE_TYPES:
            self.source_combo.addItem(label, key)
        self.source_combo.currentIndexChanged.connect(self._on_source_type_changed)
        form.addRow("来源类型:", self.source_combo)

        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(6)
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("选择本地视频文件…")
        source_layout.addWidget(self.source_edit, 1)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFixedWidth(56)
        self.browse_btn.clicked.connect(self._on_browse)
        source_layout.addWidget(self.browse_btn)
        form.addRow("源地址:", source_row)

        self.sample_fps_spin = QDoubleSpinBox()
        self.sample_fps_spin.setRange(1.0, 30.0)
        self.sample_fps_spin.setValue(15.0)
        self.sample_fps_spin.setDecimals(1)
        self.sample_fps_spin.setSuffix(" FPS")
        form.addRow("采样帧率:", self.sample_fps_spin)

        self.max_seconds_spin = QSpinBox()
        self.max_seconds_spin.setRange(5, 3600)
        self.max_seconds_spin.setValue(600)
        self.max_seconds_spin.setSuffix(" s")
        form.addRow("最长分析:", self.max_seconds_spin)

        self.roi_edit = QLineEdit()
        self.roi_edit.setPlaceholderText("x,y,w,h（可选，聚焦作业区域）")
        form.addRow("ROI:", self.roi_edit)

        self.process_edit = QLineEdit("视频工序")
        self.operator_edit = QLineEdit("视频观测")
        form.addRow("工序名:", self.process_edit)
        form.addRow("作业员:", self.operator_edit)

        params_row = QWidget()
        params_layout = QHBoxLayout(params_row)
        params_layout.setContentsMargins(0, 0, 0, 0)
        self.rating_spin = QDoubleSpinBox()
        self.rating_spin.setRange(0.5, 1.5)
        self.rating_spin.setValue(1.0)
        self.rating_spin.setDecimals(2)
        self.rating_spin.setSingleStep(0.05)
        params_layout.addWidget(QLabel("评定:"))
        params_layout.addWidget(self.rating_spin)
        self.allowance_spin = QDoubleSpinBox()
        self.allowance_spin.setRange(0.0, 30.0)
        self.allowance_spin.setValue(12.0)
        self.allowance_spin.setDecimals(1)
        self.allowance_spin.setSuffix(" %")
        params_layout.addWidget(QLabel("宽放:"))
        params_layout.addWidget(self.allowance_spin)
        params_layout.addStretch()
        form.addRow("工时参数:", params_row)

        self.mediapipe_check = QCheckBox("优先骨架识别（缺失自动降级运动特征）")
        self.mediapipe_check.setChecked(True)
        form.addRow("", self.mediapipe_check)
        row.addWidget(group, 3)

        right = QVBoxLayout()
        right.setSpacing(6)
        self.backend_label = QLabel("")
        self.backend_label.setWordWrap(True)
        self.backend_label.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 9pt;")
        right.addWidget(self.backend_label)

        self.download_btn = QPushButton("下载姿态模型（约 5.6MB）")
        self.download_btn.setStyleSheet(BUTTON_SECONDARY + _DISABLED_SUFFIX)
        self.download_btn.clicked.connect(self._on_download_model)
        self.download_btn.setVisible(False)
        right.addWidget(self.download_btn, alignment=Qt.AlignLeft)

        self.progress_label = QLabel("就绪")
        self.progress_label.setStyleSheet(f"color: {tc['text_muted']}; font-size: 9pt;")
        right.addWidget(self.progress_label)

        button_row = QHBoxLayout()
        self.start_btn = QPushButton("开始分析")
        self.start_btn.setStyleSheet(BUTTON_PRIMARY + _DISABLED_SUFFIX)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._on_start)
        button_row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet(BUTTON_SECONDARY + _DISABLED_SUFFIX)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        button_row.addWidget(self.stop_btn)
        right.addLayout(button_row)
        right.addStretch()
        row.addLayout(right, 2)
        return panel

    def _build_result_panel(self, tc) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        preview_box = QVBoxLayout()
        self.preview_label = QLabel("分析开始后在此显示视频预览与实时状态")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(520, 340)
        self.preview_label.setStyleSheet(
            f"background: {tc['bg_card']}; border: 1px solid {tc['border_light']};"
            f"border-radius: 8px; color: {tc['text_muted']};")
        preview_box.addWidget(self.preview_label, 1)
        self.live_label = QLabel("—")
        self.live_label.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 9pt;")
        preview_box.addWidget(self.live_label)
        layout.addLayout(preview_box, 3)

        result_box = QVBoxLayout()
        result_box.setSpacing(6)

        self.summary_label = QLabel("尚无结果")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(f"color: {tc['text_secondary']}; font-size: 9pt;")
        result_box.addWidget(self.summary_label)

        self.ratio_table = QTableWidget(0, 3)
        self.ratio_table.setHorizontalHeaderLabels(["状态", "时长(s)", "占比(%)"])
        self.ratio_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ratio_table.setMaximumHeight(180)
        result_box.addWidget(self.ratio_table)

        self.cycle_table = QTableWidget(0, 3)
        self.cycle_table.setHorizontalHeaderLabels(["周期", "开始(s)", "时长(s)"])
        self.cycle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_box.addWidget(self.cycle_table, 1)

        action_row = QHBoxLayout()
        self.send_btn = QPushButton("发送到工时研究")
        self.send_btn.setStyleSheet(BUTTON_SECONDARY + _DISABLED_SUFFIX)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._on_send_to_time_study)
        action_row.addWidget(self.send_btn)
        self.export_btn = QPushButton("导出结果 JSON")
        self.export_btn.setStyleSheet(BUTTON_SECONDARY + _DISABLED_SUFFIX)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_json)
        action_row.addWidget(self.export_btn)
        action_row.addStretch()
        result_box.addLayout(action_row)
        layout.addLayout(result_box, 2)
        return panel

    # ------------------------------------------------------------ 状态
    def _refresh_backend_status(self):
        from analysis.vision import backend_info

        info = backend_info()
        self._backend = info
        if not info["available"]:
            self.backend_label.setText(
                f"⚠ Vision 不可用：未安装 OpenCV。安装: {info['install_hint']}")
            self.start_btn.setEnabled(False)
            return
        backend = "MediaPipe 骨架" if info["backend"] == "mediapipe" else "OpenCV 运动特征"
        model = "已就绪" if info["pose_model"] else "未下载"
        self.backend_label.setText(
            f"后端: {backend}　·　OpenCV {info.get('cv2') and '✓' or '✗'}"
            f"　·　MediaPipe {info.get('mediapipe') and '✓' or '✗'}"
            f"　·　姿态模型: {model}")
        self.download_btn.setVisible(bool(info["mediapipe"] and not info["pose_model"]))

    def _on_source_type_changed(self, *_):
        kind = self.source_combo.currentData()
        is_file = kind == "file"
        self.browse_btn.setVisible(is_file)
        placeholders = {
            "file": "选择本地视频文件…",
            "usb": "摄像头序号，如 0",
            "rtsp": "rtsp://user:pass@host:554/stream",
            "mjpeg": "http://host:8080/video.mjpg",
            "synthetic": "演示源（无需填写）",
        }
        self.source_edit.setPlaceholderText(placeholders.get(kind, ""))
        self.source_edit.setEnabled(kind != "synthetic")

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm);;所有文件 (*)")
        if path:
            self.source_edit.setText(path)

    def _source_spec(self):
        kind = self.source_combo.currentData()
        text = self.source_edit.text().strip()
        if kind == "synthetic":
            return "synthetic"
        if not text:
            raise ValueError("请填写视频源地址")
        if kind == "file":
            if not Path(text).is_file():
                raise FileNotFoundError(f"视频文件不存在: {text}")
            return text
        if kind == "usb":
            return int(text) if text.isdigit() else 0
        return text

    def _build_config(self):
        from analysis.vision.session import VisionConfig

        roi = None
        if self.roi_edit.text().strip():
            parts = [p.strip() for p in self.roi_edit.text().replace("，", ",").split(",")]
            if len(parts) != 4:
                raise ValueError("ROI 需为 x,y,w,h 四个整数")
            roi = tuple(int(float(p)) for p in parts)
        return VisionConfig(
            sample_fps=float(self.sample_fps_spin.value()),
            width=640, roi=roi,
            max_seconds=float(self.max_seconds_spin.value()),
            process_id=self.process_edit.text().strip() or "视频工序",
            operator=self.operator_edit.text().strip() or "视频观测",
            prefer_mediapipe=bool(self.mediapipe_check.isChecked()))

    # ------------------------------------------------------------ 分析
    def _on_start(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            source = self._source_spec()
            config = self._build_config()
        except Exception as e:
            QMessageBox.warning(self, "参数错误", str(e))
            return
        self.ratio_table.setRowCount(0)
        self.cycle_table.setRowCount(0)
        self.summary_label.setText("分析中…")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.send_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.result = None
        self.worker = VisionWorker(source, config)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.progressed.connect(self._on_progress)
        self.worker.succeeded.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_stop(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.progress_label.setText("正在停止，等待当前帧…")

    def _on_frame(self, processed, state):
        from analysis.vision.action import ACTION_COLORS, ACTION_LABELS

        frame = processed.frame
        height, width = frame.shape[:2]
        image = QImage(frame.data, width, height, 3 * width,
                       QImage.Format_BGR888).copy()
        pixmap = QPixmap.fromImage(image)
        if self.preview_label.width() > 20 and self.preview_label.height() > 20:
            pixmap = pixmap.scaled(self.preview_label.size(),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter = QPainter(pixmap)
        label = ACTION_LABELS.get(state, "未知")
        color = QColor(ACTION_COLORS.get(state, "#9E9E9E"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawRoundedRect(8, 8, 132, 30, 6, 6)
        painter.setPen(color)
        painter.setFont(QFont(get_ui_font(), 11, QFont.Bold))
        painter.drawText(16, 30, f"● {label}")
        painter.end()
        self.preview_label.setPixmap(pixmap)
        self.live_label.setText(
            f"帧 {processed.ts_ms / 1000.0:.1f}s · 状态 {label} · "
            f"运动 {processed.motion_energy * 100:.1f}% · "
            f"速度 {processed.speed_px_s:.0f}px/s")

    def _on_progress(self, payload):
        self.progress_label.setText(
            f"已处理 {payload.get('frames', 0)} 帧 · "
            f"时间 {payload.get('ts_ms', 0) / 1000.0:.1f}s")

    def _on_finished(self, result):
        self.result = result
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._populate_result(result)

    def _on_failed(self, message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText(f"✗ {message}")
        self.summary_label.setText("分析失败")

    def _populate_result(self, result):
        from analysis.vision.action import ACTION_LABELS, ActionState

        self.progress_label.setText(
            f"完成: {result.frames} 帧 · {result.processed_fps:.1f} FPS · "
            f"单帧 {result.latency.get('avg_ms', 0):.1f}ms")
        cycle_text = ""
        if result.cycles:
            mean = sum(c.duration_s for c in result.cycles) / len(result.cycles)
            cycle_text = f"　·　周期 {len(result.cycles)} 个（均值 {mean:.1f}s）"
        self.summary_label.setText(
            f"后端 {result.backend} · 时长 {result.duration_s:.1f}s "
            f"· 处理 {result.frames} 帧{cycle_text}"
            + ("　·　已达分析时长上限" if result.truncated else ""))
        self.ratio_table.setRowCount(0)
        for state, pct in sorted(result.ratios.items(),
                                 key=lambda kv: kv[1], reverse=True):
            row = self.ratio_table.rowCount()
            self.ratio_table.insertRow(row)
            self.ratio_table.setItem(row, 0, QTableWidgetItem(
                ACTION_LABELS.get(ActionState(state), state)))
            self.ratio_table.setItem(row, 1, QTableWidgetItem(
                f"{result.durations.get(state, 0):.1f}"))
            self.ratio_table.setItem(row, 2, QTableWidgetItem(f"{pct:.1f}"))
        self.cycle_table.setRowCount(0)
        for cycle in result.cycles:
            row = self.cycle_table.rowCount()
            self.cycle_table.insertRow(row)
            self.cycle_table.setItem(row, 0, QTableWidgetItem(str(cycle.index)))
            self.cycle_table.setItem(row, 1, QTableWidgetItem(
                f"{cycle.start_ms / 1000.0:.1f}"))
            self.cycle_table.setItem(row, 2, QTableWidgetItem(
                f"{cycle.duration_s:.2f}"))
        self.send_btn.setEnabled(bool(result.cycles))
        self.export_btn.setEnabled(True)
        for warning in result.warnings:
            self.progress_label.setText(self.progress_label.text() + f"　|　{warning}")
        self.analysis_completed.emit()

    # ------------------------------------------------------------ 输出 / 模型
    def _on_send_to_time_study(self):
        if self.result is None:
            return
        observations = self.result.to_time_observations()
        if not observations:
            QMessageBox.information(self, "无周期", "未识别到作业周期，无法发送。")
            return
        self.send_to_time_study.emit(observations)

    def _on_export_json(self):
        if self.result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 Vision 结果",
                                              "vision_result.json",
                                              "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.result.to_dict(), f, ensure_ascii=False, indent=2)
        self.progress_label.setText(f"已导出 {path}")

    def _on_download_model(self):
        if self.download_worker is not None and self.download_worker.isRunning():
            return
        self.download_btn.setEnabled(False)
        self.progress_label.setText("正在下载姿态模型…")
        self.download_worker = _ModelDownloadWorker()

        def _progress(done, total):
            if total:
                self.progress_label.setText(
                    f"下载模型 {done / total * 100:.0f}%（{done // 1024}KB）")

        def _done(path):
            self.download_btn.setEnabled(True)
            self.progress_label.setText(f"模型已就绪: {path}")
            self._refresh_backend_status()

        def _fail(message):
            self.download_btn.setEnabled(True)
            self.progress_label.setText(f"✗ 模型下载失败: {message}")

        self.download_worker.progressed.connect(_progress)
        self.download_worker.succeeded.connect(_done)
        self.download_worker.failed.connect(_fail)
        self.download_worker.start()

    # ------------------------------------------------------------ 生命周期
    def closeEvent(self, event):
        self._stop_workers()
        super().closeEvent(event)

    def _stop_workers(self):
        for worker in (self.worker, self.download_worker):
            if worker is not None and worker.isRunning():
                stop = getattr(worker, "stop", None)
                if callable(stop):
                    stop()
                worker.wait(3000)
