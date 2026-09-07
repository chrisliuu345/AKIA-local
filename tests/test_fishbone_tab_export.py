"""鱼骨图导出 PNG — 清晰度/边界自适应/防裁切 + Tab 按钮流程"""

from PySide6.QtGui import QImage, QColor
from ui.widgets.fishbone_canvas import FishboneCanvas, BG_COLOR
from analysis.quality.fishbone import FishboneEngine


def _default_branches(problem: str = "螺纹孔孔径偏大"):
    return FishboneEngine().create_default(problem)


def _bg(pixel) -> bool:
    """像素是否为画布底色"""
    return (QColor(pixel).red() == BG_COLOR.red()
            and QColor(pixel).green() == BG_COLOR.green()
            and QColor(pixel).blue() == BG_COLOR.blue())


def _strip_has_content(img: QImage, strip_frac: float, from_left: bool) -> bool:
    """检查图像一侧 strip_frac 宽的条带内是否存在非底色内容像素"""
    w = img.width()
    x_start = 0 if from_left else int(w * (1 - strip_frac))
    x_end = int(w * strip_frac) if from_left else w
    for x in range(x_start, x_end, 4):
        for y in range(0, img.height(), 4):
            if not _bg(img.pixel(x, y)):
                return True
    return False


class TestCanvasExportPng:
    def test_empty_scene_returns_false(self, tmp_path):
        canvas = FishboneCanvas()
        assert canvas.export_png(str(tmp_path / "empty.png")) is False
        assert not (tmp_path / "empty.png").exists()

    def test_export_hires_clear_and_fills_area(self, tmp_path):
        canvas = FishboneCanvas()
        canvas.render_fishbone(_default_branches(), "螺纹孔孔径偏大")
        out = tmp_path / "fishbone.png"
        assert canvas.export_png(str(out)) is True
        img = QImage(str(out))
        assert not img.isNull()
        assert img.width() >= 2000 and img.height() >= 800, \
            f"导出分辨率不足: {img.width()}x{img.height()}"

        # 内容自适应: 尺寸比例 ≈ 内容bbox+留白比例(不裁剪、不留大片空白)
        src = canvas._scene.itemsBoundingRect().adjusted(-80, -80, 80, 80)
        aspect = img.width() / img.height()
        exp_aspect = src.width() / src.height()
        assert abs(aspect - exp_aspect) / exp_aspect < 0.05, \
            f"宽高比失真: {aspect:.2f} vs {exp_aspect:.2f}"

        # 非空: 中心区域有脊骨/内容像素
        cx, cy = img.width() // 2, img.height() // 2
        assert any(not _bg(img.pixel(x, cy)) for x in range(cx - 200, cx + 200, 4)), \
            "图像中心无内容(疑似空白导出)"
        # 四周非大片空白: 内容应铺满绝大部分区域
        assert _strip_has_content(img, 0.30, True), "左 30% 无内容"
        assert _strip_has_content(img, 0.30, False), "右 30% 无内容"
        total = sample = 0
        for x in range(0, img.width(), 8):
            for y in range(0, img.height(), 8):
                sample += 1
                if not _bg(img.pixel(x, y)):
                    total += 1
        assert 0.02 < total / sample < 0.9, f"内容占比异常: {total / sample:.2%}"

    def test_dragged_out_node_not_clipped(self, tmp_path):
        """节点拖出原场景区后仍完整导出(回归: 按内容边界而非固定 sceneRect)"""
        canvas = FishboneCanvas()
        canvas.render_fishbone(_default_branches(), "问题")
        assert canvas._causes, "默认 6M 应生成原因节点"
        cause = canvas._causes[0]
        canvas._scene.setSceneRect(canvas._scene.sceneRect())  # 固定场景区
        # 拖出场景右边很远
        cause.label.setPos(2500, 350)
        cause._on_label_moved()

        out = tmp_path / "dragged.png"
        assert canvas.export_png(str(out)) is True
        img = QImage(str(out))
        assert not img.isNull()
        # 右缘条带内必须有内容像素(拖出的节点+连线)
        assert _strip_has_content(img, 0.06, False), "拖出场景区的节点被裁切"


class TestFishboneTabExportButton:
    def _make_tab(self):
        from ui.tabs.fishbone_tab import FishboneTab
        return FishboneTab()

    def test_cancel_no_error(self, monkeypatch):
        tab = self._make_tab()
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: ("", "")))
        tab._on_export_png()  # 不抛错即可

    def test_export_via_tab(self, tmp_path, monkeypatch):
        tab = self._make_tab()
        target = str(tmp_path / "tab_fishbone.png")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (target, "PNG 图片 (*.png)")))
        tab._on_export_png()
        assert tmp_path.joinpath("tab_fishbone.png").exists()
        assert tmp_path.joinpath("tab_fishbone.png").stat().st_size > 0

    def test_export_button_present(self):
        tab = self._make_tab()
        assert tab.btn_export is not None
        assert "导出图片" in tab.btn_export.text()

    def test_problem_box_default_not_empty(self):
        """空问题回退默认文本, 杜绝空白方框"""
        tab = self._make_tab()
        assert tab.canvas.problem_text() == "质量问题"

    def test_problem_edited_syncs_to_input(self, monkeypatch):
        """双击方框编辑 → 顶部问题输入框同步"""
        tab = self._make_tab()
        monkeypatch.setattr(
            "ui.widgets.fishbone_canvas.QInputDialog.getText",
            staticmethod(lambda *a, **k: ("孔径超差问题", True)))
        box = tab.canvas._problem_box
        box.mouseDoubleClickEvent(None)
        assert tab.canvas.problem_text() == "孔径超差问题"
        assert tab.problem_input.text() == "孔径超差问题"


class TestEightDD4Fishbone:
    def _make_tab(self):
        from ui.tabs.eight_d_tab import EightDTab
        return EightDTab()

    def _d4_widgets(self, tab):
        return tab._w.get("d4_root"), tab._w.get("d4_fishbone")

    def test_d4_initial_box_has_default_text(self):
        """8D D4 初始: 方框不为空(有回退文本), 可直接读取"""
        tab = self._make_tab()
        root_edit, canvas = self._d4_widgets(tab)
        assert canvas is not None
        assert canvas.problem_text(), "问题框为空"
        assert root_edit is not None

    def test_d4_root_typing_live_syncs_problem_box(self):
        """确认根因输入 → 方框文字实时更新(此前不更新)"""
        tab = self._make_tab()
        root_edit, canvas = self._d4_widgets(tab)
        root_edit.setText("轴承磨损导致异响")
        assert canvas.problem_text() == "轴承磨损导致异响"

    def test_d4_box_edit_syncs_back_to_root(self, monkeypatch):
        """双击方框编辑 → 反写确认根因"""
        tab = self._make_tab()
        root_edit, canvas = self._d4_widgets(tab)
        monkeypatch.setattr(
            "ui.widgets.fishbone_canvas.QInputDialog.getText",
            staticmethod(lambda *a, **k: ("操作手法不一致", True)))
        canvas._problem_box.mouseDoubleClickEvent(None)
        assert root_edit.text() == "操作手法不一致"
        assert canvas.problem_text() == "操作手法不一致"

    def test_d4_export_png(self, tmp_path, monkeypatch):
        """D4 导出图片按钮流程: 文件生成且非空"""
        tab = self._make_tab()
        _, canvas = self._d4_widgets(tab)
        assert canvas is not None
        target = str(tmp_path / "d4_fishbone.png")
        monkeypatch.setattr(
            "PySide6.QtWidgets.QFileDialog.getSaveFileName",
            staticmethod(lambda *a, **k: (target, "PNG 图片 (*.png)")))
        tab._export_d4_fishbone()
        assert tmp_path.joinpath("d4_fishbone.png").exists()
        assert tmp_path.joinpath("d4_fishbone.png").stat().st_size > 0

    def test_d4_export_button_present(self):
        tab = self._make_tab()
        from PySide6.QtWidgets import QPushButton
        assert any("导出图片" in b.text()
                   for b in tab.findChildren(QPushButton)), "D4 无导出图片按钮"

    def test_canvas_context_menu_has_export(self):
        """画布右键菜单含导出项(两处使用通用)"""
        from ui.widgets.fishbone_canvas import FishboneCanvas
        canvas = FishboneCanvas()
        canvas.render_fishbone(_default_branches(), "问题")
        import inspect
        src = inspect.getsource(type(canvas).contextMenuEvent)
        assert "导出为 PNG" in src
