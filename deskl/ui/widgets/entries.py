from __future__ import annotations

import os

from PyQt6.QtCore import QMimeData, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPalette,
    QResizeEvent,
)
from PyQt6.QtWidgets import QApplication, QListWidget, QListWidgetItem, QWidget

from ... import lang
from ...utils import is_url, url_title
from .common import update_list_columns

DRAG_MIME = "application/x-deskl-entry"
TAG_ROLE = Qt.ItemDataRole.UserRole + 1

_drag_source = None  # type: ignore[var-annotated]
_drag_items = []  # type: ignore[var-annotated]
class EntryList(QListWidget):
    entriesDropped = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._press_item: QListWidgetItem | None = None

    def paintEvent(self, event: QPaintEvent | None) -> None:
        super().paintEvent(event)
        if self.count():
            return
        vp = self.viewport()
        if vp is None:
            return
        p = QPainter(vp)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
        p.drawText(
            vp.rect().adjusted(24, 0, -24, 0),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            lang.tr("tab.empty"),
        )

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._press_item = self.itemAt(self._press_pos)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._press_pos = None
        self._press_item = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if (self._press_item is not None and globals().get("_drag_source") is None
                and event and event.buttons() & Qt.MouseButton.LeftButton
                and self._press_pos is not None):
            delta = (event.position().toPoint() - self._press_pos).manhattanLength()
            vp = self.viewport()
            if vp and delta >= QApplication.startDragDistance() and not vp.rect().contains(event.position().toPoint()):
                self.startDrag(Qt.DropAction.MoveAction)
                return
        super().mouseMoveEvent(event)

    def startDrag(self, supported_actions: Qt.DropAction) -> None:
        global _drag_source, _drag_items
        item = self._press_item
        if item is None:
            return
        _drag_source = self
        _drag_items = [item]
        try:
            mime = QMimeData()
            mime.setData(DRAG_MIME, b"1")
            drag = QDrag(self)
            drag.setMimeData(mime)
            pixmap = item.icon().pixmap(QSize(48, 48))
            if not pixmap.isNull():
                drag.setPixmap(pixmap)
                drag.setHotSpot(pixmap.rect().center())
            drag.exec(Qt.DropAction.MoveAction, Qt.DropAction.MoveAction)
        finally:
            _drag_source = None
            _drag_items = []
            self._press_pos = None
            self._press_item = None

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, lambda: update_list_columns(self))

    @staticmethod
    def _droppable(mime: QMimeData) -> bool:
        if mime.hasUrls():
            return True
        return mime.hasText() and is_url(mime.text())

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        mime = event.mimeData() if event is not None else None
        if mime is not None and self._droppable(mime):
            if event is not None:
                event.acceptProposedAction()
        elif event is not None:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        mime = event.mimeData() if event is not None else None
        if mime is not None and self._droppable(mime):
            if event is not None:
                event.acceptProposedAction()
        elif event is not None:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is None:
            return
        mime = event.mimeData()
        if mime is None:
            super().dropEvent(event)
            return
        candidates: list[tuple[str, str]] = []
        for url in mime.urls():
            local = url.toLocalFile()
            if local and os.path.exists(local):
                candidates.append((
                    local,
                    os.path.splitext(os.path.basename(local))[0] or os.path.basename(local),
                ))
            elif is_url(url.toString()):
                link = url.toString()
                candidates.append((link, url_title(link)))
        if not candidates and mime.hasText() and is_url(mime.text()):
            link = mime.text().strip()
            candidates.append((link, url_title(link)))
        if candidates:
            self.entriesDropped.emit(candidates)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
