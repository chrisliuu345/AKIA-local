"""BYOK 供应商注册表测试 — 覆盖 6 家云 + 自定义端点 + 本地判定。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.agent.providers import (
    ALL_PROVIDER_IDS, CLOUD_PROVIDER_IDS, PROVIDERS, get_provider,
    is_local_endpoint, masked_key, models_for, needs_privacy_gate,
    provider_label, requires_key, resolve_base_url,
)


def test_six_cloud_vendors_plus_custom_and_local():
    assert set(CLOUD_PROVIDER_IDS) == {"openai", "anthropic", "google",
                                       "deepseek", "zai", "kimi"}
    for pid in CLOUD_PROVIDER_IDS:
        spec = PROVIDERS[pid]
        assert spec.label and spec.base_url.startswith("https://")
        assert spec.models, f"{pid} 应有默认模型清单"
        assert spec.requires_key is True
    assert PROVIDERS["ollama"].requires_key is False
    assert PROVIDERS["custom"].custom is True
    assert PROVIDERS["custom"].requires_key is False      # 本地服务常无需密钥
    assert set(ALL_PROVIDER_IDS) == set(CLOUD_PROVIDER_IDS) | {"ollama", "custom"}


def test_protocols_mapping():
    assert PROVIDERS["ollama"].protocol == "ollama"
    assert PROVIDERS["anthropic"].protocol == "anthropic"
    assert PROVIDERS["google"].protocol == "gemini"       # 原生协议
    for pid in ("openai", "deepseek", "zai", "kimi", "custom"):
        assert PROVIDERS[pid].protocol == "openai"


def test_get_provider_fallback_and_labels():
    assert get_provider("ANTHROPIC").id == "anthropic"
    assert get_provider("不存在").id == "ollama"           # 回退本地，不抛异常
    assert get_provider(None).id == "ollama"
    assert provider_label("deepseek") == "DeepSeek"
    assert requires_key("google") is True
    assert requires_key("custom") is False


def test_models_and_base_url_resolution():
    assert models_for("openai")[0] == PROVIDERS["openai"].default_model()
    assert models_for("custom", extra="qwen2.5-7b")[0] == "qwen2.5-7b"
    assert resolve_base_url("deepseek") == "https://api.deepseek.com/v1"
    assert resolve_base_url("custom", "http://192.168.1.9:8000/v1/") == \
        "http://192.168.1.9:8000/v1"
    assert resolve_base_url("openai", "https://proxy.corp/v1") == "https://proxy.corp/v1"


def test_local_endpoint_detection():
    for url in ("http://localhost:11434", "http://127.0.0.1:8000/v1",
                "http://10.1.2.3:8000/v1", "http://192.168.5.20/v1",
                "http://172.16.9.9:1234/v1", "http://[::1]:8000/v1"):
        assert is_local_endpoint(url) is True, url
    for url in ("https://api.openai.com/v1", "https://api.deepseek.com/v1",
                "http://8.8.8.8/v1", "http://172.32.0.1/v1"):
        assert is_local_endpoint(url) is False, url


def test_privacy_gate_scope():
    assert needs_privacy_gate("ollama") is False
    assert needs_privacy_gate("openai") is True
    assert needs_privacy_gate("custom") is False                      # 默认 localhost
    assert needs_privacy_gate("custom", "http://192.168.1.5:8000/v1") is False
    assert needs_privacy_gate("custom", "http://llm.corp.example.com/v1") is True


def test_masked_key_never_leaks_full_secret():
    assert masked_key("") == "未配置"
    assert masked_key("short") == "shor…"
    masked = masked_key("sk-abcdefghijklmnop")
    assert masked.startswith("sk-a") and masked.endswith("mnop")
    assert "abcdefghijkl" not in masked
