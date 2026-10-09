"""项目上下文 — 跨 Tab 共享数据模型

提供 QualityCharacteristic（质量特性）和 ProjectContext（项目级上下文），
支持五链贯通：FMEA → CP → SPC → PPAP → 8D。
"""

import contextlib
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from config.settings import RPN_HIGH
from core.standard_record import StandardRecord, StandardRegistry


@dataclass
class QualityCharacteristic:
    """质量特性 — 五链贯通的核心数据单元"""
    id: str = ""
    name: str = ""
    process: str = ""
    usl: float | None = None
    lsl: float | None = None
    target: float | None = None
    unit: str = ""
    data_source: str = ""
    spc_method: str = ""
    notes: str = ""

    fmea_item_id: str = ""
    cp_row_id: str = ""
    ppap_item_id: str = ""
    eight_d_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "process": self.process,
            "usl": self.usl, "lsl": self.lsl, "target": self.target,
            "unit": self.unit, "data_source": self.data_source,
            "spc_method": self.spc_method, "notes": self.notes,
            "fmea_item_id": self.fmea_item_id, "cp_row_id": self.cp_row_id,
            "ppap_item_id": self.ppap_item_id, "eight_d_id": self.eight_d_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QualityCharacteristic":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProjectContext:
    """项目级上下文 — 跨 Tab 共享的数据容器"""
    project_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    characteristics: list[QualityCharacteristic] = field(default_factory=list)

    fmea_items: list[dict] = field(default_factory=list)
    control_plan_rows: list[dict] = field(default_factory=list)
    ppap_report: dict[str, Any] = field(default_factory=dict)
    eight_d_reports: list[dict] = field(default_factory=list)

    analysis_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    chart_options: dict[str, dict[str, Any]] = field(default_factory=dict)
    standards: StandardRegistry = field(default_factory=StandardRegistry)
    event_sink: Any = field(default=None, repr=False, compare=False)

    def add_characteristic(self, qc: QualityCharacteristic):
        """添加质量特性"""
        if not qc.id:
            qc.id = f"QC-{len(self.characteristics) + 1:03d}"
        self.characteristics.append(qc)
        self.updated_at = datetime.now().isoformat()

    def get_characteristic(self, qc_id: str) -> QualityCharacteristic | None:
        """按 ID 获取质量特性"""
        for qc in self.characteristics:
            if qc.id == qc_id:
                return qc
        return None

    def update_characteristic(self, qc_id: str, **kwargs):
        """更新质量特性字段"""
        qc = self.get_characteristic(qc_id)
        if qc:
            for k, v in kwargs.items():
                if hasattr(qc, k):
                    setattr(qc, k, v)
            self.updated_at = datetime.now().isoformat()

    def remove_characteristic(self, qc_id: str):
        """移除质量特性"""
        self.characteristics = [qc for qc in self.characteristics if qc.id != qc_id]
        self.updated_at = datetime.now().isoformat()

    def set_fmea_items(self, items: list[dict]):
        """设置 FMEA 条目"""
        self.fmea_items = items
        self.updated_at = datetime.now().isoformat()

    @staticmethod
    def _cp_row_key(row: Any, index: int) -> str:
        if isinstance(row, dict):
            key = (f"{row.get('工序编号', '')}|"
                   f"{row.get('特性(产品/过程)', '')}").strip("|")
        elif isinstance(row, (list, tuple)):
            values = [str(row[0]) if len(row) > 0 else "",
                      str(row[2]) if len(row) > 2 else ""]
            key = "|".join(values).strip("|")
        else:
            key = ""
        return key or f"CP-{index + 1:03d}"

    def set_control_plan(self, rows: list[dict], change_reason: str = "控制计划条目更新",
                         changed_by: str = "user"):
        """设置控制计划行，并按条目差异记录标准版本（新增/修改/移除）。"""
        before_ids = {record.record_id for record in self.standards.records}
        rows = list(rows or [])
        new_map: dict[str, Any] = {}
        for index, row in enumerate(rows):
            key = self._cp_row_key(row, index)
            if key in new_map:
                key = f"{key}#{index + 1}"
            new_map[key] = row
        old_map: dict[str, Any] = {}
        for index, row in enumerate(self.control_plan_rows):
            key = self._cp_row_key(row, index)
            if key in old_map:
                key = f"{key}#{index + 1}"
            old_map[key] = row
        for key, row in new_map.items():
            if old_map.get(key) != row:
                self.standards.record_change(
                    "control_plan_row", key, {"row": row, "removed": False},
                    change_reason=change_reason, changed_by=changed_by)
        for key, row in old_map.items():
            if key not in new_map:
                self.standards.record_change(
                    "control_plan_row", key, {"row": row, "removed": True},
                    change_reason=change_reason, changed_by=changed_by)
        self._emit_new_records(before_ids)
        self.control_plan_rows = rows
        self.updated_at = datetime.now().isoformat()

    # ---------------------------------------------------------------- 标准版本
    def record_specification(self, characteristic_id: str, *, usl: float | None,
                             lsl: float | None, target: float | None = None,
                             unit: str | None = None, change_reason: str,
                             changed_by: str = "", source_case_id: str = "") -> StandardRecord:
        """记录规格限版本；若质量特性存在则同步更新其当前值。"""
        ref = str(characteristic_id or "").strip()
        if not ref:
            raise ValueError("规格限标准必须提供特性 ID / 列名")
        qc = self.get_characteristic(ref)
        payload: dict[str, Any] = {
            "usl": usl, "lsl": lsl, "target": target,
            "unit": unit if unit is not None else (qc.unit if qc else ""),
        }
        if qc is not None:
            qc.usl = None if usl is None else float(usl)
            qc.lsl = None if lsl is None else float(lsl)
            if target is not None:
                qc.target = float(target)
            payload["name"] = qc.name
            payload["process"] = qc.process
        before = len(self.standards)
        record = self.standards.record_change(
            "spec_limit", ref, payload, change_reason=change_reason,
            changed_by=changed_by, source_case_id=source_case_id)
        if len(self.standards) > before:
            self._emit_standard(record, change_reason, changed_by)
        self.updated_at = datetime.now().isoformat()
        return record

    def record_control_limit(self, object_ref: str, *, cl: float | None,
                             ucl: float | None, lcl: float | None,
                             chart_type: str = "", subgroup_size: int | None = None,
                             change_reason: str, changed_by: str = "") -> StandardRecord:
        ref = str(object_ref or "").strip()
        if not ref:
            raise ValueError("控制限标准必须提供对象引用")
        before = len(self.standards)
        record = self.standards.record_change(
            "control_limit", ref,
            {"cl": cl, "ucl": ucl, "lcl": lcl, "chart_type": chart_type,
             "subgroup_size": subgroup_size},
            change_reason=change_reason, changed_by=changed_by)
        if len(self.standards) > before:
            self._emit_standard(record, change_reason, changed_by)
        self.updated_at = datetime.now().isoformat()
        return record

    def record_standard_time(self, object_ref: str, *, standard_time_s: float,
                             normal_time_s: float | None = None,
                             allowance_pct: float | None = None,
                             rating: float | None = None,
                             cycles: int | None = None, operator: str = "",
                             change_reason: str, changed_by: str = "",
                             source_case_id: str = "") -> StandardRecord:
        ref = str(object_ref or "").strip()
        if not ref:
            raise ValueError("标准工时必须提供工序引用")
        before = len(self.standards)
        record = self.standards.record_change(
            "standard_time", ref,
            {"standard_time_s": float(standard_time_s),
             "normal_time_s": normal_time_s, "allowance_pct": allowance_pct,
             "rating": rating, "cycles": cycles, "operator": operator},
            change_reason=change_reason, changed_by=changed_by,
            source_case_id=source_case_id)
        if len(self.standards) > before:
            self._emit_standard(record, change_reason, changed_by)
        self.updated_at = datetime.now().isoformat()
        return record

    def record_work_combination(self, object_ref: str, payload: dict[str, Any], *,
                                change_reason: str, changed_by: str = "",
                                source_case_id: str = "") -> StandardRecord:
        ref = str(object_ref or "").strip()
        if not ref:
            raise ValueError("作业组合票必须提供对象引用")
        before = len(self.standards)
        record = self.standards.record_change(
            "work_combination", ref, payload, change_reason=change_reason,
            changed_by=changed_by, source_case_id=source_case_id)
        if len(self.standards) > before:
            self._emit_standard(record, change_reason, changed_by)
        self.updated_at = datetime.now().isoformat()
        return record

    def standard_as_of(self, object_ref: str, ts: str) -> StandardRecord | None:
        return self.standards.as_of(object_ref, ts)

    def _emit_standard(self, record: StandardRecord, change_reason: str,
                       changed_by: str) -> None:
        sink = self.event_sink
        if not callable(sink):
            return
        with contextlib.suppress(Exception):  # 账本旁路失败不得阻断标准写入
            sink("standard_changed", [record.object_ref, record.record_id], {
                "object_type": record.object_type,
                "record_id": record.record_id,
                "object_ref": record.object_ref,
                "change_reason": change_reason or record.change_reason,
                "changed_by": changed_by,
                "valid_from": record.valid_from,
                "fingerprint": record.fingerprint,
            })

    def _emit_new_records(self, before_ids: set[str]) -> None:
        """控制计划批量写入后，把本轮新增版本逐条写入账本（不重复记账）。"""
        sink = self.event_sink
        if not callable(sink):
            return
        for record in self.standards.records:
            if record.record_id in before_ids:
                continue
            with contextlib.suppress(Exception):
                sink("standard_changed", [record.object_ref, record.record_id], {
                    "object_type": record.object_type,
                    "record_id": record.record_id,
                    "object_ref": record.object_ref,
                    "change_reason": record.change_reason,
                    "changed_by": record.changed_by,
                    "valid_from": record.valid_from,
                    "fingerprint": record.fingerprint,
                })

    def set_ppap_report(self, report: dict[str, Any]):
        """设置 PPAP 报告状态"""
        self.ppap_report = report
        self.updated_at = datetime.now().isoformat()

    def add_eight_d_report(self, report: dict):
        """添加 8D 报告"""
        self.eight_d_reports.append(report)
        self.updated_at = datetime.now().isoformat()

    def upsert_eight_d_report(self, report: dict, report_id: str = "") -> None:
        """按 ID 新增或替换 8D 报告 — 避免同一报告反复保存时重复堆积"""
        key = report_id or report.get("id", "") or report.get("title", "")
        if key:
            for i, existing in enumerate(self.eight_d_reports):
                existing_key = existing.get("id", "") or existing.get("title", "")
                if existing_key == key:
                    self.eight_d_reports[i] = report
                    self.updated_at = datetime.now().isoformat()
                    return
        self.add_eight_d_report(report)

    def set_analysis_snapshot(self, key: str, snapshot: dict[str, Any]):
        """设置分析结果快照"""
        self.analysis_snapshots[key] = snapshot
        self.updated_at = datetime.now().isoformat()

    def get_analysis_snapshot(self, key: str) -> dict[str, Any] | None:
        """获取分析结果快照"""
        return self.analysis_snapshots.get(key)

    def set_chart_options(self, chart_id: str, options: dict[str, Any]):
        """设置图表编辑参数"""
        self.chart_options[chart_id] = options
        self.updated_at = datetime.now().isoformat()

    def get_chart_options(self, chart_id: str) -> dict[str, Any] | None:
        """获取图表编辑参数"""
        return self.chart_options.get(chart_id)

    def get_high_risk_fmea_items(self, threshold: int = RPN_HIGH) -> list[dict]:
        """获取高风险 FMEA 条目 (RPN >= threshold)"""
        return [item for item in self.fmea_items if item.get("rpn", 0) >= threshold]

    def get_characteristics_for_spc(self) -> list[QualityCharacteristic]:
        """获取需要 SPC 监控的质量特性"""
        return [qc for qc in self.characteristics if qc.spc_method and qc.data_source]

    def get_fmea_items_for_cp(self) -> list[dict]:
        """获取需要生成控制计划的 FMEA 条目 (高风险项)"""
        return self.get_high_risk_fmea_items()

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "characteristics": [qc.to_dict() for qc in self.characteristics],
            "fmea_items": self.fmea_items,
            "control_plan_rows": self.control_plan_rows,
            "ppap_report": self.ppap_report,
            "eight_d_reports": self.eight_d_reports,
            "analysis_snapshots": self.analysis_snapshots,
            "chart_options": self.chart_options,
            "standards": self.standards.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectContext":
        chars = [QualityCharacteristic.from_dict(qc) for qc in d.get("characteristics", [])]
        from core.standard_record import migrate_legacy_context

        standards_payload = d.get("standards")
        if standards_payload:
            standards = StandardRegistry.from_dict(standards_payload)
        else:
            standards = migrate_legacy_context(d)
        return cls(
            project_name=d.get("project_name", ""),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            characteristics=chars,
            fmea_items=d.get("fmea_items", []),
            control_plan_rows=d.get("control_plan_rows", []),
            ppap_report=d.get("ppap_report", {}),
            eight_d_reports=d.get("eight_d_reports", []),
            analysis_snapshots=d.get("analysis_snapshots", {}),
            chart_options=d.get("chart_options", {}),
            standards=standards,
        )
