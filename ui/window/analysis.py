"""页签加载、批量分析和结果入库。"""

from datetime import datetime
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QMessageBox,
)
from PySide6.QtCore import (
    Qt, QTimer,
)
from PySide6.QtGui import QFont

from config.settings import CHART_FIGSIZE, tab_allowed
from core.i18n import i18n
from core.time_utils import now_iso

from ui.font_config import get_ui_font
from ui.main_window_helpers import (
    _tab_is_runnable,
)

from ui.main_window_constants import (
    _CONTEXT_TAB_INDICES,
    _IE_IMPORT_TAB_INDICES,
    _PLUGIN_TAB_START,
)


class AnalysisMixin:
    def _on_analysis_finished(self, idx: int):
        """分析完成统一收纳点: analyses + 会话 + 侧栏历史 + Dashboard

        v2.4 修复: 补上 session_manager.add_analysis (原死代码 _on_run_analysis
        携带, 迁移到此处后删除死代码)
        """
        tabs = self._get_tabs()
        tab = tabs.get(idx)
        result = getattr(tab, 'current_result', None)
        if result:
            self._store_analysis(idx, result)
            self._update_tab_empty_state(idx)
            if getattr(self, "_batch_progress", None) is None:
                self._show_toast(f"分析完成：{result.get('analysis_type', '')}",
                                 "success")
        self._notify_dashboard()
        # 渲染完成后布局才稳定，分批延后同步滚动范围（立即读会拿到旧 hint）
        self._schedule_scroll_sync()

    def _on_time_observations_ready(self, observations):
        """外部插件 Tab → 工时研究 Tab：发送作业周期。"""
        tab = self._lazy_load_tab(7)
        if tab is None or not hasattr(tab, "set_ie_data"):
            return
        tab.set_ie_data(observations)
        self._switch_tab(7)
        self.status_label.setText(
            f"已发送 {len(observations)} 个视频作业周期到工时研究")

    def _notify_dashboard(self):
        """v2.4 F1: 分析完成后通知 Dashboard 刷新 (仅当已懒加载时)

        用 refresh_if_changed 去重 — 批量分析时 N 次通知只重建一次
        """
        tab = self._tab_cache.get(27)
        if tab is not None and hasattr(tab, 'refresh_if_changed'):
            tab.refresh_if_changed()

    def _on_run_all_analyses(self):
        """批量分析：逐 Tab 分步执行，带进度与取消（UI 全程可响应）。"""
        if not self.current_data:
            QMessageBox.warning(self, i18n.tr("msg.no_data"), i18n.tr("msg.no_data_file"))
            return

        tabs = self._get_tabs(force_load=True)
        queue = [(idx, tab) for idx, tab in tabs.items() if _tab_is_runnable(tab)]
        if not queue:
            self.statusBar().showMessage("没有可运行的 Tab（请先导入数据）", 5000)
            return

        from PySide6.QtWidgets import QProgressDialog

        self._batch_queue = queue
        self._batch_success = 0
        self._batch_failed = 0
        self._batch_cancelled = False
        progress = QProgressDialog("准备批量分析…", "取消", 0, len(queue), self)
        progress.setWindowTitle("批量分析")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.canceled.connect(self._cancel_batch_analysis)
        self._batch_progress = progress
        progress.setValue(0)
        progress.show()
        QTimer.singleShot(0, self._run_batch_step)

    def _cancel_batch_analysis(self):
        self._batch_cancelled = True

    def _run_batch_step(self):
        """执行一个 Tab 后让出事件循环（保持界面响应与取消可用）。"""
        progress = getattr(self, "_batch_progress", None)
        if progress is None:
            return
        if self._batch_cancelled or not self._batch_queue:
            self._finish_batch_analysis()
            return
        idx, tab = self._batch_queue.pop(0)
        total = progress.maximum()
        progress.setLabelText(
            f"批量分析 {total - len(self._batch_queue)}/{total}：{type(tab).__name__}")
        try:
            tab.run_and_display()
            result = getattr(tab, "current_result", None)
            if result:
                self._store_analysis(idx, result)
            self._batch_success += 1
        except Exception:
            import logging
            logging.getLogger(__name__).exception(f"批量分析 tab idx={idx} 失败")
            self._batch_failed += 1
        progress.setValue(total - len(self._batch_queue))
        QTimer.singleShot(0, self._run_batch_step)

    def _finish_batch_analysis(self):
        progress = getattr(self, "_batch_progress", None)
        if progress is not None:
            progress.close()
            progress.deleteLater()
            self._batch_progress = None
        self._batch_queue = []
        tail = "（已取消）" if self._batch_cancelled else ""
        message = (f"批量分析{tail}完成：成功 {self._batch_success}，"
                   f"失败 {self._batch_failed}")
        self.statusBar().showMessage(message, 6000)
        self._show_toast(message, "warning" if self._batch_failed else "success")
        self._notify_dashboard()
        self._schedule_scroll_sync()

    def _store_analysis(self, idx: int, result: dict):
        """统一收纳分析结果（analyses + 会话历史 + 侧栏历史）。"""
        previous = self.analyses.get(idx)
        self.analyses[idx] = result.copy()
        self.analyses[idx]["_completed_at"] = datetime.now().isoformat(timespec="seconds")
        self.analyses[idx]["credential"] = self._make_analysis_credential(idx, result)
        if previous and previous.get("credential"):
            # 复核模式（v4.2.0 P4-3）：同一 Tab 重跑时自动逐项比对上次结论
            from core.evidence import diff_analysis_records

            self.analyses[idx]["rerun_diff"] = diff_analysis_records(previous,
                                                                     self.analyses[idx])
        self.session_manager.add_analysis(
            result.get("analysis_type", "Unknown"),
            result.get("params", {}),
            result.get("result", {}))
        atype = result.get("analysis_type", "")
        key_res = self._summarize_result(result.get("result", {}))
        self.sidebar.add_history(idx, atype, key_res)
        credential = self.analyses[idx].get("credential") or {}
        params = credential.get("params") or {}
        rerun = self.analyses[idx].get("rerun_diff") or {}
        self._ledger_append(
            "analysis_run",
            object_refs=[f"tab:{idx}", credential.get("data_fingerprint", "")],
            payload={"tab": idx, "analysis_type": atype,
                     "rule_version": credential.get("rule_version", ""),
                     "data_fingerprint": credential.get("data_fingerprint", ""),
                     "standard_ref": params.get("standard_ref", ""),
                     "standard_as_of": params.get("standard_as_of", ""),
                     "rerun_identical": rerun.get("identical"),
                     "completed_at": self.analyses[idx]["_completed_at"]})

    def _make_analysis_credential(self, idx: int, result: dict) -> dict:
        """为该次分析生成结论凭证（规则版本 + 参数 + 数据指纹 + 软件版本）。

        v4.2.0 P4：让"当时是怎么算的"随分析记录一起留存 —— 报告页脚追溯码、
        `.qap` 快照与复核模式（同数据重跑 diff）都以此为单一事实源。
        """
        from core.evidence import make_credential

        rule_version = str(result.get("rule_version")
                           or result.get("analysis_type")
                           or result.get("chart_type")
                           or f"tab_{idx}")
        params = dict(result.get("params", {}) or {})
        params.update(self._standard_context_for(idx, result))
        return make_credential(
            rule_version=rule_version,
            params=params,
            df=self._analysis_source_frame(idx),
            algorithm=str(result.get("analysis_type", "")),
        ).to_dict()

    def _standard_context_for(self, idx: int, result: dict) -> dict:
        """解析该次分析适用的标准版本引用（B3-5），供凭证与 as-of 复判使用。"""
        from core.standard_record import resolve_standard_context

        try:
            registry = self.project_context.standards
        except AttributeError:
            return {}
        if registry is None or not len(registry):
            return {}
        params = result.get("params", {}) or {}
        refs: list[str] = []
        for key in ("standard_ref", "characteristic_id", "column", "process_id"):
            value = params.get(key)
            if value:
                refs.append(str(value))
        tab = self._tab_cache.get(idx)
        for attr in ("standard_object_ref", "characteristic_id"):
            value = getattr(tab, attr, "")
            if value:
                refs.append(str(value))
        resolved = resolve_standard_context(registry, refs)
        if resolved:
            return resolved
        # 兜底：仅当分析数据中恰好一个列名能匹配到标准时才引用，避免张冠李戴
        frame = self._analysis_source_frame(idx)
        if frame is None:
            return {}
        matches = [str(column) for column in frame.columns
                   if registry.current(str(column))
                   or registry.as_of(str(column), now_iso())]
        if len(matches) == 1:
            return resolve_standard_context(registry, matches)
        return {}

    def _analysis_source_frame(self, idx: int):
        """取该 Tab 用于分析的数据作为指纹来源；取不到则返回 None（no-data 指纹）。

        优先 Tab 自身的数据框（分析真正作用的对象），退回当前导入数据的第一张表。
        指纹属附加信息，任何取数异常都不应影响分析流程本身。
        """
        try:
            tab = self._tab_cache.get(idx)
            frame = getattr(tab, "df", None)
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return frame
        except Exception:  # 当前 Tab 取数失败 → 退回工作簿原始数据
            pass
        try:
            raw = (self.current_data or {}).get("raw_data") or {}
            for candidate in raw.values():
                if isinstance(candidate, pd.DataFrame) and not candidate.empty:
                    return candidate
        except Exception:  # 原始数据不可用 → 返回 None 由调用方兜底
            pass
        return None

    def _summarize_result(self, result: dict) -> str:
        cap = result.get("capability", {})
        if cap.get("grade"):
            return cap["grade"]
        acceptance = result.get("acceptance", {})
        if acceptance.get("message"):
            return acceptance["message"][:8]
        if "p_value" in result:
            return "显著" if result.get("is_significant") else "不显著"
        if result.get("summary_text"):
            return str(result["summary_text"])[:16]
        model = result.get("model")
        if isinstance(model, dict):        # 回归等引擎的模型详情字典
            r2 = model.get("r_squared", 0)
            return f"R²={r2:.2f}"
        return ""

    def _lazy_load_tab(self, idx: int):
        """按需加载 Tab — 首次访问时 import + 实例化 + 替换占位符"""
        if idx in self._tab_cache:
            return self._tab_cache[idx]

        if idx >= self._plugin_tab_start:
            if idx in self._plugin_tabs:
                record = self._plugin_tabs[idx]
                tab = self._pm.create_tab(record, self._plugin_host, parent=self)
                if tab is None:
                    return None
                self._tab_cache[idx] = tab
                old = self.stack.widget(idx)
                if old:
                    self.stack.removeWidget(old)
                self.stack.insertWidget(idx, tab)
                if old and old.objectName().startswith("placeholder"):
                    old.deleteLater()
                self._connect_tab_signals(idx, tab)
                return tab
            return None

        from ui._tab_registry import INDEX_MAP
        entry = INDEX_MAP.get(idx)
        if not entry or not tab_allowed(idx):
            return None

        _, _, class_name, module_path, _ = entry
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            tab = cls()
        except ImportError as exc:
            self._handle_tab_dependency_error(idx, class_name, module_path, exc)
            return None
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                f"懒加载 Tab 失败: idx={idx} {class_name} from {module_path}"
            )
            return None

        self._tab_cache[idx] = tab
        old = self.stack.widget(idx)
        if old:
            self.stack.removeWidget(old)
        self.stack.insertWidget(idx, tab)
        if old and old.objectName().startswith("placeholder"):
            old.deleteLater()

        self._connect_tab_signals(idx, tab)
        if hasattr(tab, "set_gauge_context"):
            tab.set_gauge_context(self.gauge_monitor,
                                  self._submit_gauge_measurement)
        if hasattr(tab, "set_sampling_context"):
            tab.set_sampling_context(self.sampling_manager)
        if hasattr(tab, "set_skill_context"):
            tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                  self.record_skill_balance_step)
        if hasattr(tab, "set_balance_context"):
            tab.set_balance_context(self.project_context,
                                    self.record_line_balance_step)
        return tab

    def _handle_tab_dependency_error(self, idx: int, class_name: str,
                                     module_path: str, exc: ImportError):
        """缺依赖导致 Tab 加载失败：展示可操作提示，不打印异常堆栈。"""
        import logging

        from ui.runtime_deps import (
            CHART_DEPENDENCIES, broken_chart_dependencies,
            chart_dependency_hint, missing_chart_dependencies,
        )

        top = (getattr(exc, "name", "") or "").split(".")[0]
        missing = missing_chart_dependencies()
        if not missing:
            if top in CHART_DEPENDENCIES:
                missing = [top]  # 装了一半：find_spec 成功但 import 失败
            elif not top:
                missing = broken_chart_dependencies()

        if missing:
            title = "缺少图表依赖"
            hint = chart_dependency_hint(missing)
            if not self._chart_dependency_warned:
                self._chart_dependency_warned = True
                QMessageBox.warning(self, title, hint)
        else:
            title = "缺少运行依赖"
            name = getattr(exc, "name", None) or str(exc) or class_name
            hint = (
                f"该功能依赖的组件不可用: {name}\n"
                "安装完整依赖后重新点击该功能即可（无需重启）：\n"
                "  pip install -r requirements.txt"
            )
            logging.getLogger(__name__).warning(
                "懒加载 Tab 依赖缺失: idx=%s %s from %s -> %s",
                idx, class_name, module_path, exc,
            )

        self._install_dependency_notice(idx, title, hint)
        self.statusBar().showMessage(hint.splitlines()[0], 15000)

    def _install_dependency_notice(self, idx: int, title: str, message: str):
        """把空白占位页替换为依赖提示页，避免切换后"点了没反应"。"""
        from PySide6.QtWidgets import QLabel, QVBoxLayout

        page = QWidget()
        page.setObjectName(f"dependency_notice_{idx}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.addStretch(1)
        title_label = QLabel(title)
        title_label.setFont(QFont(get_ui_font(), 15))
        title_label.setAlignment(Qt.AlignCenter)
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addStretch(1)

        old = self.stack.widget(idx)
        self.stack.insertWidget(idx, page)
        if old:
            self.stack.removeWidget(old)
            if old.objectName().startswith(("placeholder", "dependency_notice")):
                old.deleteLater()
        return page

    def _connect_tab_signals(self, idx: int, tab):
        """为新创建的 Tab 建立信号连接"""
        if hasattr(tab, 'export_clicked'):
            tab.export_clicked.connect(lambda tid=idx: self._on_export_single(tid, "docx"))
        if hasattr(tab, 'analysis_completed'):
            tab.analysis_completed.connect(lambda tid=idx: self._on_analysis_finished(tid))
        if hasattr(tab, 'import_data_requested'):
            handler = (self._on_import_ie if idx in _IE_IMPORT_TAB_INDICES
                       else self._on_import_quality)
            tab.import_data_requested.connect(handler)
        if hasattr(tab, 'set_stream_source'):
            tab.set_stream_source(self.stream_bus)
        if hasattr(tab, 'send_to_time_study'):
            tab.send_to_time_study.connect(self._on_time_observations_ready)
        if idx in _CONTEXT_TAB_INDICES and hasattr(tab, 'set_project_context'):
            tab.set_project_context(self.project_context)
            if hasattr(tab, 'load_from_context'):
                tab.load_from_context()

    def _get_tabs(self, force_load: bool = False):
        """获取 Tab 字典。force_load=False 仅返回已缓存的(懒加载友好)；force_load=True 全量加载"""
        result = {}
        if force_load:
            idx_range = list(range(1, _PLUGIN_TAB_START))
        else:
            idx_range = sorted(self._tab_cache.keys())
        for idx in idx_range:
            tab = self._lazy_load_tab(idx)
            if tab:
                result[idx] = tab
        for idx in self._plugin_tabs:
            tab = self._lazy_load_tab(idx)
            if tab:
                result[idx] = tab
        return result

    def _collect_charts(self, indices: list):
        charts = {}
        tabs = self._get_tabs()
        for idx in indices:
            tab = tabs.get(idx)
            if tab and hasattr(tab, 'current_figure') and tab.current_figure:
                fig = tab.current_figure
                fig.set_size_inches(*CHART_FIGSIZE)
                atype = self.analyses[idx].get("analysis_type", "")
                from output.chart_engine import figure_to_bytes
                charts[atype] = figure_to_bytes(fig)
                tab.canvas.draw()
        return charts
