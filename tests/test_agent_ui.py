"""QAM Harness 界面测试 — 命名/可读性渲染/端到端对话/上下文桥接。"""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.agent.engine import AgentEngine
from core.agent.tools import AgentContext, build_default_registry
from ui.agent_bridge import build_context, build_engine
from ui.dialogs.llm_dialog import LLMDialog, QAMHarnessDialog, md_to_html


@pytest.fixture(autouse=True)
def isolated_llm_config(tmp_path, monkeypatch):
    """隔离本机 user_config.json —— 真实 API Key 不应影响离线模式断言。"""
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})
    return settings


@pytest.fixture
def ctx():
    rng = np.random.default_rng(9)
    df = pd.DataFrame({"外径": rng.normal(20.0, 0.1, 50)})
    return AgentContext(data_frames={"Sheet1": df})


@pytest.fixture
def dialog(ctx):
    engine = AgentEngine(build_default_registry(ctx), context=ctx)
    dlg = QAMHarnessDialog(None, engine=engine)
    yield dlg
    dlg.close()
    dlg.deleteLater()


def _pump_until(condition, timeout: float = 25.0) -> bool:
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


# ---------- 命名 ----------


def test_naming_renamed_to_qam_harness(dialog):
    from core.i18n import i18n

    assert "QAM Harness" in dialog.windowTitle()
    assert i18n.tr("sidebar.llm") == "QAM Harness"
    assert i18n.tr("menu.ai") == "QAM Harness"


def test_alias_kept_for_backward_compat():
    assert LLMDialog is QAMHarnessDialog


def test_main_window_menu_and_sidebar_use_new_name():
    from ui.main_window import MainWindow

    win = MainWindow()
    try:
        ai_menu = next(a.menu() for a in win.menuBar().actions()
                       if "QAM Harness" in a.text())
        texts = [a.text() for a in ai_menu.actions()]
        assert any("QAM Harness" in t for t in texts)
        assert "QAM Harness" in win.sidebar.llm_btn.text()
    finally:
        win.close()


# ---------- 渲染可读性 ----------


def test_markdown_renderer_features():
    html_text = md_to_html("### 标题\n**加粗** 与 `code`\n- 项目 A\n1. 步骤\n"
                           "```\nprint(1)\n```\n<script>alert(1)</script>")
    assert "<b>加粗</b>" in html_text
    assert "background:#35354a" in html_text                # 行内代码
    assert "color:#4da6ff;font-weight:bold" in html_text    # 标题
    assert "• 项目 A" in html_text
    assert "<pre" in html_text
    assert "&lt;script&gt;" in html_text                    # HTML 转义（防注入）


def test_context_bar_shows_tools_and_offline_state(dialog):
    bar = dialog.context_label.text()
    assert f"可用工具 {dialog.engine.tool_count()} 个" in bar
    assert dialog.engine.tool_count() >= 30
    assert "离线工具模式" in bar
    assert "数据表 1 张" in bar


def test_bubbles_and_tool_card_rendered(dialog):
    from core.agent.engine import ToolCallRecord

    dialog.append_msg("user", "问一句", markdown=False)
    dialog._append_tool_card(ToolCallRecord(name="run_spc",
                                            args={"chart_type": "imr"},
                                            ok=True, summary="CL=1 UCL=2",
                                            duration_ms=5))
    dialog._append_tool_card(ToolCallRecord(name="run_oee", ok=False,
                                            error="未接入"))
    plain = dialog.chat_view.toPlainText()
    assert "问一句" in plain
    assert "run_spc" in plain and "CL=1 UCL=2" in plain
    assert "run_oee" in plain and "失败" in plain


def test_preset_fills_input(dialog):
    dialog._fill_preset("测试问题")
    assert dialog.input_box.text() == "测试问题"


# ---------- 模型名完全自定义 + 窗口自由度 ----------


def test_model_name_is_free_text_input(dialog):
    from PySide6.QtCore import QSettings

    assert hasattr(dialog, "model_edit")
    assert not hasattr(dialog, "model_combo")
    assert "完全自定义" in dialog.model_edit.placeholderText()

    settings = QSettings("QA-Tool", "LLM")
    old_model = settings.value("model", None)
    old_provider = settings.value("provider", None)
    try:
        dialog.model_edit.setText("my-own-model-42")
        dialog._apply_model_name()
        assert dialog.llm.model == "my-own-model-42"
    finally:
        for key, value in (("model", old_model), ("provider", old_provider)):
            if value is None:
                settings.remove(key)
            else:
                settings.setValue(key, value)


def test_agent_window_is_resizable_non_modal(dialog):
    from PySide6.QtCore import Qt

    flags = dialog.windowFlags()
    assert flags & Qt.WindowMaximizeButtonHint
    assert flags & Qt.WindowMinimizeButtonHint
    assert not dialog.isModal()
    assert dialog.minimumWidth() >= 860
    assert dialog.minimumHeight() >= 540
    assert dialog.isSizeGripEnabled()


def test_main_window_opens_reusable_non_modal_agent(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from ui.main_window import MainWindow

    monkeypatch.setattr(QMessageBox, "question",
                        lambda *args, **kwargs: QMessageBox.Yes)
    win = MainWindow()
    try:
        win._on_llm_assist()
        dlg = win._agent_dialog
        assert dlg is not None and dlg.isVisible()
        assert not dlg.isModal()
        win._on_llm_assist()                       # 再次点击复用同一个窗口
        assert win._agent_dialog is dlg
    finally:
        if win._agent_dialog is not None:
            win._agent_dialog.close()
        win.close()


# ---------- 流式渲染（单气泡内逐字追加）----------


def _table_count(dialog) -> int:
    return dialog.chat_view.toHtml().count("<table")


def test_streaming_tokens_stay_in_single_bubble(dialog):
    from core.agent.engine import AgentReply

    before = _table_count(dialog)
    for token in ("你", "好", "，", "世", "界"):
        dialog._on_token(token)

    assert _table_count(dialog) == before + 1          # 只新建一个回答框
    plain = dialog.chat_view.toPlainText()
    assert "你好，世界" in plain
    assert plain.count("你好，世界") == 1              # 无重复/残留片段

    dialog._on_replied(AgentReply(text="你好，世界", offline=True))
    assert _table_count(dialog) == before + 1          # 收尾不追加第二个框
    assert dialog.send_btn.isEnabled()


def test_streaming_no_partial_bubble_residue(dialog):
    for token in ("流式", "渲染", "测试"):
        dialog._on_token(token)
    plain = dialog.chat_view.toPlainText()
    assert plain.count("流式") == 1
    assert plain.count("渲染") == 1
    assert "流式渲染测试" in plain


def test_second_stream_starts_new_bubble(dialog):
    dialog.append_msg("user", "第二问", markdown=False)
    before = _table_count(dialog)
    dialog._current_ai_msg = ""
    dialog._streaming_started = False
    dialog._stream_anchor = None

    for token in ("回", "答"):
        dialog._on_token(token)

    assert _table_count(dialog) == before + 1
    assert "回答" in dialog.chat_view.toPlainText()


def test_worker_streaming_renders_single_bubble(dialog):
    """真实 Worker/信号链路：逐字 token 必须收敛到同一个回答框。"""

    class _FakeLLM:
        provider = "ollama"
        model = "fake-stream"
        api_base = "http://localhost:11434"
        available = True

        def generate(self, prompt, model=None):
            for ch in "逐字输出测试":
                yield ch

    dialog.engine.set_llm(_FakeLLM())
    before = _table_count(dialog)
    dialog.input_box.setText("请流式回答")
    dialog._send_message()

    assert _pump_until(lambda: dialog.send_btn.isEnabled()
                       and not dialog._streaming_started)
    plain = dialog.chat_view.toPlainText()
    assert "逐字输出测试" in plain
    assert plain.count("逐字输出测试") == 1
    # 用户提问 1 个气泡 + AI 回答 1 个气泡（而非每个 token 一个）
    assert _table_count(dialog) == before + 2


# ---------- 端到端（离线工具模式）----------


def test_offline_conversation_end_to_end(dialog):
    dialog.input_box.setText("用当前数据做过程能力分析 USL=20.4 LSL=19.6")
    dialog._send_message()
    assert _pump_until(lambda: dialog.worker is None or not dialog.worker.isRunning())
    QApplication.instance().processEvents()
    plain = dialog.chat_view.toPlainText()
    assert "run_capability" in plain
    assert "Cpk" in plain
    assert dialog.send_btn.isEnabled() is True
    assert "完成（离线工具模式）" in plain


def test_busy_guard_blocks_second_send(dialog):
    class FakeWorker:
        def isRunning(self):
            return True

    dialog.worker = FakeWorker()
    dialog._send_message()
    assert "正在生成回复" in dialog.chat_view.toPlainText()


def test_kb_search_reports_without_crash(dialog):
    dialog.kb_input.setText("GRR 判定")
    dialog._kb_search()          # 知识库可用/不可用都不应抛异常
    assert dialog.chat_view.toPlainText()


def test_export_history_writes_markdown(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    dialog.engine.conversation.add_user("导出测试")
    target = tmp_path / "chat.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "md")))
    dialog._export_history()
    assert target.exists() and "导出测试" in target.read_text(encoding="utf-8")


# ---------- 上下文桥接 ----------


def test_build_context_without_main_window():
    ctx = build_context(None)
    assert ctx.data_frames == {}
    assert ctx.summary().startswith("数据表 0 张")


def test_build_context_from_main_window():
    from ui.main_window import MainWindow

    win = MainWindow()
    try:
        win.current_data = {"raw_data": {"Sheet1": pd.DataFrame({"a": [1, 2, 3]})}}
        ctx = build_context(win)
        assert "Sheet1" in ctx.data_frames
        assert ctx.project_context is not None           # 五链接入
        assert ctx.journal is not None and ctx.downtime is not None
        assert ctx.knowledge is not None
    finally:
        win.close()


def test_build_engine_default_registry():
    engine, ctx = build_engine(None, llm=None)
    assert engine.tool_count() >= 16
    assert engine.llm_available is False
    assert engine.provider_label() == "离线"


# ---------- P2: BYOK 供应商选择与隐私门 ----------


def _cloud_client():
    """真实 LLMClient（云供应商），只把 generate 换成假实现，避免联网。"""
    from core.llm_client import LLMClient

    client = LLMClient(provider="deepseek", api_key="sk-test-key",
                       model="deepseek-chat")
    client.calls = []

    def fake_generate(prompt, model=None):
        client.calls.append(prompt)
        yield "云端回答"

    client.generate = fake_generate
    return client


@pytest.fixture
def cloud_dialog(ctx, tmp_path, monkeypatch):
    """带云供应商（未授权）的对话窗口 + 隔离配置存储。"""
    import config.settings as settings

    target = tmp_path / "user_config.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "_USER_CONFIG_PATH", str(target))
    monkeypatch.setattr(settings, "_defaults", {})
    monkeypatch.setattr(settings, "_user_overrides", {})

    engine = AgentEngine(build_default_registry(ctx), llm=_cloud_client(), context=ctx)
    dlg = QAMHarnessDialog(None, engine=engine)
    yield dlg, engine
    dlg.worker = None
    dlg.close()
    dlg.deleteLater()


def test_provider_combo_lists_all_byok_vendors(cloud_dialog):
    dlg, _engine = cloud_dialog
    providers = [dlg.provider_combo.itemData(i)
                 for i in range(dlg.provider_combo.count())]
    assert providers == ["ollama", "openai", "anthropic", "google",
                         "deepseek", "zai", "kimi", "custom"]
    assert dlg.provider_combo.currentData() == "deepseek"      # 跟随引擎


def test_unconfigured_provider_is_marked(cloud_dialog):
    dlg, _engine = cloud_dialog
    labels = [dlg.provider_combo.itemText(i) for i in range(dlg.provider_combo.count())]
    assert any("未配置密钥" in t for t in labels)              # 云供应商未配置提示
    assert "未配置密钥" in dlg.privacy_note


def test_privacy_gate_blocks_and_can_grant(cloud_dialog, monkeypatch):
    dlg, engine = cloud_dialog
    from ui.dialogs import privacy_dialog as pmod
    from core.agent.privacy import needs_consent

    assert needs_consent("deepseek") is True
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__",
                        _stub_privacy(consent=True))
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)
    dlg.input_box.setText("问一句")
    dlg._send_message()
    assert _pump_until(lambda: dlg.worker is None or not dlg.worker.isRunning())
    QApplication.instance().processEvents()
    assert needs_consent("deepseek") is False               # 同意后已记录
    assert len(engine.llm.calls) == 1                       # 已调用云 API
    assert "云端回答" in dlg.chat_view.toPlainText()


def test_privacy_gate_local_only(cloud_dialog, monkeypatch):
    dlg, engine = cloud_dialog
    from ui.dialogs import privacy_dialog as pmod

    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__",
                        _stub_privacy(local_only=True))
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)
    dlg.input_box.setText("用当前数据做过程能力分析 USL=20.4 LSL=19.6")
    dlg._send_message()
    assert _pump_until(lambda: dlg.worker is None or not dlg.worker.isRunning())
    QApplication.instance().processEvents()
    plain = dlg.chat_view.toPlainText()
    assert "仅使用本地工具" in plain
    assert engine.llm.calls == []                           # 云 API 未被调用
    assert "run_capability" in plain                        # 已降级本地工具
    assert engine.force_offline is False                    # 当次标记已复位


def test_local_only_blocks_even_after_consent(cloud_dialog, monkeypatch):
    """审查发现: force_offline 曾在 worker 启动后立即复位 → 仍会发出云调用。"""
    dlg, engine = cloud_dialog
    from ui.dialogs import privacy_dialog as pmod
    from core.agent import privacy

    # 云开关已开（引擎的"云调用关闭"闸门不再拦），但尚未授权 → 隐私门仍会弹出
    privacy.set_cloud_enabled(True)
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__",
                        _stub_privacy(local_only=True))
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)
    dlg.input_box.setText("用当前数据做过程能力分析 USL=20.4 LSL=19.6")
    dlg._send_message()
    assert _pump_until(lambda: dlg.worker is None or not dlg.worker.isRunning())
    QApplication.instance().processEvents()
    assert engine.llm.calls == []               # 选"仅本地"后必须零云调用
    assert "仅使用本地工具" in dlg.chat_view.toPlainText()
    # 工作线程确实读到了 force_offline（引擎侧拒绝语），而非仅 UI 提示
    assert "已按你的选择" in dlg.chat_view.toPlainText()
    assert engine.force_offline is False        # 当次标记已复位


def test_consent_granted_skips_gate_next_time(cloud_dialog, monkeypatch):
    """只拦一次: 已授权后不再弹窗，直接走云调用。"""
    dlg, engine = cloud_dialog
    from ui.dialogs import privacy_dialog as pmod
    from core.agent import privacy

    privacy.set_cloud_enabled(True)
    privacy.grant_consent("deepseek")
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__", _stub_privacy())
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)
    dlg.input_box.setText("解释一下 Cpk")
    dlg._send_message()
    assert _pump_until(lambda: dlg.worker is None or not dlg.worker.isRunning())
    QApplication.instance().processEvents()
    assert len(engine.llm.calls) == 1           # 直接云调用，未再次拦截


def test_privacy_gate_cancel_aborts(cloud_dialog, monkeypatch):
    dlg, _engine = cloud_dialog
    from ui.dialogs import privacy_dialog as pmod

    monkeypatch.setattr(pmod.CloudPrivacyDialog, "__init__", _stub_privacy())
    monkeypatch.setattr(pmod.CloudPrivacyDialog, "exec", lambda self: 0)
    dlg.input_box.setText("问一句")
    dlg._send_message()
    assert dlg.worker is None
    assert dlg.input_box.text() == "问一句"                 # 输入保留，便于改问法


def _stub_privacy(consent: bool = False, local_only: bool = False):
    """伪造隐私弹窗构造函数（避免真实模态对话框）。"""
    def init(self, *args, **kwargs):
        self.consent = consent
        self.use_local_only = local_only
        self.preview = None
    return init
