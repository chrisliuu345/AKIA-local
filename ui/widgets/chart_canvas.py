"""分析页图表画布。

图例和右侧注释是固定字号。页面把画布压窄后，它们会画出边框。
每次尺寸变化都按当前宽度把图面收回四周留白里。
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from output.chart_style import fit_figure_in_frame


class ChartCanvas(FigureCanvasQTAgg):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_inset_guard", False) or self.figure is None:
            return
        self._inset_guard = True
        try:
            if fit_figure_in_frame(self.figure):
                self.draw_idle()
        finally:
            self._inset_guard = False
