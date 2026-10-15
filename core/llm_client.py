"""LLM 客户端 — 本地 Ollama + BYOK 云供应商（v3.8.0 P2）。

协议适配（由 core.agent.providers 注册表驱动）:
  - ollama    : /api/generate（NDJSON 流）
  - openai    : /chat/completions（SSE）— OpenAI / DeepSeek / Z.ai / KIMI / 自定义端点
  - anthropic : /messages（SSE, x-api-key + anthropic-version）
  - gemini    : /models/{model}:streamGenerateContent?alt=sse（原生协议）

密钥与接口地址来自加密配置（config.settings）；环境变量仅作向后兼容回退。
"""

import contextlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from collections.abc import Generator

from core.agent.providers import (
    ProviderSpec, get_provider, masked_key, requires_key, resolve_base_url,
)

OLLAMA_MODELS = ["qwen2.5:7b", "qwen2.5:14b", "llama3.2", "deepseek-r1:8b"]
OPENAI_MODELS = ["deepseek-chat", "glm-4-flash", "gpt-4o-mini"]

ANTHROPIC_VERSION = "2023-06-01"
SYSTEM_PROMPT = "你是专业质量分析助手。"


@dataclass
class ConnectionResult:
    ok: bool
    provider: str = ""
    message: str = ""
    latency_ms: float = 0.0
    models: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "provider": self.provider, "message": self.message,
                "latency_ms": round(self.latency_ms, 1), "models": list(self.models)}


class LLMClient:
    OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    TIMEOUT = 30

    def __init__(self, model: str | None = None, provider: str = "ollama", *,
                 api_key: str | None = None, api_base: str | None = None,
                 timeout: float | None = None):
        self.provider = str(provider or "ollama").strip().lower()
        self.spec: ProviderSpec = get_provider(self.provider)
        self.protocol = self.spec.protocol

        # 密钥/地址: 显式参数 > 环境变量（向后兼容）> 供应商默认
        env_key, env_base = "", ""
        if self.provider == "openai":
            env_key = os.environ.get("OPENAI_API_KEY", "")
            env_base = os.environ.get("OPENAI_API_BASE", "")
        elif self.provider == "ollama":
            env_base = os.environ.get("OLLAMA_HOST", "")
        self.api_key = (api_key if api_key is not None else env_key).strip()
        self.api_base = resolve_base_url(self.provider, api_base or env_base)
        self.model = (model or os.environ.get("OLLAMA_MODEL", "")
                      or self.spec.default_model())
        if timeout:
            self.TIMEOUT = float(timeout)

        self._stop_event = threading.Event()
        self._resp = None
        self.available = self._check_available()

    # ------------------------------------------------------------ 配置
    @classmethod
    def from_config(cls, provider_id: str | None = None) -> "LLMClient":
        """按用户配置构建（密钥走加密存储 `llm_<id>_api_key`）。"""
        try:
            from config.settings import get_secret, get_setting
        except Exception:                      # 无配置环境（测试/脚本）
            return cls(provider=provider_id or "ollama")
        pid = str(provider_id or get_setting("llm_active_provider", "ollama")).lower()
        spec = get_provider(pid)
        model = get_setting(f"llm_{pid}_model", "") or spec.default_model()
        base = get_setting(f"llm_{pid}_api_base", "")
        key = get_secret(f"llm_{pid}_api_key", "")
        return cls(model=model, provider=pid, api_key=key, api_base=base)

    # ------------------------------------------------------------ 连接检测
    @staticmethod
    def _keyed_provider_ids(preferred: str | None = None) -> list[str]:
        """已配置密钥的云供应商（按 偏好 → 当前激活 → 注册表顺序）。"""
        from config.settings import get_secret, get_setting
        from core.agent.providers import PROVIDERS, requires_key

        order: list[str] = []
        for candidate in (preferred, get_setting("llm_active_provider", "")):
            pid = str(candidate or "").strip().lower()
            if pid and pid in PROVIDERS and pid not in order:
                order.append(pid)
        order += [pid for pid in PROVIDERS if pid not in order]
        return [pid for pid in order
                if requires_key(pid) and bool(get_secret(f"llm_{pid}_api_key", ""))]

    @classmethod
    def detect_available(cls, preferred: str | None = None) -> "LLMClient":
        """返回优先使用"已连接"供应商的客户端。

        任意云供应商已配置密钥即视为已连接（并按需把选择持久化为
        `llm_active_provider`，供设置页与下次打开保持一致）；都没有时
        回退到当前配置（本地 Ollama 会在构造时探测一次）。
        """
        keyed = cls._keyed_provider_ids(preferred)
        if keyed:
            pid = keyed[0]
            try:
                from config.settings import get_setting, save_config
                if str(get_setting("llm_active_provider", "") or "").lower() != pid:
                    save_config({"llm_active_provider": pid})
            except Exception:  # 配置不可写时仍可用
                pass
            return cls.from_config(pid)
        return cls.from_config(preferred)

    def config_summary(self) -> dict:
        return {"provider": self.provider, "label": self.spec.label,
                "protocol": self.protocol, "model": self.model,
                "api_base": self.api_base, "available": self.available,
                "key": masked_key(self.api_key)}

    def set_model(self, model: str, provider: str = "ollama"):
        pid = str(provider or "ollama").strip().lower()
        if pid != self.provider:                     # 切换供应商 → 重置地址/协议
            self.provider = pid
            self.spec = get_provider(pid)
            self.protocol = self.spec.protocol
            if pid == "ollama":
                self.api_base = resolve_base_url(
                    pid, os.environ.get("OLLAMA_HOST", ""))
            else:
                self.api_base = resolve_base_url(pid, "")
            if pid == "openai" and not self.api_key:
                self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.model = model or self.spec.default_model()
        self.available = self._check_available()

    # ------------------------------------------------------------ 状态
    def stop(self):
        """中断当前流式生成: 置停止标志并关闭底层连接以解除阻塞读"""
        self._stop_event.set()
        resp, self._resp = self._resp, None
        if resp is not None:
            with contextlib.suppress(Exception):
                resp.close()

    def _check_available(self) -> bool:
        if self.protocol == "ollama":
            try:
                req = urllib.request.Request(f"{self.api_base}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    return resp.status == 200
            except Exception:
                return False
        if not requires_key(self.provider):
            return bool(self.api_base)
        return bool(self.api_key)

    def get_models(self) -> list[str]:
        """Ollama 动态取模型列表；云供应商返回注册表内置清单。"""
        if self.protocol == "ollama":
            try:
                req = urllib.request.Request(f"{self.api_base}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode())
                    models = data.get("models", [])
                    if models:
                        return sorted(m["name"] for m in models)
            except Exception:  # 本地 Ollama 未启动/接口变更：退回内置模型清单
                pass
            return list(OLLAMA_MODELS)
        return list(self.spec.models)

    def is_model_available(self, model: str) -> bool:
        if self.protocol != "ollama":
            return True
        try:
            return model in self.get_models()
        except Exception:
            return False

    # ------------------------------------------------------------ 生成
    def generate(self, prompt: str, model: str | None = None) -> Generator[str, None, None]:
        self._stop_event.clear()
        m = model or self.model
        if self.protocol == "ollama":
            yield from self._gen_ollama(prompt, m)
        elif self.protocol == "anthropic":
            yield from self._gen_anthropic(prompt, m)
        elif self.protocol == "gemini":
            yield from self._gen_gemini(prompt, m)
        else:
            yield from self._gen_openai(prompt, m)

    # ------------------------------------------------------------ 协议: Ollama
    def _gen_ollama(self, prompt: str, model: str):
        payload = json.dumps({
            "model": model, "prompt": prompt, "stream": True,
            "options": {"temperature": 0.3, "num_predict": 1024},
        }).encode()
        try:
            req = urllib.request.Request(
                f"{self.api_base}/api/generate", data=payload,
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    buf = b""
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        if self._stop_event.is_set():
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            if not line.strip():
                                continue
                            try:
                                d = json.loads(line.decode())
                            except json.JSONDecodeError:
                                continue
                            if d.get("done"):
                                return
                            yield d.get("response", "")
                finally:
                    self._resp = None
        except Exception as e:
            if self._stop_event.is_set():
                return
            yield f"[{self._friendly_error(e)}]"

    # ------------------------------------------------------------ 协议: OpenAI 兼容
    def _gen_openai(self, prompt: str, model: str):
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": prompt}],
            "stream": True, "temperature": 0.3, "max_tokens": 1024,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "zai":
            headers["Accept-Language"] = "zh-CN"
        try:
            req = urllib.request.Request(f"{self.api_base}/chat/completions",
                                         data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    for data in self._iter_sse(resp):
                        if data == "[DONE]":
                            return
                        try:
                            j = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = j.get("choices") or [{}]
                        delta = choices[0].get("delta") or {}
                        text = delta.get("content") or ""
                        if not text:
                            text = (choices[0].get("message") or {}).get("content", "")
                        if text:
                            yield text
                finally:
                    self._resp = None
        except Exception as e:
            if self._stop_event.is_set():
                return
            yield f"[{self._friendly_error(e)}]"

    # ------------------------------------------------------------ 协议: Anthropic
    def _gen_anthropic(self, prompt: str, model: str):
        payload = json.dumps({
            "model": model, "max_tokens": 1024, "stream": True,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        headers = {"Content-Type": "application/json",
                   "x-api-key": self.api_key,
                   "anthropic-version": ANTHROPIC_VERSION}
        try:
            req = urllib.request.Request(f"{self.api_base}/messages", data=payload,
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    for data in self._iter_sse(resp):
                        try:
                            j = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        etype = j.get("type")
                        if etype == "content_block_delta":
                            text = (j.get("delta") or {}).get("text", "")
                            if text:
                                yield text
                        elif etype == "message_stop":
                            return
                finally:
                    self._resp = None
        except Exception as e:
            if self._stop_event.is_set():
                return
            yield f"[{self._friendly_error(e)}]"

    # ------------------------------------------------------------ 协议: Gemini 原生
    def _gen_gemini(self, prompt: str, model: str):
        # 密钥走请求头（x-goog-api-key）而非 URL query —— 避免代理/网关/服务端
        # 访问日志截获密钥（2026-10-15 安全审查 S3；Google 官方支持该请求头）。
        url = f"{self.api_base}/models/{model}:streamGenerateContent?alt=sse"
        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload,
                                         headers={"Content-Type": "application/json",
                                                  "x-goog-api-key": self.api_key},
                                         method="POST")
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    for data in self._iter_sse(resp):
                        try:
                            j = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        for cand in j.get("candidates", []) or []:
                            for part in (cand.get("content") or {}).get("parts", []) or []:
                                text = part.get("text", "")
                                if text:
                                    yield text
                finally:
                    self._resp = None
        except Exception as e:
            if self._stop_event.is_set():
                return
            yield f"[{self._friendly_error(e)}]"

    # ------------------------------------------------------------ 公共解析
    def _iter_sse(self, resp):
        """逐条产出 SSE data 载荷（跳过空行与注释；自动识别 [DONE]）。"""
        buf = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            if self._stop_event.is_set():
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line or line.startswith(b":") or not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                yield payload.decode("utf-8", "ignore")

    def _friendly_error(self, e: Exception) -> str:
        """把底层异常翻译成可读中文（并脱敏密钥）。"""
        if isinstance(e, urllib.error.HTTPError):
            detail = ""
            with contextlib.suppress(Exception):
                detail = e.read().decode("utf-8", "ignore")[:200]
            mapping = {
                400: "请求被拒绝（参数/模型名有误）",
                401: "密钥无效或已过期",
                403: "无权限（检查密钥权限或模型是否开通）",
                404: "接口或模型不存在（检查模型名与接口地址）",
                413: "请求体过大",
                429: "触发限流或配额不足",
                500: "服务端错误", 502: "网关错误", 503: "服务暂不可用",
            }
            msg = mapping.get(e.code, f"HTTP {e.code}")
            detail = self._mask(detail)
            return f"{msg}（{e.code}）" + (f": {detail}" if detail else "")
        if isinstance(e, urllib.error.URLError):
            return f"无法连接（网络/DNS/代理）: {getattr(e, 'reason', e)}"
        if isinstance(e, TimeoutError):
            return "请求超时（可在设置→QAM Harness 调整接口地址或稍后重试）"
        if isinstance(e, json.JSONDecodeError):
            return "响应解析失败（接口地址可能指向了非 API 页面）"
        return f"{type(e).__name__}: {self._mask(str(e))}"

    def _mask(self, text: str) -> str:
        key = (self.api_key or "").strip()
        if key and key in text:
            text = text.replace(key, masked_key(key))
        return text

    # ------------------------------------------------------------ 连通性测试
    def test_connection(self, timeout: float = 8.0) -> ConnectionResult:
        """显式连通性测试（唯一会主动联网的方法，供设置页按钮调用）。"""
        started = time.time()
        try:
            if self.protocol == "ollama":
                req = urllib.request.Request(f"{self.api_base}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode())
                models = sorted(m.get("name", "") for m in data.get("models", []))
                return ConnectionResult(True, self.provider,
                                        f"连接正常，发现 {len(models)} 个本地模型",
                                        (time.time() - started) * 1000, models)
            if requires_key(self.provider) and not self.api_key:
                return ConnectionResult(False, self.provider,
                                        "未配置 API Key（设置 → QAM Harness）")
            if self.protocol == "anthropic":
                payload = json.dumps({
                    "model": self.model, "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                }).encode()
                req = urllib.request.Request(
                    f"{self.api_base}/messages", data=payload, method="POST",
                    headers={"Content-Type": "application/json",
                             "x-api-key": self.api_key,
                             "anthropic-version": ANTHROPIC_VERSION})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp.read()
                return ConnectionResult(True, self.provider,
                                        f"连接正常（模型 {self.model}）",
                                        (time.time() - started) * 1000)
            if self.protocol == "gemini":
                url = f"{self.api_base}/models"
                with urllib.request.urlopen(
                        urllib.request.Request(
                            url, method="GET",
                            headers={"x-goog-api-key": self.api_key}),
                        timeout=timeout) as resp:
                    data = json.loads(resp.read().decode())
                models = [str(m.get("name", "")).split("/")[-1]
                          for m in data.get("models", [])]
                return ConnectionResult(True, self.provider,
                                        f"连接正常，可用模型 {len(models)} 个",
                                        (time.time() - started) * 1000, models[:50])
            # OpenAI 兼容: 先试 /models，404/405 时退化为一次最小对话
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            try:
                with urllib.request.urlopen(
                        urllib.request.Request(f"{self.api_base}/models",
                                               headers=headers, method="GET"),
                        timeout=timeout) as resp:
                    data = json.loads(resp.read().decode())
                models = [m.get("id", "") for m in data.get("data", [])]
                return ConnectionResult(True, self.provider,
                                        f"连接正常，可用模型 {len(models)} 个",
                                        (time.time() - started) * 1000, models[:50])
            except urllib.error.HTTPError as e:
                if e.code not in (404, 405):
                    raise
            payload = json.dumps({
                "model": self.model, "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }).encode()
            with urllib.request.urlopen(
                    urllib.request.Request(f"{self.api_base}/chat/completions",
                                           data=payload, headers=headers, method="POST"),
                    timeout=timeout) as resp:
                resp.read()
            return ConnectionResult(True, self.provider,
                                    f"连接正常（模型 {self.model}）",
                                    (time.time() - started) * 1000)
        except Exception as e:
            return ConnectionResult(False, self.provider, self._friendly_error(e),
                                    (time.time() - started) * 1000)
