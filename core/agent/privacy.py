"""QAM Harness 云调用隐私门（v3.8.0 P2）。

原则:
  - **默认关闭**: 未授权前不向任何云供应商发送数据（fail-closed）
  - **只拦一次**: 按供应商记忆授权（`llm_privacy_ack_<id>`），设置页可撤销
  - **可见**: 首次调用前展示"将外发什么"清单（问题 + 工具结果摘要 + 数据列名提示），
    并明确声明不上传原始数据文件
  - **本地免拦**: Ollama 与 localhost/私网端点（vLLM/LM Studio/企业内网）不需要授权

纯逻辑无 Qt；UI 只负责把 build_egress_preview 的结果展示出来。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.agent.providers import get_provider, needs_privacy_gate

logger = logging.getLogger("QA-Tool.Privacy")

ACK_KEY_TEMPLATE = "llm_privacy_ack_{provider}"
MAX_PREVIEW_CHARS = 400          # 单个工具结果在预览中的截断长度


@dataclass
class EgressPreview:
    provider: str
    provider_label: str
    model: str
    question: str
    tool_summaries: list[str] = field(default_factory=list)
    data_hint: str = ""
    estimated_chars: int = 0

    def as_text(self) -> str:
        """面向用户的"将外发内容"清单。"""
        lines = [
            f"供应商: {self.provider_label}（{self.provider}）",
            f"模型: {self.model or '未指定'}",
            "",
            "本次将发送以下内容（不含原始数据文件本身）:",
            "1) 你的问题:",
            f"   {self.question[:MAX_PREVIEW_CHARS] or '（空）'}",
        ]
        if self.tool_summaries:
            lines.append(f"2) 本机工具结果摘要（{len(self.tool_summaries)} 条）:")
            for idx, item in enumerate(self.tool_summaries, 1):
                lines.append(f"   {idx}. {item}")
        else:
            lines.append("2) 暂未调用本机工具（仅问题本身）")
        if self.data_hint:
            lines.append("3) 数据列名/结构提示（不含具体数值）:")
            lines.append(f"   {self.data_hint}")
        lines.append("")
        lines.append(f"预计外发规模: 约 {self.estimated_chars} 字符")
        lines.append("提示: 原始数据表、文件路径与 API Key 不会发送；"
                     "如涉及敏感工艺参数，请改用本地 Ollama 或内网端点。")
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {
            "provider": self.provider, "provider_label": self.provider_label,
            "model": self.model, "question": self.question,
            "tool_summaries": list(self.tool_summaries),
            "data_hint": self.data_hint,
            "estimated_chars": self.estimated_chars,
        }


def build_egress_preview(provider_id: str, model: str, question: str,
                         tool_calls=None, data_hint: str = "") -> EgressPreview:
    """组装外发内容预览。tool_calls 支持 ToolCallRecord 列表或字符串列表。"""
    summaries: list[str] = []
    for item in (tool_calls or [])[:5]:
        if isinstance(item, str):
            text = item
        else:
            name = getattr(item, "name", "")
            body = (getattr(item, "summary", "") or getattr(item, "error", "")
                    or str(getattr(item, "data", "")))
            text = f"{name}: {body}"
        text = " ".join(str(text).split())
        if len(text) > MAX_PREVIEW_CHARS:
            text = text[:MAX_PREVIEW_CHARS] + "…"
        summaries.append(text)
    size = len(question or "") + sum(len(s) for s in summaries) + len(data_hint or "")
    return EgressPreview(
        provider=provider_id,
        provider_label=get_provider(provider_id).label,
        model=model or "",
        question=question or "",
        tool_summaries=summaries,
        data_hint=data_hint or "",
        estimated_chars=size,
    )


# ---------------------------------------------------------------- 授权状态


def _get_setting(key: str, default=None):
    try:
        from config.settings import get_setting
        return get_setting(key, default)
    except Exception:
        return default


def ack_key(provider_id: str) -> str:
    return ACK_KEY_TEMPLATE.format(provider=provider_id)


def is_acknowledged(provider_id: str) -> bool:
    return bool(_get_setting(ack_key(provider_id), False))


def grant_consent(provider_id: str, persist: bool = True) -> None:
    """记录"已同意该供应商的云调用"（写入加密配置层，可撤销）。"""
    if not persist:
        return
    try:
        from config.settings import save_config
        save_config({ack_key(provider_id): True})
    except Exception as e:  # noqa: BLE001 - 写入失败仅降级为"下次再询问"，不阻断本次调用
        logger.warning("隐私授权写入失败（%s）: %s", provider_id, e)


def revoke_consent(provider_id: str) -> None:
    try:
        from config.settings import save_config
        save_config({ack_key(provider_id): False})
    except Exception as e:  # noqa: BLE001 - 撤销失败不阻断，重启后仍会重新弹出隐私门
        logger.warning("隐私授权撤销写入失败（%s）: %s", provider_id, e)


def needs_consent(provider_id: str, base_url: str = "") -> bool:
    """是否需要弹隐私门：云端点 + 尚未授权。"""
    if not provider_id or provider_id == "ollama":
        return False
    spec = get_provider(provider_id)
    endpoint = base_url or _get_setting(f"llm_{provider_id}_api_base", "") or spec.base_url
    if not needs_privacy_gate(provider_id, endpoint):
        return False
    return not is_acknowledged(provider_id)


def is_cloud_endpoint(provider_id: str, base_url: str = "") -> bool:
    """该供应商/端点是否属于"云端"（需云开关 + 隐私授权；内网端点不算）。"""
    if not provider_id or provider_id == "ollama":
        return False
    spec = get_provider(provider_id)
    endpoint = base_url or _get_setting(f"llm_{provider_id}_api_base", "") or spec.base_url
    return needs_privacy_gate(provider_id, endpoint)


def consent_status(provider_id: str, base_url: str = "") -> str:
    """给 UI 展示的授权状态文案。"""
    spec = get_provider(provider_id)
    endpoint = base_url or _get_setting(f"llm_{provider_id}_api_base", "") or spec.base_url
    if not needs_privacy_gate(provider_id, endpoint):
        return "本地端点 · 无需授权"
    return "已授权云调用" if is_acknowledged(provider_id) else "未授权（首次调用会拦截）"


def cloud_enabled() -> bool:
    """云调用总开关（默认关闭，需用户显式开启或首次授权时自动开启）。"""
    return bool(_get_setting("llm_cloud_enabled", False))


def set_cloud_enabled(enabled: bool) -> None:
    try:
        from config.settings import save_config
        save_config({"llm_cloud_enabled": bool(enabled)})
    except Exception:
        pass
