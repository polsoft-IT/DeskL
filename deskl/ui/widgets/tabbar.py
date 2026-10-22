from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import QTabBar, QWidget

from .entries import DRAG_MIME, _drag_items, _drag_source


class EntryTabBar(QTabBar):
    entryDropped = pyqtSignal(int, object, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    @staticmethod
    def _is_entry_drag(mime) -> bool:
        return mime is not None and mime.hasFormat(DRAG_MIME) and _drag_source is not None

    def dragEnterEvent(self, event: QDragEnterEvent | None) -> None:
        if event is not None and self._is_entry_drag(event.mimeData()):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        elif event is not None:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent | None) -> None:
        if event is not None and self._is_entry_drag(event.mimeData()):
            if self.tabAt(event.position().toPoint()) >= 0:
                event.setDropAction(Qt.DropAction.MoveAction)
                event.accept()
            else:
                event.ignore()
        elif event is not None:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent | None) -> None:
        if event is not None and self._is_entry_drag(event.mimeData()):
            index = self.tabAt(event.position().toPoint())
            if index >= 0:
                event.setDropAction(Qt.DropAction.MoveAction)
                event.accept()
                self.entryDropped.emit(index, _drag_source, list(_drag_items))
            else:
                event.ignore()
            return
        if event is not None:
            super().dropEvent(event)
