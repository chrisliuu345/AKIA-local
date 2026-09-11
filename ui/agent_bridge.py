"""QAM Harness UI→core 适配层 — 把主窗口状态组装成 AgentContext。

放在 ui/ 层是刻意的分层安排: core/agent 不感知 Qt，也不反向依赖 ui；
这里集中处理"主窗口有哪些数据/上下文"的取数细节，任一取数失败都不影响对话可用性。
"""
from __future__ import annotations

import logging

from core.agent.tools import AgentContext

logger = logging.getLogger(__name__)


def build_context(main_window) -> AgentContext:
    """从主窗口收集 Agent 可用的上下文（缺什么就少什么，不抛异常）。"""
    ctx = AgentContext()
    if main_window is None:
        return ctx

    # ---------- 数据表 ----------
    try:
        raw = {}
        current = getattr(main_window, "current_data", None) or {}
        raw = current.get("raw_data") or {}
        if not raw:
            loader = getattr(main_window, "data_loader", None)
            raw = getattr(loader, "raw_data", {}) or {}
        ctx.data_frames = dict(raw)
    except Exception:
        logger.debug("agent bridge: 数据表读取失败", exc_info=True)

    # ---------- 已运行分析 / 画像 ----------
    ctx.analyses = dict(getattr(main_window, "analyses", {}) or {})
    ctx.profile = dict(getattr(main_window, "profile_result", {}) or {})

    # ---------- 五链 / 产线 / 实时 ----------
    ctx.project_context = getattr(main_window, "project_context", None)
    try:
        loader = getattr(main_window, "_load_plant_safe", None)
        ctx.plant = loader() if callable(loader) else None
    except Exception:
        ctx.plant = None
    try:
        ctx.journal = main_window._get_alert_journal()
    except Exception:
        ctx.journal = None
    try:
        ctx.downtime = main_window._get_downtime_tracker()
    except Exception:
        ctx.downtime = None
    oee = getattr(main_window, "_oee_computer", None)
    if oee is not None:
        try:
            ctx.live_oee_snapshot = oee.snapshot()
        except Exception:
            ctx.live_oee_snapshot = None
    ctx.connector_health = getattr(main_window, "_connector_health", None)

    # ---------- 成本参数与采样（用于成本损失估算）----------
    try:
        from config.settings import get_setting
        ctx.currency = str(get_setting("cost_currency", "") or "")
    except Exception:
        ctx.currency = ""
    try:
        bus = getattr(main_window, "stream_bus", None)
        if bus is not None:
            ctx.extra["samples_by_device"] = {
                topic: bus.recent(topic, n=2000) for topic in bus.topics()}
    except Exception:
        logger.debug("agent bridge: 采样缓冲读取失败", exc_info=True)

    # ---------- 知识库 ----------
    try:
        from core.knowledge_base import get_knowledge_base
        ctx.knowledge = get_knowledge_base()
    except Exception:
        ctx.knowledge = None
    return ctx


def build_engine(main_window=None, llm=None):
    """组装 (AgentEngine, AgentContext) — 供对话 UI 与测试复用。"""
    from core.agent.engine import AgentEngine
    from core.agent.tools import build_default_registry

    ctx = build_context(main_window)
    registry = build_default_registry(ctx)
    engine = AgentEngine(registry, llm=llm, knowledge=ctx.knowledge, context=ctx)
    return engine, ctx
