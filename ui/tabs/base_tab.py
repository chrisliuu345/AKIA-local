"""BaseAnalysisTab — 所有分析 Tab 的共享基类"""

from typing import Any
from io import BytesIO
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem, QMenu, QApplication,
    QVBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QImage, QFont

from ui.theme import colors as theme_colors
from ui.font_config import get_ui_font


class BaseAnalysisTab(QWidget):
    export_clicked = Signal()
    analysis_completed = Signal()
    import_data_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df: pd.DataFrame = None
        self.parsed_info: dict[str, Any] = {}
        self.current_result: dict[str, Any] = {}
        self.current_figure = None
        self.canvas = None
        self._raw_data = {}
        self._data_parser = None
        self._empty_overlay: QWidget = None
        self._current_chart_type: str | None = None
        self._chart_options: dict[str, Any] = {}
        self._chart_editor_panel = None

    def _clear_canvas(self):
        """清空图表区域并释放 matplotlib 资源"""
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        import matplotlib.pyplot as plt
        if self.current_figure is not None:
            try:
                plt.close(self.current_figure)
            except Exception:
                pass
        self.canvas = None
        self.current_figure = None
        self._chart_toolbar = None

    def _render_figure(self, fig):
        """渲染图表 — 仅替换 canvas 一行，编辑面板/工具栏行保持原位，页面滚动稳定。
        每次渲染使用全新 canvas（QtAgg 不支持跨 figure 复用同一 canvas，否则残留像素乱码）"""
        old = self.current_figure
        self.current_figure = fig

        # 1) 作废旧 canvas（若在布局中则仅移除自身，不动其它行）
        if self.canvas is not None:
            idx = self.chart_layout.indexOf(self.canvas)
            if idx >= 0:
                item = self.chart_layout.takeAt(idx)
                w = item.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
            if self._chart_toolbar is not None:
                try:
                    self._chart_toolbar.hide()
                except Exception:
                    pass
                self._chart_toolbar = None

        # 2) 新 canvas 置于第一行
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        self.canvas = FigureCanvasQTAgg(fig)
        # 快照自然像素高 — 隐藏页渲染时布局会把 canvas 压小并同步改写 figure 尺寸,
        # _pin 改读快照保证 showEvent 恢复时高度不丢失
        self._canvas_natural_h = int(
            fig.get_size_inches()[1] * fig.get_dpi())
        self.chart_layout.insertWidget(0, self.canvas)

        # 3) 绑定菜单 + 工具栏(隐藏)/面板挂载 + 高度同步
        self._setup_chart_menu()
        self._add_chart_toolbar()
        self.canvas.draw()

        # 4) 释放旧图（先绘制新图再关闭，避免引用旧 figure 的绘制路径）
        if old is not None and old is not fig:
            import matplotlib.pyplot as plt
            try:
                plt.close(old)
            except Exception:
                pass

    def _switch_result_view(self, idx: int):
        self.btn_view_chart.setChecked(idx == 0)
        self.btn_view_data.setChecked(idx == 1)
        self.result_stack.setCurrentIndex(idx)

    def _on_save_png(self):
        self._on_save_figure("PNG 图片 (*.png)", "png", dpi=None)

    def _on_save_hires_png(self):
        self._on_save_figure("PNG 高清 300 DPI (*.png)", "png", dpi=300)

    def _on_save_svg(self):
        self._on_save_figure("SVG 矢量图 (*.svg)", "svg", dpi=None)

    def _on_save_figure(self, file_filter: str, fmt: str, dpi: int | None = None):
        """将当前图表导出为文件 — 与显示尺寸解耦（保存后还原画布）"""
        if not hasattr(self, 'current_figure') or self.current_figure is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出图表", f"chart.{fmt}", file_filter
        )
        if path:
            from config.settings import CHART_DPI, CHART_FIGSIZE
            fig = self.current_figure
            original_size = fig.get_size_inches()
            fig.set_size_inches(*CHART_FIGSIZE)
            try:
                fig.savefig(path, dpi=dpi or CHART_DPI, bbox_inches="tight")
            finally:
                fig.set_size_inches(*original_size)
                self.canvas.draw()

    def set_data(self, df: pd.DataFrame = None, parsed_info: dict[str, Any] | None = None):
        """设置分析数据（子类可重写以填充列选择器）"""
        self.df = df
        self.parsed_info = parsed_info or {}
        self._hide_empty_state()

    def set_raw_data(self, raw_data, data_parser):
        self._raw_data = raw_data
        self._data_parser = data_parser
        if not hasattr(self, 'sheet_combo') or self.sheet_combo is None:
            if raw_data and hasattr(self, 'set_data'):
                first_sheet = next(iter(raw_data.values()))
                if data_parser:
                    cleaned_df, info = data_parser.prepare(first_sheet)
                else:
                    cleaned_df, info = first_sheet, {}
                self.set_data(cleaned_df, info)
            return
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        if raw_data:
            self.sheet_combo.addItems(list(raw_data.keys()))
        self.sheet_combo.blockSignals(False)
        if self.sheet_combo.count() > 0:
            self.sheet_combo.setCurrentIndex(0)
            self._on_sheet_changed(self.sheet_combo.currentText())

    def _on_sheet_changed(self, sheet_name):
        if not sheet_name or not hasattr(self, '_raw_data') or not self._raw_data:
            return
        if sheet_name not in self._raw_data:
            return
        sdf = self._raw_data[sheet_name]
        dp = getattr(self, '_data_parser', None)
        if dp:
            cleaned_df, info = dp.prepare(sdf)
        else:
            cleaned_df, info = sdf, {}
        self.set_data(cleaned_df, info)

    def _populate_preview_table(self, df: pd.DataFrame, max_rows: int = 500):
        """填充数据预览表格。max_rows=500 默认限 500 行防止大数据阻塞 UI (W49)。

        注意：图表渲染采用智能系统抽样以保持可读性（详见 output/chart_engine.py），
        分析计算基于全量数据，仅在图表绘制时进行等距抽样 + 判异点强制保留。
        """
        n = min(max_rows, len(df))
        self.data_table.setRowCount(n)
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(list(df.columns))
        for i in range(n):
            for j, _col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.data_table.setItem(i, j, item)

    def _add_chart_toolbar(self):
        """确保工具栏对象存在（保持隐藏，不占用布局空间 — 界面不需要该行操作栏），
        同时挂载编辑面板并同步页面高度"""
        if not hasattr(self, '_chart_toolbar') or self._chart_toolbar is None:
            from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
            self._chart_toolbar = NavigationToolbar2QT(self.canvas, self.chart_container)
            self._chart_toolbar.setMaximumHeight(32)
            self._chart_toolbar.setStyleSheet("QToolBar { border: none; spacing: 2px; }")
            self._chart_toolbar.setVisible(False)  # 工具栏不进布局、不显示
        if not hasattr(self, '_chart_editor_panel') or self._chart_editor_panel is None:
            from ui.widgets.chart_editor import ChartEditorPanel
            self._chart_editor_panel = ChartEditorPanel()
            self._chart_editor_panel.options_changed.connect(self._on_chart_options_changed)
        if self.chart_layout.indexOf(self._chart_editor_panel) < 0:
            self.chart_layout.addWidget(self._chart_editor_panel)
        self._pin_canvas_natural_height()
        self.chart_layout.setContentsMargins(0, 4, 0, 4)
        self._animate_chart_container()
        self._sync_chart_page_height()

    def _pin_canvas_natural_height(self):
        """画布最小高跟随图片自然像素高 — 防止编辑面板挤压图表；每帧先复位再设精确值，
        图表高度变化时不会残留旧下限（页面滚动范围保持精确）"""
        if not self.isVisible():
            return
        if self.canvas is None or self.current_figure is None:
            return
        try:
            self.canvas.setMinimumHeight(0)
            natural = getattr(self, '_canvas_natural_h', 0)
            if natural <= 0:
                natural = int(
                    self.current_figure.get_size_inches()[1]
                    * self.current_figure.get_dpi())
            if natural > 200:
                self.canvas.setMinimumHeight(natural)
        except Exception:
            pass

    def _sync_chart_page_height(self):
        """将图表页自然高度同步到结果容器 — 让内容增高由页面滚动承接。

        显式累加布局各子行的最小高度：Qt 布局对刚替换(remove+insert)的 canvas
        存在 minimumSizeHint 缓存问题（新 canvas 的显式最小高被忽略，容器被压小、
        画布溢出），因此不依赖 minimumSizeHint 缓存。
        """
        if not hasattr(self, 'chart_container'):
            return
        if not self.isVisible():
            return
        h = 8  # 布局上下边距 (0,4,0,4)
        for i in range(self.chart_layout.count()):
            item = self.chart_layout.itemAt(i)
            w = item.widget() if item else None
            if w is None:
                continue
            h += max(w.minimumHeight(), w.minimumSizeHint().height())
        if h < 300:
            h = 300
        self._last_page_height = int(h)      # 记录，供切回时恢复（无 canvas 页同样适用）
        self.chart_container.setMinimumHeight(h)
        stack = getattr(self, 'result_stack', None)
        if stack is not None:
            stack.setMinimumHeight(h)

    def _setup_chart_menu(self):
        if self.canvas is None:
            return
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self._on_chart_context_menu)

    def _on_chart_context_menu(self, pos):
        menu = QMenu(self)
        popout = menu.addAction("在独立窗口中查看")
        menu.addSeparator()
        save_png = menu.addAction("保存为 PNG")
        save_hires = menu.addAction("保存为高清 PNG (300 DPI)")
        save_svg = menu.addAction("保存为 SVG 矢量图")
        copy_img = menu.addAction("复制到剪贴板")

        action = menu.exec(self.canvas.mapToGlobal(pos))
        if action == popout:
            from ui.dialogs.chart_viewer import ChartViewer
            viewer = ChartViewer(self.current_figure, self, "图表查看")
            viewer.exec()
        elif action == save_png:
            self._on_save_png()
        elif action == save_hires:
            self._on_save_hires_png()
        elif action == save_svg:
            self._on_save_svg()
        elif action == copy_img:
            buf = BytesIO()
            self.current_figure.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            img = QImage.fromData(buf.read())
            QApplication.clipboard().setImage(img)

    def _setup_empty_state(self, icon: str = "", message: str = ""):
        """创建空状态遮罩层 — 无数据时覆盖分析面板，中央提供可点击的导入按钮。"""
        tc = theme_colors()
        self._empty_overlay = QFrame(self)
        # 注意：不可对遮罩设 WA_TransparentForMouseEvents——Qt 会连同子控件
        # 一起屏蔽鼠标事件，导致"导入数据"按钮永远收不到点击（W 系列回归）。
        self._empty_overlay.setStyleSheet(
            f"QFrame {{ background: {tc['bg_body']}; border: none; }}")
        self._empty_overlay.setGeometry(self.rect())
        self._empty_overlay.raise_()

        layout = QVBoxLayout(self._empty_overlay)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setFont(QFont("Segoe UI Emoji", 36))
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("background: transparent;")
            layout.addWidget(icon_lbl)

        msg = message or "请先导入数据文件"
        msg_lbl = QLabel(msg)
        msg_lbl.setFont(QFont(get_ui_font(), 12))
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setStyleSheet(f"color: {tc['text_secondary']}; background: transparent;")
        layout.addWidget(msg_lbl)

        btn = QPushButton("导入数据")
        btn.setFont(QFont(get_ui_font(), 11, QFont.Bold))
        btn.setFixedSize(160, 40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {tc['accent']}; color: white; "
            f"border: none; border-radius: 8px; padding: 8px 20px; }}"
            f"QPushButton:hover {{ background: {tc['accent_dark']}; }}"
        )
        btn.clicked.connect(self.import_data_requested.emit)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        self._empty_overlay.show()

    def _release_page_height(self):
        """释放图表页钉死的最小高度 — 主窗口 74 个 tab 共享单一 QScrollArea，
        隐藏页残留的最小高会把整个 QStackedWidget 撑高，其他 tab 被拉伸且需滚回顶部。
        切离本页时释放，回到本页时由 showEvent 重新应用（图表本身保留在内存，不重绘）。"""
        if getattr(self, 'canvas', None) is not None:
            try:
                self.canvas.setMinimumHeight(0)
            except Exception:
                pass
        if getattr(self, 'chart_container', None) is not None:
            self.chart_container.setMinimumHeight(300)
        if getattr(self, 'result_stack', None) is not None:
            self.result_stack.setMinimumHeight(300)

    def showEvent(self, event):
        super().showEvent(event)
        if (not hasattr(self, '_empty_overlay') or self._empty_overlay is None) \
           and self.df is None:
            pass
        if getattr(self, 'canvas', None) is not None and self.current_figure is not None:
            self._pin_canvas_natural_height()
            self._sync_chart_page_height()
        elif getattr(self, '_last_page_height', 0) > 300:
            # 无 canvas 的分析页（图表由子控件承载）：hideEvent 释放后按记录恢复，
            # 否则切回该 Tab 时滚动范围会丢失（长页无法滚动）
            self.chart_container.setMinimumHeight(self._last_page_height)
            stack = getattr(self, 'result_stack', None)
            if stack is not None:
                stack.setMinimumHeight(self._last_page_height)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._release_page_height()

    def _hide_empty_state(self):
        """隐藏空状态遮罩"""
        if self._empty_overlay:
            self._empty_overlay.hide()

    def ensure_empty_state(self, message: str = ""):
        """按需创建统一空状态遮罩（无数据时提示导入）。"""
        if getattr(self, "_empty_overlay", None) is None:
            self._setup_empty_state(message=message or "请先导入数据")

    def show_empty_state(self, message: str = ""):
        """显示空状态遮罩（主窗口在切到无数据 Tab 时调用）。"""
        self.ensure_empty_state(message)
        if self._empty_overlay is not None:
            self._empty_overlay.setGeometry(self.rect())
            self._empty_overlay.show()
            self._empty_overlay.raise_()

    def _resize_empty_overlay(self):
        """在 resizeEvent 中调用，保持遮罩大小与 Tab 一致"""
        if self._empty_overlay and self._empty_overlay.isVisible():
            self._empty_overlay.setGeometry(self.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_empty_overlay()

    def _animate_chart_container(self):
        """确保容器高度不被限制 — 内容自然增高，由页面级滚动承载超长内容"""
        if not hasattr(self, 'chart_container'):
            return
        self.chart_container.setMaximumHeight(16777215)

    def _setup_chart_editor(self):
        """初始化图表编辑面板"""
        if self._chart_editor_panel is not None:
            return
        from ui.widgets.chart_editor import ChartEditorPanel
        self._chart_editor_panel = ChartEditorPanel()
        self._chart_editor_panel.options_changed.connect(self._on_chart_options_changed)

    def set_chart_type(self, chart_type: str):
        """设置当前图表类型，更新编辑面板"""
        if chart_type == self._current_chart_type:
            return
        self._current_chart_type = chart_type
        if self._chart_editor_panel:
            self._chart_editor_panel.set_chart_type(chart_type)
            self._chart_options = self._chart_editor_panel.get_options()
            # 面板控件重建后 min 尺寸已变 → 立即重算页面高度，避免滚动范围滞后一帧
            self._sync_chart_page_height()

    def _on_chart_options_changed(self, options: dict[str, Any]):
        """图表选项变更回调 — 防抖合并后重新生成当前图表"""
        self._chart_options = options.copy()
        try:
            self._refresh_timer.start()
        except AttributeError:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.setInterval(150)
            self._refresh_timer.timeout.connect(self._refresh_chart_with_options)
            self._refresh_timer.start()

    def _refresh_chart_with_options(self):
        """用当前选项重新生成图表 — 重新运行分析并显示"""
        if not hasattr(self, 'run_analysis') or not hasattr(self, 'display_result'):
            return
        try:
            analysis = self.run_analysis()
            if analysis:
                self.display_result(analysis)
        except Exception as e:
            print(f"图表重绘失败: {e}")

    def get_chart_options(self) -> dict[str, Any]:
        """获取当前图表选项"""
        return self._chart_options.copy()

    def set_chart_options(self, options: dict[str, Any]):
        """设置图表选项"""
        self._chart_options = options.copy()
        if self._chart_editor_panel:
            self._chart_editor_panel.set_options(options)
