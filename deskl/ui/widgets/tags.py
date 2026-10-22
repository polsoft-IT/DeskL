from __future__ import annotations

from PyQt6.QtCore import QEvent, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QEnterEvent,
    QPainter,
    QPaintEvent,
    QPalette,
)
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QToolButton, QWidget

from ... import lang
from .common import _readable_text, tag_color


class TagChip(QToolButton):
    def __init__(self, tag: str, label: str, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tag = tag
        self._label = label
        self._color = QColor(color)
        self._hover = False
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip(label)
        font = self.font()
        font.setPointSize(max(7, font.pointSize() - 1))
        self.setFont(font)
        self.setFixedHeight(20)
        self.setFixedWidth(self.fontMetrics().horizontalAdvance(label) + 22)

    def tag(self) -> str:
        return self._tag

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent | None) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        color = self._color
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -1.0, -1.0)
        radius = box.height() / 2.0
        fill = QColor(color)
        shadow_alpha = 0

        if self.isChecked():
            shadow_alpha = 30
        else:
            fill.setAlpha(165 if self._hover else 90)
            if self._hover:
                shadow_alpha = 15

        # Subtelny cień
        if shadow_alpha > 0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, shadow_alpha))
            p.drawRoundedRect(box.translated(0.0, 0.8), radius, radius)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(box, radius, radius)

        d = box.height() * 0.44
        p.setBrush(color)
        p.drawEllipse(QRectF(box.left() + 4.0, box.center().y() - d / 2.0, d, d))

        if self.isChecked():
            fg = _readable_text(color)
        else:
            fg = self.palette().color(QPalette.ColorRole.ButtonText)
        p.setPen(fg)
        text = QRectF(box.left() + d + 7.0, box.top(), box.width() - d - 11.0, box.height())
        p.drawText(text, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._label)


class TagBar(QWidget):
    selectionChanged = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tags: list[str] = []
        self._selected: set[str] = set()
        self._chips: dict[str, TagChip] = {}
        self._all_chip: TagChip | None = None
        self.setFixedHeight(24)

        content = QWidget()
        self._row = QHBoxLayout(content)
        self._row.setContentsMargins(4, 2, 4, 2)
        self._row.setSpacing(5)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        scroll.setFixedHeight(24)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll)

        self._rebuild()

    def tags(self) -> list[str]:
        return list(self._tags)

    def selected(self) -> list[str]:
        return sorted(self._selected)

    def set_tags(self, tags: list[str]) -> None:
        tags = list(dict.fromkeys(tags))
        if tags == self._tags:
            return
        self._tags = tags
        self._rebuild()

    def set_selected(self, tags: list[str]) -> None:
        self._selected = {t for t in tags if t in self._chips}
        self._sync()

    def retranslate(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._chips.clear()

        self._all_chip = TagChip("", lang.tr("tag.all"), QColor(140, 140, 140))
        self._all_chip.clicked.connect(lambda: self._select([]))
        self._row.addWidget(self._all_chip)

        for tag in self._tags:
            chip = TagChip(tag, tag, tag_color(tag))
            chip.clicked.connect(lambda _checked=False, t=tag: self._toggle(t))
            self._row.addWidget(chip)
            self._chips[tag] = chip

        self._row.addStretch(1)
        self._sync()

    def _sync(self) -> None:
        for tag, chip in self._chips.items():
            chip.blockSignals(True)
            chip.setChecked(tag in self._selected)
            chip.blockSignals(False)
            chip.update()
        if self._all_chip is not None:
            self._all_chip.blockSignals(True)
            self._all_chip.setChecked(not self._selected)
            self._all_chip.blockSignals(False)
            self._all_chip.update()

    def _toggle(self, tag: str) -> None:
        if tag in self._selected:
            self._selected.discard(tag)
        else:
            self._selected.add(tag)
        self._sync()
        self.selectionChanged.emit(self.selected())

    def _select(self, tags: list[str]) -> None:
        self._selected = set(tags)
        self._sync()
        self.selectionChanged.emit(self.selected())
