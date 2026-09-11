"""设置面板「QAM Harness」标签页测试 — BYOK 表单 / 保存加密 / 不回显明文。"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from ui.dialogs.settings_dialog import SettingsDialog


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """把配置读写指向临时文件，避免污染开发者本机 user_config.json。"""
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return target


@pytest.fixture
def dialog(isolated_config, _qt_application):
    dlg = SettingsDialog()
    yield dlg
    dlg.deleteLater()


def _tab_titles(dialog):
    from PySide6.QtWidgets import QTabWidget

    widget = dialog.findChild(QTabWidget)
    return [widget.tabText(i) for i in range(widget.count())]


def test_agent_tab_present(dialog):
    assert "QAM Harness" in _tab_titles(dialog)
    assert dialog.provider_combo.count() == 8          # 6 云 + ollama + custom


def test_provider_switch_updates_models_and_placeholder(dialog):
    idx = dialog.provider_combo.findData("anthropic")
    dialog.provider_combo.setCurrentIndex(idx)
    assert dialog.model_combo.currentText().startswith("claude")
    assert "api.anthropic.com" in dialog.api_base_edit.placeholderText()
    # 切换到 Gemini（原生协议）
    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("google"))
    assert dialog.model_combo.currentText().startswith("gemini")


def test_agent_values_without_key_only_metadata(dialog):
    values = dialog.get_values()
    assert values["llm_active_provider"] == "ollama"
    assert "llm_ollama_model" in values
    assert "llm_ollama_api_key" not in values        # 未填密钥不覆盖既有密钥


def test_api_key_saved_encrypted_not_plaintext(dialog, isolated_config):
    from config.settings import get_secret, save_config

    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("deepseek"))
    dialog.api_key_edit.setText("sk-secret-abcdef123456")
    values = dialog.get_values()
    assert values["llm_deepseek_api_key"] == "sk-secret-abcdef123456"

    save_config(values)
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert "llm_deepseek_api_key" not in raw                  # 明文不入盘
    assert raw.get("llm_deepseek_api_key_enc")                # 只有加密值
    assert get_secret("llm_deepseek_api_key") == "sk-secret-abcdef123456"


def test_clear_key_flag_writes_empty(dialog, isolated_config):
    from config.settings import save_config

    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("kimi"))
    dialog.api_key_edit.setText("sk-abc")
    save_config(dialog.get_values())

    dialog2 = SettingsDialog()
    try:
        dialog2.provider_combo.setCurrentIndex(dialog2.provider_combo.findData("kimi"))
        assert "已配置" in dialog2.key_state_label.text()       # 显示"已配置"不回显明文
        assert dialog2.api_key_edit.text() == ""
        dialog2._clear_api_key()
        values = dialog2.get_values()
        assert values["llm_kimi_api_key"] is None               # None = 删除键
    finally:
        dialog2.deleteLater()


def test_cleared_key_is_actually_removed(dialog, isolated_config):
    """审查发现: 清除后旧 _enc 残留会被 get_secret 读回，必须真正删除。"""
    from config.settings import get_secret, save_config

    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("kimi"))
    dialog.api_key_edit.setText("sk-to-be-removed")
    save_config(dialog.get_values())
    assert get_secret("llm_kimi_api_key") == "sk-to-be-removed"

    dialog._clear_api_key()
    save_config(dialog.get_values())
    raw = json.loads(isolated_config.read_text(encoding="utf-8"))
    assert "llm_kimi_api_key" not in raw
    assert "llm_kimi_api_key_enc" not in raw        # 加密残留一并清除
    assert get_secret("llm_kimi_api_key") == ""


def test_test_worker_stopped_on_dialog_close(dialog, monkeypatch):
    """审查发现: 连通性测试线程在关闭时可能仍在运行（QThread 销毁告警/崩溃）。"""
    from PySide6.QtCore import QThread

    class SlowWorker(QThread):
        def run(self):
            self.msleep(1500)

    worker = SlowWorker()
    dialog._test_worker = worker
    worker.start()
    assert worker.isRunning()
    dialog._stop_test_worker()
    assert worker.isRunning() is False


def test_consent_status_and_revoke(dialog, isolated_config):
    from core.agent.privacy import ack_key, grant_consent
    from config.settings import save_config

    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("openai"))
    dialog._on_provider_changed()
    assert "未授权" in dialog.consent_label.text()
    grant_consent("openai")
    dialog._on_provider_changed()
    assert "已授权" in dialog.consent_label.text()
    save_config({})                                  # 触发落盘（隔离文件）
    dialog._on_revoke_consent(lambda pid: None)
    assert "已撤销" in dialog.consent_label.text()
    assert ack_key("openai") == "llm_privacy_ack_openai"


def test_local_provider_needs_no_key(dialog):
    dialog.provider_combo.setCurrentIndex(dialog.provider_combo.findData("custom"))
    assert "无需密钥" in dialog.key_state_label.text() or \
        "可留空" in dialog.api_key_edit.placeholderText() + dialog.key_state_label.text()
    assert "无需授权" in dialog.consent_label.text()


def test_cloud_switch_defaults_off(dialog):
    assert dialog.cloud_check.isChecked() is False
    dialog.cloud_check.setChecked(True)
    assert dialog.get_values()["llm_cloud_enabled"] is True
