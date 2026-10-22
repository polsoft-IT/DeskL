from __future__ import annotations

import math

from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QEnterEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import QToolButton, QWidget


class CornerButton(QToolButton):
    def __init__(self, glyph: str, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._glyph = glyph
        self._hover = False
        self._down = False
        self._hover_alpha = 0.0
        self._target_alpha = 0.0
        self.setToolTip(tooltip)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(22, 22)

        # Animacja hover z QTimer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._animate_hover)

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._hover = True
        self._target_alpha = 1.0
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent | None) -> None:
        self._hover = False
        self._down = False
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

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        self._down = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._down = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        pal = self.palette()
        fg = pal.color(QPalette.ColorRole.ButtonText)
        accent = pal.color(QPalette.ColorRole.Highlight)
        bg = QColor(0, 0, 0, 0)
        shadow_alpha = 0

        if self.isChecked():
            bg = QColor(accent)
            fg = pal.color(QPalette.ColorRole.HighlightedText)
            shadow_alpha = 40
        elif self._down:
            bg = QColor(accent)
            bg.setAlpha(120)
            shadow_alpha = 25
        elif self._hover:
            bg = QColor(accent)
            bg.setAlpha(int(55 * self._hover_alpha))
            shadow_alpha = int(15 * self._hover_alpha)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)

        # Subtelny cień pod przyciskiem
        if shadow_alpha > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, shadow_alpha))
            p.drawRoundedRect(box.translated(0.0, 1.0), 6.0, 6.0)

        if bg.alpha() > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(box, 6.0, 6.0)

        pen = QPen(fg)
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        self._paint_glyph(p)

    def _paint_glyph(self, p: QPainter) -> None:
        c = QRectF(self.rect()).center()
        cx, cy = c.x(), c.y()
        glyph = self._glyph
        if glyph == "pin":
            p.drawEllipse(QPointF(cx, cy - 4.2), 3.2, 3.2)
            p.drawLine(QPointF(cx - 3.0, cy - 1.0), QPointF(cx - 1.5, cy + 1.8))
            p.drawLine(QPointF(cx + 3.0, cy - 1.0), QPointF(cx + 1.5, cy + 1.8))
            p.drawLine(QPointF(cx - 3.8, cy + 1.8), QPointF(cx + 3.8, cy + 1.8))
            p.drawLine(QPointF(cx, cy + 1.8), QPointF(cx, cy + 7.4))
        elif glyph == "view":
            s = 5.6
            gap = 2.6
            x0 = cx - s - gap / 2.0
            y0 = cy - s - gap / 2.0
            r = 1.4
            p.drawRoundedRect(QRectF(x0, y0, s, s), r, r)
            p.drawRoundedRect(QRectF(x0 + s + gap, y0, s, s), r, r)
            p.drawRoundedRect(QRectF(x0, y0 + s + gap, s, s), r, r)
            p.drawRoundedRect(QRectF(x0 + s + gap, y0 + s + gap, s, s), r, r)
        elif glyph == "size":
            p.drawRoundedRect(QRectF(cx - 7.5, cy + 0.5, 5.5, 5.5), 1.3, 1.3)
            p.drawRoundedRect(QRectF(cx - 1.0, cy - 6.0, 8.5, 8.5), 1.8, 1.8)
        elif glyph == "add":
            p.drawLine(QPointF(cx - 5.0, cy), QPointF(cx + 5.0, cy))
            p.drawLine(QPointF(cx, cy - 5.0), QPointF(cx, cy + 5.0))
        elif glyph == "search":
            r = 4.4
            ox, oy = cx - 1.6, cy - 1.6
            p.drawEllipse(QPointF(ox, oy), r, r)
            d = r * 0.72
            p.drawLine(QPointF(ox + d, oy + d), QPointF(cx + 6.2, cy + 6.2))
        elif glyph == "grid":
            d = 5.0
            p.drawLine(QPointF(cx - d, cy - 7.0), QPointF(cx - d, cy + 7.0))
            p.drawLine(QPointF(cx + d, cy - 7.0), QPointF(cx + d, cy + 7.0))
            p.drawLine(QPointF(cx - 7.0, cy - d), QPointF(cx + 7.0, cy - d))
            p.drawLine(QPointF(cx - 7.0, cy + d), QPointF(cx + 7.0, cy + d))
        elif glyph == "auto":
            p.drawLine(QPointF(cx - 6.5, cy + 6.5), QPointF(cx + 1.5, cy - 1.5))
            p.drawLine(QPointF(cx + 5.0, cy - 7.0), QPointF(cx + 5.0, cy - 2.0))
            p.drawLine(QPointF(cx + 2.5, cy - 4.5), QPointF(cx + 7.5, cy - 4.5))
        elif glyph == "mini":
            col = p.pen().color()
            p.drawRoundedRect(QRectF(cx - 8.0, cy - 7.0, 16.0, 14.0), 2.5, 2.5)
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(cx + 0.5, cy - 1.5, 6.0, 7.0), 1.5, 1.5)
            p.restore()
        elif glyph == "kbd":
            w, h = 15.0, 9.0
            x0 = cx - w / 2.0
            y0 = cy - h / 2.0
            p.drawRoundedRect(QRectF(x0, y0, w, h), 1.6, 1.6)
            for ky in (y0 + 2.2, y0 + 5.0):
                for kx in (x0 + 2.0, x0 + 5.2, x0 + 8.4, x0 + 11.6):
                    p.drawRoundedRect(QRectF(kx, ky, 2.2, 1.6), 0.5, 0.5)
        elif glyph == "info":
            col = p.pen().color()
            p.drawEllipse(QPointF(cx, cy), 7.0, 7.0)
            p.drawLine(QPointF(cx, cy - 1.4), QPointF(cx, cy + 4.4))
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawEllipse(QPointF(cx, cy - 4.3), 1.1, 1.1)
            p.restore()
        elif glyph == "gear":
            r_out, r_in = 5.2, 2.2
            p.drawEllipse(QPointF(cx, cy), r_out, r_out)
            p.drawEllipse(QPointF(cx, cy), r_in, r_in)
            for k in range(8):
                a = math.radians(k * 45.0)
                dx, dy = math.cos(a), math.sin(a)
                p.drawLine(QPointF(cx + dx * r_out, cy + dy * r_out), QPointF(cx + dx * 7.7, cy + dy * 7.7))
        elif glyph == "sidebar":
            w, h = 15.0, 12.0
            x0 = cx - w / 2.0
            y0 = cy - h / 2.0
            col = p.pen().color()
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawRoundedRect(QRectF(x0 + 1.2, y0 + 1.2, 3.4, h - 2.4), 1.1, 1.1)
            p.restore()
            p.drawRoundedRect(QRectF(x0, y0, w, h), 2.4, 2.4)
            p.drawLine(QPointF(x0 + 4.6, y0), QPointF(x0 + 4.6, y0 + h))
        elif glyph == "warn":
            # Warning triangle with exclamation mark
            w, h = 12.0, 10.0
            x0 = cx - w / 2.0
            y0 = cy - h / 2.0 + 1.0
            tri = QPolygonF([QPointF(x0, y0 + h), QPointF(x0 + w / 2.0, y0), QPointF(x0 + w, y0 + h)])
            p.drawPolygon(tri)
            p.setPen(QColor(255, 255, 255))
            p.drawLine(QPointF(cx, cy - 1.0), QPointF(cx, cy + 2.0))
            p.drawPoint(QPointF(cx, cy + 4.0))
        elif glyph == "chart":
            # Simple bar chart icon
            base_y = cy + 4.0
            bar_width = 2.0
            heights = [3.0, 6.0, 4.0, 7.0, 5.0]
            x_start = cx - 5.0
            for i, h in enumerate(heights):
                x = x_start + i * (bar_width + 1.0)
                p.drawRect(QRectF(x, base_y - h, bar_width, h))
