"""改善案例 schema v1 — 案例脊柱与生命周期（v4.3.0 B0/B1）。

v0（v4.2.0）只有 id/title/status/refs/steps；v1 增加 owner/product/问题与目标、
测量与标准引用、关闭门禁与重开留痕。生命周期::

    draft → active → verifying → closed
                    ↘ abandoned ↗（reopen 回到 active）

关闭门禁（路线图"案例关闭强制复测 + 统计判定"）要求：
1. 覆盖 baseline / re_measure / verify 三个阶段；
2. verify 阶段存在**带凭证**且含统计判定字段的结果（配对检验 / SPC / 能力对比等）；
3. 填写关闭原因。

v0 文件可读：``from_dict`` 接受 schema_version="0" 并补默认值；v1 严格校验。
本模块无 Qt、无 ui 依赖（core 分层守卫）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from core.time_utils import now_iso

CASE_SCHEMA_VERSION = "1"
LEGACY_CASE_SCHEMA_VERSIONS = ("0",)
CASE_STATUSES = ("draft", "active", "verifying", "closed", "abandoned")

#: 路线图定义的 6 个规范阶段
CASE_PHASES = ("baseline", "analyse", "improve", "re_measure", "verify", "standardise")
#: v4.2.0 案例工作流的 8 个执行步骤（保留兼容）
WORKFLOW_PHASES = ("baseline", "time_study", "line_balance", "improvement",
                   "remeasure", "paired_test", "conclusion", "standard")
#: add_step 允许的步骤名（两套词汇的并集）
KNOWN_STEP_PHASES = tuple(dict.fromkeys((*CASE_PHASES, *WORKFLOW_PHASES)))

#: 执行步骤 → 规范阶段
PHASE_TO_STAGE = {
    "baseline": "baseline",
    "analyse": "analyse",
    "time_study": "analyse",
    "line_balance": "analyse",
    "improve": "improve",
    "improvement": "improve",
    "re_measure": "re_measure",
    "remeasure": "re_measure",
    "verify": "verify",
    "paired_test": "verify",
    "conclusion": "verify",
    "standardise": "standardise",
    "standard": "standardise",
}

#: 关闭案例必须覆盖的规范阶段
CLOSURE_REQUIRED_STAGES = ("baseline", "re_measure", "verify")
#: verify 结果中任一字段出现即视为统计判定证据
VERIFICATION_KEYS = ("p_value", "is_significant", "cpk", "ppk", "verdict",
                     "judgement", "out_of_control", "conclusion")

ALLOWED_TRANSITIONS = {
    "draft": ("active", "abandoned"),
    "active": ("verifying", "abandoned"),
    "verifying": ("active", "abandoned"),
    "closed": (),
    "abandoned": (),
}


def _str_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, (list, tuple)) or any(
            not isinstance(item, str) for item in value):
        raise ValueError(f"{name} 必须为字符串列表")
    return [str(item) for item in value]


@dataclass
class ImprovementCase:
    """改善案例 v1 — 测量 → 分析 → 改善 → 复测 → 验证 → 标准的最小骨架。"""

    id: str
    title: str = ""
    status: str = "active"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    owner: str = ""
    product: str = ""
    problem_statement: str = ""
    target: str = ""
    due_date: str = ""
    tags: list[str] = field(default_factory=list)
    baseline_refs: list[str] = field(default_factory=list)
    conclusion_refs: list[str] = field(default_factory=list)
    measurement_refs: list[str] = field(default_factory=list)
    standard_refs: list[str] = field(default_factory=list)
    report_refs: list[str] = field(default_factory=list)
    standard_draft: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    closed_at: str = ""
    close_reason: str = ""
    reopen_count: int = 0
    reopen_history: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = CASE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not str(self.id or "").strip():
            raise ValueError("案例 id 不能为空")
        if self.status not in CASE_STATUSES:
            raise ValueError(f"非法案例状态: {self.status}（可选 {CASE_STATUSES}）")
        if self.schema_version != CASE_SCHEMA_VERSION:
            raise ValueError(f"不支持的案例 schema 版本: {self.schema_version}")
        for name in ("baseline_refs", "conclusion_refs", "measurement_refs",
                     "standard_refs", "report_refs", "tags"):
            setattr(self, name, _str_list(getattr(self, name), name))
        if not isinstance(self.steps, list):
            raise ValueError("steps 必须为列表")
        if not isinstance(self.reopen_history, list):
            raise ValueError("reopen_history 必须为列表")
        self.reopen_count = int(self.reopen_count)
        if self.reopen_count < 0:
            raise ValueError("reopen_count 不能为负")
        for name in ("title", "owner", "product", "problem_statement", "target",
                     "due_date", "standard_draft", "closed_at", "close_reason"):
            setattr(self, name, str(getattr(self, name) or ""))
        self.id = str(self.id)
        self.created_at = str(self.created_at or now_iso())
        self.updated_at = str(self.updated_at or self.created_at)

    # ---------------------------------------------------------------- 步骤
    def add_step(self, phase: str, ref: str = "", note: str = "", *,
                 result: dict[str, Any] | None = None,
                 credential: dict[str, Any] | None = None,
                 measurement_refs: list[str] | None = None,
                 standard_refs: list[str] | None = None) -> dict[str, Any]:
        """追加一个案例步骤并刷新时间戳；phase 取 ``KNOWN_STEP_PHASES``。"""
        key = str(phase or "").strip()
        if not key:
            raise ValueError("步骤 phase 不能为空")
        if key not in KNOWN_STEP_PHASES:
            raise ValueError(f"未知阶段 {key}（可选 {list(KNOWN_STEP_PHASES)}）")
        step: dict[str, Any] = {"phase": key, "ref": str(ref or ""),
                                "note": str(note or ""), "at": now_iso()}
        if result is not None:
            if not isinstance(result, dict):
                raise ValueError("步骤 result 必须为 dict")
            step["result"] = dict(result)
        if credential is not None:
            if not isinstance(credential, dict):
                raise ValueError("步骤 credential 必须为 dict")
            step["credential"] = dict(credential)
        refs = _str_list(measurement_refs or [], "measurement_refs")
        std_refs = _str_list(standard_refs or [], "standard_refs")
        if refs:
            step["measurement_refs"] = refs
            self.measurement_refs.extend(item for item in refs
                                         if item not in self.measurement_refs)
        if std_refs:
            step["standard_refs"] = std_refs
            self.standard_refs.extend(item for item in std_refs
                                      if item not in self.standard_refs)
        self.steps.append(step)
        self.updated_at = step["at"]
        return step

    # ---------------------------------------------------------------- 阶段
    def covered_stages(self) -> list[str]:
        covered = {PHASE_TO_STAGE.get(str(step.get("phase")), "")
                   for step in self.steps if isinstance(step, dict)}
        return [stage for stage in CASE_PHASES if stage in covered]

    def missing_stages(self) -> list[str]:
        covered = set(self.covered_stages())
        return [stage for stage in CASE_PHASES if stage not in covered]

    def verification_steps(self) -> list[dict[str, Any]]:
        return [step for step in self.steps if isinstance(step, dict)
                and PHASE_TO_STAGE.get(str(step.get("phase"))) == "verify"]

    def has_statistical_verification(self) -> bool:
        """verify 阶段是否存在带凭证 + 统计判定字段的结果。"""
        for step in self.verification_steps():
            result = step.get("result")
            credential = step.get("credential")
            if not isinstance(result, dict) or not result:
                continue
            if not isinstance(credential, dict) or not credential:
                continue
            if any(key in result and result[key] is not None
                   for key in VERIFICATION_KEYS):
                return True
        return False

    def closure_check(self) -> dict[str, Any]:
        """关闭门禁检查：返回 ok / missing_stages / problems。"""
        problems: list[str] = []
        covered = set(self.covered_stages())
        missing = [stage for stage in CLOSURE_REQUIRED_STAGES
                   if stage not in covered]
        if missing:
            problems.append("缺少阶段: " + "、".join(missing))
        if self.status == "closed":
            problems.append("案例已关闭")
        elif self.status not in ("active", "verifying"):
            problems.append(f"当前状态 {self.status} 不允许关闭（需先激活）")
        if not self.has_statistical_verification():
            problems.append("verify 阶段缺少带统计判定的结论证据")
        return {"ok": not problems, "missing_stages": missing, "problems": problems}

    # ---------------------------------------------------------------- 生命周期
    def transition(self, new_status: str, reason: str = "", ledger=None) -> str:
        """状态迁移；closed 走 ``close_case``，closed/abandoned 只能 ``reopen``。"""
        target = str(new_status or "").strip()
        if target not in CASE_STATUSES:
            raise ValueError(f"非法案例状态: {target}（可选 {CASE_STATUSES}）")
        if target == "closed":
            self.close_case(reason, ledger=ledger)
            return self.status
        if self.status in ("closed", "abandoned"):
            raise ValueError(f"案例状态 {self.status} 只能通过 reopen() 恢复")
        if target not in ALLOWED_TRANSITIONS.get(self.status, ()):
            raise ValueError(f"非法状态迁移: {self.status} → {target}")
        if target == "abandoned" and not str(reason or "").strip():
            raise ValueError("放弃案例必须填写原因")
        previous, self.status = self.status, target
        self.updated_at = now_iso()
        self._emit(ledger, "case_status_changed", {
            "from": previous, "to": target, "reason": str(reason or "")})
        return self.status

    def close_case(self, reason: str, ledger=None) -> dict[str, Any]:
        """通过关闭门禁后关闭案例；未通过抛结构化中文错误。"""
        check = self.closure_check()
        if not check["ok"]:
            raise ValueError("案例关闭条件未满足: " + "；".join(check["problems"]))
        text = str(reason or "").strip()
        if not text:
            raise ValueError("案例关闭必须填写关闭原因")
        previous = self.status
        self.status = "closed"
        self.closed_at = now_iso()
        self.close_reason = text
        self.updated_at = self.closed_at
        self._emit(ledger, "case_closed", {
            "reason": text, "previous_status": previous,
            "stages": self.covered_stages()})
        return check

    def reopen(self, reason: str, ledger=None) -> str:
        """重开已关闭/已放弃案例，记录原因并累计 reopen_count。"""
        if self.status not in ("closed", "abandoned"):
            raise ValueError(f"案例状态 {self.status} 不需重开")
        text = str(reason or "").strip()
        if not text:
            raise ValueError("重开案例必须填写原因")
        entry = {"at": now_iso(), "reason": text, "from": self.status}
        self.reopen_history.append(entry)
        self.reopen_count += 1
        previous = self.status
        self.status = "active"
        self.closed_at = ""
        self.close_reason = ""
        self.updated_at = entry["at"]
        self._emit(ledger, "case_reopened", {
            "from": previous, "reason": text, "count": self.reopen_count})
        return self.status

    def _emit(self, ledger, event_type: str, payload: dict[str, Any]) -> None:
        if ledger is None:
            return
        append = getattr(ledger, "append", None)
        if not callable(append):
            return
        append(event_type, actor=self.owner or "user",
               object_refs=[f"case:{self.id}"], payload=payload)

    # ---------------------------------------------------------------- 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "owner": self.owner,
            "product": self.product,
            "problem_statement": self.problem_statement,
            "target": self.target,
            "due_date": self.due_date,
            "tags": list(self.tags),
            "baseline_refs": list(self.baseline_refs),
            "conclusion_refs": list(self.conclusion_refs),
            "measurement_refs": list(self.measurement_refs),
            "standard_refs": list(self.standard_refs),
            "report_refs": list(self.report_refs),
            "standard_draft": self.standard_draft,
            "steps": [dict(step) for step in self.steps],
            "closed_at": self.closed_at,
            "close_reason": self.close_reason,
            "reopen_count": int(self.reopen_count),
            "reopen_history": [dict(item) for item in self.reopen_history],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ImprovementCase:
        if not isinstance(d, dict):
            raise ValueError("案例必须为 dict")
        if not str(d.get("id") or "").strip():
            raise ValueError("案例缺少必填字段: id")
        schema = str(d.get("schema_version") or CASE_SCHEMA_VERSION)
        if schema not in (CASE_SCHEMA_VERSION, *LEGACY_CASE_SCHEMA_VERSIONS):
            raise ValueError(f"不支持的案例 schema 版本: {schema}")
        allowed = {f.name for f in fields(cls)}
        payload = {k: v for k, v in d.items() if k in allowed}
        payload["schema_version"] = CASE_SCHEMA_VERSION
        return cls(**payload)
