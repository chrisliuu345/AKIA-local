"""改善案例工作流 v1 — 案例脊柱的编排层（v4.2.0 P5 / v4.3.0 B1）。

职责边界:
- 本模块**只编排与留痕**：定义阶段顺序、把每一步的结果、时间戳、数据引用、
  测量事件引用、标准引用与判定凭证按顺序落到 ``ImprovementCase``，并提供结论/
  标准草稿与 Markdown 导出；
- 具体统计计算仍由既有引擎完成（如配对检验调用
  ``analysis.hypothesis.t_tests.paired``），工作流只记录"用了哪份数据、算出什么、
  什么时候算的"；
- 可选注入 ``EvidenceLedger``：案例创建/步骤/关闭/重开自动写入账本事件；
  不注入时行为与 v4.2.0 一致。

阶段顺序（与路线图一致）::

    baseline → time_study → line_balance → improvement → remeasure →
    paired_test → conclusion → standard

无 Qt 依赖（分层守卫：core 不得依赖 ui）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.evidence import make_credential
from core.improvement_case import CASE_PHASES, ImprovementCase

CASE_WORKFLOW_SCHEMA_VERSION = "1"

PHASES: tuple[str, ...] = (
    "baseline", "time_study", "line_balance", "improvement",
    "remeasure", "paired_test", "conclusion", "standard",
)

#: record_step 允许的步骤名 = 工作流 8 步 + 规范 6 阶段（质量类案例直接用 verify 等）
ALL_PHASES: tuple[str, ...] = tuple(dict.fromkeys((*PHASES, *CASE_PHASES)))

PHASE_LABELS: dict[str, str] = {
    "baseline": "基线测量",
    "time_study": "时间研究",
    "line_balance": "线平衡瓶颈",
    "improvement": "改善方案",
    "remeasure": "复测",
    "paired_test": "配对检验",
    "conclusion": "结论",
    "standard": "标准草稿",
    "analyse": "分析",
    "improve": "改善",
    "re_measure": "复测",
    "verify": "验证",
    "standardise": "标准",
}

#: 既有分析结果 analysis_type → 案例阶段（长度 >=2 的子串匹配，大小写不敏感）
ANALYSIS_PHASE_MAP: dict[str, str] = {
    "时间研究": "time_study",
    "time_study": "time_study",
    "生产线平衡": "line_balance",
    "line_balance": "line_balance",
    "配对检验": "paired_test",
    "paired_t": "paired_test",
    "过程能力": "verify",
    "capability": "verify",
    "控制图": "analyse",
    "spc": "analyse",
}


class CaseWorkflow:
    """单个改善案例的执行轨迹（逐步记录，可导出/入库）。"""

    def __init__(self, title: str, product: str = "", owner: str = "",
                 case_id: str | None = None, ledger=None):
        if not str(title or "").strip():
            raise ValueError("案例标题不能为空")
        self.case = ImprovementCase(
            id=case_id or f"CASE-{datetime.now():%Y%m%d-%H%M%S}",
            title=str(title), owner=str(owner or ""), product=str(product or ""))
        self.product = str(product or "")
        self.owner = str(owner or "")
        self.ledger = ledger
        self._last_step: dict[str, Any] | None = None
        self._emit("case_created", {"title": self.case.title,
                                    "product": self.product, "owner": self.owner})

    # ---------------------------------------------------------------- 步骤
    def record_step(self, phase: str, result: dict[str, Any] | None = None,
                    data_ref: str = "", note: str = "",
                    frame: pd.DataFrame | None = None,
                    rule_version: str = "",
                    params: dict[str, Any] | None = None,
                    analysis_type: str = "",
                    measurement_refs: list[str] | None = None,
                    standard_refs: list[str] | None = None) -> dict[str, Any]:
        """记录一个阶段：结果 + 数据引用 + 时间戳 + 判定凭证。

        Args:
            phase: PHASES 之一
            result: 该阶段的引擎输出（原样留痕，不重算）
            data_ref: 数据引用（如 "sheet:工时!A2:D41" 或文件路径 + 行范围）
            note: 人工说明（改善措施、判断依据等）
            frame: 该阶段实际使用的数据（用于指纹）；None 记 ``no-data``
            rule_version: 规则/算法版本（默认阶段名）
            params: 显式判定参数；缺省取 ``result["params"]``
            analysis_type: 显式分析类型；缺省取 ``result["analysis_type"]``
            measurement_refs: 关联的 MeasurementEvent ID 列表
            standard_refs: 关联的 StandardRecord ID 列表
        """
        key = str(phase or "").strip()
        if key not in ALL_PHASES:
            raise ValueError(f"未知阶段 {phase}（可选 {list(ALL_PHASES)}）")
        if result is not None and not isinstance(result, dict):
            raise ValueError("result 必须为 dict")
        payload = dict(result or {})
        step_params: dict[str, Any] = {"data_ref": data_ref}
        if params is not None:
            step_params.update(params)
        else:
            step_params.update(payload.get("params", {}) or {})
        credential = make_credential(
            rule_version=rule_version or key,
            params=step_params,
            df=frame,
            algorithm=analysis_type or str(payload.get("analysis_type", "")),
        ).to_dict()
        step = self.case.add_step(
            key, ref=data_ref, note=note, result=payload or None,
            credential=credential,
            measurement_refs=measurement_refs, standard_refs=standard_refs)
        step.update({
            "label": PHASE_LABELS[key],
            "recorded_at": step.get("at") or credential["computed_at"],
            "result": payload,
        })
        self._last_step = step
        self._emit("case_step", {
            "phase": key, "ref": str(data_ref or ""),
            "rule_version": credential["rule_version"],
            "data_fingerprint": credential["data_fingerprint"]})
        return step

    def run_paired_test(self, before, after, data_ref: str = "",
                        alternative: str = "two-sided",
                        measurement_refs: list[str] | None = None) -> dict[str, Any]:
        """执行配对检验并把结论记入案例（唯一内置计算的步骤）。"""
        from analysis.hypothesis.t_tests import paired

        before_series = pd.Series(before, dtype=float).reset_index(drop=True)
        after_series = pd.Series(after, dtype=float).reset_index(drop=True)
        result = paired(before_series, after_series, alternative=alternative)
        frame = pd.DataFrame({"before": before_series, "after": after_series})
        significant = bool(result.get("is_significant"))
        note = ("复测与基线差异显著" if significant else "复测与基线无显著差异")
        return self.record_step("paired_test", result=result,
                                data_ref=data_ref, note=note, frame=frame,
                                rule_version=f"paired-t/{alternative}",
                                analysis_type="配对检验",
                                measurement_refs=measurement_refs)

    @staticmethod
    def phase_for_analysis(analysis_type: str) -> str:
        """把分析类型映射到案例阶段；未映射时给结构化中文错误。"""
        text = str(analysis_type or "").strip().lower()
        if not text:
            raise ValueError("分析类型不能为空")
        for key, phase in ANALYSIS_PHASE_MAP.items():
            if key.lower() in text:
                return phase
        raise ValueError(f"分析类型「{analysis_type}」尚未接入案例阶段映射")

    def record_analysis_step(self, record: dict[str, Any], data_ref: str = "",
                             frame: pd.DataFrame | None = None, note: str = "",
                             measurement_refs: list[str] | None = None,
                             standard_refs: list[str] | None = None) -> dict[str, Any]:
        """把 ``MainWindow.analyses`` 中的一条分析记录类型化记入案例。"""
        if not isinstance(record, dict):
            raise ValueError("分析记录必须为 dict")
        analysis_type = str(record.get("analysis_type") or "").strip()
        phase = self.phase_for_analysis(analysis_type)
        return self.record_step(
            phase, result=record.get("result", {}), data_ref=data_ref, note=note,
            frame=frame, params=record.get("params") or {},
            analysis_type=analysis_type,
            rule_version=str(record.get("rule_version") or f"{analysis_type}@case"),
            measurement_refs=measurement_refs, standard_refs=standard_refs)

    def conclude(self, text: str, data_ref: str = "") -> dict[str, Any]:
        """写入结论（人工判断），并附带此前的配对检验结论作为依据引用。"""
        if not str(text or "").strip():
            raise ValueError("结论内容不能为空")
        step = self.record_step("conclusion", result={"statement": str(text)},
                                data_ref=data_ref, note=str(text))
        if data_ref and data_ref not in self.case.conclusion_refs:
            self.case.conclusion_refs.append(str(data_ref))
        return step

    def standard_draft(self, text: str, data_ref: str = "") -> dict[str, Any]:
        """写入标准草稿（作业标准/控制计划更新建议）。"""
        if not str(text or "").strip():
            raise ValueError("标准草稿内容不能为空")
        self.case.standard_draft = str(text)
        return self.record_step("standard", result={"draft": str(text)},
                                data_ref=data_ref, note=str(text))

    # ---------------------------------------------------------------- 生命周期
    def close_case(self, reason: str) -> dict[str, Any]:
        """通过关闭门禁后关闭案例（事件写账本）。"""
        return self.case.close_case(reason, ledger=self.ledger)

    def reopen(self, reason: str) -> str:
        """重开案例（事件写账本）。"""
        return self.case.reopen(reason, ledger=self.ledger)

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.ledger is None:
            return
        append = getattr(self.ledger, "append", None)
        if callable(append):
            append(event_type, actor=self.owner or "user",
                   object_refs=[f"case:{self.case.id}"], payload=payload)

    # ---------------------------------------------------------------- 导出
    def missing_phases(self) -> list[str]:
        done = {step.get("phase") for step in self.case.steps}
        return [phase for phase in PHASES if phase not in done]

    def to_markdown(self) -> str:
        owner = self.owner or self.case.owner or "-"
        product = self.product or self.case.product
        lines = [f"# 改善案例: {self.case.title}",
                 f"案例号: {self.case.id} | 状态: {self.case.status} | 负责人: {owner}"
                 + (f" | 产品/线体: {product}" if product else ""),
                 f"已记录阶段: {len(self.case.steps)}/{len(PHASES)}"
                 + (f" | 待补: {'、'.join(PHASE_LABELS[p] for p in self.missing_phases())}"
                    if self.missing_phases() else ""),
                 ""]
        for step in self.case.steps:
            label = step.get("label") or PHASE_LABELS.get(str(step.get("phase")), "")
            lines.append(f"## {label}（{step.get('phase')}）")
            lines.append(f"- 时间: {step.get('recorded_at') or step.get('at', '')}")
            if step.get("ref"):
                lines.append(f"- 数据引用: {step['ref']}")
            if step.get("measurement_refs"):
                lines.append(f"- 测量事件: {'、'.join(step['measurement_refs'])}")
            if step.get("standard_refs"):
                lines.append(f"- 标准版本: {'、'.join(step['standard_refs'])}")
            credential = step.get("credential") or {}
            if credential:
                lines.append(f"- 凭证: {credential.get('rule_version', '')} · "
                             f"{credential.get('data_fingerprint', '')} · "
                             f"v{credential.get('app_version', '')}")
            if step.get("note"):
                lines.append(f"- 说明: {step['note']}")
            result = step.get("result") or {}
            if result:
                lines.append(f"- 结果: {_summarize(result)}")
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CASE_WORKFLOW_SCHEMA_VERSION,
            "case": self.case.to_dict(),
            "product": self.product,
            "owner": self.owner,
            "phase_order": list(PHASES),
            "missing_phases": self.missing_phases(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any], ledger=None) -> CaseWorkflow:
        """从 `.qap` cases 段恢复；兼容 v0 裸 ImprovementCase 与 v1 包装结构。"""
        if not isinstance(payload, dict):
            raise ValueError("案例记录必须为 dict")
        wrapped = "case" in payload
        case = ImprovementCase.from_dict(payload["case"] if wrapped else payload)
        workflow = cls(title=case.title,
                       product=str(payload.get("product") or case.product or ""),
                       owner=str(payload.get("owner") or case.owner or ""),
                       case_id=case.id)
        workflow.case = case
        workflow.ledger = ledger
        return workflow


def _summarize(result: dict[str, Any], limit: int = 3) -> str:
    """把引擎结果压缩成一行可读摘要（取标量字段，最多 limit 项）。"""
    parts: list[str] = []
    for key, value in result.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parts.append(f"{key}={value:.4g}" if isinstance(value, float) else f"{key}={value}")
        elif isinstance(value, bool):
            parts.append(f"{key}={'是' if value else '否'}")
        elif isinstance(value, str) and len(value) <= 40:
            parts.append(f"{key}={value}")
        if len(parts) >= limit:
            break
    if not parts:
        return f"（{len(result)} 个字段）"
    return "，".join(parts)
