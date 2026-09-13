"""P2 端到端集成验证 — 本地 mock API 服务器（真实 HTTP，不外联）。

覆盖:
  1. 四协议（Ollama / OpenAI 兼容 / Anthropic / Gemini）真实 HTTP 流式解析 + 连通性测试
  2. 设置保存 → LLMClient.from_config() → 连通性测试 的完整配置链路
  3. 隐私门 fail-closed：未授权时零请求；授权后放行
  4. QAM Harness 对话窗口 → 隐私确认 → 云端回答 全流程
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry
from core.llm_client import LLMClient


class _Handler(BaseHTTPRequestHandler):
    """按路径模拟四家 API 的流式响应，并记录全部请求。"""

    server_version = "MockLLM/1.0"

    def log_message(self, *args):        # 静音
        pass

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return {}

    def _record(self, body: dict) -> None:
        self.server.requests.append({
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers.items()),
            "body": body,
        })

    def _sse(self, chunks: list[str]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()

    def _json(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- GET ----------
    def do_GET(self):
        self._record({})
        if self.path.startswith("/api/tags"):
            return self._json({"models": [{"name": "mock-llama:latest"}]})
        if ("/models" in self.path and "generativelanguage" in self.path) or \
                self.path.startswith("/v1beta/models"):
            return self._json({"models": [{"name": "models/mock-gemini"}]})
        if self.path.startswith("/v1/models"):
            return self._json({"data": [{"id": "mock-gpt"}, {"id": "mock-gpt-mini"}]})
        self.send_error(404)

    # ---------- POST ----------
    def do_POST(self):
        body = self._read_json()
        self._record(body)
        if self.path.startswith("/api/generate"):
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.end_headers()
            for line in ('{"response":"\\u672c\\u5730","done":false}',
                         '{"response":"\\u56de\\u7b54","done":false}',
                         '{"done":true}'):
                self.wfile.write((line + "\n").encode())
                self.wfile.flush()
            return
        if ":streamGenerateContent" in self.path:
            return self._sse([
                'data: {"candidates":[{"content":{"parts":[{"text":"Gemini"}]}}]}\n\n',
                'data: {"candidates":[{"content":{"parts":[{"text":"回答"}]}}]}\n\n',
            ])
        if self.path.startswith("/v1/messages"):
            return self._sse([
                ('event: content_block_delta\n'
                'data: {"type":"content_block_delta","delta":{"text":"Claude"}}\n\n'),
                'data: {"type":"message_stop"}\n\n',
            ])
        if self.path.endswith("/chat/completions"):
            return self._sse([
                'data: {"choices":[{"delta":{"content":"云端"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":"回答"}}]}\n\n',
                "data: [DONE]\n\n",
            ])
        self.send_error(404)


@pytest.fixture(scope="module")
def api_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def base_url(api_server):
    api_server.requests.clear()
    return f"http://127.0.0.1:{api_server.server_port}"


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return target


@pytest.fixture
def remote_like(monkeypatch):
    """把 127.0.0.1 mock 服务器伪装成"云端"（用于触发隐私门）。"""
    import core.agent.providers as providers

    monkeypatch.setattr(providers, "is_local_endpoint", lambda url: False)
    import core.agent.privacy as privacy
    monkeypatch.setattr(privacy, "needs_privacy_gate",
                        lambda pid, base="": pid not in ("ollama",))


# ---------------------------------------------------------------- 协议


def test_ollama_over_real_http(base_url):
    client = LLMClient(provider="ollama", api_base=base_url, model="mock-llama")
    assert "".join(client.generate("hi")) == "本地回答"
    result = client.test_connection()
    assert result.ok and result.models == ["mock-llama:latest"]


@pytest.mark.parametrize("provider,expected,path_part", [
    ("openai", "云端回答", "/v1/chat/completions"),
    ("deepseek", "云端回答", "/v1/chat/completions"),
    ("zai", "云端回答", "/v1/chat/completions"),
    ("kimi", "云端回答", "/v1/chat/completions"),
])
def test_openai_compatible_vendors_over_real_http(base_url, provider, expected,
                                                  path_part):
    client = LLMClient(provider=provider, api_key="sk-mock", api_base=base_url + "/v1",
                       model="mock-gpt")
    assert "".join(client.generate("hi")) == expected
    result = client.test_connection()
    assert result.ok and "mock-gpt" in result.models


def test_anthropic_over_real_http(base_url):
    client = LLMClient(provider="anthropic", api_key="sk-ant-mock",
                       api_base=base_url + "/v1", model="claude-mock")
    assert "".join(client.generate("hi")) == "Claude"
    assert client.test_connection().ok


def test_gemini_over_real_http(base_url):
    client = LLMClient(provider="google", api_key="AIza-mock",
                       api_base=base_url + "/v1beta", model="gemini-mock")
    assert "".join(client.generate("hi")) == "Gemini回答"
    result = client.test_connection()
    assert result.ok and result.models == ["mock-gemini"]


def test_request_headers_and_bodies_on_wire(base_url, api_server):
    LLMClient(provider="anthropic", api_key="sk-ant-mock", api_base=base_url + "/v1",
              model="claude-mock").test_connection()
    anthropic_call = api_server.requests[-1]
    assert anthropic_call["path"] == "/v1/messages"
    assert anthropic_call["body"]["max_tokens"] == 1
    headers = {k.lower(): v for k, v in anthropic_call["headers"].items()}
    assert headers["x-api-key"] == "sk-ant-mock" and "anthropic-version" in headers

    api_server.requests.clear()
    LLMClient(provider="google", api_key="AIza-mock", api_base=base_url + "/v1beta",
              model="gemini-mock").test_connection()
    assert "key=AIza-mock" in api_server.requests[-1]["path"]


# ---------------------------------------------------------------- 配置链路


def test_settings_to_client_to_connection(base_url, isolated_config):
    from config.settings import save_config
    from core.llm_client import LLMClient as Client

    save_config({
        "llm_active_provider": "deepseek",
        "llm_deepseek_model": "mock-gpt",
        "llm_deepseek_api_base": base_url + "/v1",
        "llm_deepseek_api_key": "sk-config-chain",
    })
    client = Client.from_config()
    assert client.provider == "deepseek"
    assert client.model == "mock-gpt"
    assert client.api_base == base_url + "/v1"
    assert client.api_key == "sk-config-chain"
    result = client.test_connection()
    assert result.ok and result.as_dict()["provider"] == "deepseek"


# ---------------------------------------------------------------- 隐私门


def _cloud_engine(base_url, ctx, isolated_config):
    client = LLMClient(provider="deepseek", api_key="sk-mock",
                       api_base=base_url + "/v1", model="mock-gpt")
    return AgentEngine(build_default_registry(ctx), llm=client, context=ctx)


@pytest.fixture
def ctx():
    import pandas as pd
    return AgentContext(data_frames={"Sheet1": pd.DataFrame({"a": [1, 2, 3]})})


def test_privacy_gate_blocks_before_consent(base_url, api_server, remote_like,
                                            ctx, isolated_config):
    engine = _cloud_engine(base_url, ctx, isolated_config)
    requests_before = len(api_server.requests)
    reply = engine.respond("用当前数据做过程能力分析 USL=4 LSL=2")
    assert len(api_server.requests) == requests_before      # 零外发
    assert reply.offline is True
    assert "云调用已在设置中关闭" in reply.text
    assert reply.tool_calls                                   # 降级本地工具


def test_privacy_gate_allows_after_consent(base_url, api_server, remote_like,
                                           ctx, isolated_config):
    from core.agent import privacy

    privacy.set_cloud_enabled(True)
    privacy.grant_consent("deepseek")
    engine = _cloud_engine(base_url, ctx, isolated_config)
    reply = engine.respond("解释一下 Cpk 判定标准")
    assert reply.offline is False
    assert "云端回答" in reply.text
    assert any(r["path"].endswith("/chat/completions") for r in api_server.requests)
    # 密钥确实随请求发出（Bearer），但不出现在回复文本中
    chat_call = [r for r in api_server.requests
                 if r["path"].endswith("/chat/completions")][-1]
    assert chat_call["headers"].get("Authorization") == "Bearer sk-mock"
    assert "sk-mock" not in reply.text


# ---------------------------------------------------------------- 对话窗口全流程


def _pump_until(condition, timeout: float = 30.0) -> bool:
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


def test_harness_dialog_consent_then_cloud_answer(base_url, api_server, remote_like,
                                                 ctx, isolated_config, monkeypatch):
    """完整用户路径: 打开窗口 → 提问 → 隐私门拦截 → 同意 → 云端回答。"""
    from ui.dialogs import privacy_dialog as pmod
    from ui.dialogs.llm_dialog import QAMHarnessDialog

    prompts = []

    def stub_init(self, *args, **kwargs):        # 模拟用户点「同意并继续」
        self.consent = True
        self.use_local_only = False
        # 构造签名: CloudPrivacyDialog(parent, preview, provider_label)
        self.preview = args[1] if len(args) > 1 else kwargs.get("preview")
        prompts.append(self.preview)

    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__", stub_init)
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)

    engine = _cloud_engine(base_url, ctx, isolated_config)
    dlg = QAMHarnessDialog(None, engine=engine)
    try:
        assert dlg.provider_combo.currentData() == "deepseek"
        dlg.input_box.setText("帮我解释一下 Cpk")
        dlg._send_message()
        assert _pump_until(lambda: dlg.worker is None or not dlg.worker.isRunning())
        QApplication.instance().processEvents()
        plain = dlg.chat_view.toPlainText()
        assert "云端回答" in plain
        assert prompts and prompts[0] is not None          # 弹窗拿到了外发预览
        assert "Cpk" in prompts[0].question
        from core.agent.privacy import needs_consent
        assert needs_consent("deepseek") is False          # 已记录授权
    finally:
        dlg.worker = None
        dlg.close()
        dlg.deleteLater()


def test_harness_dialog_cancel_sends_nothing(base_url, api_server, remote_like,
                                             ctx, isolated_config, monkeypatch):
    from ui.dialogs import privacy_dialog as pmod
    from ui.dialogs.llm_dialog import QAMHarnessDialog

    def stub_init(self, *args, **kwargs):        # 模拟用户点「取消」
        self.consent = False
        self.use_local_only = False
        self.preview = None

    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__", stub_init)
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)

    engine = _cloud_engine(base_url, ctx, isolated_config)
    dlg = QAMHarnessDialog(None, engine=engine)
    try:
        before = len(api_server.requests)
        dlg.input_box.setText("这条不该发出去")
        dlg._send_message()
        QApplication.instance().processEvents()
        assert dlg.worker is None
        assert len(api_server.requests) == before
        assert dlg.input_box.text() == "这条不该发出去"
    finally:
        dlg.close()
        dlg.deleteLater()
