"""LLM 协议适配测试 — OpenAI 兼容 / Anthropic / Gemini 原生 + 错误归一化。

全部通过 mock urlopen 完成，不访问真实网络。
"""
import json
import os
import urllib.error

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from core.llm_client import LLMClient


class FakeResp:
    """可控 SSE 响应: 按块返回预置内容。"""

    def __init__(self, chunks, status: int = 200):
        self._chunks = list(chunks)
        self.status = status

    def read(self, n: int = 4096):
        return self._chunks.pop(0) if self._chunks else b""

    def close(self):
        self.closed = True          # 不清空数据: 同一响应可能被连接检测+生成复用

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _capture(monkeypatch, response):
    """替换 urlopen 并捕获请求对象。"""
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = getattr(req, "full_url", str(req))
        captured["headers"] = dict(getattr(req, "headers", {}) or {})
        captured["body"] = json.loads((getattr(req, "data", b"") or b"{}").decode())
        captured["method"] = getattr(req, "get_method", lambda: "GET")()
        return response

    monkeypatch.setattr("core.llm_client.urllib.request.urlopen", fake_urlopen)
    return captured


def _header(headers: dict, name: str):
    """urllib 会规范化 header 大小写，这里做大小写无关读取。"""
    for key, value in (headers or {}).items():
        if key.lower() == name.lower():
            return value
    return None


# ---------- OpenAI 兼容（OpenAI / DeepSeek / Z.ai / KIMI / 自定义）----------


def test_openai_protocol_request_and_stream(monkeypatch):
    body = (b'data: {"choices":[{"delta":{"content":"\\u4f60"}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"\\u597d"}}]}\n\n'
            b"data: [DONE]\n\n")
    captured = _capture(monkeypatch, FakeResp([body]))
    client = LLMClient(provider="deepseek", api_key="sk-test-key",
                       model="deepseek-chat")
    assert list(client.generate("hi")) == ["你", "好"]
    assert captured["url"].endswith("/chat/completions")
    assert _header(captured["headers"], "Authorization") == "Bearer sk-test-key"
    assert captured["body"]["model"] == "deepseek-chat"
    assert captured["body"]["stream"] is True
    assert captured["body"]["messages"][1]["content"] == "hi"


def test_custom_endpoint_without_key(monkeypatch):
    captured = _capture(monkeypatch, FakeResp(
        [b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n']))
    client = LLMClient(provider="custom", api_key="", api_base="http://localhost:8000/v1",
                       model="qwen2.5-7b")
    assert list(client.generate("ping")) == ["ok"]
    assert captured["url"] == "http://localhost:8000/v1/chat/completions"
    assert _header(captured["headers"], "Authorization") is None   # 本地服务无需密钥


# ---------- Anthropic 原生 ----------


def test_anthropic_protocol_request_and_stream(monkeypatch):
    body = (b'event: content_block_delta\n'
            b'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Cpk"}}\n\n'
            b'data: {"type":"message_stop"}\n\n')
    captured = _capture(monkeypatch, FakeResp([body]))
    client = LLMClient(provider="anthropic", api_key="sk-ant-x",
                       model="claude-sonnet-4-5")
    assert list(client.generate("解释 Cpk")) == ["Cpk"]
    assert captured["url"].endswith("/messages")
    assert _header(captured["headers"], "x-api-key") == "sk-ant-x"
    assert _header(captured["headers"], "anthropic-version")
    assert captured["body"]["system"] and captured["body"]["messages"]
    assert "max_tokens" in captured["body"]


# ---------- Gemini 原生 ----------


def test_gemini_protocol_request_and_stream(monkeypatch):
    body = (b'data: {"candidates":[{"content":{"parts":[{"text":"\\u6b63"}]}}]}\n\n'
            b'data: {"candidates":[{"content":{"parts":[{"text":"\\u5e38"}]}}]}\n\n')
    captured = _capture(monkeypatch, FakeResp([body]))
    client = LLMClient(provider="google", api_key="AIza-test",
                       model="gemini-2.5-flash")
    assert list(client.generate("ping")) == ["正", "常"]
    assert ":streamGenerateContent" in captured["url"]
    assert "alt=sse" in captured["url"]
    # 密钥必须走请求头，不得出现在 URL（安全审查 S3，2026-10-15）
    assert "key=" not in captured["url"]
    assert _header(captured["headers"], "x-goog-api-key") == "AIza-test"
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "ping"
    assert captured["body"]["systemInstruction"]


# ---------- Ollama ----------


def test_ollama_protocol_request_and_stream(monkeypatch):
    body = (b'{"response":"\\u4f60","done":false}\n'
            b'{"response":"\\u597d","done":false}\n'
            b'{"done":true}\n')
    captured = _capture(monkeypatch, FakeResp([body]))
    client = LLMClient(provider="ollama", model="qwen2.5:7b")
    assert list(client.generate("hi")) == ["你", "好"]
    assert captured["url"].endswith("/api/generate")


# ---------- 错误归一化 ----------


def _http_error(monkeypatch, code: int, payload: bytes = b'{"error":"x"}'):
    def raise_error(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, code, "err", {}, FakeResp([payload]))

    monkeypatch.setattr("core.llm_client.urllib.request.urlopen", raise_error)


@pytest.mark.parametrize("code,keyword", [
    (401, "密钥无效"), (403, "无权限"), (404, "模型不存在"),
    (429, "限流"), (500, "服务端错误"),
])
def test_friendly_errors(monkeypatch, code, keyword):
    _http_error(monkeypatch, code)
    client = LLMClient(provider="openai", api_key="sk-secret-12345", model="gpt-4o-mini")
    text = "".join(client.generate("hi"))
    assert keyword in text


def test_error_message_masks_api_key(monkeypatch):
    _http_error(monkeypatch, 400, b'{"error":"bad key sk-secret-12345 rejected"}')
    client = LLMClient(provider="openai", api_key="sk-secret-12345", model="gpt-4o-mini")
    text = "".join(client.generate("hi"))
    assert "sk-secret-12345" not in text
    assert "sk-s…2345" in text


def test_network_error_is_readable(monkeypatch):
    def raise_urlerror(req, timeout=None):
        raise urllib.error.URLError("Name or service not known")

    monkeypatch.setattr("core.llm_client.urllib.request.urlopen", raise_urlerror)
    client = LLMClient(provider="kimi", api_key="sk-x", model="moonshot-v1-8k")
    text = "".join(client.generate("hi"))
    assert "无法连接" in text


# ---------- 连通性测试 ----------


def test_connection_openai_lists_models(monkeypatch):
    captured = _capture(monkeypatch, FakeResp(
        [json.dumps({"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}).encode()]))
    result = LLMClient(provider="openai", api_key="sk-x").test_connection()
    assert result.ok and len(result.models) == 2
    assert captured["url"].endswith("/models")
    assert result.latency_ms >= 0
    assert result.as_dict()["provider"] == "openai"


def test_connection_anthropic_posts_probe(monkeypatch):
    captured = _capture(monkeypatch, FakeResp([b"{}"]))
    result = LLMClient(provider="anthropic", api_key="sk-ant-x",
                       model="claude-sonnet-4-5").test_connection()
    assert result.ok
    assert captured["url"].endswith("/messages")
    assert captured["body"]["max_tokens"] == 1


def test_connection_gemini_lists_models(monkeypatch):
    captured = _capture(monkeypatch, FakeResp(
        [json.dumps({"models": [{"name": "models/gemini-2.5-flash"}]}).encode()]))
    result = LLMClient(provider="google", api_key="AIza-x").test_connection()
    assert result.ok and result.models == ["gemini-2.5-flash"]
    assert "key=" not in captured["url"]
    assert _header(captured["headers"], "x-goog-api-key") == "AIza-x"


def test_connection_ollama_lists_models(monkeypatch):
    captured = _capture(monkeypatch, FakeResp(
        [json.dumps({"models": [{"name": "qwen2.5:7b"}]}).encode()]))
    result = LLMClient(provider="ollama").test_connection()
    assert result.ok and captured["url"].endswith("/api/tags")


def test_connection_missing_key_is_reported():
    result = LLMClient(provider="openai", api_key="").test_connection()
    assert result.ok is False and "未配置 API Key" in result.message


def test_connection_failure_reports_friendly_error(monkeypatch):
    _http_error(monkeypatch, 401)
    result = LLMClient(provider="deepseek", api_key="sk-x").test_connection()
    assert result.ok is False and "密钥无效" in result.message
