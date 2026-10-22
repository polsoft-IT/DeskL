from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtGui import QCursor, QIcon, QMouseEvent, QPainter, QPaintEvent
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from ... import lang


class FloatIcon(QWidget):
    SIZE: int = 52

    def __init__(
        self,
        on_restore: Callable[[], None],
        icon: QIcon | None,
        menu_builder: Callable[[QMenu], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self._on_restore = on_restore
        self._icon = icon
        self._menu_builder = menu_builder
        self._on_quit = on_quit or QApplication.quit
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self._drag_offset: QPoint | None = None
        self.retranslate()

    def retranslate(self) -> None:
        self.setToolTip(lang.tr("float.tooltip"))

    def _show_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction(lang.tr("action.restore")).triggered.connect(self._on_restore)
        if self._menu_builder is not None:
            menu.addSeparator()
            self._menu_builder(menu)
        menu.addSeparator()
        menu.addAction(lang.tr("action.quit")).triggered.connect(self._on_quit)
        menu.exec(self.mapToGlobal(pos))

    def paintEvent(self, event: QPaintEvent | None) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._icon is not None and not self._icon.isNull():
            p.drawPixmap(0, 0, self._icon.pixmap(QSize(self.SIZE, self.SIZE)))

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if self._drag_offset is not None and event and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint() - self._drag_offset
            screen = QApplication.screenAt(pos) or self.screen() or QApplication.primaryScreen()
            if screen is not None:
                area = screen.availableGeometry()
                pos.setX(max(area.left(), min(pos.x(), area.right() - self.width() + 1)))
                pos.setY(max(area.top(), min(pos.y(), area.bottom() - self.height() + 1)))
            self.move(pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        self._drag_offset = None
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        self._drag_offset = None
        self._on_restore()
