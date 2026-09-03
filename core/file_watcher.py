"""文件监控引擎 — 监控 Excel 数据文件变化并自动执行 SPC 分析 (v2.4 E1)

Qt-free 纯 Python 模块：
- pick_numeric_column / auto_spc: 数据列选择与 SPC 自动分派
- FileMonitor: 后台守护线程轮询文件变化 (mtime/大小)，稳定确认后
  通过回调 (on_change) 推送分析结果；供 monitor_tab 跨线程转发 UI
"""

import os
import threading
from datetime import datetime

import pandas as pd

from core.data_loader import DataLoader
from analysis.spc.imr import analyze as imr_analyze
from analysis.spc.xbar_r import analyze as xbar_r_analyze

MIN_POINTS = 8


def _coerce_numeric(s: pd.Series) -> pd.Series:
    """把可整体转换为数值的字符串列转为数值，否则原样返回。"""
    if pd.api.types.is_numeric_dtype(s):
        return s
    out = pd.to_numeric(s, errors="coerce")
    if out.notna().sum() >= s.notna().sum():
        return out
    return s


def pick_numeric_column(df: pd.DataFrame) -> str:
    """选择首个可用于监控的数值列：数值类型、非全空、样本数 ≥ MIN_POINTS。"""
    for col in df.columns:
        s = df[col]
        if not pd.api.types.is_numeric_dtype(s):
            continue
        clean = s.dropna()
        if len(clean) >= MIN_POINTS:
            return str(col)
    raise ValueError("no numeric column with enough points")


def auto_spc(df: pd.DataFrame, column: str, subgroup_size: int = 1) -> dict:
    """按子组大小自动分派 SPC 分析：1 → I-MR 单值图，>1 → XBar-R。"""
    data = df[column].dropna().astype(float)
    if len(data) < MIN_POINTS:
        raise ValueError(f"insufficient data points: {len(data)}")
    if subgroup_size <= 1:
        result = imr_analyze(data)
    else:
        result = xbar_r_analyze(data, subgroup_size=subgroup_size)
    return {
        "column": column,
        "num_points": len(data),
        "result": result,
    }


class FileMonitor(threading.Thread):
    """轮询文件变化的后台监控线程。

    变化判定：os.stat 的 (mtime_ns, size) 元组改变。为避免读到写了一半的
    文件，检测到变化后等待一个 interval 再确认状态一致才触发分析。
    """

    def __init__(self, file_path, on_change, interval=2.0, subgroup_size=1,
                 sheet_name=None, column=None):
        super().__init__(daemon=True)
        self.file_path = file_path
        self.on_change = on_change
        self.interval = float(interval)
        self.subgroup_size = subgroup_size
        self.sheet_name = sheet_name
        self.column = column
        self._stop_event = threading.Event()
        self._last_state = None

    def _stat(self):
        try:
            st = os.stat(self.file_path)
            return (st.st_mtime_ns, st.st_size)
        except (FileNotFoundError, OSError):
            return None

    def check_once(self) -> dict:
        """立即读取并分析一次，返回 payload（供首次显示与轮询共用）。"""
        payload = {
            "file_path": self.file_path,
            "run": 0,
            "updated_at": None,
            "sheet": self.sheet_name,
            "column": self.column,
            "num_points": 0,
            "violations": 0,
            "spc": None,
            "error": None,
        }
        try:
            if not os.path.exists(self.file_path):
                payload["error"] = "文件不存在"
                return payload
            loader = DataLoader()
            sheets = loader.load(self.file_path)
            if not sheets:
                payload["error"] = "文件中没有数据表"
                return payload
            if self.sheet_name and self.sheet_name in sheets:
                df = sheets[self.sheet_name]
            else:
                df = next(iter(sheets.values()))
                self.sheet_name = list(sheets.keys())[0]
            if df.empty:
                payload["error"] = "数据表为空"
                return payload
            df = df.apply(_coerce_numeric)
            column = self.column
            if column is None or column not in df.columns:
                column = pick_numeric_column(df)
                self.column = column
            out = auto_spc(df, column, self.subgroup_size)
            result = out["result"]
            viol = 0
            for key in ("i_chart", "mr_chart", "xbar_chart", "r_chart"):
                chart = result.get(key)
                if chart:
                    viol += len(chart.get("violations", []) or [])
            payload.update({
                "run": getattr(self, "_run_count", 0) + 1,
                "updated_at": datetime.now().strftime("%H:%M:%S"),
                "sheet": self.sheet_name,
                "column": column,
                "num_points": out["num_points"],
                "violations": viol,
                "spc": result,
            })
            self._run_count = getattr(self, "_run_count", 0) + 1
        except FileNotFoundError:
            payload["error"] = "文件不存在"
        except Exception as exc:  # noqa: BLE001 — 监控线程兜底
            payload["error"] = str(exc)
        return payload

    def run(self):
        self._last_state = self._stat()
        while not self._stop_event.wait(self.interval):
            state = self._stat()
            if state is None:
                if self._last_state is not None:
                    self._last_state = None
                    self.on_change(self.check_once())
                continue
            if state != self._last_state:
                self._stop_event.wait(self.interval)
                if self._stop_event.is_set():
                    break
                state2 = self._stat()
                if state2 == state:
                    self._last_state = state
                    self.on_change(self.check_once())

    def stop(self, timeout: float = 5.0):
        self._stop_event.set()
        self.join(timeout=timeout)
