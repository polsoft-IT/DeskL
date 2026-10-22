"""Okna dialogowe DeskL: dodawanie/edycja wpisu, ustawienia, informacje."""

import os
import sys

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import lang
from .utils import fetch_favicon, is_startup_enabled, native_icon, url_title
from .widgets import ToggleSwitch


class AddDialog(QDialog):
    """Okno dodawania i edycji wpisu (plik, folder lub adres internetowy)."""

    def __init__(self, parent=None, title=None, initial=None, ok_text=None, web=False,
                 dirs=None, on_dir_change=None):
        super().__init__(parent)
        title = title or lang.tr("add.title")
        ok_text = ok_text or lang.tr("action.add")
        self.setWindowTitle(title)
        self.selected_path = initial.get("path") if initial else None
        self.icon_path = initial.get("icon") if initial else None
        self.display_name = None
        self.tag = None
        self._initial = initial or {}
        self._web = bool(web)
        self._dirs = dirs if dirs is not None else {}
        self._on_dir_change = on_dir_change
        self._favicon_fetcher = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        link_edit = None
        self.link_edit = None
        if self._web:
            link_row = QHBoxLayout()
            link_row.setSpacing(8)
            link_edit = QLineEdit()
            link_edit.setPlaceholderText(lang.tr("add.link.placeholder"))
            link_edit.setStyleSheet("""
                QLineEdit {
                    padding: 6px 10px;
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    background-color: palette(base);
                }
                QLineEdit:focus {
                    border: 1px solid palette(highlight);
                }
            """)
            link_edit.textChanged.connect(self._on_link_changed)
            self.link_edit = link_edit
            link_row.addWidget(link_edit, 1)
            paste_btn = QPushButton(lang.tr("action.paste"))
            paste_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            paste_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 14px;
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    background-color: palette(button);
                    color: palette(button-text);
                }
                QPushButton:hover {
                    background-color: palette(button);
                    border: 1px solid palette(highlight);
                }
                QPushButton:pressed {
                    background-color: palette(mid);
                }
            """)
            paste_btn.clicked.connect(self._paste_link)
            link_row.addWidget(paste_btn)
            form.addRow(lang.tr("add.link"), link_row)
        else:
            type_row = QHBoxLayout()
            type_row.setSpacing(8)
            self.file_btn = QPushButton(lang.tr("add.file"))
            self.file_btn.clicked.connect(self._pick_file)
            self.file_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 14px;
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    background-color: palette(button);
                    color: palette(button-text);
                }
                QPushButton:hover {
                    background-color: palette(button);
                    border: 1px solid palette(highlight);
                }
                QPushButton:pressed {
                    background-color: palette(mid);
                }
            """)
            type_row.addWidget(self.file_btn)
            self.folder_btn = QPushButton(lang.tr("add.folder"))
            self.folder_btn.clicked.connect(self._pick_folder)
            self.folder_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 14px;
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    background-color: palette(button);
                    color: palette(button-text);
                }
                QPushButton:hover {
                    background-color: palette(button);
                    border: 1px solid palette(highlight);
                }
                QPushButton:pressed {
                    background-color: palette(mid);
                }
            """)
            type_row.addWidget(self.folder_btn)
            form.addRow(lang.tr("add.type"), type_row)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText(
            lang.tr("add.name.web") if self._web else lang.tr("add.name.file")
        )
        name_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(base);
            }
            QLineEdit:focus {
                border: 1px solid palette(highlight);
            }
        """)
        self.name_edit = name_edit
        form.addRow(lang.tr("add.name"), name_edit)

        tag_edit = QLineEdit()
        tag_edit.setPlaceholderText(lang.tr("add.tag.placeholder"))
        tag_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(base);
            }
            QLineEdit:focus {
                border: 1px solid palette(highlight);
            }
        """)
        self.tag_edit = tag_edit
        form.addRow(lang.tr("add.tag"), tag_edit)

        if self._initial:
            name_edit.setText(self._initial.get("name", ""))
            tag_edit.setText(self._initial.get("tag", ""))
            if link_edit is not None:
                link_edit.blockSignals(True)
                link_edit.setText(self._initial.get("path") or "")
                link_edit.blockSignals(False)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(28, 28)
        icon_row.addWidget(self.icon_preview)
        self.icon_edit = QLineEdit()
        self.icon_edit.setReadOnly(True)
        self.icon_edit.setPlaceholderText(
            lang.tr("add.icon.web") if self._web else lang.tr("add.icon.file")
        )
        self.icon_edit.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(alternate-base);
                color: palette(text);
            }
        """)
        icon_row.addWidget(self.icon_edit, 1)
        icon_btn = QPushButton(lang.tr("action.change"))
        icon_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(button);
                color: palette(button-text);
            }
            QPushButton:hover {
                background-color: palette(button);
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """)
        icon_btn.clicked.connect(self._browse_icon)
        icon_row.addWidget(icon_btn)
        reset_icon_btn = QPushButton(lang.tr("add.icon.default"))
        reset_icon_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        reset_icon_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 14px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(button);
                color: palette(button-text);
            }
            QPushButton:hover {
                background-color: palette(button);
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """)
        reset_icon_btn.clicked.connect(self._reset_icon)
        icon_row.addWidget(reset_icon_btn)
        if self._web:
            self.fetch_btn = QPushButton(lang.tr("add.icon.fetch"))
            self.fetch_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.fetch_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 14px;
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    background-color: palette(button);
                    color: palette(button-text);
                }
                QPushButton:hover {
                    background-color: palette(button);
                    border: 1px solid palette(highlight);
                }
                QPushButton:pressed {
                    background-color: palette(mid);
                }
            """)
            self.fetch_btn.clicked.connect(self._fetch_icon)
            icon_row.addWidget(self.fetch_btn)
        form.addRow(lang.tr("add.icon"), icon_row)

        layout.addLayout(form)
        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)
        cancel_btn = QPushButton(lang.tr("action.cancel"))
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(button);
                color: palette(button-text);
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: palette(button);
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        add_btn = QPushButton(ok_text)
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid palette(highlight);
                border-radius: 6px;
                background-color: palette(highlight);
                color: palette(highlighted-text);
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: palette(highlight);
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """)
        add_btn.clicked.connect(self.accept)
        btn_row.addWidget(add_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        if self._initial:
            self.icon_edit.setText(self._initial.get("icon") or "")
            self._refresh_preview()

    def _remember(self, kind, path):
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if folder:
            self._dirs[kind] = folder
            if self._on_dir_change is not None:
                self._on_dir_change()

    def _pick_file(self):
        path = QFileDialog.getOpenFileName(
            self, lang.tr("dialog.pick_file"), self._dirs.get("file", "")
        )[0]
        if path:
            self.selected_path = path
            self._remember("file", path)
            if not self.name_edit.text().strip():
                self.name_edit.setText(os.path.splitext(os.path.basename(path))[0])
            self._refresh_preview()

    def _pick_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, lang.tr("dialog.pick_folder"), self._dirs.get("folder", "")
        )
        if path:
            self.selected_path = path
            self._remember("folder", path)
            if not self.name_edit.text().strip():
                self.name_edit.setText(os.path.basename(path))
            self._refresh_preview()

    def _browse_icon(self):
        path = QFileDialog.getOpenFileName(
            self, lang.tr("dialog.pick_icon"), self._dirs.get("icon", ""),
            lang.tr("dialog.image_filter"),
        )[0]
        if path:
            self.icon_path = path
            self.icon_edit.setText(path)
            self._remember("icon", path)
            self._refresh_preview()

    def _paste_link(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.link_edit.setText(text)

    def _on_link_changed(self, text):
        self.selected_path = text.strip() or None
        self._refresh_preview()

    def _reset_icon(self):
        self.icon_path = None
        self.icon_edit.clear()
        self._refresh_preview()

    def _fetch_icon(self):
        """Pobiera favicon dla strony www."""
        if not self.selected_path:
            return
        # Czyść poprzedni fetcher jeśli istnieje
        if self._favicon_fetcher is not None:
            self._favicon_fetcher.deleteLater()
        # Zablokuj przycisk i pokaż ładowanie
        if hasattr(self, 'fetch_btn'):
            self.fetch_btn.setEnabled(False)
            self.fetch_btn.setText(lang.tr("add.icon.fetching"))
        self._favicon_fetcher = fetch_favicon(self.selected_path, self._on_favicon_fetched, self)

    def _on_favicon_fetched(self, icon_path):
        """Callback po pobraniu favicon."""
        if icon_path:
            self.icon_path = icon_path
            self.icon_edit.setText(icon_path)
            self._refresh_preview()
        # Odblokuj przycisk
        if hasattr(self, 'fetch_btn'):
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText(lang.tr("add.icon.fetch"))
        # Czyść fetcher po zakończeniu
        if self._favicon_fetcher is not None:
            self._favicon_fetcher.deleteLater()
            self._favicon_fetcher = None

    def _refresh_preview(self):
        if self.icon_path and os.path.exists(self.icon_path):
            icon = QIcon(self.icon_path)
        elif self.selected_path:
            icon = native_icon(self.selected_path)
        else:
            icon = QIcon()
        if icon.isNull():
            self.icon_preview.clear()
        else:
            self.icon_preview.setPixmap(icon.pixmap(QSize(24, 24)))

    def accept(self):
        if not self.selected_path:
            return
        name = self.name_edit.text().strip()
        if name:
            self.display_name = name
        elif self._web:
            self.display_name = url_title(self.selected_path)
        else:
            self.display_name = os.path.splitext(os.path.basename(self.selected_path))[0]
        self.tag = self.tag_edit.text().strip()
        # Czyść fetcher przed zamknięciem
        if self._favicon_fetcher is not None:
            self._favicon_fetcher.deleteLater()
            self._favicon_fetcher = None
        # Odblokuj przycisk jeśli był zablokowany
        if hasattr(self, 'fetch_btn'):
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText(lang.tr("add.icon.fetch"))
        super().accept()

    def reject(self):
        # Czyść fetcher przed zamknięciem
        if self._favicon_fetcher is not None:
            self._favicon_fetcher.deleteLater()
            self._favicon_fetcher = None
        # Odblokuj przycisk jeśli był zablokowany
        if hasattr(self, 'fetch_btn'):
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText(lang.tr("add.icon.fetch"))
        super().reject()

def _other_language():
    """Język alternatywny wobec domyślnego — cel przełącznika w ustawieniach."""
    for code in lang.available():
        if code != lang.DEFAULT:
            return code
    return lang.DEFAULT

def _switch_row(key, checked):
    """Wiersz ustawienia: etykieta z wtyczki językowej + przełącznik."""
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    label = QLabel(lang.tr(key))
    label.setWordWrap(True)
    lay.addWidget(label, 1)
    switch = ToggleSwitch(checked)
    lay.addWidget(switch, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return row, label, switch

class SettingsPopup(QDialog):
    """Kompaktowe okno popup z ustawieniami aplikacji."""

    def __init__(self, parent=None, dark=False, locked=True, startup=False,
                 language=None, on_dark=None, on_lock=None, on_startup=None,
                 on_language=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setFixedWidth(250)
        self._on_startup = on_startup
        self._on_language = on_language
        self._language = language or lang.current()
        self._labels = []

        self.setWindowTitle(lang.tr("settings.title"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        self.title = QLabel(lang.tr("settings.title"))
        f = self.title.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 1)
        self.title.setFont(f)
        layout.addWidget(self.title)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        dark_row, dark_label, self.dark_switch = _switch_row("settings.dark", dark)
        self._labels.append((dark_label, "settings.dark"))
        if on_dark is not None:
            self.dark_switch.toggled.connect(on_dark)
        layout.addWidget(dark_row)

        startup_row, startup_label, self.startup_switch = _switch_row(
            "settings.startup", startup
        )
        self._labels.append((startup_label, "settings.startup"))
        self.startup_switch.setEnabled(sys.platform == "win32")
        self.startup_switch.toggled.connect(self._on_startup_toggled)
        layout.addWidget(startup_row)

        lock_row, lock_label, self.lock_switch = _switch_row("settings.lock", locked)
        self._labels.append((lock_label, "settings.lock"))
        if on_lock is not None:
            self.lock_switch.toggled.connect(on_lock)
        layout.addWidget(lock_row)

        self._alt_language = _other_language()
        lang_row, self.lang_label, self.lang_switch = _switch_row(
            "settings.language", self._language == self._alt_language
        )
        self.lang_switch.setEnabled(self._alt_language != lang.DEFAULT)
        self.lang_switch.toggled.connect(self._on_language_toggled)
        layout.addWidget(lang_row)
        self._refresh_language_label()

    def _refresh_language_label(self):
        self.lang_label.setText("{}: {}".format(
            lang.tr("settings.language"), lang.language_name(self._language)
        ))

    def _on_language_toggled(self, checked):
        self._language = self._alt_language if checked else lang.DEFAULT
        if self._on_language is not None:
            self._on_language(self._language)
        self.retranslate()

    def retranslate(self):
        """Odświeża teksty popupu po zmianie języka."""
        self.setWindowTitle(lang.tr("settings.title"))
        self.title.setText(lang.tr("settings.title"))
        for label, key in self._labels:
            label.setText(lang.tr(key))
        self._refresh_language_label()

    def _on_startup_toggled(self, checked):
        if self._on_startup is None or self._on_startup(checked):
            return
        self.startup_switch.blockSignals(True)
        self.startup_switch.setChecked(is_startup_enabled())
        self.startup_switch.blockSignals(False)
        parent = self.parent()
        if parent is not None and hasattr(parent, "statusBar"):
            parent.statusBar().showMessage(lang.tr("settings.startup_failed"))

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(box, 10.0, 10.0)

        # Cień pod oknem
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 20))
        p.drawPath(path.translated(0.0, 1.5))

        # Rama okna
        pal = self.palette()
        p.setPen(QPen(pal.color(QPalette.ColorRole.Mid), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

class AboutPopup(QDialog):
    """Kompaktowe okno popup z informacjami o aplikacji."""

    RADIUS = 12.0
    HEADER_H = 60.0
    MARGIN = 16.0

    def __init__(self, parent=None, icon=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(280)

        pal = self.palette()
        dim = pal.color(QPalette.ColorRole.PlaceholderText).name()
        accent = pal.color(QPalette.ColorRole.Highlight).name()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(self.MARGIN), 10, int(self.MARGIN), 12)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)
        logo = QLabel()
        if icon is not None:
            logo.setPixmap(icon.pixmap(QSize(38, 38)))
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("DeskL")
        f = title.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 4)
        title.setFont(f)
        titles.addWidget(title)
        subtitle = QLabel(lang.tr("about.subtitle"))
        sf = subtitle.font()
        sf.setPointSize(max(7, sf.pointSize() - 1))
        subtitle.setFont(sf)
        subtitle.setStyleSheet(f"color: {dim};")
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        layout.addLayout(header)

        layout.addSpacing(10)

        desc = QLabel(lang.tr("about.description"))
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(9)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)
        fields = (
            ("author:", "Sebastian Januchowski", None),
            ("company:", "polsoft.ITS\u2122", None),
            ("email:", "polsoft.its@mail.com", "mailto:polsoft.its@mail.com"),
            ("GitHub:", "github.com/polsoft-it", "https://github.com/polsoft-it"),
        )
        for i, (name, value, href) in enumerate(fields):
            key = QLabel(name)
            key.setStyleSheet(f"color: {dim};")
            key.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(key, i, 0)
            if href:
                val = QLabel(f"<a style='color:{accent}; text-decoration:none;' href='{href}'>{value}</a>")
                val.setOpenExternalLinks(True)
                val.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            else:
                val = QLabel(value)
                val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(val, i, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        layout.addSpacing(7)

        meta = QLabel("Python {}  •  PyQt6".format(
            ".".join(str(v) for v in sys.version_info[:3])
        ))
        meta.setStyleSheet(f"color: {dim};")
        layout.addWidget(meta)

    def paintEvent(self, event):
        pal = self.palette()
        accent = pal.color(QPalette.ColorRole.Highlight)
        mid = pal.color(QPalette.ColorRole.Mid)
        base = pal.color(QPalette.ColorRole.Window)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(box, self.RADIUS, self.RADIUS)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        band = QColor(accent)
        band.setAlpha(46)
        p.fillRect(QRectF(box.left(), box.top(), box.width(), self.HEADER_H), band)
        p.fillRect(QRectF(box.left(), box.top(), 3.0, self.HEADER_H), accent)
        p.restore()

        pen = QPen(mid)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        y = box.top() + self.HEADER_H
        p.drawLine(QPointF(box.left() + 1.0, y), QPointF(box.right() - 1.0, y))


class KeyBadge(QWidget):
    """Pojedyncza plakietka klawisza w stylu klawiatury fizycznej (kbd)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        f = self.font()
        f.setFamily("Segoe UI, Consolas, sans-serif")
        f.setPointSize(max(8, f.pointSize() - 1))
        f.setBold(True)
        self.setFont(f)
        fm = self.fontMetrics()
        w = max(26, fm.horizontalAdvance(text) + 14)
        self.setFixedSize(w, 22)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pal = self.palette()
        fg = pal.color(QPalette.ColorRole.ButtonText)
        bg = pal.color(QPalette.ColorRole.AlternateBase)
        mid = pal.color(QPalette.ColorRole.Mid)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -1.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 4.0, 4.0)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawPath(path)

        p.setPen(QPen(mid, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Dolny akcent imitujący krawędź 3D klawisza
        shadow = mid.darker(125) if pal.color(QPalette.ColorRole.Window).lightness() > 128 else mid.lighter(130)
        p.setPen(QPen(shadow, 1.2))
        p.drawLine(
            QPointF(rect.left() + 3.0, rect.bottom() + 0.8),
            QPointF(rect.right() - 3.0, rect.bottom() + 0.8),
        )

        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(self.rect().adjusted(0, -1, 0, 0), Qt.AlignmentFlag.AlignCenter, self._text)


class QuitDialog(QDialog):
    """Ulepszone okno dialogowe potwierdzenia wyjścia."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("ask.quit.title"))
        self.setFixedWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Tytuł i ikona
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: palette(highlight);
                border-radius: 24px;
            }
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText("✕")
        icon_label.setStyleSheet("""
            QLabel {
                background-color: #FF5252;
                color: white;
                border-radius: 24px;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header.addWidget(icon_label)

        title = QLabel(lang.tr("ask.quit.title"))
        f = title.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 2)
        title.setFont(f)
        header.addWidget(title, 1)
        layout.addLayout(header)

        # Tekst pytania
        message = QLabel(lang.tr("ask.quit.text"))
        message.setWordWrap(True)
        message.setStyleSheet("color: palette(text); margin-top: 8px;")
        layout.addWidget(message)

        layout.addStretch(1)

        # Przyciski
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch(1)

        no_btn = QPushButton(lang.tr("action.cancel"))
        no_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        no_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                border: 1px solid palette(mid);
                border-radius: 6px;
                background-color: palette(button);
                color: palette(button-text);
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: palette(button);
                border: 1px solid palette(highlight);
            }
            QPushButton:pressed {
                background-color: palette(mid);
            }
        """)
        no_btn.clicked.connect(self.reject)
        btn_row.addWidget(no_btn)

        yes_btn = QPushButton(lang.tr("action.quit"))
        yes_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        yes_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 24px;
                border: 1px solid #FF5252;
                border-radius: 6px;
                background-color: #FF5252;
                color: white;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #FF1744;
                border: 1px solid #FF1744;
            }
            QPushButton:pressed {
                background-color: #D32F2F;
            }
        """)
        yes_btn.clicked.connect(self.accept)
        btn_row.addWidget(yes_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(box, 12.0, 12.0)

        # Cień pod oknem
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawPath(path.translated(0.0, 2.0))

        # Rama okna
        pal = self.palette()
        p.setPen(QPen(pal.color(QPalette.ColorRole.Mid), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


def _make_keys_widget(combo: str, parent: QWidget | None = None) -> QWidget:
    """Tworzy poziomy kontener ze stylizowanymi plakietkami klawiszy."""
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    parts = combo.split("+")
    for i, part in enumerate(parts):
        badge = KeyBadge(part.strip(), container)
        layout.addWidget(badge)
        if i < len(parts) - 1:
            plus = QLabel("+", container)
            plus.setStyleSheet("color: #888888; font-weight: bold;")
            layout.addWidget(plus)
    layout.addStretch(0)
    return container


def _make_keyboard_icon(accent_color: QColor) -> QPixmap:
    """Rysuje wektorową ikonę klawiatury dla nagłówka okna."""
    pm = QPixmap(36, 36)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(accent_color)
    p.drawRoundedRect(QRectF(1, 1, 34, 34), 8.0, 8.0)

    p.setPen(QPen(QColor(255, 255, 255), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    cx, cy = 18.0, 18.0
    w, h = 20.0, 13.0
    x0 = cx - w / 2.0
    y0 = cy - h / 2.0
    p.drawRoundedRect(QRectF(x0, y0, w, h), 2.2, 2.2)

    for ky in (y0 + 2.8, y0 + 6.8):
        for kx in (x0 + 2.4, x0 + 6.6, x0 + 10.8, x0 + 15.0):
            p.drawRoundedRect(QRectF(kx, ky, 2.6, 2.2), 0.6, 0.6)
    p.end()
    return pm


class ShortcutsPopup(QDialog):
    """Eleganckie okno popup prezentujące skróty klawiszowe aplikacji."""

    RADIUS = 12.0
    HEADER_H = 58.0
    MARGIN = 16.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(360)

        pal = self.palette()
        dim = pal.color(QPalette.ColorRole.PlaceholderText).name()
        accent = pal.color(QPalette.ColorRole.Highlight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(self.MARGIN), 10, int(self.MARGIN), 14)
        layout.setSpacing(0)

        # Nagłówek
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(_make_keyboard_icon(accent))
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel(lang.tr("shortcuts.title"))
        f = title.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 3)
        title.setFont(f)
        titles.addWidget(title)

        subtitle = QLabel(lang.tr("shortcuts.subtitle"))
        sf = subtitle.font()
        sf.setPointSize(max(7, sf.pointSize() - 1))
        subtitle.setFont(sf)
        subtitle.setStyleSheet(f"color: {dim};")
        titles.addWidget(subtitle)

        header.addLayout(titles, 1)
        layout.addLayout(header)

        layout.addSpacing(10)

        # Grupy skrótów
        groups = [
            ("shortcuts.group.entries", [
                ("Ctrl+N", "shortcuts.add"),
                ("Ctrl+T", "shortcuts.tab"),
                ("Enter", "shortcuts.open"),
                ("F2", "shortcuts.edit"),
                ("Delete", "shortcuts.delete"),
            ]),
            ("shortcuts.group.search", [
                ("Ctrl+F", "shortcuts.search"),
                ("Esc", "shortcuts.escape"),
            ]),
            ("shortcuts.group.config", [
                ("Ctrl+E", "shortcuts.export"),
                ("Ctrl+I", "shortcuts.import"),
            ]),
        ]

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        row = 0

        for group_key, items in groups:
            group_label = QLabel(lang.tr(group_key).upper())
            gf = group_label.font()
            gf.setPointSize(max(6, gf.pointSize() - 2))
            gf.setBold(True)
            group_label.setFont(gf)
            group_label.setStyleSheet(f"color: {accent.name()}; margin-top: 4px;")
            grid.addWidget(group_label, row, 0, 1, 2)
            row += 1

            for combo, text_key in items:
                keys_widget = _make_keys_widget(combo, self)
                grid.addWidget(keys_widget, row, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                desc_label = QLabel(lang.tr(text_key))
                df = desc_label.font()
                df.setPointSize(max(8, df.pointSize()))
                desc_label.setFont(df)
                grid.addWidget(desc_label, row, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                row += 1

        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        layout.addSpacing(10)

        # Stopka
        hint = QLabel(lang.tr("shortcuts.close_hint"))
        hint.setStyleSheet(f"color: {dim}; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def paintEvent(self, event) -> None:
        pal = self.palette()
        accent = pal.color(QPalette.ColorRole.Highlight)
        mid = pal.color(QPalette.ColorRole.Mid)
        base = pal.color(QPalette.ColorRole.Window)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(box, self.RADIUS, self.RADIUS)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        band = QColor(accent)
        band.setAlpha(46)
        p.fillRect(QRectF(box.left(), box.top(), box.width(), self.HEADER_H), band)
        p.fillRect(QRectF(box.left(), box.top(), 3.5, self.HEADER_H), accent)
        p.restore()

        pen = QPen(mid)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        y = box.top() + self.HEADER_H
        p.drawLine(QPointF(box.left() + 1.0, y), QPointF(box.right() - 1.0, y))


class UsageStatsPopup(QDialog):
    """Eleganckie okno popup prezentujące statystyki użycia wpisów."""

    RADIUS = 10.0
    HEADER_H = 56.0
    MARGIN = 14.0

    def __init__(self, parent=None, stats_data=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(360)

        pal = self.palette()
        dim = pal.color(QPalette.ColorRole.PlaceholderText)
        accent = pal.color(QPalette.ColorRole.Highlight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(self.MARGIN), 8, int(self.MARGIN), 12)
        layout.setSpacing(0)

        # Nagłówek
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(_make_keyboard_icon(accent))
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel(lang.tr("stats.title"))
        f = title.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 3)
        title.setFont(f)
        titles.addWidget(title)

        subtitle = QLabel(lang.tr("stats.subtitle"))
        sf = subtitle.font()
        sf.setPointSize(max(7, sf.pointSize() - 1))
        subtitle.setFont(sf)
        subtitle.setStyleSheet(f"color: {dim};")
        titles.addWidget(subtitle)

        header.addLayout(titles, 1)
        layout.addLayout(header)

        layout.addSpacing(10)

        # Dane statystyk
        if stats_data:
            total_entries = stats_data.get("total_entries", 0)
            total_launches = stats_data.get("total_launches", 0)
            tab_stats = stats_data.get("tab_stats", [])
            top_entries = stats_data.get("top_entries", [])

            # Podsumowanie
            summary_layout = QHBoxLayout()
            summary_layout.setSpacing(12)

            entries_box = self._stat_box(str(total_entries), lang.tr("stats.entries"), accent, dim)
            summary_layout.addWidget(entries_box, 1)

            launches_box = self._stat_box(str(total_launches), lang.tr("stats.launches"), accent, dim)
            summary_layout.addWidget(launches_box, 1)

            layout.addLayout(summary_layout)
            layout.addSpacing(12)

            # Statystyki według zakładek
            if tab_stats:
                tabs_label = QLabel(lang.tr("stats.by_tab"))
                gf = tabs_label.font()
                gf.setPointSize(max(6, gf.pointSize() - 2))
                gf.setBold(True)
                tabs_label.setFont(gf)
                tabs_label.setStyleSheet(f"color: {accent.name()}; margin-top: 4px;")
                layout.addWidget(tabs_label)

                tabs_grid = QGridLayout()
                tabs_grid.setContentsMargins(0, 4, 0, 0)
                tabs_grid.setHorizontalSpacing(8)
                tabs_grid.setVerticalSpacing(2)

                for i, (tab_name, count, uses) in enumerate(tab_stats):
                    name_label = QLabel(tab_name)
                    name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    tabs_grid.addWidget(name_label, i, 0)

                    count_label = QLabel(f"{count} {lang.tr('stats.entries_short')}, {uses} {lang.tr('stats.launches_short')}")
                    count_label.setStyleSheet(f"color: {dim.name()};")
                    count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                    tabs_grid.addWidget(count_label, i, 1)

                tabs_grid.setColumnStretch(1, 1)
                layout.addLayout(tabs_grid)
                layout.addSpacing(10)

            # Top 10
            if top_entries:
                top_label = QLabel(lang.tr("stats.top_10"))
                gf = top_label.font()
                gf.setPointSize(max(6, gf.pointSize() - 2))
                gf.setBold(True)
                top_label.setFont(gf)
                top_label.setStyleSheet(f"color: {accent.name()}; margin-top: 4px;")
                layout.addWidget(top_label)

                top_layout = QVBoxLayout()
                top_layout.setContentsMargins(0, 4, 0, 0)
                top_layout.setSpacing(3)

                for i, (name, uses, _tab) in enumerate(top_entries[:10], 1):
                    row = QWidget()
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(8)

                    rank = QLabel(str(i))
                    rank.setStyleSheet(f"color: {accent.name()}; font-weight: bold;")
                    rank.setFixedWidth(20)
                    row_layout.addWidget(rank)

                    item_name = QLabel(name)
                    item_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    item_name.setWordWrap(True)
                    row_layout.addWidget(item_name, 1)

                    item_uses = QLabel(str(uses))
                    item_uses.setStyleSheet(f"color: {dim.name()};")
                    row_layout.addWidget(item_uses)

                    top_layout.addWidget(row)

                layout.addLayout(top_layout)

        layout.addSpacing(8)

        # Stopka
        hint = QLabel(lang.tr("stats.close_hint"))
        hint.setStyleSheet(f"color: {dim.name()}; font-size: 10px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def _stat_box(self, value, label, accent_color, dim_color):
        """Tworzy box z liczbą i etykietą."""
        box = QWidget()
        box.setStyleSheet(f"""
            QWidget {{
                background-color: {accent_color.name()}20;
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        val_label = QLabel(value)
        vf = val_label.font()
        vf.setBold(True)
        vf.setPointSize(vf.pointSize() + 4)
        val_label.setFont(vf)
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_label.setStyleSheet(f"color: {accent_color.name()};")
        layout.addWidget(val_label)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {dim_color.name()}; font-size: 10px;")
        layout.addWidget(lbl)

        return box

    def paintEvent(self, event) -> None:
        pal = self.palette()
        accent = pal.color(QPalette.ColorRole.Highlight)
        mid = pal.color(QPalette.ColorRole.Mid)
        base = pal.color(QPalette.ColorRole.Window)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(box, self.RADIUS, self.RADIUS)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        band = QColor(accent)
        band.setAlpha(46)
        p.fillRect(QRectF(box.left(), box.top(), box.width(), self.HEADER_H), band)
        p.fillRect(QRectF(box.left(), box.top(), 3.5, self.HEADER_H), accent)
        p.restore()

        pen = QPen(mid)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        y = box.top() + self.HEADER_H
        p.drawLine(QPointF(box.left() + 1.0, y), QPointF(box.right() - 1.0, y))

