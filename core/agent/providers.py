"""BYOK 供应商注册表（v3.8.0 P2）—— 6 家云厂商 + 自定义 OpenAI 兼容端点。

设计:
  - 纯数据 + 纯函数，无网络、无 Qt（可单测）
  - protocol 决定客户端用哪套协议适配器: openai / anthropic / gemini / ollama
  - 密钥与地址不落在这里，由 config.settings 加密保存（键名 `llm_<id>_api_key`）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    protocol: str                       # ollama / openai / anthropic / gemini
    base_url: str
    models: tuple[str, ...] = ()
    key_hint: str = ""
    docs_url: str = ""
    requires_key: bool = True
    custom: bool = False
    note: str = ""
    extra: dict = field(default_factory=dict)

    def default_model(self) -> str:
        return self.models[0] if self.models else ""

    def is_local(self, base_url: str | None = None) -> bool:
        """本地/内网端点不需要隐私门（数据不出机）。"""
        if self.protocol == "ollama":
            return True
        return is_local_endpoint(base_url or self.base_url)


def is_local_endpoint(url: str) -> bool:
    """localhost / 127.x / ::1 / 局域网私网地址视为本地端点。"""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    if host in ("localhost", "::1") or host.startswith("127."):
        return True
    parts = host.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        a, b = int(parts[0]), int(parts[1])
        return (a == 10 or (a == 192 and b == 168)
                or (a == 172 and 16 <= b <= 31) or a == 169)
    return False


PROVIDERS: dict[str, ProviderSpec] = {
    "ollama": ProviderSpec(
        id="ollama", label="本地 Ollama", protocol="ollama",
        base_url="http://localhost:11434",
        models=("qwen2.5:7b", "qwen2.5:14b", "llama3.2", "deepseek-r1:8b"),
        requires_key=False, note="完全离线，数据不出本机",
    ),
    "openai": ProviderSpec(
        id="openai", label="OpenAI", protocol="openai",
        base_url="https://api.openai.com/v1",
        models=("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"),
        key_hint="sk-...", docs_url="https://platform.openai.com/api-keys",
    ),
    "anthropic": ProviderSpec(
        id="anthropic", label="Anthropic Claude", protocol="anthropic",
        base_url="https://api.anthropic.com/v1",
        models=("claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-1"),
        key_hint="sk-ant-...", docs_url="https://console.anthropic.com/settings/keys",
    ),
    "google": ProviderSpec(
        id="google", label="Google Gemini", protocol="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        models=("gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"),
        key_hint="AIza...", docs_url="https://aistudio.google.com/app/apikey",
        note="原生协议（streamGenerateContent SSE）",
    ),
    "deepseek": ProviderSpec(
        id="deepseek", label="DeepSeek", protocol="openai",
        base_url="https://api.deepseek.com/v1",
        models=("deepseek-chat", "deepseek-reasoner"),
        key_hint="sk-...", docs_url="https://platform.deepseek.com/api_keys",
    ),
    "zai": ProviderSpec(
        id="zai", label="Z.ai (GLM)", protocol="openai",
        base_url="https://api.z.ai/api/paas/v4",
        models=("glm-4.5", "glm-4.5-flash", "glm-4-plus"),
        key_hint="...", docs_url="https://z.ai/manage-apikey/apikey-list",
    ),
    "kimi": ProviderSpec(
        id="kimi", label="KIMI (Moonshot)", protocol="openai",
        base_url="https://api.moonshot.cn/v1",
        models=("moonshot-v1-8k", "moonshot-v1-32k", "kimi-k2-0711-preview"),
        key_hint="sk-...", docs_url="https://platform.moonshot.cn/console/api-keys",
    ),
    "custom": ProviderSpec(
        id="custom", label="自定义 OpenAI 兼容端点", protocol="openai",
        base_url="http://localhost:8000/v1", models=(),
        key_hint="可留空（本地服务通常不需要）",
        requires_key=False, custom=True,
        note="vLLM / LM Studio / OneAPI / 企业网关等",
    ),
}

CLOUD_PROVIDER_IDS = ("openai", "anthropic", "google", "deepseek", "zai", "kimi")
ALL_PROVIDER_IDS = tuple(PROVIDERS)


def get_provider(provider_id: str | None) -> ProviderSpec:
    """按 id 取供应商；未知 id 回退本地 Ollama（不抛异常）。"""
    return PROVIDERS.get(str(provider_id or "").strip().lower(), PROVIDERS["ollama"])


def provider_ids(include_custom: bool = True) -> list[str]:
    ids = list(ALL_PROVIDER_IDS)
    if not include_custom:
        ids = [p for p in ids if p != "custom"]
    return ids


def provider_label(provider_id: str | None) -> str:
    return get_provider(provider_id).label


def models_for(provider_id: str, extra: str = "") -> list[str]:
    spec = get_provider(provider_id)
    models = list(spec.models)
    if extra and extra not in models:
        models.insert(0, extra)
    return models


def resolve_base_url(provider_id: str, override: str = "") -> str:
    """接口地址：用户覆盖优先，其次供应商默认；统一去掉结尾斜杠。"""
    spec = get_provider(provider_id)
    base = (override or "").strip() or spec.base_url
    return base.rstrip("/")


def requires_key(provider_id: str) -> bool:
    return bool(get_provider(provider_id).requires_key)


def needs_privacy_gate(provider_id: str, base_url: str = "") -> bool:
    """是否需要隐私门：非本地协议 + 非本地端点。"""
    spec = get_provider(provider_id)
    if spec.protocol == "ollama":
        return False
    return not spec.is_local(base_url or spec.base_url)


def masked_key(key: str, keep: int = 4) -> str:
    """脱敏显示: sk-abcdef…wxyz"""
    text = (key or "").strip()
    if not text:
        return "未配置"
    if len(text) <= keep * 2:
        return text[:keep] + "…"
    return f"{text[:keep]}…{text[-keep:]}"
