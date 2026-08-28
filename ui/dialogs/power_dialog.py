"""
Power & Sample Size 分析对话框
"""

import math
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QDoubleSpinBox, QSpinBox, QPushButton, QLabel, QGroupBox,
    QStackedWidget, QWidget, QTextEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from analysis.doe.power_analysis import (
    compute_power, compute_sample_size, oc_curve,
    TEST_TYPE_LABELS, power_one_way_anova_delta,
)
from ui.theme import colors as theme_colors, BUTTON_PRIMARY_STRETCH, BUTTON_SECONDARY
from ui.font_config import get_ui_font


class PowerDialog(QDialog):
    """Power & Sample Size 分析对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Power & Sample Size 分析")
        self.setMinimumSize(650, 580)
        self._setup_ui()

    def _setup_ui(self):
        tc = theme_colors()
        self.setStyleSheet(f"background-color: {tc['bg_body']}; color: {tc['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── 标题 ──
        title = QLabel("Power & Sample Size 分析")
        title.setFont(QFont(get_ui_font(), 16, QFont.Bold))
        layout.addWidget(title)

        # ── 检验类型选择 ──
        type_group = QGroupBox("检验类型")
        type_layout = QFormLayout(type_group)

        self.type_combo = QComboBox()
        for key, label in TEST_TYPE_LABELS.items():
            self.type_combo.addItem(label, key)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addRow("检验类型:", self.type_combo)

        layout.addWidget(type_group)

        # ── 参数配置（动态切换）──
        self.params_stack = QStackedWidget()
        self._setup_param_panels()
        layout.addWidget(self.params_stack)

        # ── 操作按钮 ──
        btn_layout = QHBoxLayout()

        self.calc_sample_btn = QPushButton("计算样本量")
        self.calc_sample_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.calc_sample_btn.clicked.connect(self._calc_sample_size)
        btn_layout.addWidget(self.calc_sample_btn)

        self.calc_power_btn = QPushButton("计算 Power")
        self.calc_power_btn.setStyleSheet(BUTTON_PRIMARY_STRETCH)
        self.calc_power_btn.clicked.connect(self._calc_power)
        btn_layout.addWidget(self.calc_power_btn)

        self.oc_curve_btn = QPushButton("绘制 OC 曲线")
        self.oc_curve_btn.setStyleSheet(BUTTON_SECONDARY)
        self.oc_curve_btn.clicked.connect(self._plot_oc_curve)
        btn_layout.addWidget(self.oc_curve_btn)

        layout.addLayout(btn_layout)

        # ── 结果显示 ──
        result_group = QGroupBox("结果")
        result_layout = QVBoxLayout(result_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont(get_ui_font(), 12))
        self.result_text.setMinimumHeight(100)
        result_layout.addWidget(self.result_text)

        layout.addWidget(result_group)

        # ── 关闭按钮 ──
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        # 初始化
        self._on_type_changed(0)

    def _setup_param_panels(self):
        """创建各检验类型的参数面板"""
        # 0: 单样本 t
        self.panel_1sample_t = self._create_1sample_t_panel()
        self.params_stack.addWidget(self.panel_1sample_t)

        # 1: 双样本 t
        self.panel_2sample_t = self._create_2sample_t_panel()
        self.params_stack.addWidget(self.panel_2sample_t)

        # 2: 配对 t
        self.panel_paired_t = self._create_paired_t_panel()
        self.params_stack.addWidget(self.panel_paired_t)

        # 3: 单比例
        self.panel_1prop = self._create_1prop_panel()
        self.params_stack.addWidget(self.panel_1prop)

        # 4: 双比例
        self.panel_2prop = self._create_2prop_panel()
        self.params_stack.addWidget(self.panel_2prop)

        # 5: 单方差
        self.panel_1var = self._create_1var_panel()
        self.params_stack.addWidget(self.panel_1var)

        # 6: 单因素 ANOVA
        self.panel_anova = self._create_anova_panel()
        self.params_stack.addWidget(self.panel_anova)

    def _create_1sample_t_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_delta_1s = QDoubleSpinBox()
        self.spin_delta_1s.setRange(0.01, 1000)
        self.spin_delta_1s.setValue(1.0)
        self.spin_delta_1s.setDecimals(3)
        layout.addRow("均值差 (δ):", self.spin_delta_1s)

        self.spin_sigma_1s = QDoubleSpinBox()
        self.spin_sigma_1s.setRange(0.01, 1000)
        self.spin_sigma_1s.setValue(2.0)
        self.spin_sigma_1s.setDecimals(3)
        layout.addRow("标准差 (σ):", self.spin_sigma_1s)

        self.spin_n_1s = QSpinBox()
        self.spin_n_1s.setRange(3, 10000)
        self.spin_n_1s.setValue(20)
        layout.addRow("样本量 (n):", self.spin_n_1s)

        self.spin_alpha_1s = QDoubleSpinBox()
        self.spin_alpha_1s.setRange(0.001, 0.2)
        self.spin_alpha_1s.setValue(0.05)
        self.spin_alpha_1s.setDecimals(3)
        self.spin_alpha_1s.setSingleStep(0.01)
        layout.addRow("显著性水平 (α):", self.spin_alpha_1s)

        self.spin_power_1s = QDoubleSpinBox()
        self.spin_power_1s.setRange(0.5, 0.999)
        self.spin_power_1s.setValue(0.8)
        self.spin_power_1s.setDecimals(3)
        self.spin_power_1s.setSingleStep(0.05)
        layout.addRow("目标 Power:", self.spin_power_1s)
        return w

    def _create_2sample_t_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_delta_2s = QDoubleSpinBox()
        self.spin_delta_2s.setRange(0.01, 1000)
        self.spin_delta_2s.setValue(0.5)
        self.spin_delta_2s.setDecimals(3)
        layout.addRow("均值差 (δ):", self.spin_delta_2s)

        self.spin_sigma_2s = QDoubleSpinBox()
        self.spin_sigma_2s.setRange(0.01, 1000)
        self.spin_sigma_2s.setValue(1.0)
        self.spin_sigma_2s.setDecimals(3)
        layout.addRow("合并标准差 (σ):", self.spin_sigma_2s)

        self.spin_n1_2s = QSpinBox()
        self.spin_n1_2s.setRange(2, 10000)
        self.spin_n1_2s.setValue(30)
        layout.addRow("样本量 n1:", self.spin_n1_2s)

        self.spin_ratio_2s = QDoubleSpinBox()
        self.spin_ratio_2s.setRange(0.5, 3.0)
        self.spin_ratio_2s.setValue(1.0)
        self.spin_ratio_2s.setDecimals(2)
        layout.addRow("分配比 (n2/n1):", self.spin_ratio_2s)

        self.spin_alpha_2s = QDoubleSpinBox()
        self.spin_alpha_2s.setRange(0.001, 0.2)
        self.spin_alpha_2s.setValue(0.05)
        self.spin_alpha_2s.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_2s)

        self.spin_power_2s = QDoubleSpinBox()
        self.spin_power_2s.setRange(0.5, 0.999)
        self.spin_power_2s.setValue(0.8)
        self.spin_power_2s.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_2s)
        return w

    def _create_paired_t_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_delta_pt = QDoubleSpinBox()
        self.spin_delta_pt.setRange(0.01, 1000)
        self.spin_delta_pt.setValue(1.0)
        self.spin_delta_pt.setDecimals(3)
        layout.addRow("差值均值 (δ):", self.spin_delta_pt)

        self.spin_sigma_pt = QDoubleSpinBox()
        self.spin_sigma_pt.setRange(0.01, 1000)
        self.spin_sigma_pt.setValue(1.5)
        self.spin_sigma_pt.setDecimals(3)
        layout.addRow("差值标准差 (σ_d):", self.spin_sigma_pt)

        self.spin_n_pt = QSpinBox()
        self.spin_n_pt.setRange(2, 10000)
        self.spin_n_pt.setValue(15)
        layout.addRow("对数 (n):", self.spin_n_pt)

        self.spin_alpha_pt = QDoubleSpinBox()
        self.spin_alpha_pt.setRange(0.001, 0.2)
        self.spin_alpha_pt.setValue(0.05)
        self.spin_alpha_pt.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_pt)

        self.spin_power_pt = QDoubleSpinBox()
        self.spin_power_pt.setRange(0.5, 0.999)
        self.spin_power_pt.setValue(0.8)
        self.spin_power_pt.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_pt)
        return w

    def _create_1prop_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_p1_1p = QDoubleSpinBox()
        self.spin_p1_1p.setRange(0.01, 0.99)
        self.spin_p1_1p.setValue(0.15)
        self.spin_p1_1p.setDecimals(3)
        layout.addRow("真实比例 (p1):", self.spin_p1_1p)

        self.spin_p0_1p = QDoubleSpinBox()
        self.spin_p0_1p.setRange(0.01, 0.99)
        self.spin_p0_1p.setValue(0.10)
        self.spin_p0_1p.setDecimals(3)
        layout.addRow("原假设比例 (p0):", self.spin_p0_1p)

        self.spin_n_1p = QSpinBox()
        self.spin_n_1p.setRange(2, 100000)
        self.spin_n_1p.setValue(100)
        layout.addRow("样本量 (n):", self.spin_n_1p)

        self.spin_alpha_1p = QDoubleSpinBox()
        self.spin_alpha_1p.setRange(0.001, 0.2)
        self.spin_alpha_1p.setValue(0.05)
        self.spin_alpha_1p.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_1p)

        self.spin_power_1p = QDoubleSpinBox()
        self.spin_power_1p.setRange(0.5, 0.999)
        self.spin_power_1p.setValue(0.8)
        self.spin_power_1p.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_1p)
        return w

    def _create_2prop_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_p1_2p = QDoubleSpinBox()
        self.spin_p1_2p.setRange(0.01, 0.99)
        self.spin_p1_2p.setValue(0.30)
        self.spin_p1_2p.setDecimals(3)
        layout.addRow("比例 1 (p1):", self.spin_p1_2p)

        self.spin_p2_2p = QDoubleSpinBox()
        self.spin_p2_2p.setRange(0.01, 0.99)
        self.spin_p2_2p.setValue(0.20)
        self.spin_p2_2p.setDecimals(3)
        layout.addRow("比例 2 (p2):", self.spin_p2_2p)

        self.spin_n_2p = QSpinBox()
        self.spin_n_2p.setRange(2, 100000)
        self.spin_n_2p.setValue(50)
        layout.addRow("样本量 (n per group):", self.spin_n_2p)

        self.spin_alpha_2p = QDoubleSpinBox()
        self.spin_alpha_2p.setRange(0.001, 0.2)
        self.spin_alpha_2p.setValue(0.05)
        self.spin_alpha_2p.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_2p)

        self.spin_power_2p = QDoubleSpinBox()
        self.spin_power_2p.setRange(0.5, 0.999)
        self.spin_power_2p.setValue(0.8)
        self.spin_power_2p.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_2p)
        return w

    def _create_1var_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_sigma_1v = QDoubleSpinBox()
        self.spin_sigma_1v.setRange(0.01, 1000)
        self.spin_sigma_1v.setValue(1.5)
        self.spin_sigma_1v.setDecimals(3)
        layout.addRow("真实标准差 (σ):", self.spin_sigma_1v)

        self.spin_sigma0_1v = QDoubleSpinBox()
        self.spin_sigma0_1v.setRange(0.01, 1000)
        self.spin_sigma0_1v.setValue(1.0)
        self.spin_sigma0_1v.setDecimals(3)
        layout.addRow("原假设标准差 (σ0):", self.spin_sigma0_1v)

        self.spin_n_1v = QSpinBox()
        self.spin_n_1v.setRange(3, 10000)
        self.spin_n_1v.setValue(25)
        layout.addRow("样本量 (n):", self.spin_n_1v)

        self.spin_alpha_1v = QDoubleSpinBox()
        self.spin_alpha_1v.setRange(0.001, 0.2)
        self.spin_alpha_1v.setValue(0.05)
        self.spin_alpha_1v.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_1v)

        self.spin_power_1v = QDoubleSpinBox()
        self.spin_power_1v.setRange(0.5, 0.999)
        self.spin_power_1v.setValue(0.8)
        self.spin_power_1v.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_1v)
        return w

    def _create_anova_panel(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        self.spin_k_an = QSpinBox()
        self.spin_k_an.setRange(2, 20)
        self.spin_k_an.setValue(3)
        layout.addRow("组数 (k):", self.spin_k_an)

        self.spin_delta_an = QDoubleSpinBox()
        self.spin_delta_an.setRange(0.01, 1000)
        self.spin_delta_an.setValue(0.5)
        self.spin_delta_an.setDecimals(3)
        layout.addRow("均值差 (δ):", self.spin_delta_an)

        self.spin_sigma_an = QDoubleSpinBox()
        self.spin_sigma_an.setRange(0.01, 1000)
        self.spin_sigma_an.setValue(1.0)
        self.spin_sigma_an.setDecimals(3)
        layout.addRow("标准差 (σ):", self.spin_sigma_an)

        self.spin_n_an = QSpinBox()
        self.spin_n_an.setRange(2, 10000)
        self.spin_n_an.setValue(10)
        layout.addRow("每组样本量 (n):", self.spin_n_an)

        self.spin_alpha_an = QDoubleSpinBox()
        self.spin_alpha_an.setRange(0.001, 0.2)
        self.spin_alpha_an.setValue(0.05)
        self.spin_alpha_an.setDecimals(3)
        layout.addRow("显著性水平 (α):", self.spin_alpha_an)

        self.spin_power_an = QDoubleSpinBox()
        self.spin_power_an.setRange(0.5, 0.999)
        self.spin_power_an.setValue(0.8)
        self.spin_power_an.setDecimals(3)
        layout.addRow("目标 Power:", self.spin_power_an)
        return w

    def _on_type_changed(self, index: int):
        """切换检验类型时更新参数面板"""
        self.params_stack.setCurrentIndex(index)

    def _get_test_type(self) -> str:
        return self.type_combo.currentData()

    def _calc_power(self):
        """计算 Power"""
        test_type = self._get_test_type()
        try:
            if test_type == "1_sample_t":
                n = self.spin_n_1s.value()
                power = compute_power(test_type, n,
                    delta=self.spin_delta_1s.value(),
                    sigma=self.spin_sigma_1s.value(),
                    alpha=self.spin_alpha_1s.value())
                d = abs(self.spin_delta_1s.value()) / self.spin_sigma_1s.value()
                self._show_result(
                    f"单样本 t 检验 Power\n"
                    f"{'='*40}\n"
                    f"样本量 (n): {n}\n"
                    f"均值差 (δ): {self.spin_delta_1s.value()}\n"
                    f"标准差 (σ): {self.spin_sigma_1s.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1s.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}\n"
                    f"Cohen's d: {d:.3f}\n"
                    f"非中心参数: {self.spin_delta_1s.value() * math.sqrt(n) / self.spin_sigma_1s.value():.3f}"
                )

            elif test_type == "2_sample_t":
                n1 = self.spin_n1_2s.value()
                ratio = self.spin_ratio_2s.value()
                n2 = max(2, int(n1 * ratio))
                power = compute_power(test_type, n1,
                    n2=n2,
                    delta=self.spin_delta_2s.value(),
                    sigma=self.spin_sigma_2s.value(),
                    alpha=self.spin_alpha_2s.value())
                self._show_result(
                    f"双样本 t 检验 Power\n"
                    f"{'='*40}\n"
                    f"样本量 n1: {n1}\n"
                    f"样本量 n2: {n2}\n"
                    f"均值差 (δ): {self.spin_delta_2s.value()}\n"
                    f"合并标准差 (σ): {self.spin_sigma_2s.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_2s.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

            elif test_type == "paired_t":
                n = self.spin_n_pt.value()
                power = compute_power(test_type, n,
                    delta=self.spin_delta_pt.value(),
                    sigma_d=self.spin_sigma_pt.value(),
                    alpha=self.spin_alpha_pt.value())
                self._show_result(
                    f"配对 t 检验 Power\n"
                    f"{'='*40}\n"
                    f"对数 (n): {n}\n"
                    f"差值均值 (δ): {self.spin_delta_pt.value()}\n"
                    f"差值标准差 (σ_d): {self.spin_sigma_pt.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_pt.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

            elif test_type == "1_proportion":
                n = self.spin_n_1p.value()
                power = compute_power(test_type, n,
                    p1=self.spin_p1_1p.value(),
                    p0=self.spin_p0_1p.value(),
                    alpha=self.spin_alpha_1p.value())
                self._show_result(
                    f"单比例检验 Power\n"
                    f"{'='*40}\n"
                    f"样本量 (n): {n}\n"
                    f"真实比例 (p1): {self.spin_p1_1p.value()}\n"
                    f"原假设比例 (p0): {self.spin_p0_1p.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1p.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

            elif test_type == "2_proportions":
                n = self.spin_n_2p.value()
                power = compute_power(test_type, n,
                    p1=self.spin_p1_2p.value(),
                    p2=self.spin_p2_2p.value(),
                    alpha=self.spin_alpha_2p.value())
                self._show_result(
                    f"双比例检验 Power\n"
                    f"{'='*40}\n"
                    f"每组样本量 (n): {n}\n"
                    f"比例 1 (p1): {self.spin_p1_2p.value()}\n"
                    f"比例 2 (p2): {self.spin_p2_2p.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_2p.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

            elif test_type == "1_variance":
                n = self.spin_n_1v.value()
                power = compute_power(test_type, n,
                    sigma=self.spin_sigma_1v.value(),
                    sigma0=self.spin_sigma0_1v.value(),
                    alpha=self.spin_alpha_1v.value())
                self._show_result(
                    f"单方差检验 Power\n"
                    f"{'='*40}\n"
                    f"样本量 (n): {n}\n"
                    f"真实标准差 (σ): {self.spin_sigma_1v.value()}\n"
                    f"原假设标准差 (σ0): {self.spin_sigma0_1v.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1v.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

            elif test_type == "1_way_anova":
                k = self.spin_k_an.value()
                n = self.spin_n_an.value()
                delta = self.spin_delta_an.value()
                sigma = self.spin_sigma_an.value()
                f2 = (delta ** 2) / (2 * sigma ** 2) if sigma > 0 else 0
                power = compute_power(test_type, n,
                    n_groups=k,
                    f_squared=f2,
                    alpha=self.spin_alpha_an.value())
                self._show_result(
                    f"单因素 ANOVA Power\n"
                    f"{'='*40}\n"
                    f"组数 (k): {k}\n"
                    f"每组样本量 (n): {n}\n"
                    f"均值差 (δ): {delta}\n"
                    f"标准差 (σ): {sigma}\n"
                    f"效应量 f²: {f2:.4f}\n"
                    f"Cohen's f: {math.sqrt(f2):.4f}\n"
                    f"显著性水平 (α): {self.spin_alpha_an.value()}\n"
                    f"{'─'*40}\n"
                    f"Power (1-β): {power:.4f}"
                )

        except Exception as e:
            self._show_result(f"计算失败: {str(e)}", error=True)

    def _calc_sample_size(self):
        """计算所需样本量"""
        test_type = self._get_test_type()
        try:
            if test_type == "1_sample_t":
                n = compute_sample_size(test_type,
                    power=self.spin_power_1s.value(),
                    alpha=self.spin_alpha_1s.value(),
                    delta=self.spin_delta_1s.value(),
                    sigma=self.spin_sigma_1s.value())
                power_actual = compute_power(test_type, n,
                    delta=self.spin_delta_1s.value(),
                    sigma=self.spin_sigma_1s.value(),
                    alpha=self.spin_alpha_1s.value())
                self._show_result(
                    f"单样本 t 检验样本量计算\n"
                    f"{'='*40}\n"
                    f"均值差 (δ): {self.spin_delta_1s.value()}\n"
                    f"标准差 (σ): {self.spin_sigma_1s.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1s.value()}\n"
                    f"目标 Power: {self.spin_power_1s.value()}\n"
                    f"{'─'*40}\n"
                    f"所需样本量: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "2_sample_t":
                n1 = compute_sample_size(test_type,
                    power=self.spin_power_2s.value(),
                    alpha=self.spin_alpha_2s.value(),
                    delta=self.spin_delta_2s.value(),
                    sigma=self.spin_sigma_2s.value(),
                    ratio=self.spin_ratio_2s.value())
                n2 = max(2, int(n1 * self.spin_ratio_2s.value()))
                power_actual = compute_power(test_type, n1,
                    n2=n2,
                    delta=self.spin_delta_2s.value(),
                    sigma=self.spin_sigma_2s.value(),
                    alpha=self.spin_alpha_2s.value())
                self._show_result(
                    f"双样本 t 检验样本量计算\n"
                    f"{'='*40}\n"
                    f"均值差 (δ): {self.spin_delta_2s.value()}\n"
                    f"合并标准差 (σ): {self.spin_sigma_2s.value()}\n"
                    f"分配比 (n2/n1): {self.spin_ratio_2s.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_2s.value()}\n"
                    f"目标 Power: {self.spin_power_2s.value()}\n"
                    f"{'─'*40}\n"
                    f"所需样本量: n1 = {n1}, n2 = {n2}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "paired_t":
                n = compute_sample_size(test_type,
                    power=self.spin_power_pt.value(),
                    alpha=self.spin_alpha_pt.value(),
                    delta=self.spin_delta_pt.value(),
                    sigma_d=self.spin_sigma_pt.value())
                power_actual = compute_power(test_type, n,
                    delta=self.spin_delta_pt.value(),
                    sigma_d=self.spin_sigma_pt.value(),
                    alpha=self.spin_alpha_pt.value())
                self._show_result(
                    f"配对 t 检验样本量计算\n"
                    f"{'='*40}\n"
                    f"差值均值 (δ): {self.spin_delta_pt.value()}\n"
                    f"差值标准差 (σ_d): {self.spin_sigma_pt.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_pt.value()}\n"
                    f"目标 Power: {self.spin_power_pt.value()}\n"
                    f"{'─'*40}\n"
                    f"所需对数: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "1_proportion":
                n = compute_sample_size(test_type,
                    power=self.spin_power_1p.value(),
                    alpha=self.spin_alpha_1p.value(),
                    p1=self.spin_p1_1p.value(),
                    p0=self.spin_p0_1p.value())
                power_actual = compute_power(test_type, n,
                    p1=self.spin_p1_1p.value(),
                    p0=self.spin_p0_1p.value(),
                    alpha=self.spin_alpha_1p.value())
                self._show_result(
                    f"单比例检验样本量计算\n"
                    f"{'='*40}\n"
                    f"真实比例 (p1): {self.spin_p1_1p.value()}\n"
                    f"原假设比例 (p0): {self.spin_p0_1p.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1p.value()}\n"
                    f"目标 Power: {self.spin_power_1p.value()}\n"
                    f"{'─'*40}\n"
                    f"所需样本量: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "2_proportions":
                n = compute_sample_size(test_type,
                    power=self.spin_power_2p.value(),
                    alpha=self.spin_alpha_2p.value(),
                    p1=self.spin_p1_2p.value(),
                    p2=self.spin_p2_2p.value())
                power_actual = compute_power(test_type, n,
                    p1=self.spin_p1_2p.value(),
                    p2=self.spin_p2_2p.value(),
                    alpha=self.spin_alpha_2p.value())
                self._show_result(
                    f"双比例检验样本量计算\n"
                    f"{'='*40}\n"
                    f"比例 1 (p1): {self.spin_p1_2p.value()}\n"
                    f"比例 2 (p2): {self.spin_p2_2p.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_2p.value()}\n"
                    f"目标 Power: {self.spin_power_2p.value()}\n"
                    f"{'─'*40}\n"
                    f"所需每组样本量: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "1_variance":
                n = compute_sample_size(test_type,
                    power=self.spin_power_1v.value(),
                    alpha=self.spin_alpha_1v.value(),
                    sigma=self.spin_sigma_1v.value(),
                    sigma0=self.spin_sigma0_1v.value())
                power_actual = compute_power(test_type, n,
                    sigma=self.spin_sigma_1v.value(),
                    sigma0=self.spin_sigma0_1v.value(),
                    alpha=self.spin_alpha_1v.value())
                self._show_result(
                    f"单方差检验样本量计算\n"
                    f"{'='*40}\n"
                    f"真实标准差 (σ): {self.spin_sigma_1v.value()}\n"
                    f"原假设标准差 (σ0): {self.spin_sigma0_1v.value()}\n"
                    f"显著性水平 (α): {self.spin_alpha_1v.value()}\n"
                    f"目标 Power: {self.spin_power_1v.value()}\n"
                    f"{'─'*40}\n"
                    f"所需样本量: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

            elif test_type == "1_way_anova":
                k = self.spin_k_an.value()
                delta = self.spin_delta_an.value()
                sigma = self.spin_sigma_an.value()
                f2 = (delta ** 2) / (2 * sigma ** 2) if sigma > 0 else 0
                n = compute_sample_size(test_type,
                    power=self.spin_power_an.value(),
                    alpha=self.spin_alpha_an.value(),
                    n_groups=k,
                    f_squared=f2)
                power_actual = compute_power(test_type, n,
                    n_groups=k,
                    f_squared=f2,
                    alpha=self.spin_alpha_an.value())
                self._show_result(
                    f"单因素 ANOVA 样本量计算\n"
                    f"{'='*40}\n"
                    f"组数 (k): {k}\n"
                    f"均值差 (δ): {delta}\n"
                    f"标准差 (σ): {sigma}\n"
                    f"效应量 f²: {f2:.4f}\n"
                    f"显著性水平 (α): {self.spin_alpha_an.value()}\n"
                    f"目标 Power: {self.spin_power_an.value()}\n"
                    f"{'─'*40}\n"
                    f"所需每组样本量: n = {n}\n"
                    f"实际 Power: {power_actual:.4f}"
                )

        except Exception as e:
            self._show_result(f"计算失败: {str(e)}", error=True)

    def _plot_oc_curve(self):
        """绘制 OC 曲线"""
        test_type = self._get_test_type()
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

            params = {}
            if test_type == "1_sample_t":
                params = {"delta": self.spin_delta_1s.value(), "sigma": self.spin_sigma_1s.value(), "alpha": self.spin_alpha_1s.value()}
            elif test_type == "2_sample_t":
                params = {"delta": self.spin_delta_2s.value(), "sigma": self.spin_sigma_2s.value(), "alpha": self.spin_alpha_2s.value()}
            elif test_type == "paired_t":
                params = {"delta": self.spin_delta_pt.value(), "sigma_d": self.spin_sigma_pt.value(), "alpha": self.spin_alpha_pt.value()}
            elif test_type == "1_proportion":
                params = {"p1": self.spin_p1_1p.value(), "p0": self.spin_p0_1p.value(), "alpha": self.spin_alpha_1p.value()}
            elif test_type == "2_proportions":
                params = {"p1": self.spin_p1_2p.value(), "p2": self.spin_p2_2p.value(), "alpha": self.spin_alpha_2p.value()}
            elif test_type == "1_variance":
                params = {"sigma": self.spin_sigma_1v.value(), "sigma0": self.spin_sigma0_1v.value(), "alpha": self.spin_alpha_1v.value()}
            elif test_type == "1_way_anova":
                k = self.spin_k_an.value()
                delta = self.spin_delta_an.value()
                sigma = self.spin_sigma_an.value()
                f2 = (delta ** 2) / (2 * sigma ** 2) if sigma > 0 else 0
                params = {"n_groups": k, "f_squared": f2, "alpha": self.spin_alpha_an.value()}

            data = oc_curve(test_type, n_range=(5, 100), steps=30, **params)

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(data["n_values"], data["power_values"], "b-o", linewidth=2, markersize=4)
            ax.axhline(y=0.8, color="r", linestyle="--", alpha=0.7, label="Power = 0.80")
            ax.set_xlabel("Sample Size (n)", fontsize=11)
            ax.set_ylabel("Power (1 - β)", fontsize=11)
            ax.set_title(f"OC Curve — {TEST_TYPE_LABELS.get(test_type, test_type)}", fontsize=13)
            ax.set_ylim(0, 1.05)
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()

            # 显示图表
            canvas = FigureCanvasQTAgg(fig)
            dlg = QDialog(self)
            dlg.setWindowTitle("OC 曲线")
            dlg.setMinimumSize(700, 450)
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.addWidget(canvas)
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dlg.close)
            dlg_layout.addWidget(close_btn)
            dlg.exec()
            plt.close(fig)

        except Exception as e:
            self._show_result(f"绘制失败: {str(e)}", error=True)

    def _show_result(self, text: str, error: bool = False):
        """显示结果文本"""
        tc = theme_colors()
        if error:
            self.result_text.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.result_text.setStyleSheet(f"color: {tc['text_primary']};")
        self.result_text.setPlainText(text)
