"""QAM Harness Agent 主循环（v3.8.0 Phase 1）。

两条执行路径:
  1. **在线（LLM + 工具调用）**: 把工具清单写进 system prompt，模型以
     `{"tool": "...", "args": {...}}` 形式请求调用；引擎执行工具后把结果回灌，
     最多 max_tool_steps 轮，最后输出自然语言结论。
  2. **离线（规则路由）**: 无 Ollama/云 API 时按关键词路由到同一批工具，
     用模板 + core.agent.explain 生成"带判定与建议"的答案，保证工厂断网可用。

在线调度（成功或调用失败后的降级）把输入、模型、配置写入 core.audit 的操作日志，
并附在 AgentReply 上。纯离线不记模型调用。纯逻辑层，无 Qt 依赖；UI 通过
respond_stream() 获取事件流。
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from collections.abc import Iterator

from core.agent.conversation import Conversation
from core.agent.explain import explain_metric
from core.agent.privacy import (
    build_egress_preview, cloud_enabled, consent_status, grant_consent,
    is_cloud_endpoint, needs_consent,
)
from core.agent.tools import AgentContext, ToolRegistry, ToolResult
from core.audit import record_model_call

logger = logging.getLogger(__name__)

TOOL_PROTOCOL = """你可以调用下列本地工具（数据不出本机）：

{tools}

调用规则（必须严格遵守）:
- 需要真实数据/计算时，只输出一行 JSON: {{"tool": "工具名", "args": {{...}}}}
- 拿到工具结果后，用中文给出结论（引用关键数值），并给出 1-3 条可执行建议
- 不需要工具时直接回答；不要编造未提供的数值
- 统计结论需给出判定依据（如 Cpk≥1.33 良好、%GRR<10% 可接受、p<0.05 显著）
- 回答面向车间工程师，先结论后依据，控制在 300 字内
"""


@dataclass
class ToolCallRecord:
    name: str
    args: dict = field(default_factory=dict)
    ok: bool = True
    summary: str = ""
    error: str = ""
    data: dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def label(self) -> str:
        args = ", ".join(f"{k}={v}" for k, v in (self.args or {}).items())
        return f"{self.name}({args})" if args else f"{self.name}()"


@dataclass
class AgentReply:
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    offline: bool = False
    provider: str = ""
    model: str = ""
    elapsed_ms: float = 0.0
    # 追溯留在结果对象上。as_dict 不带这些字段，避免进入 SDK/MCP 的 JSON 信封。
    input: str = ""
    config: dict = field(default_factory=dict)
    audit_record: str = ""

    def as_dict(self) -> dict:
        return {"text": self.text, "offline": self.offline,
                "provider": self.provider, "model": self.model,
                "elapsed_ms": round(self.elapsed_ms, 1),
                "tool_calls": [{"name": c.name, "args": c.args, "ok": c.ok,
                                "summary": c.summary, "error": c.error}
                               for c in self.tool_calls]}

    def trace(self) -> dict:
        """本机追溯：输入、模型、当时的模型配置、操作日志中的审计行。"""
        return {"input": self.input, "model": self.model,
                "config": dict(self.config or {}),
                "audit_record": self.audit_record}


_SPEC_RES = (
    re.compile(r"(?:usl|规格上限|上规格限)\s*[=:：]?\s*(-?\d+(?:\.\d+)?)", re.I),
    re.compile(r"(?:lsl|规格下限|下规格限)\s*[=:：]?\s*(-?\d+(?:\.\d+)?)", re.I),
)

# 关键词 → 工具（顺序即优先级，先具体后一般）
_OFFLINE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("automl", "自动选模", "自动建模", "机器学习", "随机森林", "梯度提升",
      "决策树模型", "mars"), "ml_automl"),
    (("特征重要性", "shap", "模型解释", "可解释", "哪些特征重要"), "ml_explain"),
    (("模型预测", "用模型预测", "预测新数据", "加载模型", "qamodel"), "ml_predict"),
    (("模型评估", "交叉验证", "学习曲线", "残差诊断"), "ml_evaluate"),
    (("训练模型", "建模", "模型训练"), "ml_train"),
    (("实时",), "get_live_oee"),
    (("成本", "损失", "废品", "金额", "省了多少"), "estimate_cost"),
    (("告警", "报警", "异常点", "超差"), "get_alerts"),
    (("连接器", "数据源", "断线", "重连", "掉线"), "get_connector_health"),
    (("五链", "fmea", "控制计划", "ppap", "8d"), "get_project_context"),
    (("产线", "工位", "通道", "节拍", "班次"), "get_plant"),
    (("oee", "设备综合效率", "开动率", "利用率"), "run_oee"),
    (("grr", "msa", "量具", "测量系统", "重复性", "再现性"), "run_msa_grr"),
    (("cpk", "ppk", "过程能力", "能力分析", "cp值", "capability"), "run_capability"),
    (("控制图", "判异", "spc", "受控", "ucl", "lcl", "极差图"), "run_spc"),
    (("正态", "p值", "p 值", "显著", "anova", "方差分析", "t检验", "t 检验", "假设检验"),
     "run_hypothesis_test"),
    (("已运行", "分析结果", "跑过哪些", "结果列表"), "list_analyses"),
    (("哪张表", "有哪些表", "数据表", "多少行", "列名", "字段"), "list_data"),
)


def _match_offline(question: str, has_live: bool) -> str | None:
    text = (question or "").lower()
    for keywords, tool in _OFFLINE_RULES:
        if tool == "get_live_oee" and not has_live:
            continue
        for kw in keywords:
            if ("实时" in kw and "实时" not in text):
                continue
            if kw in text:
                # "实时 OEE" 优先实时快照，否则走 IE 引擎
                if tool == "get_live_oee" and "oee" not in text:
                    continue
                return tool
    return None


class AgentEngine:
    """QAM Harness 引擎 — 工具调度 + 结论生成。"""

    def __init__(self, registry: ToolRegistry, conversation: Conversation | None = None,
                 llm=None, knowledge=None, max_tool_steps: int = 3,
                 context: AgentContext | None = None, privacy_check=None):
        self.registry = registry
        self.conversation = conversation or Conversation()
        self.llm = llm
        self.knowledge = knowledge
        self.context = context
        self.max_tool_steps = max(1, int(max_tool_steps))
        # 隐私门: None → 用 core.agent.privacy 的默认策略（云端未授权即拒绝，fail-closed）
        self.privacy_check = privacy_check
        self.force_offline = False          # UI「仅用本地工具」当次生效
        self.conversation.set_system_prompt(self._system_prompt())

    # ---------- 状态 ----------
    @property
    def llm_available(self) -> bool:
        return bool(self.llm is not None and getattr(self.llm, "available", False))

    def provider_label(self) -> str:
        if self.llm is None:
            return "离线"
        provider = getattr(self.llm, "provider", "ollama")
        model = getattr(self.llm, "model", "")
        label = {"ollama": "Ollama", "openai": "OpenAI 兼容"}.get(provider, provider)
        return f"{label} · {model}" if model else label

    def tool_count(self) -> int:
        return len(self.registry)

    def set_llm(self, llm) -> None:
        self.llm = llm

    def set_context(self, context: AgentContext) -> None:
        self.context = context

    # ---------- 隐私门 ----------
    def provider_id(self) -> str:
        return str(getattr(self.llm, "provider", "") or "")

    def api_base(self) -> str:
        return str(getattr(self.llm, "api_base", "") or "")

    def privacy_state(self) -> str:
        pid = self.provider_id()
        if not pid or not self.llm_available:
            return "本地工具模式"
        return consent_status(pid, self.api_base())

    def egress_preview(self, question: str):
        """当前将外发的内容（供 UI 预览/测试断言）。"""
        hint = self._data_hint()
        return build_egress_preview(self.provider_id(),
                                    getattr(self.llm, "model", ""),
                                    question, data_hint=hint)

    def privacy_allows(self, question: str) -> tuple[bool, str]:
        """返回 (是否允许云调用, 拒绝原因)。云端未授权 → 拒绝（fail-closed）。"""
        if not self.llm_available:
            return False, ""
        if self.force_offline:
            return False, "已按你的选择仅使用本地工具（本次不调用云 API）。"
        pid = self.provider_id()
        if is_cloud_endpoint(pid, self.api_base()) and not cloud_enabled():
            return False, ("云调用已在设置中关闭（设置 → QAM Harness → 云调用）；"
                           "本次已改用本地工具。")
        if self.privacy_check is not None:
            try:
                allowed = bool(self.privacy_check(pid, self.egress_preview(question)))
            except Exception:
                return False, "隐私确认失败，已降级为本地工具模式。"
            return (True, "") if allowed else (False, "已取消云调用，改用本地工具。")
        if needs_consent(pid, self.api_base()):
            return False, ("云端调用需先授权（设置 → QAM Harness → 隐私与授权），"
                           "本次已改用本地工具。")
        return True, ""

    def grant_cloud_consent(self) -> None:
        """UI 隐私弹窗点"同意"后调用（按供应商记忆，只拦一次）。"""
        pid = self.provider_id()
        if pid:
            grant_consent(pid)

    def _system_prompt(self) -> str:
        return ("你是 AKIA 的 QAM Harness —— 面向质量工程（QE）与工业工程（IE）的"
                "本地分析助手，运行在用户电脑上，可调用软件内的分析工具。\n\n"
                + TOOL_PROTOCOL.format(tools=self.registry.describe()))

    # ---------- 对外接口 ----------
    def respond(self, question: str) -> AgentReply:
        events = list(self.respond_stream(question))
        for kind, payload in events:
            if kind == "done":
                return payload
        return AgentReply(text="（未产生回复）", offline=not self.llm_available)

    def respond_stream(self, question: str) -> Iterator[tuple[str, object]]:
        """事件流: ("tool", ToolCallRecord) / ("token", str) / ("done", AgentReply)。"""
        started = time.time()
        question = (question or "").strip()
        if not question:
            yield "done", AgentReply(text="请输入问题。", offline=not self.llm_available)
            return
        self.conversation.add_user(question)
        self.conversation.set_system_prompt(self._system_prompt())

        allowed, deny_note = self.privacy_allows(question)
        if self.llm_available and not allowed and deny_note:
            # 隐私门拒绝/取消 → 直接走离线工具模式（功能不丢，仅不调用云 API）
            reply = self._run_offline(question)
            reply.text = f"{deny_note}\n\n{reply.text}"
            reply.elapsed_ms = (time.time() - started) * 1000
            for record in reply.tool_calls:
                yield "tool", record
            self.conversation.add_assistant(reply.text)
            yield "done", reply
            return

        failed = False
        if self.llm_available:
            reply = None
            try:
                reply = yield from self._run_llm(question)
            except Exception as e:                     # LLM 异常 → 降级离线
                failed = True
                self.conversation.add("system", f"LLM 调用失败，降级离线模式: {e}")
                reply = None
            if reply is not None:
                reply.elapsed_ms = (time.time() - started) * 1000
                self._attach_call_audit(question, reply, "ok")
                self.conversation.add_assistant(reply.text)
                yield "done", reply
                return

        reply = self._run_offline(question)
        reply.elapsed_ms = (time.time() - started) * 1000
        if failed:
            # 模型已调度但失败：仍留下输入、模型和配置，outcome 标明改走了离线。
            self._attach_call_audit(question, reply, "fallback")
        # 离线路径同样上报工具卡片（与在线路径一致的可观测性）
        for record in reply.tool_calls:
            yield "tool", record
        self.conversation.add_assistant(reply.text)
        yield "done", reply

    def _attach_call_audit(self, question: str, reply: AgentReply, outcome: str) -> None:
        """把本次模型调度写入操作日志，并让回复能对上那一行。失败不打断回答。"""
        try:
            recorded = record_model_call(
                "user",
                question=question,
                model=self._dispatch_model(reply),
                config=self._dispatch_config(),
                outcome=outcome,
                elapsed_ms=reply.elapsed_ms,
                tools=[c.name for c in reply.tool_calls],
            )
        except Exception:
            logger.warning("模型调用审计失败", exc_info=True)
            return
        reply.input = recorded.input
        if recorded.model:
            reply.model = recorded.model
        reply.config = dict(recorded.config)
        reply.audit_record = recorded.line

    def _dispatch_model(self, reply: AgentReply) -> str:
        return str(getattr(self.llm, "model", "") or reply.model or "")

    def _dispatch_config(self) -> dict:
        """用客户端已有的 config_summary；没有时只取调度时已经在用的字段。"""
        llm = self.llm
        summary = getattr(llm, "config_summary", None)
        if callable(summary):
            try:
                data = summary()
            except Exception:
                data = None
            if isinstance(data, dict):
                return data
        if llm is None:
            return {}
        config = {}
        for key in ("provider", "protocol", "model", "api_base"):
            value = getattr(llm, key, "")
            if value:
                config[key] = value
        available = getattr(llm, "available", None)
        if isinstance(available, bool):
            config["available"] = available
        return config

    # ---------- 在线路径 ----------
    def _run_llm(self, question: str) -> Iterator:
        tool_calls: list[ToolCallRecord] = []
        for _step in range(self.max_tool_steps):
            prompt = self._build_prompt(question, tool_calls)
            text, _streamed = yield from self._generate(prompt)
            name, args = self._extract_tool_call(text)
            if not name:
                return AgentReply(text=text.strip() or "（模型无输出）",
                                  tool_calls=tool_calls, offline=False,
                                  provider=getattr(self.llm, "provider", ""),
                                  model=getattr(self.llm, "model", ""))
            record = self._execute(name, args)
            tool_calls.append(record)
            yield "tool", record
            self.conversation.add_tool_result(name, record.ok, record.summary or record.error,
                                              record.args)
        # 步数用尽 → 用最后一次工具结果兜底作答
        last = tool_calls[-1] if tool_calls else None
        text = (f"已完成 {len(tool_calls)} 步工具调用，结论基于最后一次结果：\n"
                f"{last.summary if last else '无结果'}")
        return AgentReply(text=text, tool_calls=tool_calls, offline=False,
                          provider=getattr(self.llm, "provider", ""),
                          model=getattr(self.llm, "model", ""))

    def _generate(self, prompt: str) -> Iterator:
        """调用 LLM 并决定是否流式输出（v3.8.0 O2 修复）。

        规则:
          1. 输出以 `{` 或 ``` 开头 → 工具调用候选，全部缓冲不流式（避免把 JSON 打到界面）
          2. 正文中出现 `{"tool"` → 只补发其之前的正文，JSON 片段及之后不再外泄
          3. 其余情况正常逐块流式，保持打字机体验
        """
        buffer = ""
        emitted = 0
        mode = None                     # None=未定 / "text" / "tool"
        # 尾部保守保留: 防止 `{"tool"` 被分块切断而先泄漏出 `{"to`
        guard = len('{"tool"') - 1
        for chunk in self.llm.generate(prompt):
            buffer += chunk
            if mode is None:
                stripped = buffer.lstrip()
                if not stripped:
                    continue
                mode = "tool" if stripped[0] in ("{", "`") else "text"
            if mode == "tool":
                idx = buffer.find('{"tool"')
                if idx > emitted:
                    yield "token", buffer[emitted:idx]
                    emitted = idx
                continue
            idx = buffer.find('{"tool"', emitted)
            if idx == -1:
                send_upto = max(emitted, len(buffer) - guard)
                if send_upto > emitted:
                    yield "token", buffer[emitted:send_upto]
                    emitted = send_upto
            else:
                if idx > emitted:
                    yield "token", buffer[emitted:idx]
                emitted = idx
                mode = "tool"
        # 流结束: 正文模式下把保留的尾部补发（工具模式下留给解析器）
        if mode == "text" and emitted < len(buffer):
            yield "token", buffer[emitted:]
            emitted = len(buffer)
        return buffer, emitted > 0

    def _build_prompt(self, question: str, tool_calls: list[ToolCallRecord]) -> str:
        parts = [self._system_prompt()]
        if self.context is not None:
            parts.append(f"当前软件状态: {self.context.summary()}")
            data_hint = self._data_hint()
            if data_hint:
                parts.append(data_hint)
        if self.knowledge is not None and getattr(self.knowledge, "available", False):
            try:
                hits = self.knowledge.search(question, top_k=3)
            except Exception:
                hits = []
            if hits:
                parts.append("相关知识库条目:\n" + "\n".join(
                    f"- [{h.category_label()}] {h.title}: {getattr(h, 'content', '')[:240]}"
                    for h in hits))
        history = self.conversation.prompt_history(limit=6)
        if history:
            parts.append("对话历史:\n" + history)
        if tool_calls:
            parts.append("已执行的工具与结果:\n" + "\n".join(
                f"- {c.label()} → {c.summary[:400]}" for c in tool_calls))
        parts.append(f"用户问题: {question}")
        return "\n\n".join(parts)

    def _data_hint(self) -> str:
        ctx = self.context
        if ctx is None or not ctx.data_frames:
            return ""
        lines = ["可用数据:"]
        for name in ctx.sheet_names()[:5]:
            nums = ctx.numeric_columns(name)
            lines.append(f"- 表「{name}」数值列: {', '.join(nums[:8]) or '无'}")
        return "\n".join(lines)

    @staticmethod
    def _extract_tool_call(text: str) -> tuple[str | None, dict]:
        if not text:
            return None, {}
        candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
        stripped = text.strip()
        candidates.append(stripped)
        for start in (m.start() for m in re.finditer(r"\{", text)):
            depth = 0
            for idx in range(start, len(text)):
                ch = text[idx]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append(text[start:idx + 1])
                        break
        for cand in candidates:
            try:
                obj = json.loads(cand)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
                args = obj.get("args") or obj.get("arguments") or {}
                return obj["tool"], dict(args) if isinstance(args, dict) else {}
        return None, {}

    # ---------- 离线路径 ----------
    def _run_offline(self, question: str) -> AgentReply:
        has_live = bool(self.context is not None and self.context.live_oee_snapshot)
        name = _match_offline(question, has_live)
        tool_calls: list[ToolCallRecord] = []

        if name is None:
            name = "search_knowledge"
        args = self._offline_args(name, question)
        record = self._execute(name, args)
        tool_calls.append(record)

        if not record.ok and name == "search_knowledge":
            text = self._capability_hint()
        elif not record.ok:
            body = record.summary or record.error
            text = f"没能完成「{name}」: {body}\n\n{self._capability_hint()}"
        else:
            text = self._compose_offline_answer(question, record)
        text = self._augment_with_knowledge(question, text)
        return AgentReply(text=text, tool_calls=tool_calls, offline=True,
                          provider="offline", model="")

    def _offline_args(self, name: str, question: str) -> dict:
        ctx = self.context
        if ctx is None:
            return {}
        if name == "run_capability":
            args: dict = {}
            for key, regex in zip(("usl", "lsl"), _SPEC_RES, strict=True):
                match = regex.search(question)
                if match:
                    args[key] = float(match.group(1))
            return args
        if name == "run_spc":
            args = {}
            text = question.lower()
            if "xbar" in text or "均值极差" in text or "子组" in text:
                args["chart_type"] = "xbar_r"
            elif "cusum" in text:
                args["chart_type"] = "cusum"
            elif "ewma" in text:
                args["chart_type"] = "ewma"
            return args
        if name == "run_hypothesis_test":
            text = question.lower()
            if "anova" in text or "方差分析" in text:
                return {"test": "anova_oneway"}
            if "正态" in text:
                return {"test": "normality"}
            return {"test": "normality"}
        if name == "get_alerts":
            return {"limit": 10, "only_unacked": "全部" not in question}
        if name == "search_knowledge":
            return {"query": question, "top_k": 3}
        if name == "ml_predict":
            match = re.search(r"[^\s，。'\"]+\.qamodel", question)
            args = {"rows": 10}
            if match:
                args["model_path"] = match.group(0)
            return args
        if name == "ml_explain":
            match = re.search(r"第\s*(\d+)\s*行", question)
            return {"row_index": int(match.group(1))} if match else {}
        if name == "ml_automl":
            budget = re.search(r"(\d+)\s*秒", question)
            return {"time_budget_s": float(budget.group(1))} if budget else {}
        return {}

    def _execute(self, name: str, args: dict) -> ToolCallRecord:
        result: ToolResult = self.registry.call(name, args, self.context)
        return ToolCallRecord(
            name=name, args=args, ok=result.ok,
            summary=result.summary() if result.ok else "",
            error=result.error, data=result.data,
            duration_ms=result.duration_ms,
        )

    def _compose_offline_answer(self, question: str, record: ToolCallRecord) -> str:
        # 工具名已由 UI 的工具卡片呈现，这里只给结论 + 建议，避免重复噪音
        lines = [record.summary]
        advice = self._advice_for(record)
        if advice:
            lines.append("")
            lines.append("建议: " + advice)
        lines.append("")
        lines.append("（离线工具模式：结论来自本机分析引擎，配置 Ollama/云 API 可获得更自然的解读）")
        return "\n".join(lines)

    def _advice_for(self, record: ToolCallRecord) -> str:
        data = record.data or {}
        name = record.name
        if name == "run_capability":
            info = explain_metric("cpk", data.get("cpk"))
            return info["advice"] if info else ""
        if name == "run_msa_grr":
            info = explain_metric("grr", data.get("grr_pct"))
            return info["advice"] if info else ""
        if name in ("run_oee", "get_live_oee"):
            overall = data.get("overall") or {}
            if not overall and data.get("lines"):
                first = next(iter(data["lines"].values()), {})
                overall = first
            info = explain_metric("oee", overall.get("oee"))
            return info["advice"] if info else ""
        if name == "run_spc":
            if data.get("violations"):
                return ("先确认测量系统（MSA）与数据录入，再按 Nelson 规则定位特殊原因；"
                        "判异点对应的批次建议隔离复检。")
            return "过程受控：保持现有控制限并按周期复核（控制限不要用规格限替代）。"
        if name == "estimate_cost":
            return "按损失金额排序改善：通常停机与主要不良模式贡献最大（可用 8D 闭环）。"
        if name == "get_alerts":
            count = len(data.get("entries", []))
            return (f"共 {count} 条待处置：严重级优先确认并记录原因；"
                    "确认动作会写入审计（工具→告警中心）。") if count else \
                "当前没有未确认告警，保持监控即可。"
        if name == "get_project_context":
            return "五链建议：高风险 FMEA 条目应先落到控制计划，再配 SPC 监控与 PPAP 证据。"
        if name == "get_plant":
            return "若工位缺规格限/节拍，实时图与 OEE 会按缺省处理；建议在「工具→产线配置」补全。"
        if name == "get_connector_health":
            return "异常数据源会自动指数退避重连；持续失败请检查网络/协议配置。"
        if name == "list_data":
            return "可直接继续问: “对<列名>做能力分析”“跑 XBar-R 控制图”。"
        return ""

    def _augment_with_knowledge(self, question: str, text: str) -> str:
        kb = self.knowledge
        if kb is None or not getattr(kb, "available", False):
            return text
        try:
            offline = kb.offline_answer(question)
        except Exception:
            offline = None
        if not offline:
            return text
        return f"{text}\n\n参考知识库:\n{offline}"

    def _capability_hint(self) -> str:
        categories = ", ".join(sorted(self.registry.by_category()))
        return ("当前可用的分析能力: " + categories +
                "。可以这样问: “用当前数据做过程能力分析”“跑 I-MR 控制图”"
                "“最近有哪些未确认告警”“五链现在什么状态”“成本损失多少”。")
