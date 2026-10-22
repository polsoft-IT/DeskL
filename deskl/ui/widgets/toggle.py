from __future__ import annotations

from PyQt6.QtCore import QEvent, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QEnterEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPalette,
)
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = bool(checked)
        self._hover = False
        self._hover_alpha = 0.0
        self._target_alpha = 0.0
        self.setFixedSize(34, 18)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Animacja hover z QTimer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._animate_hover)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        checked = bool(checked)
        if checked == self._checked:
            return
        self._checked = checked
        self.update()
        self.toggled.emit(checked)

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._hover = True
        self._target_alpha = 1.0
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent | None) -> None:
        self._hover = False
        self._target_alpha = 0.0
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        super().leaveEvent(event)

    def _animate_hover(self):
        """Animacja hover z płynnym przejściem."""
        diff = self._target_alpha - self._hover_alpha
        if abs(diff) < 0.01:
            self._hover_alpha = self._target_alpha
            self._anim_timer.stop()
        else:
            self._hover_alpha += diff * 0.15
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.setChecked(not self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        group = (QPalette.ColorGroup.Active if self.isEnabled() else QPalette.ColorGroup.Disabled)
        pal = self.palette()
        accent = pal.color(group, QPalette.ColorRole.Highlight)
        shadow_alpha = 0

        if not self.isEnabled():
            track = pal.color(group, QPalette.ColorRole.Mid)
        elif self._checked:
            track = QColor(accent)
            shadow_alpha = 30
        elif self._hover:
            track = pal.color(group, QPalette.ColorRole.Midlight)
            shadow_alpha = 20
        else:
            track = pal.color(group, QPalette.ColorRole.Mid)
        knob = (pal.color(group, QPalette.ColorRole.HighlightedText) if self._checked else pal.color(group, QPalette.ColorRole.ButtonText))

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = box.height() / 2.0

        # Subtelny cień pod przełącznikiem
        if shadow_alpha > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, shadow_alpha))
            p.drawRoundedRect(box.translated(0.0, 1.0), radius, radius)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(box, radius, radius)

        d = box.height() - 4.0
        x = box.right() - d - 2.0 if self._checked else box.left() + 2.0
        p.setBrush(knob)
        p.drawEllipse(QRectF(x, box.top() + 2.0, d, d))
