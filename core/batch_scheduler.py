"""
批量任务调度引擎 — QTimer 定时 + QThread 后台执行
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, QThread, Signal


@dataclass
class BatchTask:
    """批量任务定义 — 复用 TemplateParser 的分析配置格式"""
    name: str
    data_source: str = ""
    sheet_filter: list[str] = field(default_factory=list)
    analyses: list[dict] = field(default_factory=list)
    output_path: str = ""
    output_format: str = "docx"
    schedule: str = "once"
    enabled: bool = True

    id: str = ""
    last_run: str = ""
    last_status: str = ""
    last_error: str = ""


class _WorkerThread(QThread):
    """后台执行线程"""
    task_finished = Signal(str, bool, str)

    def __init__(self, task: BatchTask, execute_fn: Callable):
        super().__init__()
        self.task = task
        self.execute_fn = execute_fn

    def run(self):
        try:
            self.execute_fn(self.task)
            self.task_finished.emit(self.task.id, True, "")
        except Exception as e:
            self.task_finished.emit(self.task.id, False, str(e))


class BatchScheduler(QObject):
    """批量任务调度器"""

    task_added = Signal(str)
    task_removed = Signal(str)
    task_completed = Signal(str, bool, str)
    log_message = Signal(str)

    TASKS_FILE = os.path.join(os.path.expanduser("~"), ".qa_tool_batch", "tasks.json")

    def __init__(self, execute_fn: Callable | None = None, parent=None):
        super().__init__(parent)
        self.tasks: dict[str, BatchTask] = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check_schedule)
        self._workers: list[_WorkerThread] = []
        self._running: set[str] = set()
        self._poll_interval_ms = 30000
        self._log: list[str] = []
        self._execute_fn = execute_fn or self._default_execute
        self._load_tasks()

    def add_task(self, task: BatchTask) -> str:
        task.id = task.id or uuid.uuid4().hex[:8]
        self.tasks[task.id] = task
        self._save_tasks()
        self.task_added.emit(task.id)
        self._log_msg(f"任务已添加: {task.name}")
        return task.id

    def remove_task(self, task_id: str):
        if task_id in self.tasks:
            name = self.tasks[task_id].name
            del self.tasks[task_id]
            self._save_tasks()
            self.task_removed.emit(task_id)
            self._log_msg(f"任务已删除: {name}")

    def get_tasks(self) -> list[BatchTask]:
        return list(self.tasks.values())

    def start(self, interval_ms: int = 30000):
        """启动调度器，每 interval_ms 检查一次"""
        self._poll_interval_ms = interval_ms
        self._timer.start(interval_ms)
        self._log_msg("调度器已启动")

    def stop(self):
        self._timer.stop()
        self._log_msg("调度器已停止")

    def run_now(self, task_id: str):
        if task_id in self.tasks:
            self._execute_task(self.tasks[task_id])

    def _check_schedule(self):
        now = datetime.now()
        for task in self.tasks.values():
            if not task.enabled:
                continue
            if self._should_run(task, now):
                self._execute_task(task)

    def _should_run(self, task: BatchTask, now: datetime) -> bool:
        if task.schedule == "once":
            return not task.last_run
        if task.schedule == "hourly":
            if task.last_run:
                last = datetime.fromisoformat(task.last_run)
                return (now - last) >= timedelta(hours=1)
            return True
        if task.schedule.startswith("daily@"):
            target_time = task.schedule[6:]
            try:
                h, m = map(int, target_time.split(":"))
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                diff = abs((now - target).total_seconds())
                if diff <= max(30, self._poll_interval_ms / 1000 * 2):
                    if task.last_run:
                        last_date = datetime.fromisoformat(task.last_run).date()
                        return last_date < now.date()
                    return True
            except Exception:
                pass
        return False

    def _execute_task(self, task: BatchTask):
        if task.id in self._running:
            self._log_msg(f"任务正在执行中，跳过重复启动: {task.name}")
            return
        self._running.add(task.id)
        worker = _WorkerThread(task, self._execute_fn)
        worker.task_finished.connect(self._on_task_finished)
        self._workers.append(worker)
        worker.start()

    def _on_task_finished(self, task_id: str, success: bool, error: str):
        self._running.discard(task_id)
        if task_id in self.tasks:
            t = self.tasks[task_id]
            t.last_run = datetime.now().isoformat()
            t.last_status = "success" if success else "failed"
            t.last_error = error
            if t.schedule == "once":
                t.enabled = False
            self._save_tasks()
        self._workers = [w for w in self._workers if w.task.id != task_id]
        status = "成功" if success else f"失败: {error}"
        self._log_msg(f"任务完成 [{task_id}]: {status}")
        self.task_completed.emit(task_id, success, error)

    @staticmethod
    def _default_execute(task: BatchTask):
        """默认执行器——必须由调用方注入具体执行逻辑"""
        task_name = task.id if hasattr(task, 'id') else str(task)
        raise NotImplementedError(
            f"未注入 execute_fn，无法执行任务 {task_name}。"
            "请在创建 BatchScheduler 时通过 execute_fn 参数注入执行函数。"
        )

    def _log_msg(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self._log.append(entry)
        self.log_message.emit(entry)

    def get_log(self) -> list[str]:
        return self._log[-200:]

    def _save_tasks(self):
        os.makedirs(os.path.dirname(self.TASKS_FILE), exist_ok=True)
        data = []
        for t in self.tasks.values():
            data.append({
                "id": t.id, "name": t.name, "data_source": t.data_source,
                "sheet_filter": t.sheet_filter, "analyses": t.analyses,
                "output_path": t.output_path, "output_format": t.output_format,
                "schedule": t.schedule, "enabled": t.enabled,
                "last_run": t.last_run, "last_status": t.last_status,
                "last_error": t.last_error,
            })
        with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_tasks(self):
        if not os.path.exists(self.TASKS_FILE):
            return
        try:
            with open(self.TASKS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                t = BatchTask(
                    id=d.get("id", ""), name=d.get("name", ""),
                    data_source=d.get("data_source", ""),
                    sheet_filter=d.get("sheet_filter", []),
                    analyses=d.get("analyses", []),
                    output_path=d.get("output_path", ""),
                    output_format=d.get("output_format", "docx"),
                    schedule=d.get("schedule", "once"),
                    enabled=d.get("enabled", True),
                )
                t.last_run = d.get("last_run", "")
                t.last_status = d.get("last_status", "")
                t.last_error = d.get("last_error", "")
                if not t.id:
                    t.id = uuid.uuid4().hex[:8]
                self.tasks[t.id] = t
        except Exception:
            pass
