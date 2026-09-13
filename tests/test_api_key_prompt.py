"""QAM Harness API Key 快速接入测试 — 未配置弹窗 / 已有密钥不弹 / 取消回退。"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QDialog

from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry
from ui.dialogs.llm_dialog import QAMHarnessDialog


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """隔离配置读写，避免污染开发者本机 user_config.json。"""
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return settings


@pytest.fixture
def dialog(isolated_config, _qt_application):
    dlg = _make_dialog()
    yield dlg
    dlg.close()
    dlg.deleteLater()


def _make_dialog() -> QAMHarnessDialog:
    ctx = AgentContext(data_frames={})
    engine = AgentEngine(build_default_registry(ctx), context=ctx)
    return QAMHarnessDialog(None, engine=engine)


def _stub_key_dialog(monkeypatch, key: str = "sk-test-key",
                     accepted: bool = True) -> list:
    """把 ApiKeyDialog 换成不回显的测试替身，返回调用记录列表。"""
    calls: list = []

    class _Stub:
        def __init__(self, provider_id, parent=None):
            calls.append(provider_id)

        def exec(self):
            return (QDialog.DialogCode.Accepted if accepted
                    else QDialog.DialogCode.Rejected)

        def key(self):
            return key

    monkeypatch.setattr("ui.dialogs.api_key_dialog.ApiKeyDialog", _Stub)
    return calls


def _select(dlg, provider_id: str):
    idx = dlg.provider_combo.findData(provider_id)
    assert idx >= 0
    dlg.provider_combo.setCurrentIndex(idx)


# ---------- 未配置 → 弹窗 ----------


def test_unconfigured_provider_prompts_and_saves_key(dialog, monkeypatch,
                                                     isolated_config):
    calls = _stub_key_dialog(monkeypatch, key="sk-openai-test")

    _select(dialog, "openai")

    assert calls == ["openai"]                                  # 弹了输入框
    assert isolated_config.get_secret("llm_openai_api_key") == "sk-openai-test"
    assert dialog.llm.provider == "openai"
    assert dialog.llm.api_key == "sk-openai-test"
    idx = dialog.provider_combo.findData("openai")
    assert dialog.provider_combo.itemText(idx) == "OpenAI"      # 去掉未配置标注


def test_clicking_current_unconfigured_provider_prompts(dialog, monkeypatch,
                                                        isolated_config):
    """重复点击当前项不触发 currentIndexChanged，activated 也要能弹窗。"""
    isolated_config.save_config({"llm_active_provider": "deepseek"})
    dlg = _make_dialog()
    try:
        assert dlg.llm.provider == "deepseek"
        calls = _stub_key_dialog(monkeypatch, key="sk-deepseek-test")
        idx = dlg.provider_combo.findData("deepseek")

        dlg.provider_combo.activated.emit(idx)

        assert calls == ["deepseek"]
        assert isolated_config.get_secret("llm_deepseek_api_key") == "sk-deepseek-test"
        assert dlg.llm.provider == "deepseek"
        assert dlg.llm.api_key == "sk-deepseek-test"
    finally:
        dlg.close()
        dlg.deleteLater()


# ---------- 已有 key → 静默切换 ----------


def test_existing_key_skips_prompt(dialog, monkeypatch, isolated_config):
    isolated_config.save_config({"llm_anthropic_api_key": "sk-ant-existing"})

    class _Boom:
        def __init__(self, *args, **kwargs):
            raise AssertionError("已有密钥时不应弹出输入框")

    monkeypatch.setattr("ui.dialogs.api_key_dialog.ApiKeyDialog", _Boom)

    _select(dialog, "anthropic")

    assert dialog.llm.provider == "anthropic"
    assert dialog.llm.api_key == "sk-ant-existing"


def test_local_provider_never_prompts(dialog, monkeypatch):
    calls = _stub_key_dialog(monkeypatch)

    _select(dialog, "ollama")       # 本地供应商无需密钥

    assert calls == []


# ---------- 取消 → 回退 ----------


def test_cancel_prompt_reverts_selection(dialog, monkeypatch, isolated_config):
    calls = _stub_key_dialog(monkeypatch, accepted=False)
    assert dialog.provider_combo.currentData() == "ollama"

    _select(dialog, "openai")

    assert calls == ["openai"]
    assert dialog.provider_combo.currentData() == "ollama"      # 回退原供应商
    assert dialog.llm.provider == "ollama"
    assert isolated_config.get_secret("llm_openai_api_key") == ""


# ---------- 输入框本身 ----------


class _StubMessageBox:
    """替换 QMessageBox 以捕获「未连接 API」询问（不真正弹窗）。"""

    Yes = QDialog.DialogCode.Accepted
    No = QDialog.DialogCode.Rejected
    calls: list = []

    @classmethod
    def question(cls, *args, **kwargs):
        cls.calls.append(args)
        return cls._reply

    _reply = Yes


# ---------- 已连接供应商：静默通过 + 自动选中 ----------


def test_detect_available_prefers_configured_cloud_provider(isolated_config,
                                                            _qt_application):
    isolated_config.save_config({"llm_deepseek_api_key": "sk-deepseek-test"})

    from core.llm_client import LLMClient

    client = LLMClient.detect_available()
    assert client.provider == "deepseek"
    assert client.available is True
    # 自动把选择持久化为激活供应商（设置页/下次打开一致）
    assert isolated_config.get_setting("llm_active_provider") == "deepseek"


def test_any_key_skips_main_window_prompt(isolated_config, monkeypatch,
                                          _qt_application):
    isolated_config.save_config({"llm_deepseek_api_key": "sk-deepseek-test"})
    import ui.main_window as mw

    _StubMessageBox.calls = []
    _StubMessageBox._reply = _StubMessageBox.Yes
    monkeypatch.setattr(mw, "QMessageBox", _StubMessageBox)

    client = mw._resolve_llm_client(None)
    assert _StubMessageBox.calls == [], "已连接云 API 时不应弹出离线模式询问"
    assert client is not None and client.provider == "deepseek"
    assert client.available is True


def test_no_connection_still_prompts(isolated_config, monkeypatch,
                                     _qt_application):
    import ui.main_window as mw
    from core.llm_client import LLMClient

    monkeypatch.setattr(LLMClient, "_check_available", lambda self: False)
    _StubMessageBox.calls = []
    _StubMessageBox._reply = _StubMessageBox.No
    monkeypatch.setattr(mw, "QMessageBox", _StubMessageBox)

    assert mw._resolve_llm_client(None) is None
    assert len(_StubMessageBox.calls) == 1

    _StubMessageBox._reply = _StubMessageBox.Yes
    client = mw._resolve_llm_client(None)
    assert client is not None and len(_StubMessageBox.calls) == 2


def test_dialog_auto_selects_configured_provider(isolated_config,
                                                 monkeypatch,
                                                 _qt_application):
    isolated_config.save_config({"llm_deepseek_api_key": "sk-deepseek-test"})
    calls = _stub_key_dialog(monkeypatch)

    dlg = _make_dialog()
    try:
        assert dlg.llm.provider == "deepseek"
        assert dlg.llm.available is True
        assert dlg.provider_combo.currentData() == "deepseek"
        assert "未配置密钥" not in dlg.provider_combo.currentText()
        assert calls == []                       # 不应弹密钥输入框
    finally:
        dlg.close()
        dlg.deleteLater()


def test_api_key_dialog_validates_and_trims(_qt_application):
    from ui.dialogs.api_key_dialog import ApiKeyDialog

    dlg = ApiKeyDialog("openai")
    try:
        assert "OpenAI" in dlg.windowTitle()
        dlg.key_edit.setText("   ")
        dlg._on_save()
        assert dlg.result() != QDialog.DialogCode.Accepted          # 空输入不放行
        assert "请输入" in dlg.error_label.text()
        assert not dlg.error_label.isHidden()

        dlg.key_edit.setText("  sk-abc-123  ")
        dlg._on_save()
        assert dlg.result() == QDialog.DialogCode.Accepted
        assert dlg.key() == "sk-abc-123"
    finally:
        dlg.deleteLater()
