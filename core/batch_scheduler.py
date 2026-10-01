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

from core.log_util import get_logger
from core.legacy import legacy_home_dir, migrate_legacy_file

_DEFAULT_TASKS_FILE = os.path.join(os.path.expanduser("~"), ".akia_batch", "tasks.json")

_log = get_logger(__name__)

# 模板分析类型 → 一键分析执行器类型（core.one_click_analyzer 的能力域）
_ANALYSIS_TYPE_MAP = {
    "xbar_r": "spc", "xbar_s": "spc", "imr": "spc",
    "p_chart": "spc", "np_chart": "spc", "c_chart": "spc", "u_chart": "spc",
    "cusum": "spc", "ewma": "spc",
    "normal_capability": "capability", "non_normal_capability": "capability",
    "between_within_capability": "capability",
    "gage_rr_crossed": "msa", "gage_rr_nested": "msa",
    "linearity_bias": "msa", "attribute_agreement": "msa",
    "t_test_1sample": "hypothesis", "t_test_2sample": "hypothesis",
    "t_test_paired": "hypothesis", "anova_oneway": "hypothesis",
    "anova_twoway": "hypothesis", "normality_test": "hypothesis",
    "variance_test": "hypothesis",
    "linear_regression": "regression", "correlation_heatmap": "regression",
    "factorial_design": "doe", "response_surface": "doe",
    "doe_analysis": "doe", "box_behnken": "doe",
}

_OUTPUT_SUFFIX = {"docx": ".docx", "xlsx": ".xlsx", "pdf": ".pdf", "md": ".md",
                  "markdown": ".md", "json": ".json"}


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

    TASKS_FILE = _DEFAULT_TASKS_FILE

    def __init__(self, execute_fn: Callable | None = None, parent=None):
        super().__init__(parent)
        if self.TASKS_FILE == _DEFAULT_TASKS_FILE:   # 自定义路径（测试）不搬迁
            migrate_legacy_file(legacy_home_dir("batch") / "tasks.json", self.TASKS_FILE)
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
            except Exception as e:  # 时间格式非法：该任务当日不触发，但必须留痕
                _log.warning("批量任务 %s 的 target_time 解析失败（%r）: %s",
                             getattr(task, "name", "?"), target_time, e)
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
        except Exception as e:  # 配置损坏：不覆盖磁盘文件，已解析的任务保留
            _log.warning("批量任务配置读取失败（%s），后续任务未加载: %s", self.TASKS_FILE, e)


# ---------------------------------------------------------------- 默认执行器
# 无 Qt 依赖，可在 _WorkerThread 中安全运行（不触碰任何 widget / matplotlib 画布）

def _load_task_source(task: BatchTask) -> dict:
    """读取任务数据源为 {sheet: DataFrame}（支持 xlsx/xls/xlsm/csv）。"""
    import pandas as pd

    path = (task.data_source or "").strip()
    if not path:
        raise FileNotFoundError("任务未配置数据源文件（data_source 为空）")
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据源不存在: {path}")
    if path.lower().endswith(".csv"):
        return {os.path.splitext(os.path.basename(path))[0]: pd.read_csv(path)}

    from core.data_loader import DataLoader

    loader = DataLoader()
    raw = loader.load(path)
    if task.sheet_filter:
        keep = [s for s in raw if s in set(task.sheet_filter)]
        raw = {s: raw[s] for s in keep} or raw
    return raw


def _selected_analysis_types(task: BatchTask) -> list[str]:
    """任务里声明的模板分析类型 → 执行器类型（去重保序）；未声明则用默认组合。"""
    selected: list[str] = []
    for item in task.analyses or []:
        atype = str((item or {}).get("analysis_type", "")).strip().lower()
        mapped = _ANALYSIS_TYPE_MAP.get(atype)
        if mapped and mapped not in selected:
            selected.append(mapped)
        elif atype in _ANALYSIS_TYPE_MAP.values() and atype not in selected:
            selected.append(atype)
    return selected or ["spc", "capability"]


def _resolve_output_path(task: BatchTask) -> str:
    """任务输出路径：显式配置优先，否则生成"数据源名_时间戳"同目录文件。"""
    configured = (task.output_path or "").strip()
    if configured:
        return configured
    stem = os.path.splitext(os.path.basename(task.data_source or "batch"))[0] or "batch"
    fmt = (task.output_format or "docx").lower()
    suffix = _OUTPUT_SUFFIX.get(fmt, ".docx")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.dirname(os.path.abspath(task.data_source)) if task.data_source else os.getcwd()
    return os.path.join(base, f"{stem}_{stamp}{suffix}")


def _write_task_report(task: BatchTask, analyses: list[dict], output_path: str) -> str:
    """按任务格式写出报告（docx/xlsx/pdf 走报告引擎，其余写 Markdown）。"""
    fmt = (task.output_format or "docx").lower()
    title = f"{task.name or '批量任务'} — 自动分析报告"
    subtitle = f"数据源: {os.path.basename(task.data_source or '')}"
    if fmt in {"docx", "pdf", "xlsx"}:
        if fmt == "docx":
            from output.word_report import WordReport

            return WordReport().generate(analyses=analyses, output_path=output_path,
                                         title=title, subtitle=subtitle)
        if fmt == "pdf":
            from output.pdf_report import PDFReport

            return PDFReport().generate(analyses=analyses, output_path=output_path,
                                        title=title, subtitle=subtitle)
        from output.excel_report import ExcelReport

        return ExcelReport().generate(analyses, output_path, title)

    lines = [f"# {title}", "", f"- 数据源: {task.data_source}", f"- 任务: {task.name}", ""]
    for i, analysis in enumerate(analyses, 1):
        lines.append(f"## {i}. {analysis.get('analysis_type', '分析')}")
        for key, value in (analysis.get("result") or {}).items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


def run_task_headless(task: BatchTask) -> str:
    """默认任务执行器（无 Qt）—— 载入数据源 → 跑分析 → 写出报告，返回文件路径。

    由 ``ui/dialogs/batch_dialog.py`` 注入给 ``BatchScheduler``；进程内后台线程执行，
    因此这里**不得**创建任何 QWidget / matplotlib 画布。
    """
    from core.one_click_analyzer import OneClickAnalyzer

    raw = _load_task_source(task)
    selected = _selected_analysis_types(task)
    analyzer = OneClickAnalyzer()
    plan = analyzer.profile_and_recommend(raw)
    results = analyzer.execute_analyses(raw, plan, selected)
    failed = [r for r in results if not r.get("success")]
    if failed and len(failed) == len(results):
        raise RuntimeError("全部分析失败: " + "; ".join(str(r.get("error")) for r in failed[:3]))

    payload = [
        {
            "analysis_type": r.get("analysis_type", "分析"),
            "params": {"column": r.get("column", ""), "任务": task.name},
            "result": r.get("summary") or {},
            "conclusion": "成功" if r.get("success") else f"失败: {r.get('error')}",
        }
        for r in results
    ]
    output_path = _resolve_output_path(task)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    written = _write_task_report(task, payload, output_path)
    return written
