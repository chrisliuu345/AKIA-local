"""主窗口模块级助手（v4.1.0 B4 从 main_window.py 拆出）。

包含：
  - Tab 数据/可运行性判定（批量分析用）
  - ``_CurrentPageStack``：共享滚动区只按当前页计算尺寸提示
  - ``_resolve_llm_client``：任意云供应商已配置密钥即静默通过，否则询问离线模式
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QStackedWidget


def _tab_has_data(tab) -> bool:
    """Tab 是否有可分析数据 — 不能用 not df 测试 DataFrame 真值 (恒抛 ValueError)"""
    df = getattr(tab, 'df', None)
    return df is not None and len(df) != 0


def _tab_is_runnable(tab) -> bool:
    """Tab 能否参与批量分析 — 有数据且定义了 run_and_display（文档型 Tab 无此方法）"""
    return _tab_has_data(tab) and callable(getattr(tab, 'run_and_display', None))


class _CurrentPageStack(QStackedWidget):
    """尺寸提示只跟随当前页的堆叠容器（共享 QScrollArea 专用）。

    QStackedWidget 默认取**所有页**尺寸提示的最大值：某个 Tab 运行分析后，
    即使已切换到其他 Tab，隐藏页的参数面板 / 数据表 / 图表残留仍会把共享
    滚动区撑长（滚动条不回落）。这里改为只返回当前页的提示值，隐藏页不再
    影响布局；页内高度仍由各 Tab 自身的 min hint 与脚本化 pin 控制。
    """

    def sizeHint(self):
        current = self.currentWidget()
        return current.sizeHint() if current is not None else super().sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        if current is None:
            return super().minimumSizeHint()
        hint = current.minimumSizeHint()
        return hint if hint.isValid() else current.sizeHint()


def _resolve_llm_client(parent=None):
    """检测可用 LLM 连接；任意云供应商已配置密钥即静默通过。

    完全没有可用连接时询问是否以离线工具模式打开（取消返回 None）。
    """
    from core.llm_client import LLMClient

    client = LLMClient.detect_available()
    if client.available:
        return client
    reply = QMessageBox.question(
        parent, "QAM Harness",
        "未检测到可用的 LLM 连接（本地 Ollama 未运行，且未配置任何云 API Key）。\n\n"
        "离线工具模式仍然可用: QAM Harness 会直接调用软件内分析引擎"
        "（SPC / 过程能力 / MSA / OEE / 成本 / 告警 / 五链 / 知识库），"
        "给出数值结论与改善建议。\n\n"
        "需要自然语言长文解读时:\n"
        "1. 访问 https://ollama.com 下载安装（ollama pull qwen2.5:7b && ollama serve），或\n"
        "2. 菜单「工具 → 设置 → QAM Harness」配置云供应商 API Key\n\n"
        "是否打开 QAM Harness？",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
    )
    return client if reply == QMessageBox.Yes else None
