"""改善案例、收益、技能矩阵和标准工时证据。"""

import os
import pandas as pd

from PySide6.QtWidgets import (
    QMessageBox,
)

from core.benefit_ledger import (
    record_case_benefit as core_record_case_benefit,
)
from core.skill_matrix import SkillMatrix

from ui._tab_registry import TAB_INDEX


class CaseMixin:
    def _default_case_frame(self):
        """当前导入数据中的第一张非空表 → (DataFrame, 表名)。"""
        raw = (self.current_data or {}).get("raw_data") or {}
        for name, candidate in raw.items():
            if isinstance(candidate, pd.DataFrame) and not candidate.empty:
                return candidate, str(name)
        return None, "Sheet1"

    def _register_case_workflow(self, workflow):
        """登记案例到当前项目并返回（保存 .qap 时统一落盘）。"""
        self.case_workflows.append(workflow)
        self._last_case_workflow = workflow
        return workflow

    def _create_case_from_current_data(self, title: str = ""):
        """以当前导入数据建立案例基线。"""
        from core.case_workflow import CaseWorkflow

        source = str((self.current_data or {}).get("source", "") or "")
        default_title = (f"改善案例 — {os.path.basename(source)}" if source
                         else "改善案例")
        workflow = CaseWorkflow(title=title or default_title, ledger=self.ledger)
        frame, sheet_name = self._default_case_frame()
        if frame is not None:
            workflow.record_step(
                "baseline", {"params": {"rows": int(len(frame))}},
                data_ref=f"sheet:{sheet_name}",
                frame=frame, note="从当前导入数据建立基线")
        return self._register_case_workflow(workflow)

    def _open_case_workflow_dialog(self, workflow):
        from ui.dialogs.case_workflow_dialog import CaseWorkflowDialog

        CaseWorkflowDialog(workflow, self).exec()

    def _on_case_workbench(self):
        """改善案例工作台（v4.2.0 P5）：以当前导入数据建立案例并打开工作台。"""
        workflow = self._create_case_from_current_data()
        self._open_case_workflow_dialog(workflow)

    def _on_case_center(self):
        """改善案例中心（v4.3.0 B1-4）：查看/新建/打开当前项目的案例。"""
        from ui.dialogs.case_center_dialog import CaseCenterDialog

        dialog = CaseCenterDialog(self.case_workflows, self,
                                  create_callback=self._create_case_from_current_data)
        if dialog.exec() == CaseCenterDialog.Accepted:
            workflow = dialog.selected_workflow()
            if workflow is not None:
                self._last_case_workflow = workflow
                self._open_case_workflow_dialog(workflow)

    # ------------------------------------------------------------ 告警自动立案（v4.4.0 B1）
    def _create_alert_case(self, title: str, product: str = "",
                           owner: str = ""):
        """orchestrator 的案例工厂：创建并登记（保存 .qap 时统一落盘）。"""
        from core.case_workflow import CaseWorkflow

        workflow = CaseWorkflow(title=title, product=product, owner=owner,
                                ledger=self.ledger)
        return self._register_case_workflow(workflow)

    def _find_case_by_id(self, case_id: str):
        target = str(case_id or "").strip()
        for workflow in self.case_workflows:
            if getattr(workflow.case, "id", "") == target:
                return workflow
        return None

    def _on_live_alert(self, event) -> None:
        """告警引擎钩子（采集线程内）：按策略立案/合并；UI 通知经信号回主线程。"""
        try:
            decision = self.alert_case_orchestrator.handle(event)
        except Exception:  # 立案失败不得影响告警通知/留存主链路
            import logging
            logging.getLogger(__name__).exception("告警自动立案失败")
            return
        if decision.action == "opened":
            self.alert_case_opened.emit(decision.case_id, decision.title,
                                        decision.rule_key)

    def _on_alert_case_opened_ui(self, case_id: str, title: str,
                                 rule_key: str) -> None:
        self.statusBar().showMessage(
            f"已自动立案: {title}（{case_id}）", 15000)

    def _open_case_by_id(self, case_id: str) -> bool:
        workflow = self._find_case_by_id(case_id)
        if workflow is None:
            QMessageBox.information(self, "改善案例", f"未找到案例 {case_id}")
            return False
        self._last_case_workflow = workflow
        self._open_case_workflow_dialog(workflow)
        return True

    def open_eight_d_report(self, report_id: str) -> bool:
        """打开项目上下文中的 8D 报告并载入 8D Tab（含自动立案草稿）。"""
        report = None
        for item in list(getattr(self.project_context, "eight_d_reports", []) or []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("title") or "")
            if key == str(report_id or "").strip():
                report = item
                break
        if report is None:
            QMessageBox.information(self, "8D 报告", f"未找到 8D 报告 {report_id}")
            return False
        tab = self._lazy_load_tab(TAB_INDEX["eight_d"])
        if tab is None or not hasattr(tab, "load_report"):
            return False
        tab.set_project_context(self.project_context)
        tab.load_report(report)
        self._switch_tab(TAB_INDEX["eight_d"])
        return True

    # ------------------------------------------------------------ 收益账本（v4.4.0 B4）
    def _benefit_event_sink(self, event_type: str, object_refs: list,
                            payload: dict) -> None:
        self._ledger_append(event_type, object_refs=object_refs, payload=payload)

    def record_case_benefit(self, workflow, draft: dict):
        """案例收益入账（关闭案例后由工作台调用；口径自动带标准版本）。"""
        record = core_record_case_benefit(
            self.benefit_ledger, workflow.case,
            standards=self.project_context.standards,
            event_sink=self._benefit_event_sink, **draft)
        return record

    def recompute_benefits(self, month: str) -> dict:
        """月度复算（当月口径前移；历史月冻结），复算事件入证据账本。"""
        return self.benefit_ledger.recompute_month(
            month, standards=self.project_context.standards,
            event_sink=self._benefit_event_sink)

    def case_benefit_summary(self, case_id: str) -> str:
        """案例维度的收益摘要（工作台显示，回答"这条改善省了多少"）。"""
        records = self.benefit_ledger.for_case(case_id)
        if not records:
            return ""
        admitted = [record for record in records if record.admits_to_summary]
        total = sum(record.amount for record in admitted
                    if record.ledger_kind == "improvement")
        parts = [f"改善收益 {total:,.2f}（{len(admitted)} 条入账）"]
        pending = len(records) - len(admitted)
        if pending:
            parts.append(f"{pending} 条待完善(C)")
        return " · ".join(parts)

    def _on_benefit_ledger(self):
        from ui.dialogs.benefit_ledger_dialog import BenefitLedgerDialog

        dialog = BenefitLedgerDialog(self.benefit_ledger, self,
                                     recompute=self.recompute_benefits)
        dialog.exec()

    # ------------------------------------------------------------ 技能矩阵（v4.4.0 B5）
    def save_skill_matrix(self, matrix) -> None:
        """保存技能矩阵（对话框回调）并同步已加载的线平衡页签。"""
        if not isinstance(matrix, SkillMatrix):
            raise TypeError("save_skill_matrix 仅接受 SkillMatrix")
        self.skill_matrix = matrix
        tab = self._tab_cache.get(TAB_INDEX["line_balance"])
        if tab is not None and hasattr(tab, "set_skill_context"):
            tab.set_skill_context(self.skill_matrix, self.save_skill_matrix,
                                  self.record_skill_balance_step)
        if tab is not None and hasattr(tab, "set_balance_context"):
            tab.set_balance_context(self.project_context,
                                    self.record_line_balance_step)

    def record_skill_balance_step(self, phase: str, result: dict, frame=None):
        """把技能约束排班结果记入案例（基线/复测）；凭证含技能矩阵指纹。"""
        key = str(phase or "").strip().lower()
        if key not in ("baseline", "re_measure", "remeasure"):
            raise ValueError(f"不支持的案例阶段: {phase!r}")
        workflow = self._last_case_workflow
        if workflow is None:
            # 技能排班即基线：新建空案例直接记技能步骤（不叠加"当前数据"基线）
            from core.case_workflow import CaseWorkflow

            source = str((self.current_data or {}).get("source", "") or "")
            title = (f"改善案例 — {os.path.basename(source)}" if source
                     else "改善案例")
            workflow = self._register_case_workflow(
                CaseWorkflow(title=title, ledger=self.ledger))
        constraints = result.get("constraints") or {}
        step = workflow.record_step(
            key, result=result, frame=frame, rule_version="skills-lpt@1",
            analysis_type="技能约束线平衡",
            params={"skill_fingerprint": self.skill_matrix.fingerprint(),
                    "headcount_required": constraints.get("headcount_required"),
                    "unmet": list(result.get("unmet") or [])},
            note="技能约束线平衡（含技能矩阵指纹）")
        return step

    def record_line_balance_step(self, phase: str, bundle: dict):
        """把已确认标准工时算出的线平衡记入案例，并写入证据账本。"""
        from analysis.ie.chain import IE_STANDARD_VERSION, record_balance

        key = str(phase or "").strip().lower()
        if key in ("re_measure", "remeasure"):
            key = "re_measure"
        elif key != "baseline":
            raise ValueError(f"不支持的案例阶段: {phase!r}")
        workflow = self._last_case_workflow
        if workflow is None:
            from core.case_workflow import CaseWorkflow

            source = str((self.current_data or {}).get("source", "") or "")
            title = (f"改善案例 — {os.path.basename(source)}" if source
                     else "改善案例")
            workflow = self._register_case_workflow(
                CaseWorkflow(title=title, ledger=self.ledger))
        event = record_balance(
            self.ledger, phase=key, case_id=workflow.case.id, result=bundle)
        record_ids = [str(item.get("standard_record_id"))
                      for item in bundle.get("records") or []
                      if item.get("standard_record_id")]
        workflow.record_step(
            key, result=bundle.get("balance") or {},
            rule_version=IE_STANDARD_VERSION,
            analysis_type="生产线平衡",
            params={"standard_version": IE_STANDARD_VERSION,
                    "standard_record_ids": record_ids,
                    "evidence_event_id": event.event_id},
            standard_refs=record_ids,
            note="已确认标准工时进入线平衡")
        return event

    def _on_standard_history(self):
        """标准版本时间线（B3）：对象 / 生效区间 / 变更原因 / 变更人。"""
        from ui.dialogs.standard_history_dialog import StandardHistoryDialog

        registry = getattr(self.project_context, "standards", None)
        if registry is None or not len(registry):
            QMessageBox.information(self, "标准版本记录", "当前项目尚无标准版本记录")
            return
        StandardHistoryDialog(registry, self).exec()

    def _on_evidence_view(self):
        """证据视图（B4-2）：结论 → 凭证 → 账本事件 → 原始引用。"""
        from ui.dialogs.evidence_view_dialog import EvidenceViewDialog

        dialog = EvidenceViewDialog(
            self.analyses, self.ledger, parent=self,
            registry=getattr(self.project_context, "standards", None),
            measurements=self.measurement_store,
            frame_provider=self._analysis_source_frame,
            ledger_failures=self._ledger_failures)
        dialog.exec()

    def _restore_case_workflows(self, entries: list):
        """从 .qap cases 段恢复案例；单条损坏不影响项目其余内容。"""
        from core.case_workflow import CaseWorkflow

        restored = []
        for entry in entries or []:
            try:
                restored.append(CaseWorkflow.from_dict(entry, ledger=self.ledger))
            except Exception:  # 单条案例损坏 → 跳过并留痕，不阻断项目加载
                import logging
                logging.getLogger(__name__).warning(
                    "跳过无法恢复的改善案例: %r", entry, exc_info=True)
        self.case_workflows = restored
        self._last_case_workflow = restored[-1] if restored else None
        orchestrator = getattr(self, "alert_case_orchestrator", None)
        if orchestrator is not None:
            orchestrator.rebuild(restored)
