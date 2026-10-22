from __future__ import annotations

from PyQt6.QtCore import QModelIndex, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QListWidget, QStyledItemDelegate, QStyleOptionViewItem

from .common import _readable_text, tag_color
from .entries import TAG_ROLE


def install_delegate(lw: QListWidget) -> None:
    class Delegate(QStyledItemDelegate):
        @staticmethod
        def _list_mode() -> bool:
            return bool(lw.property("listMode")) and lw.property("listMode") != "false"

        def initStyleOption(self, option: QStyleOptionViewItem | None, index: QModelIndex) -> None:
            if option is None:
                return
            super().initStyleOption(option, index)
            if self._list_mode():
                option.decorationPosition = QStyleOptionViewItem.Position.Left
                option.decorationAlignment = (
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                option.decorationSize = lw.iconSize()

        def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
            if self._list_mode():
                gs = lw.gridSize()
                if gs.isValid() and not gs.isEmpty():
                    return gs
            return super().sizeHint(option, index)

        def paint(self, painter: QPainter | None, option: QStyleOptionViewItem,
                  index: QModelIndex) -> None:
            if painter is None:
                return
            tag = index.data(TAG_ROLE) or ""
            pill_w = 0
            if tag and self._list_mode():
                pill_w = option.fontMetrics.horizontalAdvance(tag) + 16
            opt = QStyleOptionViewItem(option)
            if pill_w:
                opt.rect.setRight(max(opt.rect.left(), opt.rect.right() - pill_w))
            super().paint(painter, opt, index)
            if not tag:
                return
            color = tag_color(tag)
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            if self._list_mode():
                h = min(18, option.fontMetrics.height() + 2)
                box = option.rect
                pill = QRectF(
                    box.right() - pill_w + 2.0, box.center().y() - h / 2.0,
                    pill_w - 6.0, h,
                )
                # Subtelny cień pod pill
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 15))
                painter.drawRoundedRect(pill.translated(0.0, 0.5), h / 2.0, h / 2.0)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(pill, h / 2.0, h / 2.0)
                painter.setPen(_readable_text(color))
                painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, tag)
            else:
                d = 10.0
                dot = QRectF(
                    option.rect.right() - d - 7.0, option.rect.top() + 7.0, d, d,
                )
                # Subtelny cień pod kropką
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 20))
                painter.drawEllipse(dot.translated(0.0, 0.5))
                painter.setPen(QPen(color.darker(150), 1.0))
                painter.setBrush(color)
                painter.drawEllipse(dot)
            painter.restore()

    lw.setItemDelegate(Delegate(lw))
