"""BaseAnalysisTab — 所有分析 Tab 的共享基类"""

from typing import Dict, Any
from io import BytesIO
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QFileDialog, QTableWidgetItem, QMenu, QApplication,
    QVBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QImage, QFont
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

from core.i18n import i18n
from ui.theme import colors as theme_colors


class BaseAnalysisTab(QWidget):
    export_clicked = Signal()
    analysis_completed = Signal()
    import_data_requested = Signal()  # 空状态中"导入数据"按钮信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df: pd.DataFrame = None
        self.parsed_info: Dict[str, Any] = {}
        self.current_result: Dict[str, Any] = {}
        # W59-W62: 标准三件套契约 — 所有 Tab 的 current_result 必须包含以下键
        # analysis_type: str  分析类型名称
        # params: Dict         分析参数
        # result: Dict         引擎返回结果
        self.current_figure = None
        self.canvas = None
        self._raw_data = {}
        self._data_parser = None
        self._empty_overlay: QWidget = None

    def _clear_canvas(self):
        """清空图表区域并释放 matplotlib 资源"""
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        import matplotlib.pyplot as plt
        # W48: 仅关闭当前 figure，避免批量分析时误关其他 Tab 的图表
        if self.current_figure is not None:
            try:
                plt.close(self.current_figure)
            except Exception:
                pass
        self.canvas = None
        self.current_figure = None

    def _switch_result_view(self, idx: int):
        self.btn_view_chart.setChecked(idx == 0)
        self.btn_view_data.setChecked(idx == 1)
        self.result_stack.setCurrentIndex(idx)

    def _on_save_png(self):
        if not hasattr(self, 'current_figure') or self.current_figure is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.tr("spc.save_png"), "chart.png", "PNG (*.png)"
        )
        if path:
            from config.settings import CHART_DPI, CHART_FIGSIZE
            fig = self.current_figure
            fig.set_size_inches(*CHART_FIGSIZE)
            fig.savefig(path, dpi=CHART_DPI, bbox_inches="tight")
            self.canvas.draw()

    def set_data(self, df: pd.DataFrame = None, parsed_info: Dict[str, Any] = None):
        """设置分析数据（子类可重写以填充列选择器）"""
        self.df = df
        self.parsed_info = parsed_info or {}
        self._hide_empty_state()

    def set_raw_data(self, raw_data, data_parser):
        self._raw_data = raw_data
        self._data_parser = data_parser
        # 没有 sheet_combo 的 Tab (如 Reliability/Pareto): 直接将第一个 Sheet 数据传入
        if not hasattr(self, 'sheet_combo') or self.sheet_combo is None:
            if raw_data and hasattr(self, 'set_data'):
                first_sheet = next(iter(raw_data.values()))
                # 通过 data_parser 解析（如果有）
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
            for j, col in enumerate(df.columns):
                val = str(df.iloc[i, j])
                item = QTableWidgetItem(val)
                item.setToolTip(val)
                self.data_table.setItem(i, j, item)

    def _add_chart_toolbar(self):
        if not hasattr(self, '_chart_toolbar'):
            self._chart_toolbar = NavigationToolbar2QT(self.canvas, self.chart_container)
            self._chart_toolbar.setMaximumHeight(32)
            self._chart_toolbar.setStyleSheet("QToolBar { border: none; spacing: 2px; }")
            self.chart_layout.addWidget(self._chart_toolbar)
            # 结果区首次渲染时平滑展开
            self._animate_chart_container()
        self._setup_chart_menu()

    def _setup_chart_menu(self):
        if self.canvas is None:
            return
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        try:
            self.canvas.customContextMenuRequested.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.canvas.customContextMenuRequested.connect(self._on_chart_context_menu)

    def _on_chart_context_menu(self, pos):
        menu = QMenu(self)
        popout = menu.addAction("在独立窗口中查看")
        menu.addSeparator()
        save_png = menu.addAction("保存为 PNG")
        copy_img = menu.addAction("复制到剪贴板")

        action = menu.exec(self.canvas.mapToGlobal(pos))
        if action == popout:
            from ui.dialogs.chart_viewer import ChartViewer
            viewer = ChartViewer(self.current_figure, self, "图表查看")
            viewer.exec()
        elif action == save_png:
            self._on_save_png()
        elif action == copy_img:
            buf = BytesIO()
            self.current_figure.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            img = QImage.fromData(buf.read())
            QApplication.clipboard().setImage(img)

    # ── 空状态引导 ─────────────────────────────────────────
    def _setup_empty_state(self, icon: str = "", message: str = ""):
        """创建空状态遮罩层 — 鼠标事件穿透, 不遮挡下方分析面板"""
        tc = theme_colors()
        self._empty_overlay = QFrame(self)
        self._empty_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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
        msg_lbl.setFont(QFont("Microsoft YaHei", 12))
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setStyleSheet(f"color: {tc['text_secondary']}; background: transparent;")
        layout.addWidget(msg_lbl)

        # 按钮需单独恢复鼠标事件
        btn = QPushButton("导入数据")
        btn.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        btn.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
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

    def showEvent(self, event):
        super().showEvent(event)
        # 首次显示时检查：无数据则展示空状态
        if (not hasattr(self, '_empty_overlay') or self._empty_overlay is None) \
           and self.df is None:
            pass  # 子类应在 _setup_ui 末尾调用 _setup_empty_state()

    def _hide_empty_state(self):
        """隐藏空状态遮罩"""
        if self._empty_overlay:
            self._empty_overlay.hide()

    def _resize_empty_overlay(self):
        """在 resizeEvent 中调用，保持遮罩大小与 Tab 一致"""
        if self._empty_overlay and self._empty_overlay.isVisible():
            self._empty_overlay.setGeometry(self.rect())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_empty_overlay()

    # ── 结果区展开动画 ─────────────────────────────────────
    def _animate_chart_container(self):
        """图表容器平滑展开动画 — 首次渲染时从 0 展开到实际高度"""
        if not hasattr(self, 'chart_container'):
            return
        container = self.chart_container
        current = container.height()
        # 如果已有内容(二次渲染)，跳过动画
        if current > 80:
            return
        target = max(container.sizeHint().height(), 400)
        container.setMaximumHeight(10)
        anim = QPropertyAnimation(container, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(10)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
