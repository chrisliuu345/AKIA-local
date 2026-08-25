"""轻量动画工具 — 淡入 / 数字滚动 / 轮播交叉淡入 (v2.4.1)

- 动画开关: config.settings.get_setting("animations_enabled", True)
  关闭时所有函数走瞬时路径 (不创建动画对象, 便于测试与低端机)
- 实现: QGraphicsOpacityEffect + QPropertyAnimation; 动画 parent 到目标
  widget, 由 Qt 父子机制持有引用防 GC; 结束回调移除 effect 避免持续绘制开销
"""

from PySide6.QtCore import QPropertyAnimation, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import QGraphicsOpacityEffect

from config.settings import get_setting

# 进行中的交叉淡入动画: id(stack) -> [animation, ...] (防 GC + 支持快速切换打断)
_ACTIVE = {}


def _animations_enabled() -> bool:
    return bool(get_setting("animations_enabled", True))


def cleanup(stack):
    """W74: 清理指定 stack 的所有活跃动画，释放引用"""
    key = id(stack)
    prev = _ACTIVE.pop(key, None)
    if prev:
        for a in prev:
            if a is not None and a.state() == QPropertyAnimation.Running:
                a.stop()
        for i in range(stack.count()):
            w = stack.widget(i)
            if w is not None:
                w.setGraphicsEffect(None)


def _safe_stop(anim):
    """安全停止动画 — 防止 C++ 对象已删除时的 RuntimeError"""
    try:
        if anim is not None and anim.state() == QPropertyAnimation.Running:
            anim.stop()
    except (RuntimeError, AttributeError):
        pass


def fade_in(widget, duration: int = 280, start_opacity: float = 0.0):
    """widget 淡入显示 (start_opacity→1)。动画关闭时直接显示。返回动画对象或 None。"""
    if widget is None:
        return None
    if not _animations_enabled():
        widget.setGraphicsEffect(None)
        widget.show()
        return None
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(float(start_opacity))
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.InOutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None) if widget is not None else None)
    widget.destroyed.connect(lambda *_args: _safe_stop(anim))
    widget.show()
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def count_up(label, target: float, fmt, duration: int = 900):
    """数字滚动动画: 0→target, 每帧以 fmt(value) 写 label 文本 (格式函数支持带后缀)。

    fmt 必须返回 str, 如 lambda v: f"{v:.1f}%"。动画关闭时直接写终值。
    """
    if not _animations_enabled():
        label.setText(fmt(float(target)))
        return None
    anim = QVariantAnimation(label)
    anim.setStartValue(0.0)
    anim.setEndValue(float(target))
    anim.setDuration(duration)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.valueChanged.connect(lambda v: label.setText(fmt(v)))
    anim.finished.connect(lambda: label.setText(fmt(float(target))))
    label.destroyed.connect(lambda *_args: _safe_stop(anim))
    anim.start(QVariantAnimation.DeleteWhenStopped)
    return anim


def cross_fade(stack, to_idx: int, duration: int = 400):
    """QStackedWidget 交叉淡入切换: 旧页淡出 → 切换索引 → 新页淡入。

    - 动画关闭或索引非法时瞬切 (setCurrentIndex)
    - 快速连续切换会先打断上一轮动画并复位所有页的透明效果
    - W74: 连接 destroyed 信号确保 stack 销毁时清理 _ACTIVE
    """
    if to_idx == stack.currentIndex() or to_idx < 0 or to_idx >= stack.count():
        return None
    if not _animations_enabled():
        stack.setCurrentIndex(to_idx)
        return None

    key = id(stack)
    prev = _ACTIVE.pop(key, None)
    if prev:
        for a in prev:
            if a is not None and a.state() == QPropertyAnimation.Running:
                a.stop()
        for i in range(stack.count()):
            stack.widget(i).setGraphicsEffect(None)

    old_widget = stack.currentWidget()
    half = max(duration // 2, 100)
    out_anim = None

    def _switch():
        stack.setCurrentIndex(to_idx)
        if old_widget is not None:
            old_widget.setGraphicsEffect(None)
        new_widget = stack.currentWidget()
        if hasattr(new_widget, "_fit") and not getattr(new_widget, "_user_zoomed", True):
            new_widget._fit()
        in_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(in_effect)
        in_anim = QPropertyAnimation(in_effect, b"opacity", stack)
        in_anim.setDuration(half)
        in_anim.setStartValue(0.0)
        in_anim.setEndValue(1.0)

        def _finish():
            if new_widget is not None:
                new_widget.setGraphicsEffect(None)
            _ACTIVE.pop(key, None)

        in_anim.finished.connect(_finish)
        in_anim.start(QPropertyAnimation.DeleteWhenStopped)
        _ACTIVE[key] = [in_anim]

    if old_widget is not None:
        out_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(out_effect)
        out_anim = QPropertyAnimation(out_effect, b"opacity", stack)
        out_anim.setDuration(half)
        out_anim.setStartValue(1.0)
        out_anim.setEndValue(0.0)
        out_anim.finished.connect(_switch)
        out_anim.start(QPropertyAnimation.DeleteWhenStopped)
        _ACTIVE[key] = [out_anim]
        stack.destroyed.connect(lambda: cleanup(stack))
        return out_anim
    _switch()
    stack.destroyed.connect(lambda: cleanup(stack))
    return None
