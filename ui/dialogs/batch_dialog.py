"""
批量调度对话框 — 任务列表 + 编辑面板 + 日志
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTextEdit, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QFileDialog, QSplitter,
    QWidget, QCheckBox,
)
from PySide6.QtCore import Qt, QTimer

from core.batch_scheduler import BatchTask, BatchScheduler, run_task_headless
from ui.theme import colors as theme_colors, BUTTON_SECONDARY, BUTTON_TOGGLE
from ui.font_config import get_mono_font


class BatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 注入无 Qt 依赖的默认执行器：后台线程内载入数据源 → 跑分析 → 写报告
        self.scheduler = BatchScheduler(execute_fn=run_task_headless)
        self._setup_ui()
        self._refresh_task_list()
        self._connect_signals()

        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._refresh_log)
        self._log_timer.start(2000)
        self._displayed_log_lines: set = set()

    def _setup_ui(self):
        tc = theme_colors()
        self.setWindowTitle("批量调度")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"background-color: {tc['bg_body']};")

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)

        left_layout.addWidget(QLabel("任务列表"))
        self.task_list = QListWidget()
        self.task_list.setStyleSheet(
            f"QListWidget {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border_light']}; border-radius: 4px; }}"
        )
        self.task_list.currentRowChanged.connect(self._on_task_selected)
        left_layout.addWidget(self.task_list, 1)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ 新建")
        btn_add.setStyleSheet(BUTTON_SECONDARY)
        btn_add.clicked.connect(self._on_new_task)
        btn_row.addWidget(btn_add)
        btn_del = QPushButton("删除")
        btn_del.setStyleSheet(BUTTON_TOGGLE)
        btn_del.clicked.connect(self._on_delete_task)
        btn_row.addWidget(btn_del)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 6, 6, 6)

        edit_group = QGroupBox("任务配置")
        form = QFormLayout(edit_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("任务名称")
        form.addRow("名称:", self.name_edit)

        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("数据文件路径或留空手动选择")
        source_row = QHBoxLayout()
        source_row.addWidget(self.source_edit, 1)
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_source)
        source_row.addWidget(btn_browse)
        form.addRow("数据源:", source_row)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("报告输出路径")
        form.addRow("输出:", self.output_edit)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["docx", "xlsx", "pdf"])
        form.addRow("格式:", self.format_combo)

        self.schedule_combo = QComboBox()
        self.schedule_combo.addItems(["仅一次", "每小时", "每日 09:00"])
        form.addRow("调度:", self.schedule_combo)

        self.enabled_check = QCheckBox("启用")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        right_layout.addWidget(edit_group)

        right_layout.addWidget(QLabel("执行日志"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(200)
        self.log_view.setStyleSheet(
            f"QTextEdit {{ background: {tc['bg_card']}; color: {tc['text_primary']};"
            f"border: 1px solid {tc['border_light']}; font-family: {get_mono_font()}; font-size: 11px; }}"
        )
        right_layout.addWidget(self.log_view)

        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ 启动调度")
        self.start_btn.setStyleSheet(BUTTON_SECONDARY)
        self.start_btn.clicked.connect(self._on_start)
        ctrl_row.addWidget(self.start_btn)
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet(BUTTON_TOGGLE)
        self.stop_btn.clicked.connect(self._on_stop)
        ctrl_row.addWidget(self.stop_btn)
        ctrl_row.addStretch()
        self.run_btn = QPushButton("立即执行当前任务")
        self.run_btn.setStyleSheet(BUTTON_TOGGLE)
        self.run_btn.clicked.connect(self._on_run_now)
        ctrl_row.addWidget(self.run_btn)
        right_layout.addLayout(ctrl_row)

        splitter.addWidget(right)
        splitter.setSizes([280, 600])

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)

    def _connect_signals(self):
        self.scheduler.log_message.connect(self._append_log)
        self.scheduler.task_completed.connect(lambda tid, ok, err: self._refresh_task_list())

    def _refresh_task_list(self):
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for t in self.scheduler.get_tasks():
            status_icon = "OK" if t.last_status == "success" else ("FAIL" if t.last_status == "failed" else "...")
            item = QListWidgetItem(f"{status_icon} {t.name}")
            item.setData(Qt.UserRole, t.id)
            self.task_list.addItem(item)
        self.task_list.blockSignals(False)

    def _on_task_selected(self, row: int):
        if row < 0:
            return
        item = self.task_list.item(row)
        tid = item.data(Qt.UserRole)
        if tid in self.scheduler.tasks:
            t = self.scheduler.tasks[tid]
            self.name_edit.setText(t.name)
            self.source_edit.setText(t.data_source)
            self.output_edit.setText(t.output_path)
            self.format_combo.setCurrentText(t.output_format)
            sched_map = {"once": 0, "hourly": 1, "daily@09:00": 2}
            self.schedule_combo.setCurrentIndex(sched_map.get(t.schedule, 0))
            self.enabled_check.setChecked(t.enabled)

    def _on_new_task(self):
        self.name_edit.clear()
        self.name_edit.setPlaceholderText("输入任务名称...")
        self.source_edit.clear()
        self.output_edit.clear()

    def _on_delete_task(self):
        row = self.task_list.currentRow()
        if row >= 0:
            item = self.task_list.item(row)
            tid = item.data(Qt.UserRole)
            self.scheduler.remove_task(tid)
            self._refresh_task_list()

    def _save_current_task(self):
        name = self.name_edit.text().strip() or "未命名任务"
        schedule_map = {0: "once", 1: "hourly", 2: "daily@09:00"}
        task = BatchTask(
            name=name,
            data_source=self.source_edit.text().strip(),
            output_path=self.output_edit.text().strip(),
            output_format=self.format_combo.currentText(),
            schedule=schedule_map.get(self.schedule_combo.currentIndex(), "once"),
            enabled=self.enabled_check.isChecked(),
        )
        row = self.task_list.currentRow()
        if row >= 0:
            item = self.task_list.item(row)
            tid = item.data(Qt.UserRole)
            if tid in self.scheduler.tasks:
                task.id = tid
                task.last_run = self.scheduler.tasks[tid].last_run
                task.last_status = self.scheduler.tasks[tid].last_status
        self.scheduler.add_task(task)
        return task

    def _on_start(self):
        self._save_current_task()
        self._refresh_task_list()
        self.scheduler.start()
        self._append_log("=== 调度器已启动 ===")

    def _on_stop(self):
        self.scheduler.stop()
        self._append_log("=== 调度器已停止 ===")

    def _on_run_now(self):
        task = self._save_current_task()
        self._refresh_task_list()
        if task.id:
            self.scheduler.run_now(task.id)

    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "Excel/CSV (*.xlsx *.xls *.csv);;All (*.*)"
        )
        if path:
            self.source_edit.setText(path)

    def _append_log(self, msg: str):
        self.log_view.append(msg)

    def _refresh_log(self):
        for entry in self.scheduler.get_log():
            if entry not in self._displayed_log_lines:
                self._displayed_log_lines.add(entry)
                self.log_view.append(entry)
