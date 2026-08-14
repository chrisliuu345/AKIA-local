"""LLM 客户端中断机制单元测试 — stop() 应能解除阻塞读并快速终止流式生成"""
import sys, os, threading, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

from core.llm_client import LLMClient


class FakeResp:
    """模拟阻塞的流式响应: read() 阻塞直到 close() 被调用"""

    def __init__(self):
        self._closed = threading.Event()
        self._reading = threading.Event()

    def read(self, n):
        self._reading.set()
        self._closed.wait(timeout=10)
        return b""

    def close(self):
        self._closed.set()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def openai_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_BASE", "http://localhost:9")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return LLMClient(provider="openai")


class TestLLMClientStop:
    def test_stop_unblocks_generation(self, monkeypatch, openai_client):
        fake = FakeResp()
        monkeypatch.setattr("core.llm_client.urllib.request.urlopen",
                            lambda *a, **k: fake)
        gen = openai_client.generate("测试")
        errors = []

        def consume():
            try:
                for _ in gen:
                    pass
            except Exception as e:
                errors.append(e)

        th = threading.Thread(target=consume, daemon=True)
        start = time.monotonic()
        th.start()
        assert fake._reading.wait(timeout=2), "生成线程未进入阻塞读"
        openai_client.stop()
        th.join(timeout=3)
        assert not th.is_alive(), "stop() 后生成线程未在 3 秒内退出"
        assert time.monotonic() - start < 5, "stop() 耗时过长"
        assert not errors, f"stop() 过程中抛异常: {errors}"

    def test_generate_reusable_after_stop(self, monkeypatch, openai_client):
        fake = FakeResp()
        monkeypatch.setattr("core.llm_client.urllib.request.urlopen",
                            lambda *a, **k: fake)
        openai_client.stop()
        fake._closed.set()  # 模拟已关闭的连接, read 立即返回空
        # stop 后再次调用 generate 应清除停止标志并正常结束
        tokens = list(openai_client.generate("再次生成"))
        assert tokens == []

    def test_stop_without_active_request(self, openai_client):
        openai_client.stop()  # 无活动连接时不抛异常


class TestLLMWorkerInterruption:
    def test_worker_breaks_on_interruption(self, monkeypatch, openai_client):
        from PySide6.QtCore import QCoreApplication
        from ui.dialogs.llm_dialog import LLMWorker
        app = QCoreApplication.instance() or QCoreApplication([])
        fake = FakeResp()
        monkeypatch.setattr("core.llm_client.urllib.request.urlopen",
                            lambda *a, **k: fake)
        worker = LLMWorker(openai_client, "hi")
        received = []
        finished = []
        worker.token_received.connect(received.append)
        worker.finished.connect(finished.append)
        worker.start()
        assert fake._reading.wait(timeout=2), "worker 未进入阻塞读"
        worker.requestInterruption()
        openai_client.stop()
        assert worker.wait(3000), "worker 未在中断后退出"
        app.processEvents()  # 冲刷跨线程队列信号
        assert finished, "finished 信号未发出"
        assert worker.isFinished()
