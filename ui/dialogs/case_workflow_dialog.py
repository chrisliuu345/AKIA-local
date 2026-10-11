"""改善案例工作台（v4.2.0 P5 / v4.3.0 B1-B2）— 查看轨迹并推进案例。

测量四通道：文件/工作表（当前数据、最近分析、配对检验）、连接器（StreamBus
最近窗口）、插件（API 2.1 data_source）、手工录入。每批测量写成 MeasurementEvent
并随案例步骤引用，事件由主窗口的 MeasurementStore 持有并随 `.qap` 保存。
"""

import pandas as pd
import os

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QInputDialog,
    QMessageBox, QPushButton, QTextBrowser, QVBoxLayout,
)

from core.case_workflow import PHASE_LABELS, PHASES


class CaseWorkflowDialog(QDialog):
    """案例工作台：阶段进度 + 留痕 + 记录步骤/测量/结论/标准/关闭。"""

    def __init__(self, workflow, parent=None):
        super().__init__(parent)
        self.workflow = workflow
        self.host = parent if parent is not None else None
        self.setWindowTitle(f"改善案例工作台 — {workflow.case.title}")
        self.resize(980, 720)

        layout = QVBoxLayout(self)
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(False)
        layout.addWidget(self.browser)

        layout.addLayout(self._build_step_actions())
        layout.addLayout(self._build_measurement_actions())
        layout.addLayout(self._build_evidence_actions())
        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_availability()
        self.refresh()

    # ------------------------------------------------------------ UI
    def _build_step_actions(self):
        row = QHBoxLayout()
        self.record_button = QPushButton("记录当前数据", self)
        self.analysis_button = QPushButton("记录最近分析", self)
        self.pair_button = QPushButton("配对检验", self)
        self.conclusion_button = QPushButton("填写结论", self)
        self.standard_button = QPushButton("标准草稿", self)
        for button in (self.record_button, self.analysis_button, self.pair_button,
                       self.conclusion_button, self.standard_button):
            row.addWidget(button)
        row.addStretch()
        self.record_button.clicked.connect(self._on_record_current)
        self.analysis_button.clicked.connect(self._on_record_analysis)
        self.pair_button.clicked.connect(self._on_paired_test)
        self.conclusion_button.clicked.connect(self._on_conclude)
        self.standard_button.clicked.connect(self._on_standard)
        return row

    def _build_measurement_actions(self):
        row = QHBoxLayout()
        self.connector_button = QPushButton("采集连接器测量", self)
        self.plugin_button = QPushButton("导入插件测量", self)
        self.manual_button = QPushButton("手工录入", self)
        self.close_case_button = QPushButton("关闭案例", self)
        self.refresh_button = QPushButton("刷新", self)
        self.export_button = QPushButton("导出 Markdown", self)
        for button in (self.connector_button, self.plugin_button,
                       self.manual_button, self.close_case_button,
                       self.refresh_button, self.export_button):
            row.addWidget(button)
        row.addStretch()
        self.connector_button.clicked.connect(self._on_connector_measurements)
        self.plugin_button.clicked.connect(self._on_plugin_measurements)
        self.manual_button.clicked.connect(self._on_manual_measurement)
        self.close_case_button.clicked.connect(self._on_close_case)
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button.clicked.connect(self._export)
        return row

    def _build_evidence_actions(self):
        row = QHBoxLayout()
        self.evidence_button = QPushButton("查看证据", self)
        self.evidence_pack_button = QPushButton("导出证据包", self)
        self.share_pack_button = QPushButton("导出脱敏分享包", self)
        for button in (self.evidence_button, self.evidence_pack_button,
                       self.share_pack_button):
            row.addWidget(button)
        row.addStretch()
        self.evidence_button.clicked.connect(self._on_view_evidence)
        self.evidence_pack_button.clicked.connect(self._on_export_evidence_pack)
        self.share_pack_button.clicked.connect(self._on_export_share_pack)
        return row

    # ------------------------------------------------------------ 渲染
    def _build_text(self) -> str:
        done = {step.get("phase") for step in self.workflow.case.steps}
        progress = "  ".join(
            f"{'✅' if phase in done else '⬜'} {PHASE_LABELS[phase]}"
            for phase in PHASES)
        missing = "、".join(PHASE_LABELS[p] for p in self.workflow.missing_phases()) or "无"
        gate = self.workflow.case.closure_check()
        gate_text = "可关闭" if gate["ok"] else "；".join(gate["problems"])
        return (f"{progress}\n\n待补阶段：{missing}\n"
                f"关闭门禁：{gate_text}\n\n"
                + self.workflow.to_markdown())

    def refresh(self):
        self.browser.setMarkdown(self._build_text())

    def _refresh_availability(self):
        has_data = bool(getattr(self.host, "current_data", None))
        has_analysis = bool(getattr(self.host, "analyses", None))
        self.record_button.setEnabled(has_data)
        self.analysis_button.setEnabled(has_analysis)
        self.pair_button.setEnabled(has_data)

    # ------------------------------------------------------------ 数据访问
    def _current_frame(self):
        raw = (getattr(self.host, "current_data", None) or {}).get("raw_data") or {}
        for name, candidate in raw.items():
            if hasattr(candidate, "empty") and not candidate.empty:
                return candidate, str(name)
        return None, "Sheet1"

    def _analysis_frame(self, index):
        source_frame = getattr(self.host, "_analysis_source_frame", None)
        if callable(source_frame):
            try:
                frame = source_frame(index)
                if frame is not None:
                    return frame
            except Exception:  # 取数失败 → 退回当前导入数据首表
                pass
        return self._current_frame()[0]

    # ------------------------------------------------------------ 测量事件
    def _measurement_phase(self, title="关联测量"):
        phases = ["baseline", "remeasure", "verify"]
        labels = [PHASE_LABELS[phase] for phase in phases]
        label, ok = QInputDialog.getItem(self, title, "关联阶段:", labels, 0, False)
        if not ok:
            return ""
        return phases[labels.index(label)]

    def _store_events(self, events):
        store = getattr(self.host, "measurement_store", None)
        if store is None or not hasattr(store, "add"):
            return []
        return [store.add(event).event_id for event in events]

    def _record_measurements(self, events, data_ref: str, note: str = "") -> bool:
        """写事件 → 选阶段 → 记步骤；返回是否记录成功。"""
        if not events:
            return False
        phase = self._measurement_phase()
        if not phase:
            return False
        ids = self._store_events(events)
        total = sum(int(event.summary.get("n", 0)) for event in events)
        self.workflow.record_step(
            phase, {"measurements": len(events)},
            data_ref=data_ref, note=note,
            params={"measurements": len(events), "samples": total},
            measurement_refs=ids)
        self.refresh()
        return True

    def _on_connector_measurements(self):
        topic_fn = getattr(self.host, "connector_topics", None)
        topics = list(topic_fn() if callable(topic_fn) else [])
        if not topics:
            QMessageBox.information(self, "无连接器数据",
                                    "当前没有连接器主题（请先配置并启动采集）")
            return
        topic, ok = QInputDialog.getItem(self, "采集连接器测量", "主题:", topics, 0, False)
        if not ok:
            return
        recent = getattr(self.host, "recent_measurements", None)
        events = recent(topic, 2000) if callable(recent) else []
        if not events:
            QMessageBox.information(self, "无数据", f"主题 {topic} 的最近窗口没有样本")
            return
        self._record_measurements(events, data_ref=f"connector:{topic}",
                                  note=f"连接器 {topic} 最近窗口")

    def _on_plugin_measurements(self):
        from core.plugin_manager import PluginManager

        manager = PluginManager()
        manager.discover()
        records = manager.data_source_plugins()
        if not records:
            QMessageBox.information(self, "无插件数据源",
                                    "没有已信任且可用的 data_source 插件")
            return
        events = manager.collect_measurements(context={"host": self.host})
        if not events:
            QMessageBox.warning(self, "无测量数据",
                                "插件未返回有效测量事件（详见插件状态/日志）")
            return
        names = "、".join(record.name for record in records)
        self._record_measurements(events, data_ref=f"plugin:{names}",
                                  note=f"插件数据源 {names}")

    def _on_manual_measurement(self):
        from core.measurement_event import MeasurementEvent

        value, ok = QInputDialog.getDouble(self, "手工录入", "测量值:",
                                           0.0, -1e12, 1e12, 6)
        if not ok:
            return
        characteristic, ok = QInputDialog.getText(self, "手工录入",
                                                  "特性 / 通道（可选）:")
        if not ok:
            return
        event = MeasurementEvent.from_manual(
            value, characteristic_id=str(characteristic or "").strip(),
            channel=str(characteristic or "").strip())
        self._record_measurements([event],
                                  data_ref=f"manual:{characteristic or '-'}",
                                  note="手工录入测量值")

    # ------------------------------------------------------------ 步骤动作
    def _on_record_current(self):
        from core.measurement_event import MeasurementEvent

        labels = [PHASE_LABELS[phase] for phase in PHASES]
        label, ok = QInputDialog.getItem(self, "记录当前数据", "阶段:", labels, 0, False)
        if not ok:
            return
        phase = PHASES[labels.index(label)]
        note, ok = QInputDialog.getText(self, "记录当前数据", "说明（可选）:")
        if not ok:
            return
        frame, sheet = self._current_frame()
        if frame is None:
            QMessageBox.warning(self, "无数据", "当前没有可记录的导入数据")
            return
        event_ids = []
        try:
            event = MeasurementEvent.from_dataframe(
                frame, source_kind="file", source_id=sheet, source_name=sheet,
                channel=sheet, raw_ref=f"sheet://{sheet}")
            event_ids = self._store_events([event])
        except ValueError:  # 无数值列 → 仍允许记录阶段，只是不带测量事件
            event_ids = []
        try:
            self.workflow.record_step(
                phase, {"params": {"rows": int(len(frame))}},
                data_ref=f"sheet:{sheet}", frame=frame, note=str(note or ""),
                measurement_refs=event_ids)
        except ValueError as exc:
            QMessageBox.warning(self, "记录失败", str(exc))
            return
        self.refresh()

    def _on_record_analysis(self):
        from core.measurement_event import MeasurementEvent

        analyses = getattr(self.host, "analyses", None) or {}
        if not analyses:
            QMessageBox.information(self, "无分析结果", "请先运行一次分析")
            return
        index = max(analyses)
        record = analyses[index]
        frame, sheet = None, "Sheet1"
        source_frame = self._analysis_frame(index)
        if source_frame is not None:
            frame = source_frame
        else:
            frame, sheet = self._current_frame()
        event_ids = []
        if frame is not None:
            try:
                event = MeasurementEvent.from_dataframe(
                    frame, source_kind="analysis", source_id=f"tab:{index}",
                    channel=sheet, raw_ref=f"tab://{index}")
                event_ids = self._store_events([event])
            except ValueError:
                event_ids = []
        try:
            self.workflow.record_analysis_step(
                record, data_ref=f"tab:{index} · sheet:{sheet}", frame=frame,
                measurement_refs=event_ids)
        except ValueError as exc:
            QMessageBox.warning(self, "无法记入案例", str(exc))
            return
        self.refresh()

    def _on_paired_test(self):
        from core.measurement_event import MeasurementEvent

        frame, sheet = self._current_frame()
        if frame is None:
            QMessageBox.warning(self, "无数据", "当前没有可用的导入数据")
            return
        numeric_map = {str(c): c for c in frame.columns
                       if pd.api.types.is_numeric_dtype(frame[c])}
        numeric = list(numeric_map)
        if len(numeric) < 2:
            QMessageBox.warning(self, "无法配对检验",
                                "当前数据至少需要两个数值列（改善前 / 复测列）")
            return
        before_col, ok = QInputDialog.getItem(self, "配对检验", "改善前列:",
                                              numeric, 0, False)
        if not ok:
            return
        after_col, ok = QInputDialog.getItem(self, "配对检验", "复测列:",
                                             numeric, 1, False)
        if not ok:
            return
        if before_col == after_col:
            QMessageBox.warning(self, "无法配对检验", "改善前列与复测列不能相同")
            return
        # 成对删除缺失值：两列任一侧缺失即整行剔除，保证配对来自同一行
        # （旧实现两列各自 dropna 后按位对齐，缺失位置不同会错配配对）
        pair_frame = pd.DataFrame({
            "before": frame[numeric_map[before_col]],
            "after": frame[numeric_map[after_col]],
        }).dropna().reset_index(drop=True)
        if len(pair_frame) < 2:
            QMessageBox.warning(self, "配对检验失败", "有效配对数据不足 2 对")
            return
        event_ids = []
        try:
            event = MeasurementEvent.from_dataframe(
                pair_frame, source_kind="file", source_id=sheet,
                channel=f"{before_col}/{after_col}",
                raw_ref=f"sheet://{sheet}:{before_col}/{after_col}")
            event_ids = self._store_events([event])
        except ValueError:
            event_ids = []
        try:
            self.workflow.run_paired_test(
                pair_frame["before"], pair_frame["after"],
                data_ref=f"sheet:{sheet}:{before_col}/{after_col}",
                measurement_refs=event_ids)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "配对检验失败", str(exc))
            return
        self.refresh()

    def _on_conclude(self):
        text, ok = QInputDialog.getMultiLineText(self, "填写结论", "结论:")
        if not ok or not str(text).strip():
            return
        self.workflow.conclude(str(text).strip(), data_ref="case:conclusion")
        self.refresh()

    def _on_standard(self):
        text, ok = QInputDialog.getMultiLineText(self, "标准草稿", "标准/作业文件草稿:")
        if not ok or not str(text).strip():
            return
        self.workflow.standard_draft(str(text).strip(), data_ref="standard:draft")
        self.refresh()

    def _on_close_case(self):
        gate = self.workflow.case.closure_check()
        if not gate["ok"]:
            QMessageBox.warning(self, "无法关闭案例",
                                "关闭条件未满足：\n- " + "\n- ".join(gate["problems"]))
            return
        reason, ok = QInputDialog.getMultiLineText(self, "关闭案例", "关闭原因:")
        if not ok or not str(reason).strip():
            return
        try:
            self.workflow.close_case(str(reason).strip())
        except ValueError as exc:
            QMessageBox.warning(self, "关闭失败", str(exc))
            return
        self.refresh()

    # ------------------------------------------------------------ 证据与交换（B4）
    def _on_view_evidence(self):
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        host = self.host
        context = getattr(host, "project_context", None)
        dialog = EvidenceViewDialog(
            getattr(host, "analyses", {}) or {}, getattr(host, "ledger", None),
            self,
            registry=getattr(context, "standards", None),
            measurements=getattr(host, "measurement_store", None),
            frame_provider=getattr(host, "_analysis_source_frame", None),
            ledger_failures=getattr(host, "_ledger_failures", 0))
        dialog.exec()

    def _on_export_evidence_pack(self):
        from core.evidence_pack import export_evidence_pack

        host = self.host
        ledger = getattr(host, "ledger", None)
        if ledger is None:
            QMessageBox.warning(self, "无证据账本", "当前窗口未启用证据账本")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出证据包", f"{self.workflow.case.id}-evidence.zip",
            "证据包 (*.zip)")
        if not path:
            return
        context = getattr(host, "project_context", None)
        try:
            result = export_evidence_pack(
                path, case=self.workflow.to_dict(),
                case_markdown=self.workflow.to_markdown(),
                analyses=getattr(host, "analyses", {}) or {}, ledger=ledger,
                standards=(context.standards.to_dict() if context else None),
                measurements=getattr(host, "measurement_store", None))
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        verify = result.get("verify") or {}
        append = getattr(host, "_ledger_append", None)
        if callable(append):
            append("evidence_pack_exported",
                   object_refs=[f"case:{self.workflow.case.id}"],
                   payload={"file": os.path.basename(result["path"]),
                            "ok": bool(verify.get("ok")),
                            "event_count": result["manifest"].get("event_count", 0)})
        if verify.get("ok"):
            QMessageBox.information(
                self, "证据包已导出",
                f"已导出并通过独立校验：\n{result['path']}")
        else:
            QMessageBox.warning(
                self, "证据包校验失败",
                "；".join(verify.get("problems", [])[:5]))

    def _on_export_share_pack(self):
        from core.share_pack import build_share_pack

        host = self.host
        raw = (getattr(host, "current_data", None) or {}).get("raw_data") or {}
        if not raw:
            QMessageBox.warning(self, "无数据", "当前没有可合成分享的数据表")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出脱敏分享包", f"{self.workflow.case.id}-share.zip",
            "脱敏分享包 (*.zip)")
        if not path:
            return
        source = str((getattr(host, "current_data", None) or {}).get("file_path", ""))
        forbidden = [self.workflow.case.title, self.workflow.owner,
                     self.workflow.product, os.path.basename(source)]
        try:
            result = build_share_pack(
                path, raw_data=raw, case=self.workflow.to_dict(),
                ledger=getattr(host, "ledger", None), forbidden=forbidden)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        scan = result.get("scan") or {}
        append = getattr(host, "_ledger_append", None)
        if callable(append):
            append("share_pack_exported",
                   object_refs=[f"case:{self.workflow.case.id}"],
                   payload={"file": os.path.basename(result["path"]),
                            "scan_ok": bool(scan.get("ok")),
                            "sheets": len(result.get("sheets") or {})})
        if scan.get("ok"):
            QMessageBox.information(
                self, "脱敏分享包已导出",
                f"泄漏扫描通过（无原始值/路径/人名）：\n{result['path']}")
        else:
            QMessageBox.warning(
                self, "泄漏扫描告警",
                "发现可疑内容：" + str(scan.get("findings", [])[:3]))

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出改善案例", f"{self.workflow.case.id}.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.workflow.to_markdown())
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"已导出：{path}")
