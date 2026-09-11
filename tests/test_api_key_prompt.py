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
