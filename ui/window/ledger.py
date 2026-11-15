"""证据账本、测量事件和量具漂移。"""

import os


from core.measurement_store import MeasurementStore
from core.evidence_ledger import EvidenceLedger


class LedgerMixin:
    # ------------------------------------------------------------ 证据账本（B4）
    def _ledger_append(self, event_type: str, *, actor: str = "user",
                       object_refs: list[str] | None = None,
                       payload: dict | None = None):
        """写入证据账本；失败只计数/留痕，绝不阻断业务动作。"""
        try:
            return self.ledger.append(event_type, actor=actor,
                                      object_refs=object_refs or [],
                                      payload=payload or {})
        except Exception:  # 记账失败不得影响导入/分析/导出等主流程
            import logging
            self._ledger_failures += 1
            logging.getLogger(__name__).warning(
                "证据账本写入失败（累计 %d 次）", self._ledger_failures,
                exc_info=True)
            return None

    def _on_measurement_event(self, event):
        self._ledger_append(
            "measurement_recorded", actor="system",
            object_refs=[event.event_id,
                         event.characteristic_id or event.channel or event.device],
            payload={"source_kind": event.source_kind, "source_id": event.source_id,
                     "channel": event.channel, "n": event.summary.get("n", 0),
                     "fingerprint": event.fingerprint, "raw_ref": event.raw_ref,
                     "ts_start": event.ts_start, "ts_end": event.ts_end})
        try:
            outcome = self.gauge_monitor.ingest_event(event)
        except Exception:  # 量具监控失败不得影响测量写入主链路
            import logging
            logging.getLogger(__name__).exception("量具在线监控摄入失败")
            return
        if outcome is None:
            return
        self._last_gauge_outcome[outcome.gauge_id] = outcome
        if outcome.prompt:
            self._handle_gauge_drift(outcome)

    # ------------------------------------------------------------ 量具在线（v4.4.0 B2）
    def _handle_gauge_drift(self, outcome) -> None:
        """漂移提示：账本事件 + 告警中心留存 + 主线程状态栏（带冷却）。"""
        self.gauge_monitor.note_prompted(outcome.gauge_id)
        reasons = "；".join(outcome.drift_reasons[:3]) or "偏倚/控制图超限"
        refs = [f"gauge:{outcome.gauge_id}"]
        if outcome.event_id:
            refs.append(f"measurement:{outcome.event_id}")
        self._ledger_append(
            "gauge_drift_alerted", actor="system", object_refs=refs,
            payload={"gauge_id": outcome.gauge_id, "bias": outcome.bias,
                     "repeatability_sigma": outcome.repeatability_sigma,
                     "health_score": outcome.health_score,
                     "reasons": outcome.drift_reasons})
        try:
            import time as _time

            from core.streaming.alert_journal import JournalEntry

            self._get_alert_journal().record(JournalEntry(
                id=f"GAUGE-{outcome.gauge_id}-{int(_time.time())}",
                ts=_time.time(), device=outcome.gauge_id, channel="bias",
                kind="gauge_drift", severity="warning",
                desc=f"量具漂移: {reasons}", value=float(outcome.bias)))
        except Exception:  # 留存失败不影响提示
            import logging
            logging.getLogger(__name__).exception("量具漂移写入告警日志失败")
        self.gauge_drift_alerted.emit(outcome.gauge_id, reasons)

    def _on_gauge_drift_ui(self, gauge_id: str, reasons: str) -> None:
        self.statusBar().showMessage(
            f"量具漂移提示：{gauge_id} — {reasons}（建议重做测量系统研究）", 20000)

    def _submit_gauge_measurement(self, gauge_id: str, value: float):
        """量具测量录入（统一走 MeasurementStore：账本/监控/持久化同源）。"""
        from core.measurement_event import MeasurementEvent

        event = MeasurementEvent.from_manual(
            float(value), characteristic_id=str(gauge_id))
        self.measurement_store.add(event)
        return self._last_gauge_outcome.get(str(gauge_id))

    def _on_standard_event(self, event_type: str, object_refs: list[str],
                           payload: dict) -> None:
        self._ledger_append(event_type, object_refs=object_refs, payload=payload)

    def _on_alert_event(self, entry) -> None:
        self._ledger_append(
            "alert_ack", object_refs=[f"alert:{entry.id}", entry.device],
            payload={"device": entry.device, "channel": entry.channel,
                     "kind": entry.kind, "severity": entry.severity,
                     "ack_by": entry.ack_by})

    def _record_data_imported(self, source: str, raw_data: dict,
                              kind: str = "file", extra: dict | None = None) -> None:
        sheets = len(raw_data or {})
        rows = sum(len(df) for df in (raw_data or {}).values()
                   if hasattr(df, "__len__"))
        payload = {"source": str(source), "kind": kind,
                   "sheets": sheets, "rows": int(rows)}
        # 截断等会影响分析范围的事实要进证据，事后才能说明数据不是全量。
        payload.update(extra or {})
        self._ledger_append("data_imported", object_refs=[str(source)],
                            payload=payload)

    def _record_report_exported(self, fmt: str, file_path: str,
                                analyses=None) -> None:
        from core.evidence import credential_trace_code

        records = analyses if analyses is not None else list(self.analyses.values())
        trace = credential_trace_code(
            [(record or {}).get("credential") for record in records])
        refs = [os.path.basename(file_path)]
        if trace:
            refs.append(f"trace:{trace}")
        self._ledger_append("report_exported", object_refs=refs,
                            payload={"format": fmt,
                                     "file": os.path.basename(file_path),
                                     "trace": trace})

    def _restore_ledger(self, events: list, errors: list | None = None) -> None:
        try:
            self.ledger = EvidenceLedger.from_events(events or [])
        except (TypeError, ValueError):
            import logging
            logging.getLogger(__name__).warning(
                "证据账本恢复失败，回退为空账本", exc_info=True)
            self.ledger = EvidenceLedger()
        # 写入失败计数只统计本会话的追加失败；加载期解析错误由 ledger.verify()
        # 在证据视图中以"链校验失败"呈现（若解析错误在，后续追加会被账本拒绝
        # 并计入写入失败，语义不再混叠）
        self._ledger_failures = 0
        if errors:
            import logging
            logging.getLogger(__name__).warning(
                "证据账本存在 %d 条解析错误: %s", len(errors), errors[:3])
        chain = self.ledger.verify()
        if not chain.get("ok"):
            import logging
            logging.getLogger(__name__).warning(
                "证据账本链校验失败: %s", chain.get("reason", ""))

    def _restore_measurement_store(self, entries: list):
        """从 .qap measurements 段恢复测量事件；单条损坏跳过并留痕。"""
        store = MeasurementStore()
        for entry in entries or []:
            try:
                store.add(entry)
            except (TypeError, ValueError):
                import logging
                logging.getLogger(__name__).warning(
                    "跳过无法恢复的测量事件: %r", entry, exc_info=True)
        store.event_sink = self._on_measurement_event
        self.measurement_store = store

    def _on_stream_measurements(self, events):
        """连接器采集旁路：仅在测量采集开启时写入项目事件集合。"""
        if not getattr(self, "measurement_capture", False):
            return
        self.measurement_store.extend(events)
