"""改善案例工作流 — 案例脊柱的编排层（v4.2.0 P5）。

职责边界:
- 本模块**只编排与留痕**：定义阶段顺序、把每一步的结果、时间戳、数据引用与
  判定凭证按顺序落到 `ImprovementCase`，并提供结论/标准草稿与 Markdown 导出；
- 具体统计计算仍由既有引擎完成（如配对检验调用 `analysis.hypothesis.t_tests.paired`），
  工作流只记录"用了哪份数据、算出什么、什么时候算的"。

阶段顺序（与路线图一致）:
    baseline → time_study → line_balance → improvement → remeasure →
    paired_test → conclusion → standard

无 Qt 依赖（分层守卫：core 不得依赖 ui）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.evidence import make_credential
from core.improvement_case import ImprovementCase

PHASES: tuple[str, ...] = (
    "baseline", "time_study", "line_balance", "improvement",
    "remeasure", "paired_test", "conclusion", "standard",
)

PHASE_LABELS: dict[str, str] = {
    "baseline": "基线测量",
    "time_study": "时间研究",
    "line_balance": "线平衡瓶颈",
    "improvement": "改善方案",
    "remeasure": "复测",
    "paired_test": "配对检验",
    "conclusion": "结论",
    "standard": "标准草稿",
}


class CaseWorkflow:
    """单个改善案例的执行轨迹（逐步记录，可导出/入库）。"""

    def __init__(self, title: str, product: str = "", owner: str = "",
                 case_id: str | None = None):
        if not str(title or "").strip():
            raise ValueError("案例标题不能为空")
        self.case = ImprovementCase(
            id=case_id or f"CASE-{datetime.now():%Y%m%d-%H%M%S}",
            title=str(title))
        self.product = product
        self.owner = owner
        self._last_step: dict[str, Any] | None = None

    # ---------------------------------------------------------------- 步骤
    def record_step(self, phase: str, result: dict[str, Any] | None = None,
                    data_ref: str = "", note: str = "",
                    frame: pd.DataFrame | None = None,
                    rule_version: str = "") -> dict[str, Any]:
        """记录一个阶段：结果 + 数据引用 + 时间戳 + 判定凭证。

        Args:
            phase: PHASES 之一
            result: 该阶段的引擎输出（原样留痕，不重算）
            data_ref: 数据引用（如 "sheet:工时!A2:D41" 或文件路径 + 行范围）
            note: 人工说明（改善措施、判断依据等）
            frame: 该阶段实际使用的数据（用于指纹）；None 记 ``no-data``
            rule_version: 规则/算法版本（默认阶段名）
        """
        key = str(phase or "").strip()
        if key not in PHASES:
            raise ValueError(f"未知阶段 {phase}（可选 {list(PHASES)}）")
        step_params: dict[str, Any] = {"data_ref": data_ref}
        if result:
            step_params.update(result.get("params", {}) or {})
        credential = make_credential(
            rule_version=rule_version or key,
            params=step_params,
            df=frame,
            algorithm=(result or {}).get("analysis_type", ""),
        ).to_dict()
        step = self.case.add_step(key, ref=data_ref, note=note)
        step.update({
            "label": PHASE_LABELS[key],
            "recorded_at": step.get("at") or credential["computed_at"],
            "result": result or {},
            "credential": credential,
        })
        self._last_step = step
        return step

    def run_paired_test(self, before, after, data_ref: str = "",
                        alternative: str = "two-sided") -> dict[str, Any]:
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
                                rule_version=f"paired-t/{alternative}")

    def conclude(self, text: str, data_ref: str = "") -> dict[str, Any]:
        """写入结论（人工判断），并附带此前的配对检验结论作为依据引用。"""
        if not str(text or "").strip():
            raise ValueError("结论内容不能为空")
        return self.record_step("conclusion", result={"statement": str(text)},
                                data_ref=data_ref, note=str(text))

    def standard_draft(self, text: str, data_ref: str = "") -> dict[str, Any]:
        """写入标准草稿（作业标准/控制计划更新建议）。"""
        if not str(text or "").strip():
            raise ValueError("标准草稿内容不能为空")
        self.case.standard_draft = str(text)
        return self.record_step("standard", result={"draft": str(text)},
                                data_ref=data_ref, note=str(text))

    # ---------------------------------------------------------------- 导出
    def missing_phases(self) -> list[str]:
        done = {step.get("phase") for step in self.case.steps}
        return [phase for phase in PHASES if phase not in done]

    def to_markdown(self) -> str:
        lines = [f"# 改善案例: {self.case.title}",
                 f"案例号: {self.case.id} | 负责人: {self.owner or '-'}"
                 + (f" | 产品/线体: {self.product}" if self.product else ""),
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
            "case": self.case.to_dict(),
            "product": self.product,
            "owner": self.owner,
            "phase_order": list(PHASES),
            "missing_phases": self.missing_phases(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CaseWorkflow:
        """从 `.qap` cases 段恢复（旧版案例无 stage 元数据也能读）。"""
        case = ImprovementCase.from_dict(payload.get("case") or payload)
        workflow = cls(title=case.title, product=payload.get("product", ""),
                       owner=payload.get("owner", ""), case_id=case.id)
        workflow.case = case
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
