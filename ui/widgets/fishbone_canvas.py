"""交互式鱼骨图画布 — 节点拖动/分支联动/文字背景框/滚轮缩放"""

from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem,
    QMenu, QInputDialog,
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import (
    QPen, QBrush, QColor, QFont, QPainter, QPolygonF, QPainterPath,
    QImage,
)
from ui.font_config import get_ui_font


M6_COLORS = [
    QColor("#4da6ff"), QColor("#ff6b6b"), QColor("#51cf66"),
    QColor("#ffa726"), QColor("#cc5de8"), QColor("#20c997"),
]
BG_COLOR = QColor("#262632")
TEXT_COLOR = QColor("#e1e2e6")
MUTED_COLOR = QColor("#a0a3ae")


class _LabelNode(QGraphicsItem):
    """文字 + 半透明圆角背景框, 可拖动, 双击编辑"""

    def __init__(self, text: str, font_size: int = 10, bold: bool = False,
                 color: QColor = TEXT_COLOR):
        super().__init__()
        self._text = text
        self._font = QFont(get_ui_font(), font_size)
        self._font.setBold(bold)
        self._color = color
        self._padding = 6
        self._radius = 6
        self._on_moved = None
        self._on_edited = None

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.OpenHandCursor)
        self._calc_rect()

    def _calc_rect(self):
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        tw = fm.horizontalAdvance(self._text)
        th = fm.height()
        self._text_w = tw
        self._text_h = th
        self._w = tw + self._padding * 2
        self._h = th + self._padding

    def setText(self, text: str):
        self._text = text
        self._calc_rect()
        self.update()

    def text(self) -> str:
        return self._text

    def boundingRect(self):
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter, option, widget):
        r = self.boundingRect()
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        painter.fillPath(path, QBrush(QColor(30, 30, 42, 220)))
        pen = QPen(QColor(70, 70, 85), 1)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.setFont(self._font)
        painter.setPen(self._color)
        painter.drawText(r.adjusted(self._padding, 0, -self._padding, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, self._text)

    def mouseDoubleClickEvent(self, event):
        text, ok = QInputDialog.getText(None, "编辑", "文本:", text=self._text)
        if ok and text.strip():
            self.setText(text.strip())
            if self._on_edited:
                self._on_edited(text.strip())
        if event is not None:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            if self._on_moved:
                self._on_moved()
        return super().itemChange(change, value)

    def center(self) -> QPointF:
        return self.pos() + QPointF(self._w / 2, self._h / 2)

    def top_center(self) -> QPointF:
        return self.pos() + QPointF(self._w / 2, 0)

    def bottom_center(self) -> QPointF:
        return self.pos() + QPointF(self._w / 2, self._h)

    def left_center(self) -> QPointF:
        return self.pos() + QPointF(0, self._h / 2)

    def right_center(self) -> QPointF:
        return self.pos() + QPointF(self._w, self._h / 2)


class _ProblemBox(QGraphicsRectItem):
    """问题描述框(脊骨箭头指向的最终结果) — 双击可编辑, 宽度随文字自适应"""

    def __init__(self, x, y, text: str):
        self._on_edited = None
        self._text = text or ""
        self._h = 38
        self._x = x
        self._y = y
        w = self._fit_width()
        super().__init__(x, y - self._h / 2, w, self._h)
        self.setBrush(QBrush(QColor("#363648")))
        self.setPen(QPen(QColor("#4da6ff"), 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setCursor(Qt.IBeamCursor)

        self.label = QGraphicsTextItem(self._text, self)
        self.label.setFont(QFont(get_ui_font(), 13, QFont.Bold))
        self.label.setDefaultTextColor(TEXT_COLOR)
        self.label.setAcceptedMouseButtons(Qt.NoButton)
        self._place_label()

    def _fit_width(self) -> float:
        """按文字宽度自适应框宽(最小 170)"""
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(QFont(get_ui_font(), 13, QFont.Bold))
        tw = fm.horizontalAdvance(self._text)
        return max(170.0, tw + 24)

    def _place_label(self):
        """文字在框内垂直居中, 左对齐 + 8px 内边距
        (子项坐标 == 场景坐标: item 原点 (0,0); 框左上角在 (x, y-h/2))"""
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.label.font())
        th = fm.height()
        self.label.setPos(self._x + 8, self._y - self._h / 2 + (self._h - th) / 2)

    def set_problem(self, text: str):
        text = text or ""
        if text == self._text:
            return
        self._text = text
        w = self._fit_width()
        self.setRect(self._x, self._y - self._h / 2, w, self._h)
        self.label.setPlainText(text)
        self._place_label()
        self.update()

    def text(self) -> str:
        return self._text

    def mouseDoubleClickEvent(self, event):
        text, ok = QInputDialog.getText(None, "编辑问题", "问题描述:", text=self._text)
        if ok:
            self.set_problem(text.strip())
            if self._on_edited:
                self._on_edited(self._text)
        if event is not None:
            super().mouseDoubleClickEvent(event)


class _CauseSpike:
    """通用原因刺: 锚点在父对象上 → 标签框, 支持 3 层嵌套"""

    def __init__(self, scene, parent, t: float, label: str, color: QColor,
                 level: int = 1):
        self.scene = scene
        self.parent = parent
        self.t = t
        self._color = color
        self._level = level
        self._side = 1
        self._children: list[_CauseSpike] = []

        fs = max(8, 10 - level)
        self.line = QGraphicsLineItem()
        self.line.setPen(QPen(color, max(1.0, 2.0 - level * 0.5)))
        scene.addItem(self.line)

        self.label = _LabelNode(label, font_size=fs, color=QColor("#d0d2d8"))
        self.label._on_moved = self._on_label_moved
        self.label._on_edited = self._on_label_changed
        scene.addItem(self.label)

    def add_child(self, label_text: str, t: float, side: int) -> "_CauseSpike":
        child = _CauseSpike(self.scene, self, t, label_text, self._color,
                           level=self._level + 1)
        child._side = side
        child._reposition()
        self._children.append(child)
        return child

    def _parent_anchor(self) -> tuple:
        """父对象上的锚点坐标"""
        if isinstance(self.parent, _Branch):
            bl = self.parent.line
            x1, y1 = bl.line().x1(), bl.line().y1()
            x2, y2 = bl.line().x2(), bl.line().y2()
            return (x1 + self.t * (x2 - x1), y1 + self.t * (y2 - y1))
        pl = self.parent.label
        pc = pl.center()
        bw, _bh = pl.boundingRect().width(), pl.boundingRect().height()
        side = self._side
        return (pc.x() + side * bw * 0.5, pc.y())

    def _update_line(self):
        """线: 父锚点 → 当前标签框边缘"""
        ax, ay = self._parent_anchor()
        lc = self.label.center()
        dx, dy = lc.x() - ax, lc.y() - ay
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            length = 1
        bw, bh = self.label.boundingRect().width(), self.label.boundingRect().height()
        ex = lc.x() - dx / length * (bw / 2 + 6)
        ey = lc.y() - dy / length * (bh / 2 + 6)
        self.line.setLine(ax, ay, ex, ey)

    def _reposition(self):
        """计算初始位置: 从父锚点垂直偏移（基于父对象的实际方向）"""
        ax, ay = self._parent_anchor()
        side = self._side
        length = 60 - self._level * 8
        bw = self.label.boundingRect().width()
        bh = self.label.boundingRect().height()

        if isinstance(self.parent, _Branch):
            bl = self.parent.line
            dx = bl.line().x2() - bl.line().x1()
            dy = bl.line().y2() - bl.line().y1()
            plen = (dx * dx + dy * dy) ** 0.5
            if plen > 0.001:
                perp_x = -dy / plen
                perp_y = dx / plen
            else:
                perp_x, perp_y = 0, 1
        else:
            lc = self.parent.label.center()
            dx = lc.x() - ax
            dy = lc.y() - ay
            plen = (dx * dx + dy * dy) ** 0.5
            if plen > 0.001:
                perp_x = dy / plen
                perp_y = -dx / plen
            else:
                perp_x, perp_y = 0, 1

        self.label.setPos(ax + perp_x * length * side - bw / 2,
                          ay + perp_y * length * side - bh / 2)
        self._update_line()

    def update_anchor(self):
        """父对象移动后: 重算位置 + 线 + 递归子"""
        self._reposition()
        self._update_line()
        for c in self._children:
            c.update_anchor()

    def set_side(self, side: int):
        self._side = side

    def _on_label_moved(self):
        self._update_line()
        for c in self._children:
            c.update_anchor()

    def _on_label_changed(self, text: str):
        pass

    def remove(self):
        for c in self._children:
            c.remove()
        self.scene.removeItem(self.line)
        self.scene.removeItem(self.label)


class _Branch:
    """主分支: 线从脊骨接点→标签, 标签拖动时线+所有子原因联动"""

    def __init__(self, scene, bx, by, label_text: str, color: QColor,
                 angle_up: bool):
        self.scene = scene
        self._bx = bx
        self._by = by
        self._color = color
        self._angle_up = angle_up
        self._causes: list[_CauseSpike] = []

        init_len = 190
        y_dir = -1 if angle_up else 1
        ex = bx - init_len * 0.82
        ey = by + y_dir * init_len * 0.52

        self.line = QGraphicsLineItem(bx, by, ex, ey)
        self.line.setPen(QPen(color, 3))
        scene.addItem(self.line)

        self.label = _LabelNode(label_text, font_size=11, bold=True, color=color)
        self.label.setPos(ex - self.label.boundingRect().width() / 2,
                          ey - self.label.boundingRect().height() / 2)
        self.label._on_moved = self._on_label_moved
        scene.addItem(self.label)

    def add_cause(self, label_text: str, t: float, side: int) -> _CauseSpike:
        spike = _CauseSpike(self.scene, self, t, label_text, self._color)
        spike.set_side(side)
        spike._reposition()
        self._causes.append(spike)
        return spike

    def _on_label_moved(self):
        """标签拖动 → 线跟随 + 所有子原因重算锚点"""
        lc = self.label.center()
        self.line.setLine(self._bx, self._by, lc.x(), lc.y())
        for c in self._causes:
            c.update_anchor()

    def remove(self):
        for c in self._causes:
            c.remove()
        self.scene.removeItem(self.line)
        self.scene.removeItem(self.label)


class FishboneCanvas(QGraphicsView):
    """交互式鱼骨图: 滚轮缩放 + 中键/右键拖拽平移"""

    node_added = Signal(str, str)
    node_deleted = Signal(str)
    zoom_changed = Signal()
    problem_edited = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.setMinimumHeight(350)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._branches: list[_Branch] = []
        self._causes: list[_CauseSpike] = []
        self._problem_box: _ProblemBox = None
        self._panning = False
        self._pan_start = QPointF()
        self._zoom_level = 1.0

    def render_fishbone(self, branches: dict, problem: str = "质量问题"):
        self._scene.clear()
        self._branches.clear()
        self._causes.clear()
        self._problem_box = None

        problem = (problem or "").strip() or "质量问题"
        n = len(branches)
        if n == 0:
            t = self._scene.addText("请添加分析分支", QFont(get_ui_font(), 14))
            t.setDefaultTextColor(MUTED_COLOR)
            return

        colors = M6_COLORS[:n] if n <= len(M6_COLORS) else M6_COLORS * 2

        w, h = 1200, 700
        self._scene.setSceneRect(-20, -20, w + 40, h + 40)
        cx, cy = w / 2, h / 2

        spine_x1, spine_x2 = cx - 380, cx + 260
        spine = QGraphicsLineItem(spine_x1, cy, spine_x2, cy)
        spine.setPen(QPen(MUTED_COLOR, 3))
        self._scene.addItem(spine)
        arrow = QPolygonF([
            QPointF(spine_x2, cy), QPointF(spine_x2 - 14, cy - 7),
            QPointF(spine_x2 - 14, cy + 7),
        ])
        path = QPainterPath()
        path.addPolygon(arrow)
        self._scene.addPath(path, QPen(Qt.NoPen), QBrush(MUTED_COLOR))

        pb = _ProblemBox(spine_x2 + 10, cy, problem)
        pb._on_edited = self.problem_edited.emit
        self._problem_box = pb
        self._scene.addItem(pb)

        bx_spacing = (spine_x2 - 80 - spine_x1 - 60) / max(n - 1, 1) if n > 1 else 0
        bx_start = spine_x1 + 70

        for i, (bname, root) in enumerate(branches.items()):
            color = colors[i % len(colors)]
            bx = bx_start + i * bx_spacing if n > 1 else cx - 50
            angle_up = (i % 2 == 0)

            branch = _Branch(self._scene, bx, cy, bname, color, angle_up)
            self._branches.append(branch)

            sub_count = len(root.children)
            for j, child in enumerate(root.children):
                t = (j + 1) / (sub_count + 1)
                side = 1 if j % 2 == 0 else -1
                spike = branch.add_cause(child.name, t, side)
                self._causes.append(spike)

                self._render_children(spike, child, side)

        self.fitInView(self._scene.sceneRect().adjusted(-30, -30, 60, 60),
                       Qt.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

    def set_problem(self, text: str):
        """就地更新问题框文字(不重建场景, 不重置节点位置/缩放)"""
        if self._problem_box is not None:
            self._problem_box.set_problem(text)

    def problem_text(self) -> str:
        return self._problem_box.text() if self._problem_box is not None else ""

    def export_png(self, path: str, target_longest: int = 3200,
                   margin: float = 80.0) -> bool:
        """将整幅鱼骨图导出为高清 PNG。

        以实际内容边界(itemsBoundingRect, 含被拖出场景区的节点) + 留白作为源区域,
        等比渲染到最长边 target_longest 像素(不低于 2x), 直接 scene.render,
        不受当前视口缩放/平移影响 —— 不会裁切、不会留大片空白。
        """
        if not self._scene.items():
            return False
        content = self._scene.itemsBoundingRect()
        src = content.adjusted(-margin, -margin, margin, margin)
        longest = max(src.width(), src.height())
        scale = max(2.0, target_longest / longest if longest > 0 else 1.0)
        w, h = max(1, int(src.width() * scale)), max(1, int(src.height() * scale))

        img = QImage(w, h, QImage.Format_RGB32)
        img.fill(BG_COLOR)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        try:
            self._scene.render(painter, QRectF(0, 0, w, h), src)
        finally:
            painter.end()
        return img.save(path, "PNG")

    def _render_children(self, parent_spike: _CauseSpike, node,
                         side: int, depth: int = 1):
        """W73: 递归渲染子原因 (最多 3 层, depth 1=第2层, depth 2=第3层)"""
        MAX_DEPTH = 2
        MAX_CAUSES_PER_LEVEL = 20
        if depth > MAX_DEPTH or not node.children:
            return
        n = min(len(node.children), MAX_CAUSES_PER_LEVEL)
        for k in range(n):
            gc = node.children[k]
            t = (k + 1) / (n + 1)
            s = 1 if k % 2 == 0 else -1
            child = parent_spike.add_child(gc.name, t, s)
            self._causes.append(child)
            self._render_children(child, gc, s, depth + 1)

    def wheelEvent(self, event):
        """滚轮缩放"""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        self._zoom_level = self.transform().m11()
        self.zoom_changed.emit()

    def mousePressEvent(self, event):
        if event.button() in (Qt.MiddleButton, Qt.RightButton):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = QMenu(self)

        if isinstance(item, _LabelNode):
            edit_action = menu.addAction("编辑文本")
            delete_action = menu.addAction("删除此节点")
            menu.addSeparator()
            export_action = menu.addAction("导出为 PNG")
            action = menu.exec(event.globalPos())
            if action == edit_action:
                item.mouseDoubleClickEvent(None)
            elif action == delete_action:
                self._remove_node(item)
            elif action == export_action:
                self._export_dialog()
        else:
            add_action = menu.addAction("在此添加原因")
            reset_action = menu.addAction("重置缩放")
            menu.addSeparator()
            export_action = menu.addAction("导出为 PNG")
            action = menu.exec(event.globalPos())
            if action == add_action:
                sp = self.mapToScene(event.pos())
                text, ok = QInputDialog.getText(self, "添加原因", "原因描述:")
                if ok and text.strip():
                    node = _LabelNode(text.strip(), font_size=8)
                    node.setPos(sp)
                    self._scene.addItem(node)
            elif action == reset_action:
                self.fitInView(self._scene.sceneRect().adjusted(-30, -30, 60, 60),
                               Qt.KeepAspectRatio)
                self._zoom_level = self.transform().m11()
                self.zoom_changed.emit()
            elif action == export_action:
                self._export_dialog()

    def _export_dialog(self):
        """右键导出为高清 PNG"""
        if not self._scene.items():
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "导出鱼骨图", "fishbone.png", "PNG 图片 (*.png)")
        if path:
            self.export_png(path)

    def _remove_node(self, item: _LabelNode):
        for c in self._causes:
            if c.label is item:
                c.remove()
                self._causes.remove(c)
                self.node_deleted.emit(item.text())
                return
        self._scene.removeItem(item)
