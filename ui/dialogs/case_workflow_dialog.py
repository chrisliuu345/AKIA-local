"""改善案例工作台（v4.2.0 P5）— 展示案例脊柱的执行轨迹并可导出 Markdown。"""

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QMessageBox, QTextBrowser, QVBoxLayout,
)

from core.case_workflow import PHASE_LABELS, PHASES


class CaseWorkflowDialog(QDialog):
    """只读工作台：阶段进度 + 逐步留痕 + 导出。"""

    def __init__(self, workflow, parent=None):
        super().__init__(parent)
        self.workflow = workflow
        self.setWindowTitle(f"改善案例工作台 — {workflow.case.title}")
        self.resize(880, 640)

        layout = QVBoxLayout(self)
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(False)
        self.browser.setMarkdown(self._build_text())
        layout.addWidget(self.browser)

        buttons = QDialogButtonBox(self)
        self.export_button = buttons.addButton("导出 Markdown",
                                               QDialogButtonBox.ActionRole)
        buttons.addButton("关闭", QDialogButtonBox.RejectRole)
        self.export_button.clicked.connect(self._export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_text(self) -> str:
        done = {step.get("phase") for step in self.workflow.case.steps}
        progress = "  ".join(
            f"{'✅' if phase in done else '⬜'} {PHASE_LABELS[phase]}"
            for phase in PHASES)
        missing = "、".join(PHASE_LABELS[p] for p in self.workflow.missing_phases()) or "无"
        return (f"{progress}\n\n待补阶段：{missing}\n\n"
                + self.workflow.to_markdown())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出改善案例", f"{self.workflow.case.id}.md", "Markdown (*.md)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.workflow.to_markdown())
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))
            return
        QMessageBox.information(self, "导出完成", f"已导出：{path}")
