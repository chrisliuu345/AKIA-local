"""LLM 客户端 — Ollama + OpenAI 兼容 API 多模型支持"""

import json, os, threading, urllib.request, urllib.error
from typing import Generator, List

OLLAMA_MODELS = ["qwen2.5:7b", "qwen2.5:14b", "llama3.2", "deepseek-r1:8b"]
OPENAI_MODELS = ["deepseek-chat", "glm-4-flash", "gpt-4o-mini", "custom"]


class LLMClient:
    OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    TIMEOUT = 30

    def __init__(self, model: str = None, provider: str = "ollama"):
        self.provider = provider
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        self.api_base = os.environ.get("OPENAI_API_BASE", "")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self._stop_event = threading.Event()
        self._resp = None
        self.available = self._check_available()

    def stop(self):
        """中断当前流式生成: 置停止标志并关闭底层连接以解除阻塞读"""
        self._stop_event.set()
        resp, self._resp = self._resp, None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    def set_model(self, model: str, provider: str = "ollama"):
        self.model = model; self.provider = provider
        self.available = self._check_available()

    def _check_available(self) -> bool:
        if self.provider == "ollama":
            try:
                req = urllib.request.Request(f"{self.OLLAMA_BASE}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    return resp.status == 200
            except Exception: return False
        return bool(self.api_base and self.api_key)

    def get_models(self) -> List[str]:
        if self.provider == "ollama":
            try:
                req = urllib.request.Request(f"{self.OLLAMA_BASE}/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    return [m["name"] for m in json.loads(resp.read().decode()).get("models", [])]
            except Exception: return OLLAMA_MODELS
        return OPENAI_MODELS

    def generate(self, prompt: str, model: str = None) -> Generator[str, None, None]:
        self._stop_event.clear()
        m = model or self.model
        if self.provider == "ollama":
            yield from self._gen_ollama(prompt, m)
        else:
            yield from self._gen_openai(prompt, m)

    def _gen_ollama(self, prompt: str, model: str):
        payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
            "options": {"temperature": 0.3, "num_predict": 1024}}).encode()
        try:
            req = urllib.request.Request(f"{self.OLLAMA_BASE}/api/generate", data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    buf = b""
                    while True:
                        chunk = resp.read(4096)
                        if not chunk: break
                        if self._stop_event.is_set(): break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            if not line.strip(): continue
                            try:
                                d = json.loads(line.decode())
                                if d.get("done"): return
                                yield d.get("response", "")
                            except json.JSONDecodeError: continue
                finally:
                    self._resp = None
        except urllib.error.URLError as e:
            if self._stop_event.is_set(): return
            yield f"[连接失败: {e}]"
        except Exception as e:
            if self._stop_event.is_set(): return
            yield f"[异常: {e}]"

    def _gen_openai(self, prompt: str, model: str):
        payload = json.dumps({"model": model, "messages": [
            {"role": "system", "content": "你是专业质量分析助手。"},
            {"role": "user", "content": prompt}],
            "stream": True, "temperature": 0.3, "max_tokens": 1024}).encode()
        try:
            url = f"{self.api_base}/chat/completions"
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                self._resp = resp
                try:
                    buf = b""
                    while True:
                        chunk = resp.read(4096)
                        if not chunk: break
                        if self._stop_event.is_set(): break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            line = line.strip()
                            if not line or not line.startswith(b"data: "): continue
                            d = line[6:]
                            if d == b"[DONE]": return
                            try:
                                j = json.loads(d)
                                yield j.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            except json.JSONDecodeError: continue
                finally:
                    self._resp = None
        except urllib.error.URLError as e:
            if self._stop_event.is_set(): return
            yield f"[连接失败: {e}]"
        except Exception as e:
            if self._stop_event.is_set(): return
            yield f"[异常: {e}]"
