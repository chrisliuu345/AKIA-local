"""抽样状态编排 v1 — 转移状态机 / 检验批历史 / 抽样决定留痕（v4.4.0 B3）。

职责边界:
- 按「供应商·产品线」作用域维护 ``TransferState``（正常/加严/放宽）与检验批
  历史；每次登记检验批后调用 ``SamplingEngine.evaluate_transfer``（纯函数，
  阈值即 B0 冻结值），状态变化写 ``sampling_transfer_changed`` 事件；
- 方案选择写 ``sampling_plan_selected``，并在 ``StandardRegistry`` 登记
  ``sampling_plan`` 版本记录（as-of 可复判）；
- 检验批判定写 ``lot_inspected``（含决定 ID、方案引用、样本行指纹），
  证据链：sampling_plan_selected（方案）→ lot_inspected（指纹+判定）。

红线:
- 放宽检验默认禁用（``reduced_enabled=False``，PLAN §8 决策 3）；
- 手动覆盖转移状态必须填写原因；
- 无 Qt / 无 ui 依赖（core 分层守卫）；确定性（同输入批序列 → 同状态轨迹）。
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from dataclasses import fields
from datetime import datetime
from typing import Any
from collections.abc import Callable

import pandas as pd

from core.sampling_engine import SamplingEngine
from core.sampling_plan import (
    TRANSFER_STATES,
    LotRecord,
    SamplingDecision,
    TransferState,
    fingerprint_from_frames,
    scope_key_for,
)
from core.time_utils import parse_iso

logger = logging.getLogger(__name__)

SAMPLING_STATE_SCHEMA_VERSION = "1"

#: 转移评估所需的最小近期批窗口（覆盖"连续 10 批接收 → 放宽"）
_TRANSFER_LOOKBACK = 12


class SamplingStateManager:
    """抽样状态编排器（无 Qt；账本/标准注册表/时钟均可注入）。"""

    def __init__(self, *, ledger=None, standards=None,
                 clock: Callable[[], datetime] | None = None,
                 reduced_enabled: bool = False):
        self.ledger = ledger
        self.standards = standards
        self.reduced_enabled = bool(reduced_enabled)
        self._clock = clock or (lambda: datetime.now().astimezone())
        self.states: dict[str, TransferState] = {}
        self.lots: list[LotRecord] = []
        self.decisions: list[SamplingDecision] = []
        self._last_decisions: dict[str, SamplingDecision] = {}

    # ------------------------------------------------------------ 查询
    def state_for(self, scope_key: str) -> TransferState:
        key = str(scope_key or "").strip()
        if not key:
            raise ValueError("必须提供 scope_key（供应商·产品线）")
        state = self.states.get(key)
        if state is None:
            state = TransferState(scope_key=key)
            self.states[key] = state
        return state

    def lots_for(self, scope_key: str, limit: int | None = None) -> list[LotRecord]:
        key = str(scope_key or "").strip()
        items = [lot for lot in self.lots
                 if scope_key_for(lot.supplier, lot.product) == key]
        return items[-int(limit):] if limit else items

    def decision_for(self, scope_key: str) -> SamplingDecision | None:
        return self._last_decisions.get(str(scope_key or "").strip())

    def snapshot(self, scope_key: str) -> dict[str, Any]:
        """作用域状态快照（UI 用）。"""
        key = str(scope_key or "").strip()
        state = self.states.get(key)
        lots = self.lots_for(key)
        last_transfer = (state.history[-1] if state and state.history else None)
        return {
            "scope_key": key,
            "state": state.state if state else "normal",
            "override_reason": state.override_reason if state else "",
            "lots_total": len(lots),
            "last_lot_at": lots[-1].at if lots else "",
            "last_transfer": dict(last_transfer) if last_transfer else None,
            "reduced_enabled": self.reduced_enabled,
        }

    def timeline(self, scope_key: str, limit: int = 50) -> list[dict[str, Any]]:
        """批历史 + 转移 + 方案选择 → 倒序展示行（为何加严/放宽可还原）。"""
        key = str(scope_key or "").strip()
        rows: list[dict[str, Any]] = []
        for lot in self.lots_for(key):
            text = (f"判定 {lot.decision} · 检验 {lot.inspected}/{lot.qty} · "
                    f"不合格 {lot.defects}" + ("（严重）" if lot.serious else ""))
            rows.append({"at": lot.at, "kind": "lot",
                         "title": f"检验批 {lot.lot_id}", "text": text})
        state = self.states.get(key)
        for entry in (state.history if state else []) or []:
            rows.append({
                "at": str(entry.get("at") or ""), "kind": "transfer",
                "title": f"{entry.get('from', '')} → {entry.get('to', '')}",
                "text": (str(entry.get("reason") or "")
                         + (f" · 规则 {entry['rule']}" if entry.get("rule") else "")
                         + (" · 手动覆盖" if entry.get("override") else "")),
            })
        for decision in self.decisions:
            if decision.scope_key != key:
                continue
            rows.append({
                "at": decision.sampled_at, "kind": "plan",
                "title": f"方案 n={decision.n}"
                         + (f" · {decision.plan_ref}" if decision.plan_ref else ""),
                "text": (f"方法 {decision.method} · 种子 {decision.seed}"
                         + (f" · AQL {decision.aql}" if decision.aql is not None else "")
                         + (f" · 指纹 {decision.row_fingerprint}"
                            if decision.row_fingerprint else "")),
            })
        # 同一时间戳时：转移 > 批 > 方案（转移由本批触发的语义）
        rank = {"plan": 0, "lot": 1, "transfer": 2}
        rows.sort(key=lambda item: (item["at"], rank.get(item["kind"], 0)),
                  reverse=True)
        return rows[:int(limit)]

    # ------------------------------------------------------------ 方案选择
    def select_plan(self, scope_key: str, *, lot_size: int, aql: float = 1.0,
                    level: str = "II", method: str = "random",
                    seed: int | None = None, actor: str = "user",
                    source_ref: str = "") -> dict[str, Any]:
        """按当前检验状态查表并登记方案（sampling_plan_selected 入账本）。"""
        state = self.state_for(scope_key)
        plan = SamplingEngine.aql_lookup(
            int(lot_size), float(aql), str(level), inspection=state.state)
        plan_ref = self._record_plan(scope_key, plan, method)
        decision = SamplingDecision(
            scope_key=str(scope_key).strip(), method=method,
            seed=None if seed is None else int(seed), n=int(plan["sample_size"]),
            aql=float(plan["aql_actual"]), level=str(plan["level"]),
            plan_ref=plan_ref, sampled_at=self._stamp(), actor=actor,
            source_ref=source_ref,
            note=f"{state.state} 检验方案")
        self.decisions.append(decision)
        self._last_decisions[decision.scope_key] = decision
        plan_keys = ("code", "plan_code", "sample_size", "accept", "reject",
                     "aql_actual", "level", "inspection", "via_arrow", "lot_size")
        self._emit(
            "sampling_plan_selected",
            [f"scope:{decision.scope_key}"]
            + ([f"plan:{plan_ref}"] if plan_ref else []),
            payload={"stage": "plan_selected", "decision": decision.to_dict(),
                     "plan": {k: plan.get(k) for k in plan_keys}})
        return {"plan": plan, "decision": decision,
                "state": state.state, "plan_ref": plan_ref}

    # ------------------------------------------------------------ 抽样执行
    def sample(self, frame: pd.DataFrame, scope_key: str, *,
               method: str = "", n: int | None = None, column: str = "",
               seed: int | None = None) -> tuple[pd.DataFrame, SamplingDecision | None]:
        """确定性抽样并回填决定（行指纹入决定与后续 lot_inspected）。"""
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            raise ValueError("抽样数据为空")
        decision = self._last_decisions.get(str(scope_key or "").strip())
        mode = str(method or (decision.method if decision else "random")).strip().lower()
        target_n = int(n if n is not None else (decision.n if decision else 0))
        if target_n < 1:
            raise ValueError("请先选择抽样方案或指定样本量")
        sampled = SamplingEngine.sample_frame(
            frame, method=mode, n=target_n, column=column, seed=seed)
        if decision is not None:
            decision.method = mode
            decision.n = int(len(sampled))
            if seed is not None:
                decision.seed = int(seed)
            decision.row_fingerprint = fingerprint_from_frames(sampled)
        return sampled, decision

    # ------------------------------------------------------------ 检验批登记
    def record_lot(self, *, scope_key: str = "", supplier: str = "",
                   product: str = "", line: str = "", qty: int,
                   inspected: int, defects: int, decision: str,
                   lot_id: str = "", serious: bool = False,
                   actor: str = "user", at: str = "",
                   raw_ref: str = "") -> dict[str, Any]:
        """登记检验批 → 转移评估（纯函数）→ 事件留痕；返回 lot/transfer/state。"""
        key = str(scope_key or "").strip() or scope_key_for(supplier, product)
        if not supplier or not product:
            parsed_supplier, _, parsed_product = key.partition("|")
            supplier = supplier or parsed_supplier
            product = product or parsed_product
        state_obj = self.state_for(key)
        stamp = self._stamp(at)
        last_decision = self._last_decisions.get(key)
        lot = LotRecord(
            lot_id=lot_id or f"LOT-{stamp.replace(':', '').replace('-', '')}"
                             f"-{uuid.uuid4().hex[:4]}",
            supplier=supplier, product=product, line=line,
            qty=int(qty), inspected=int(inspected), defects=int(defects),
            decision=decision, serious=bool(serious),
            plan_ref=last_decision.plan_ref if last_decision else "",
            at=stamp, actor=actor, raw_ref=raw_ref)
        # 转移评估必须包含"本批"：取历史窗口后追加当前批（v4.4.0 B3 修复）
        recent = self.lots_for(key, limit=_TRANSFER_LOOKBACK - 1)
        previous_state = state_obj.state
        transfer = SamplingEngine.evaluate_transfer(
            previous_state, [*recent, lot],
            reduced_enabled=self.reduced_enabled,
            scope_key=key)
        self.lots.append(lot)
        self._emit(
            "lot_inspected",
            [f"scope:{key}", f"lot:{lot.lot_id}"]
            + ([f"plan:{lot.plan_ref}"] if lot.plan_ref else []),
            payload={"lot": lot.to_dict(),
                     "decision_id": last_decision.decision_id if last_decision else "",
                     "row_fingerprint": (last_decision.row_fingerprint
                                         if last_decision else ""),
                     "state_before": previous_state,
                     "state_after": transfer.to_state})
        if transfer.changed:
            state_obj.state = transfer.to_state
            state_obj.history.append({
                "at": lot.at, "from": transfer.from_state,
                "to": transfer.to_state, "rule": transfer.rule,
                "reason": transfer.reason,
                "triggering_lots": list(transfer.triggering_lots),
            })
            state_obj.updated_at = lot.at
            self._emit(
                "sampling_transfer_changed",
                [f"scope:{key}"]
                + [f"lot:{item}" for item in transfer.triggering_lots],
                payload={"from": transfer.from_state, "to": transfer.to_state,
                         "rule": transfer.rule, "reason": transfer.reason,
                         "triggering_lots": list(transfer.triggering_lots)})
        return {"lot": lot, "transfer": transfer, "state": state_obj.state,
                "changed": transfer.changed}

    # ------------------------------------------------------------ 手动覆盖
    def manual_override(self, scope_key: str, target_state: str, reason: str,
                        actor: str = "user") -> TransferState:
        """人工覆盖检验状态；必须填写原因（写 sampling_transfer_changed 留痕）。"""
        text = str(reason or "").strip()
        if not text:
            raise ValueError("手动覆盖必须填写原因")
        target = str(target_state or "").strip().lower()
        if target not in TRANSFER_STATES:
            raise ValueError(
                f"非法目标状态: {target_state!r}（可选 {list(TRANSFER_STATES)}）")
        state = self.state_for(scope_key)
        if target == state.state:
            raise ValueError(f"目标状态与当前一致: {target}")
        previous, state.state = state.state, target
        stamp = self._stamp()
        state.override_reason = text
        state.updated_at = stamp
        state.history.append({
            "at": stamp, "from": previous, "to": target,
            "rule": "manual_override", "reason": text, "override": True,
            "triggering_lots": [],
        })
        self._emit(
            "sampling_transfer_changed",
            [f"scope:{state.scope_key}"],
            payload={"from": previous, "to": target, "rule": "manual_override",
                     "reason": text, "override": True, "actor": actor})
        return state

    # ------------------------------------------------------------ 内部
    def _record_plan(self, scope_key: str, plan: dict[str, Any],
                     method: str) -> str:
        registry = self.standards
        if registry is None or not hasattr(registry, "record_change"):
            return ""
        payload = {
            "inspection": plan.get("inspection", "normal"),
            "aql": plan.get("aql_actual"), "level": plan.get("level"),
            "sample_size": plan.get("sample_size"),
            "accept": plan.get("accept"), "reject": plan.get("reject"),
            "plan_code": plan.get("plan_code"), "via_arrow": plan.get("via_arrow"),
            "method": method,
        }
        try:
            record = registry.record_change(
                "sampling_plan", str(scope_key), payload,
                change_reason=f"{payload['inspection']} 检验抽样方案",
                changed_by="system")
        except Exception:  # 方案版本登记失败不阻断查表（账本另有事件）
            logger.exception("抽样方案写标准注册表失败: %s", scope_key)
            return ""
        return record.record_id

    def _emit(self, event_type: str, object_refs: list[str],
              payload: dict[str, Any]) -> None:
        append = getattr(self.ledger, "append", None)
        if not callable(append):
            return
        with contextlib.suppress(Exception):  # 记账失败不得阻断抽样业务
            append(event_type, actor="user", object_refs=object_refs,
                   payload=payload)

    def _stamp(self, at: str = "") -> str:
        return (parse_iso(at, "at").isoformat(timespec="seconds")
                if str(at or "").strip()
                else self._clock().isoformat(timespec="seconds"))

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SAMPLING_STATE_SCHEMA_VERSION,
            "reduced_enabled": self.reduced_enabled,
            "states": [state.to_dict() for state in self.states.values()],
            "lots": [lot.to_dict() for lot in self.lots],
            "decisions": [decision.to_dict() for decision in self.decisions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, *, ledger=None,
                  standards=None,
                  clock: Callable[[], datetime] | None = None
                  ) -> SamplingStateManager:
        if data is None:
            return cls(ledger=ledger, standards=standards, clock=clock)
        if not isinstance(data, dict):
            raise ValueError("抽样状态载荷必须为 dict")
        schema = str(data.get("schema_version") or SAMPLING_STATE_SCHEMA_VERSION)
        if schema != SAMPLING_STATE_SCHEMA_VERSION:
            raise ValueError(f"不支持的抽样状态 schema 版本: {schema}")

        def _items(name: str) -> list:
            raw = data.get(name)
            if raw is None:
                return []
            if not isinstance(raw, list):
                raise ValueError(f"抽样状态 {name} 必须为列表")
            return raw

        manager = cls(ledger=ledger, standards=standards, clock=clock,
                      reduced_enabled=bool(data.get("reduced_enabled", False)))
        for item in _items("states"):
            state = TransferState.from_dict(item)
            manager.states[state.scope_key] = state
        manager.lots = [LotRecord.from_dict(item) for item in _items("lots")]
        allowed = {f.name for f in fields(SamplingDecision)}
        for item in _items("decisions"):
            if not isinstance(item, dict):
                raise ValueError("抽样决定必须为 dict")
            decision = SamplingDecision.from_dict(
                {k: v for k, v in item.items() if k in allowed})
            manager.decisions.append(decision)
            manager._last_decisions[decision.scope_key] = decision
        return manager


__all__ = ["SAMPLING_STATE_SCHEMA_VERSION", "SamplingStateManager"]
