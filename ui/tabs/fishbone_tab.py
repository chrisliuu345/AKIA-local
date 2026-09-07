"""鱼骨图分析 Tab — 交互式 QGraphicsView 画布 (拖动/双击编辑/右键删除)"""

from typing import Dict

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QSplitter,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.tabs.base_tab import BaseAnalysisTab
from ui.theme import BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.theme import colors as theme_colors
from ui.widgets.fishbone_canvas import FishboneCanvas
from ui.font_config import get_ui_font
from analysis.quality.fishbone import FishboneEngine


class FishboneTab(BaseAnalysisTab):
    def __init__(self, parent=None):
        self._engine = FishboneEngine()
        self._branches: Dict = {}
        self._problem = "质量问题"
        super().__init__(parent)
        self._setup_ui()
        self._new_analysis()

    def _setup_ui(self):
        tc = theme_colors()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.title_label = QLabel("鱼骨图 (石川图)")
        self.title_label.setFont(QFont(get_ui_font(), 18, QFont.Bold))
        layout.addWidget(self.title_label)
        layout.addSpacing(4)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {tc['border']}; }}")

        left = QWidget()
        left.setMinimumWidth(260)
        left.setMaximumWidth(360)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        prob_group = QGroupBox("问题描述")
        prob_layout = QFormLayout(prob_group)
        self.problem_input = QLineEdit(self._problem)
        self.problem_input.setFont(QFont(get_ui_font(), 12))
        self.problem_input.textChanged.connect(self._on_problem_changed)
        prob_layout.addRow("问题:", self.problem_input)
        left_layout.addWidget(prob_group)

        tree_group = QGroupBox("原因分析 (6M)")
        tree_layout = QVBoxLayout(tree_group)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["原因", ""])
        self.tree.setColumnWidth(0, 190)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(
            f"QTreeWidget {{ background: {tc['bg_card']}; "
            f"border: 1px solid {tc['border']}; border-radius: 4px; }}"
        )
        tree_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        btn_row1 = QHBoxLayout()
        btn_row2 = QHBoxLayout()
        btn_row1.setSpacing(4)
        btn_row2.setSpacing(4)
        tree_btn_layout = QVBoxLayout()
        tree_btn_layout.setSpacing(4)
        tree_btn_layout.addLayout(btn_row1)
        tree_btn_layout.addLayout(btn_row2)

        self.btn_add_branch = QPushButton("+ 分支")
        self.btn_add_branch.setStyleSheet(BUTTON_SECONDARY)
        self.btn_add_branch.setCursor(Qt.PointingHandCursor)
        self.btn_add_branch.clicked.connect(self._add_branch)
        btn_row1.addWidget(self.btn_add_branch)

        self.btn_add_cause = QPushButton("+ 子原因")
        self.btn_add_cause.setStyleSheet(BUTTON_SECONDARY)
        self.btn_add_cause.setCursor(Qt.PointingHandCursor)
        self.btn_add_cause.clicked.connect(self._add_cause)
        btn_row1.addWidget(self.btn_add_cause)

        self.btn_delete = QPushButton("删除")
        self.btn_delete.setStyleSheet(BUTTON_SECONDARY)
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_row2.addWidget(self.btn_delete)

        self.btn_reset = QPushButton("恢复 6M")
        self.btn_reset.setStyleSheet(BUTTON_SECONDARY)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._reset_6m)
        btn_row2.addWidget(self.btn_reset)

        tree_layout.addLayout(tree_btn_layout)

        self.btn_render = QPushButton("绘制鱼骨图")
        self.btn_render.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.btn_render.setCursor(Qt.PointingHandCursor)
        self.btn_render.clicked.connect(self._render)
        tree_layout.addWidget(self.btn_render)

        self.btn_export = QPushButton("导出图片")
        self.btn_export.setStyleSheet(BUTTON_SECONDARY)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._on_export_png)
        tree_layout.addWidget(self.btn_export)

        left_layout.addWidget(tree_group)
        splitter.addWidget(left)

        self.canvas = FishboneCanvas()
        self.canvas.problem_edited.connect(self.problem_input.setText)
        splitter.addWidget(self.canvas)

        splitter.setSizes([320, 750])
        layout.addWidget(splitter, 1)

    def _new_analysis(self):
        self._branches = self._engine.create_default(self._problem)
        self._rebuild_tree()
        self._render()

    def _on_problem_changed(self, text: str):
        self._problem = text or "质量问题"

    def _rebuild_tree(self):
        self.tree.clear()
        for bname, root in self._branches.items():
            branch_item = QTreeWidgetItem([bname, f"{self._count_children(root)}项"])
            branch_item.setData(0, Qt.UserRole, {"type": "branch"})
            branch_item.setFont(0, QFont(get_ui_font(), 10, QFont.Bold))
            self._add_tree_children(branch_item, root)
            self.tree.addTopLevelItem(branch_item)
        self.tree.expandAll()

    def _add_tree_children(self, parent_item, node):
        for child in node.children:
            item = QTreeWidgetItem([child.name, ""])
            item.setData(0, Qt.UserRole, {"type": "cause"})
            self._add_tree_children(item, child)
            parent_item.addChild(item)

    @staticmethod
    def _count_children(node) -> int:
        return len(node.children) + sum(
            FishboneTab._count_children(c) for c in node.children
        )

    def _add_branch(self):
        name, ok = QInputDialog.getText(self, "添加分支", "分支名称:")
        if ok and name.strip():
            from analysis.quality.fishbone import CauseNode

            self._branches[name.strip()] = CauseNode(name=name.strip(), level=0)
            self._rebuild_tree()
            self._render()

    def _add_cause(self):
        selected = self.tree.currentItem()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择一个分支或子原因")
            return
        name, ok = QInputDialog.getText(self, "添加子原因", "原因描述:")
        if ok and name.strip():
            bname = self._find_branch_name(selected)
            if bname and bname in self._branches:
                target = self._find_node_by_path(selected, bname)
                if target:
                    from analysis.quality.fishbone import CauseNode

                    new_level = target.level + 1 if not self._is_branch(selected) else 1
                    target.children.append(
                        CauseNode(name=name.strip(), level=min(new_level, 2))
                    )
            self._rebuild_tree()
            self._render()

    def _delete_selected(self):
        selected = self.tree.currentItem()
        if not selected:
            return
        bname = self._find_branch_name(selected)
        if bname is None:
            return
        if self._is_branch(selected):
            reply = QMessageBox.question(self, "确认删除", f"删除分支 '{bname}'?")
            if reply == QMessageBox.Yes:
                del self._branches[bname]
        else:
            parent_item = selected.parent()
            if parent_item:
                parent_node = self._find_node_by_path(parent_item, bname)
                if parent_node:
                    parent_node.children = [
                        c for c in parent_node.children if c.name != selected.text(0)
                    ]
        self._rebuild_tree()
        self._render()

    def _reset_6m(self):
        reply = QMessageBox.question(self, "恢复默认", "恢复为默认 6M 模板?")
        if reply == QMessageBox.Yes:
            self._branches = self._engine.create_default(self._problem)
            self._rebuild_tree()
            self._render()

    def _render(self):
        self.canvas.render_fishbone(self._branches, self._problem)
        self.analysis_completed.emit()

    def _on_export_png(self):
        if not self._branches:
            QMessageBox.information(self, "提示", "请先绘制鱼骨图")
            return
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "导出鱼骨图", "fishbone.png", "PNG 图片 (*.png)"
        )
        if path and not self.canvas.export_png(path):
            QMessageBox.warning(self, "导出失败", "图片保存失败，请重试")

    @staticmethod
    def _is_branch(item):
        data = item.data(0, Qt.UserRole)
        return data and data.get("type") == "branch"

    def _find_branch_name(self, item):
        while item:
            if self._is_branch(item):
                return item.text(0)
            item = item.parent()
        return None

    def _find_node_by_path(self, item, bname):
        if bname not in self._branches:
            return None
        path = []
        cur = item
        while cur and not self._is_branch(cur):
            path.insert(0, cur.text(0))
            cur = cur.parent()
        node = self._branches[bname]
        for name in path:
            found = next((c for c in node.children if c.name == name), None)
            if found is None:
                return None
            node = found
        return node
