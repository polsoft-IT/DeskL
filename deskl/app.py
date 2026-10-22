"""DeskL — logika aplikacji: zakładki, wpisy, ustawienia i pętla zdarzeń."""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Callable, Iterable

from PyQt6.QtCore import QLockFile, QPoint, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QCursor,
    QIcon,
    QKeySequence,
    QPalette,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import config, lang
from .core import operations
from .dialogs import AboutPopup, AddDialog, QuitDialog, SettingsPopup, ShortcutsPopup
from .utils import (
    app_icon as make_app_icon,
)
from .utils import (
    copy_path_to_clipboard,
    is_broken_link,
    is_startup_enabled,
    is_url,
    native_icon,
    normalize_url,
    open_parent_folder,
    open_path,
    run_as_admin,
    set_startup,
    show_properties,
)
from .widgets import (
    TAG_ROLE,
    CornerButton,
    EntryList,
    EntryTabBar,
    FloatIcon,
    install_delegate,
    update_list_columns,
)

logger = logging.getLogger(__name__)

ICON_ROLE = Qt.ItemDataRole.UserRole + 2
USES_ROLE = Qt.ItemDataRole.UserRole + 3

# Akcje menu zasobnika: (akcja, klucz tekstu) — do odświeżania po zmianie języka.
TrayItem = tuple[QAction, str]
# Przyciski narożne: (przycisk, klucz tekstu) — do odświeżania po zmianie języka.
CornerItem = tuple[CornerButton, str]


class MainWindow(QMainWindow):
    """Okno główne — zamknięcie chowa je do zasobnika zamiast kończyć proces."""

    def __init__(self, on_close: Callable[[], None]) -> None:
        super().__init__()
        self._on_close = on_close

    def closeEvent(self, event: QCloseEvent | None) -> None:
        if event is not None:
            event.ignore()
        self._on_close()


class DeskLApp:
    """Aplikacja DeskL — cały stan (okno, zakładki, ustawienia) żyje w instancji."""

    def __init__(self) -> None:
        # Elementy UI — tworzone w build(); do tego czasu pozostają puste.
        self.app: QApplication | None = None
        self.window: MainWindow | None = None
        self.tabs: QTabWidget | None = None
        self.add_page: QWidget | None = None
        self.sidebar: QWidget | None = None
        self.toggle_btn: CornerButton | None = None
        self.top_btn: CornerButton | None = None
        self.sidebar_grid_btn: CornerButton | None = None
        self.sidebar_auto_btn: CornerButton | None = None
        self.search_edit: QLineEdit | None = None
        self.search_row: QWidget | None = None
        self.app_icon: QIcon | None = None
        self.tray: QSystemTrayIcon | None = None
        # Stan aplikacji.
        self._save_timer: QTimer | None = None
        self._float_icon: FloatIcon | None = None
        self._light_palette: QPalette = QPalette()
        self._default_style: str = ""
        self._sidebar_visible: bool = True
        self._window_locked: bool = True
        self._topmost: bool = False
        self._dark_mode: bool = False
        self._last_dirs: dict[str, str] = {"file": "", "folder": "", "icon": ""}
        self._corners: list[CornerItem] = []
        self._tray_items: list[TrayItem] = []
        self._save_failed: bool = False
        self._settings_popup: SettingsPopup | None = None

    # --- pomocnicze -------------------------------------------------------

    @staticmethod
    def _is_web_list(widget: QWidget | None) -> bool:
        return bool(widget is not None and widget.property("webMode"))

    def _corner(self, glyph: str, key: str) -> CornerButton:
        """Tworzy przycisk narożny, pamiętając klucz jego tekstu (dla i18n)."""
        btn = CornerButton(glyph, lang.tr(key))
        self._corners.append((btn, key))
        return btn

    # --- wpisy na listach -------------------------------------------------

    @staticmethod
    def _add_entry(
        path: str, display_name: str, icon_path: str | None,
        widget: QListWidget, tag: str = "", uses: int = 0,
    ) -> None:
        if not path:
            return
        item = QListWidgetItem(display_name or path)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setData(TAG_ROLE, tag or "")
        item.setData(ICON_ROLE, icon_path or "")
        item.setData(USES_ROLE, int(uses or 0))
        item.setToolTip(path)
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                item.setIcon(icon)
        else:
            item.setIcon(native_icon(path))
        # Zaznacz uszkodzone skróty (nieistniejące ścieżki) kolorem.
        if path and not is_url(path) and not os.path.exists(path):
            item.setForeground(QColor(200, 60, 60))
        widget.addItem(item)
        if widget.currentItem() is None:
            widget.setCurrentItem(item)

    @staticmethod
    def _update_entry(
        item: QListWidgetItem, path: str, display_name: str,
        icon_path: str | None, tag: str = "",
    ) -> None:
        if not path:
            return
        old_path = item.data(Qt.ItemDataRole.UserRole)
        item.setText(display_name or path)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setData(TAG_ROLE, tag or "")
        item.setData(ICON_ROLE, icon_path or "")
        item.setToolTip(path)
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                item.setIcon(icon)
                return
        if path != old_path or not icon_path:
            item.setIcon(native_icon(path))

    def _remove_entry(
        self, widget: QListWidget, item: QListWidgetItem, confirm: bool = True,
    ) -> None:
        if confirm:
            answer = QMessageBox.question(
                widget, lang.tr("ask.remove.title"),
                lang.tr("ask.remove.text", name=item.text()),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        widget.takeItem(widget.row(item))
        self._save_config()

    def _on_dropped(
        self, widget: QListWidget, pairs: Iterable[tuple[str, str]],
    ) -> None:
        for path, name in pairs:
            self._add_entry(path, name, None, widget)
        self._apply_filter()
        self._save_config()

    def _show_add_dialog(self, parent: QWidget | None, widget: QWidget | None) -> None:
        if not isinstance(widget, QListWidget):
            return
        dlg = AddDialog(
            parent, web=self._is_web_list(widget), dirs=self._last_dirs,
            on_dir_change=self._save_config,
        )
        if dlg.exec() == AddDialog.DialogCode.Accepted:
            self._add_entry(
                dlg.selected_path, dlg.display_name, dlg.icon_path, widget, dlg.tag,
            )
            self._apply_filter()
            self._save_config()

    def _show_edit_dialog(
        self, parent: QWidget | None, widget: QListWidget, item: QListWidgetItem,
    ) -> None:
        initial = {
            "path": item.data(Qt.ItemDataRole.UserRole),
            "name": item.text(),
            "tag": item.data(TAG_ROLE) or "",
            "icon": item.data(ICON_ROLE) or "",
        }
        dlg = AddDialog(
            parent, title=lang.tr("action.edit"), initial=initial,
            ok_text=lang.tr("action.save"),
            web=self._is_web_list(widget), dirs=self._last_dirs,
            on_dir_change=self._save_config,
        )
        if dlg.exec() == AddDialog.DialogCode.Accepted:
            self._update_entry(
                item, dlg.selected_path, dlg.display_name, dlg.icon_path, dlg.tag,
            )
            self._save_config()

    # --- widok i filtry ---------------------------------------------------

    @staticmethod
    def _set_view(tabs_widget: QTabWidget, mode: str) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        if mode == "icon":
            lw.setProperty("listMode", False)
            lw.setViewMode(QListView.ViewMode.IconMode)
            lw.setFlow(QListView.Flow.TopToBottom)
            lw.setWrapping(True)
            lw.setIconSize(QSize(48, 48))
            lw.setGridSize(QSize(96, 96))
        else:
            lw.setProperty("listMode", True)
            lw.setViewMode(QListView.ViewMode.IconMode)
            lw.setFlow(QListView.Flow.LeftToRight)
            lw.setWrapping(True)
            lw.setResizeMode(QListView.ResizeMode.Adjust)
            QTimer.singleShot(0, lambda: update_list_columns(lw))

    @staticmethod
    def _set_size(tabs_widget: QTabWidget, small: bool = False) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        if small:
            lw.setIconSize(QSize(16, 16))
            lw.setGridSize(QSize(64, 64))
        else:
            lw.setIconSize(QSize(48, 48))
            lw.setGridSize(QSize(96, 96))
        update_list_columns(lw)

    def _toggle_view(self, tabs_widget: QTabWidget) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        list_mode = bool(lw.property("listMode")) and lw.property("listMode") != "false"
        self._set_view(tabs_widget, "icon" if list_mode else "list")
        self._save_config()

    def _toggle_size(self, tabs_widget: QTabWidget) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        self._set_size(tabs_widget, lw.iconSize().width() > 20)
        self._save_config()

    @staticmethod
    def _apply_movement(lw: QListWidget) -> None:
        auto = lw.property("autoArrange") and lw.property("autoArrange") != "false"
        grid = lw.property("alignGrid") and lw.property("alignGrid") != "false"
        if auto:
            lw.setMovement(QListView.Movement.Static)
        elif grid:
            lw.setMovement(QListView.Movement.Snap)
        else:
            lw.setMovement(QListView.Movement.Free)

    def _set_align_grid(self, tabs_widget: QTabWidget, enabled: bool) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        lw.setProperty("alignGrid", enabled)
        self._apply_movement(lw)
        self._sync_sidebar()
        self._save_config()

    def _set_auto_arrange(self, tabs_widget: QTabWidget, enabled: bool) -> None:
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        lw.setProperty("autoArrange", enabled)
        self._apply_movement(lw)
        self._sync_sidebar()
        self._save_config()

    def _smart_sort(self, tabs_widget: QTabWidget) -> None:
        """Sortuje wpisy w aktywnej zakładce według częstotliwości użycia."""
        lw = tabs_widget.currentWidget()
        if not isinstance(lw, QListWidget):
            return

        # Zbierz wszystkie wpisy z ich danymi
        items_data = []
        for i in range(lw.count()):
            item = lw.item(i)
            if item is not None:
                items_data.append({
                    "item": item,
                    "path": item.data(Qt.ItemDataRole.UserRole),
                    "uses": item.data(USES_ROLE) or 0,
                    "name": item.text(),
                })

        # Sortuj według częstotliwości użycia (malejąco)
        items_data.sort(key=lambda x: x["uses"], reverse=True)

        # Przenieś wpisy w nowej kolejności
        for i, data in enumerate(items_data):
            lw.takeItem(lw.row(data["item"]))
            lw.insertItem(i, data["item"])

        self._save_config()
        if self.window is not None:
            self.window.statusBar().showMessage("Sorted by usage frequency", 3000)

    def _detect_broken_links(self) -> None:
        """Wykrywa uszkodzone linki we wszystkich zakładkach."""
        if self.tabs is None:
            return

        broken_count = 0
        broken_items = []

        for t in range(self.tabs.count()):
            lw = self.tabs.widget(t)
            if not isinstance(lw, QListWidget):
                continue

            for i in range(lw.count()):
                item = lw.item(i)
                if item is None:
                    continue
                path = item.data(Qt.ItemDataRole.UserRole)
                if is_broken_link(path):
                    broken_count += 1
                    broken_items.append((item, lw))
                    # Oznacz kolorem (już robione w _add_entry)

        if self.window is not None:
            if broken_count > 0:
                msg = f"Found {broken_count} broken link(s)"
                self.window.statusBar().showMessage(msg, 5000)
                # Pokaż szczegóły z opcją usunięcia
                details = "\n".join([f"- {item.text()}: {item.data(Qt.ItemDataRole.UserRole)}" for item, _ in broken_items[:10]])
                if len(broken_items) > 10:
                    details += f"\n... and {len(broken_items) - 10} more"

                reply = QMessageBox.question(
                    self.window,
                    lang.tr("ask.remove.title"),
                    f"{msg}:\n\n{details}\n\n{lang.tr('ask.broken.delete')}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Usuń wszystkie uszkodzone linki
                    for item, lw in broken_items:
                        lw.takeItem(lw.row(item))
                    self._save_config()
                    self.window.statusBar().showMessage(f"Removed {broken_count} broken link(s)", 3000)
            else:
                self.window.statusBar().showMessage("No broken links found", 3000)

    def _show_usage_statistics(self) -> None:
        """Wyświetla statystyki użycia wszystkich wpisów."""
        if self.tabs is None:
            return

        try:
            stats = []
            total_entries = 0
            total_uses = 0
            top_entries = []

            for t in range(self.tabs.count()):
                lw = self.tabs.widget(t)
                if not isinstance(lw, QListWidget):
                    continue

                tab_name = self.tabs.tabText(t)
                tab_uses = 0
                tab_count = lw.count()

                for i in range(lw.count()):
                    item = lw.item(i)
                    if item is None:
                        continue
                    uses = item.data(USES_ROLE) or 0
                    path = item.data(Qt.ItemDataRole.UserRole)
                    name = item.text()
                    tab_uses += uses
                    total_uses += uses
                    total_entries += 1

                    top_entries.append((name, path, uses, tab_name))

                stats.append((tab_name, tab_count, tab_uses))

            # Sortuj top entries by usage
            top_entries.sort(key=lambda x: x[2], reverse=True)
            top_10 = [(name, uses, tab) for name, _path, uses, tab in top_entries[:10]]

            # Przygotuj dane dla popupu
            stats_data = {
                "total_entries": total_entries,
                "total_launches": total_uses,
                "tab_stats": stats,
                "top_entries": top_10,
            }

            if self.window is not None:
                from .dialogs import UsageStatsPopup
                popup = UsageStatsPopup(self.window, stats_data)
                popup.exec()
        except Exception as e:
            logger.error("Error showing usage statistics: %s", e, exc_info=True)
            if self.window is not None:
                QMessageBox.warning(
                    self.window,
                    lang.tr("status.save_failed"),
                    f"Could not show statistics: {e}"
                )

    def _show_search(self, show: bool | None = None) -> None:
        """Pokazuje/ukrywa pole wyszukiwania w aktywnej zakładce."""
        if self.search_row is None or self.search_edit is None:
            return
        visible = (not self.search_row.isVisible()) if show is None else bool(show)
        self.search_row.setVisible(visible)
        if visible:
            self.search_edit.setFocus()
            self.search_edit.selectAll()
        else:
            self.search_edit.clear()
            self._apply_filter("")

    def _apply_filter(self, text: str | None = None) -> None:
        """Filtruje wpisy we wszystkich zakładkach po nazwie, ścieżce i tagu.

        Gdy wyszukiwanie jest aktywne, przechodzi do pierwszej zakładki z trafieniami
        (jeśli bieżąca nie ma żadnego), aby wynik był od razu widoczny.
        """
        if self.search_edit is None or self.tabs is None or self.window is None:
            return
        needle = operations.search_query(self.search_edit.text() if text is None else text)
        total = matches = 0
        per_tab: dict[int, int] = {}
        for t in range(self.tabs.count()):
            lw = self.tabs.widget(t)
            if not isinstance(lw, QListWidget):
                continue
            tab_matches = 0
            total += lw.count()
            lw.setUpdatesEnabled(False)
            try:
                for i in range(lw.count()):
                    item = lw.item(i)
                    if item is None:
                        continue
                    hay = operations.filter_haystack(
                        item.text(),
                        str(item.data(Qt.ItemDataRole.UserRole) or ""),
                        str(item.data(TAG_ROLE) or ""),
                    )
                    hit = not needle or needle in hay
                    should_hide = not hit
                    if item.isHidden() != should_hide:
                        item.setHidden(should_hide)
                    if hit:
                        tab_matches += 1
            finally:
                lw.setUpdatesEnabled(True)
            per_tab[t] = tab_matches
            matches += tab_matches
        if not needle:
            lw = self.tabs.currentWidget()
            self._show_tag(lw.currentItem() if isinstance(lw, QListWidget) else None)
            return
        if per_tab.get(self.tabs.currentIndex(), 0) == 0:
            for t in sorted(per_tab):
                if per_tab[t] > 0:
                    self.tabs.setCurrentIndex(t)
                    break
        self.window.statusBar().showMessage(
            lang.tr("status.found", done=matches, total=total)
        )

    # --- menu kontekstowe -------------------------------------------------

    def _add_tabs_submenu(self, menu: QMenu, tabs_widget: QTabWidget) -> QMenu:
        tabs_menu = menu.addMenu(lang.tr("menu.tabs"))
        for i in range(tabs_widget.count()):
            tab_widget = tabs_widget.widget(i)
            if not isinstance(tab_widget, QListWidget):
                continue
            sub = tabs_menu.addMenu(tabs_widget.tabText(i))
            sub.setEnabled(tab_widget.count() > 0)
            for j in range(tab_widget.count()):
                entry = tab_widget.item(j)
                if entry is None:
                    continue
                action = sub.addAction(entry.text())
                if not entry.icon().isNull():
                    action.setIcon(entry.icon())
                path_data = entry.data(Qt.ItemDataRole.UserRole)
                action.triggered.connect(
                    lambda _checked=False, p=path_data: open_path(p)
                )
        return tabs_menu

    def _show_context_menu(self, widget: QListWidget, pos: QPoint) -> None:
        menu = QMenu(widget)
        menu.setStyleSheet("""
            QMenu {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 26px;
                border-radius: 6px;
                min-width: 160px;
            }
            QMenu::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QMenu::separator {
                height: 1px;
                background-color: palette(mid);
                margin: 6px 10px;
            }
        """)
        add_action = menu.addAction(lang.tr("action.add"))
        add_action.triggered.connect(
            lambda: self._show_add_dialog(widget.window(), widget)
        )
        open_action = menu.addAction(lang.tr("action.open"))
        item = widget.itemAt(pos)
        open_action.setEnabled(item is not None)
        if item is not None:
            path = item.data(Qt.ItemDataRole.UserRole)
            open_action.triggered.connect(lambda: self._open_entry(item))
            edit_action = menu.addAction(lang.tr("action.edit"))
            edit_action.triggered.connect(
                lambda: self._show_edit_dialog(widget.window(), widget, item)
            )
            remove_action = menu.addAction(lang.tr("action.remove"))
            remove_action.triggered.connect(lambda: self._remove_entry(widget, item))

            # Quick Actions submenu
            if not is_url(path):
                quick_menu = menu.addMenu("Quick Actions")
                admin_action = quick_menu.addAction("Run as Administrator")
                admin_action.triggered.connect(lambda: run_as_admin(path))
                parent_action = quick_menu.addAction("Open Parent Folder")
                parent_action.triggered.connect(lambda: open_parent_folder(path))
                copy_path_action = quick_menu.addAction("Copy Path")
                copy_path_action.triggered.connect(lambda: copy_path_to_clipboard(path))
                menu.addSeparator()
                props_action = menu.addAction(lang.tr("action.properties"))
                props_action.triggered.connect(lambda: show_properties(path))
            else:
                copy_action = menu.addAction(lang.tr("action.copy_link"))
                copy_action.triggered.connect(
                    lambda: (
                        QApplication.clipboard().setText(normalize_url(path))
                        if QApplication.clipboard() is not None else None
                    )
                )
        tabs = self.tabs
        if tabs is not None:
            view_menu = menu.addMenu(lang.tr("menu.view"))
            view_menu.addAction(lang.tr("view.icons")).triggered.connect(
                lambda: self._set_view(tabs, "icon")
            )
            view_menu.addAction(lang.tr("view.list")).triggered.connect(
                lambda: self._set_view(tabs, "list")
            )
            view_menu.addSeparator()
            view_menu.addAction(lang.tr("view.small")).triggered.connect(
                lambda: self._set_size(tabs, True)
            )
            view_menu.addAction(lang.tr("view.large")).triggered.connect(
                lambda: self._set_size(tabs, False)
            )
            view_menu.addSeparator()
            grid_action = view_menu.addAction(lang.tr("view.grid"))
            grid_action.setCheckable(True)
            grid_action.setChecked(bool(widget.property("alignGrid")))
            grid_action.triggered.connect(
                lambda checked: self._set_align_grid(tabs, checked)
            )
            auto_action = view_menu.addAction(lang.tr("view.auto"))
            auto_action.setCheckable(True)
            auto_action.setChecked(bool(widget.property("autoArrange")))
            auto_action.triggered.connect(
                lambda checked: self._set_auto_arrange(tabs, checked)
            )
            view_menu.addSeparator()
            smart_sort_action = view_menu.addAction("Smart Sort (by usage)")
            smart_sort_action.triggered.connect(lambda: self._smart_sort(tabs))
        menu.exec(widget.mapToGlobal(pos))

    # --- konfiguracja -----------------------------------------------------

    def _save_config(self, delay: int = 300) -> None:
        """Planuje zapis konfiguracji (debounce), aby nie pisać pliku przy każdej zmianie."""
        if self._save_timer is None:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._write_config)
        self._save_timer.start(delay)

    def _flush_config(self) -> None:
        if self._save_timer is not None and self._save_timer.isActive():
            self._save_timer.stop()
        self._write_config()

    def _report_save_failure(self) -> None:
        """Pokazuje (raz) komunikat, że konfiguracji nie udało się zapisać."""
        if self._save_failed or self.window is None:
            return
        self._save_failed = True
        self.window.statusBar().showMessage(lang.tr("status.save_failed"), 8000)

    def _write_config(self) -> None:
        if self.tabs is None or self.window is None:
            return
        data: dict = {}
        for i in range(self.tabs.count()):
            lw = self.tabs.widget(i)
            if not isinstance(lw, QListWidget):
                continue
            tab_id = lw.property("tabId")
            if not tab_id:
                tab_id = uuid.uuid4().hex
                lw.setProperty("tabId", tab_id)
            items = []
            for j in range(lw.count()):
                item = lw.item(j)
                items.append({
                    "name": item.text(),
                    "path": item.data(Qt.ItemDataRole.UserRole),
                    "tag": item.data(TAG_ROLE) or "",
                    "icon": item.data(ICON_ROLE) or "",
                    "uses": item.data(USES_ROLE) or 0,
                })
            list_mode = bool(lw.property("listMode")) and lw.property("listMode") != "false"
            data[tab_id] = {
                "name": self.tabs.tabText(i),
                "items": items,
                "web": bool(lw.property("webMode")),
                "view": "list" if list_mode else "icon",
                "icon_size": lw.iconSize().width(),
                "grid": bool(lw.property("alignGrid")),
                "auto": bool(lw.property("autoArrange")),
            }
        data["_ui"] = {
            "sidebar": self._sidebar_visible,
            "language": lang.current(),
            "dark": self._dark_mode,
            "size": [self.window.width(), self.window.height()],
            "locked": self._window_locked,
            "topmost": self._topmost,
            "dirs": dict(self._last_dirs),
        }
        if config.write(data):
            self._save_failed = False
        else:
            self._report_save_failure()

    @staticmethod
    def _stored_language() -> str:
        """Kod języka zapisany w konfiguracji (albo domyślny z wtyczek)."""
        data = config.read()
        if isinstance(data, dict):
            ui = data.get("_ui")
            if isinstance(ui, dict) and isinstance(ui.get("language"), str):
                return ui["language"]
        return lang.DEFAULT

    def _load_config(self) -> None:
        if self.tabs is None or self.window is None:
            return
        data = config.read()
        if not isinstance(data, dict):
            return
        for key, section in data.items():
            if key.startswith("_"):
                continue
            if isinstance(section, dict):
                tab_id = key if section.get("name") else None
                name = section.get("name") or key
                entries = section.get("items", [])
            else:
                tab_id = None
                name = key
                entries = section
            lw = self._find_tab(tab_id, name)
            if lw is None:
                lw = self._create_tab(name, tab_id)
            elif tab_id and not lw.property("tabId"):
                lw.setProperty("tabId", tab_id)
            if isinstance(section, dict) and section.get("web"):
                lw.setProperty("webMode", True)
            for entry in entries:
                self._add_entry(
                    entry.get("path", ""), entry.get("name", ""),
                    entry.get("icon", ""), lw, entry.get("tag", ""),
                    entry.get("uses", 0),
                )
            if isinstance(section, dict):
                if section.get("view") == "icon":
                    lw.setProperty("listMode", False)
                    lw.setViewMode(QListView.ViewMode.IconMode)
                    lw.setFlow(QListView.Flow.TopToBottom)
                    lw.setWrapping(True)
                else:
                    lw.setProperty("listMode", True)
                    lw.setViewMode(QListView.ViewMode.IconMode)
                    lw.setFlow(QListView.Flow.LeftToRight)
                    lw.setWrapping(True)
                    lw.setResizeMode(QListView.ResizeMode.Adjust)
                size = section.get("icon_size", 48)
                if size <= 20:
                    lw.setIconSize(QSize(16, 16))
                    lw.setGridSize(QSize(64, 64))
                else:
                    lw.setIconSize(QSize(48, 48))
                    lw.setGridSize(QSize(96, 96))
                update_list_columns(lw)
                lw.setProperty("alignGrid", section.get("grid", False))
                lw.setProperty("autoArrange", section.get("auto", False))
                self._apply_movement(lw)
                lw.viewport().update()

        ui = data.get("_ui")
        if isinstance(ui, dict):
            self._sidebar_visible = bool(ui.get("sidebar", True))
            self.sidebar.setVisible(self._sidebar_visible)
            self.toggle_btn.blockSignals(True)
            self.toggle_btn.setChecked(self._sidebar_visible)
            self.toggle_btn.blockSignals(False)
            self._dark_mode = bool(ui.get("dark", False))
            if self._dark_mode:
                self._apply_theme()
            size = ui.get("size")
            if isinstance(size, list) and len(size) == 2:
                self.window.resize(int(size[0]), int(size[1]))
            self._window_locked = bool(ui.get("locked", True))
            self._topmost = bool(ui.get("topmost", False))
            self.top_btn.blockSignals(True)
            self.top_btn.setChecked(self._topmost)
            self.top_btn.blockSignals(False)
            if self._topmost:
                self._apply_topmost()
            dirs = ui.get("dirs")
            if isinstance(dirs, dict):
                for key in ("file", "folder", "icon"):
                    value = dirs.get(key)
                    if isinstance(value, str):
                        self._last_dirs[key] = value

    # --- wygląd i okno ----------------------------------------------------

    @staticmethod
    def _dark_palette() -> QPalette:
        text = QColor(240, 240, 240)
        dim = QColor(140, 140, 140)
        accent = QColor(66, 165, 245)  # Bardziej nowoczesny niebieski
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))  # Bardziej neutralna szarość
        p.setColor(QPalette.ColorRole.WindowText, text)
        p.setColor(QPalette.ColorRole.Base, QColor(35, 35, 38))
        p.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 55))
        p.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 65))
        p.setColor(QPalette.ColorRole.ToolTipText, text)
        p.setColor(QPalette.ColorRole.Text, text)
        p.setColor(QPalette.ColorRole.Button, QColor(50, 50, 55))
        p.setColor(QPalette.ColorRole.ButtonText, text)
        p.setColor(QPalette.ColorRole.BrightText, QColor(255, 100, 100))
        p.setColor(QPalette.ColorRole.Link, accent)
        p.setColor(QPalette.ColorRole.Highlight, accent)
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        p.setColor(QPalette.ColorRole.PlaceholderText, dim)
        p.setColor(QPalette.ColorRole.Light, QColor(100, 100, 105))
        p.setColor(QPalette.ColorRole.Midlight, QColor(60, 60, 65))
        p.setColor(QPalette.ColorRole.Mid, QColor(70, 70, 75))
        p.setColor(QPalette.ColorRole.Dark, QColor(30, 30, 33))
        p.setColor(QPalette.ColorRole.Shadow, QColor(20, 20, 23))
        for role in (
            QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText, QPalette.ColorRole.HighlightedText,
        ):
            p.setColor(QPalette.ColorGroup.Disabled, role, dim)
        return p

    def _apply_theme(self) -> None:
        if self.app is None:
            return
        if self._dark_mode:
            self.app.setStyle("Fusion")
            self.app.setPalette(self._dark_palette())
        else:
            if self._default_style:
                self.app.setStyle(self._default_style)
            self.app.setPalette(self._light_palette)

    def _set_dark_mode(self, enabled: bool) -> None:
        self._dark_mode = bool(enabled)
        self._apply_theme()
        self._save_config()

    def _apply_window_lock(self) -> None:
        if self.window is None:
            return
        if self._window_locked:
            self.window.setFixedSize(self.window.width(), self.window.height())
        else:
            self.window.setMinimumSize(QSize(0, 0))
            self.window.setMaximumSize(QSize(16777215, 16777215))

    def _set_window_lock(self, enabled: bool) -> None:
        self._window_locked = bool(enabled)
        self._apply_window_lock()
        self._save_config()

    def _apply_topmost(self) -> None:
        if self.window is None:
            return
        self.window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._topmost)
        self.window.show()

    def _set_topmost(self, enabled: bool) -> None:
        self._topmost = bool(enabled)
        self._apply_topmost()
        self._save_config()

    def _set_language(self, code: str) -> None:
        """Zmienia język interfejsu i zapisuje wybór w konfiguracji."""
        lang.set_language(code)
        self._save_config()
        self._retranslate()

    def _retranslate(self) -> None:
        """Odświeża teksty widocznych elementów po zmianie języka."""
        for button, key in self._corners:
            button.setToolTip(lang.tr(key))
        for action, key in self._tray_items:
            action.setText(lang.tr(key))
        if self.tabs is not None:
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                key = widget.property("nameKey") if widget is not None else ""
                if key:
                    self.tabs.setTabText(i, lang.tr(key))
                    self.tabs.setTabToolTip(i, lang.tr(key))
                    widget.setToolTip(lang.tr(key))
                if widget is not None:
                    widget.update()  # odświeża podpowiedź pustej zakładki
            if self.add_page is not None:
                self.tabs.setTabToolTip(
                    self.tabs.indexOf(self.add_page), lang.tr("tab.add"),
                )
        if self.search_edit is not None:
            self.search_edit.setPlaceholderText(lang.tr("search.placeholder"))
        if self._float_icon is not None:
            self._float_icon.retranslate()
        lw = self.tabs.currentWidget() if self.tabs is not None else None
        self._show_tag(lw.currentItem() if isinstance(lw, QListWidget) else None)

    # --- zakładki ---------------------------------------------------------

    @staticmethod
    def _make_list(web: bool = False) -> EntryList:
        lw = EntryList()
        lw.setProperty("webMode", bool(web))
        # Stan wyjściowy nowej zakładki — zapisywany później do konfiguracji.
        lw.setProperty("listMode", True)
        lw.setProperty("alignGrid", False)
        lw.setProperty("autoArrange", False)
        lw.setIconSize(QSize(48, 48))
        lw.setAcceptDrops(True)
        lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        return lw

    def _bind_list(self, lw: EntryList) -> EntryList:
        """Podpina sygnały listy do akcji aplikacji."""
        lw.customContextMenuRequested.connect(
            lambda pos, w=lw: self._show_context_menu(w, pos)
        )
        lw.itemDoubleClicked.connect(
            lambda item: self._open_entry(item)
        )
        lw.entriesDropped.connect(lambda pairs, w=lw: self._on_dropped(w, pairs))
        lw.currentItemChanged.connect(lambda cur, prev: self._show_tag(cur))
        lw.setViewportMargins(6, 0, 0, 0)
        install_delegate(lw)
        return lw

    def _find_tab(self, tab_id: str | None, name: str | None = None) -> EntryList | None:
        if self.tabs is None:
            return None
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, QListWidget) and tab_id and w.property("tabId") == tab_id:
                return w
        if name:
            for i in range(self.tabs.count()):
                w = self.tabs.widget(i)
                if isinstance(w, QListWidget) and self.tabs.tabText(i) == name:
                    return w
        return None

    @staticmethod
    def _name_tab(lw: EntryList, key: str) -> EntryList:
        """Naznacza zakładkę nazwą domyślną (klucz tekstu), tłumaczoną z językiem."""
        lw.setProperty("nameKey", key or "")
        lw.setToolTip(lang.tr(key))
        return lw

    def _create_tab(self, name: str | None = None, tab_id: str | None = None) -> EntryList:
        if self.tabs is None:
            raise RuntimeError("Interfejs nie został jeszcze zbudowany")
        if name is None:
            name = lang.tr("tab.new")
            key = "tab.new"
        else:
            key = ""
        lw = self._bind_list(self._name_tab(self._make_list(), key))
        lw.setProperty("tabId", tab_id or uuid.uuid4().hex)
        idx = self.tabs.indexOf(self.add_page)
        if idx < 0:
            idx = self.tabs.count()
        self.tabs.insertTab(idx, lw, name)
        self.tabs.setTabToolTip(idx, name)
        return lw

    def _new_tab(self) -> None:
        """Tworzy nową zakładkę (skrót Ctrl+T)."""
        self.tabs.setCurrentWidget(self._create_tab())
        self._save_config()

    def _move_entries(
        self, source: QListWidget, target: QListWidget,
        items: Iterable[QListWidgetItem],
    ) -> None:
        """Przenosi wpisy z jednej zakładki do drugiej i utrwala zmiany."""
        moved = False
        for item in list(items):
            path = item.data(Qt.ItemDataRole.UserRole)
            row = source.row(item)
            if not path or row < 0:
                continue
            data_items = operations.move_entries_items([
                (
                    path,
                    item.text(),
                    item.data(ICON_ROLE) or "",
                    item.data(TAG_ROLE) or "",
                    item.data(USES_ROLE) or 0,
                )
            ])
            for p, dname, iconp, tagv, usesv in data_items:
                self._add_entry(p, dname, iconp, target, tagv, usesv)
            source.takeItem(row)
            moved = True
        if moved:
            self._apply_filter()
            self._save_config()

    def _on_tab_entry_dropped(
        self, index: int, source: QListWidget, items: list[QListWidgetItem],
    ) -> None:
        """Obsługuje wpisy upuszczone na etykietę zakładki (przenoszenie między zakładkami)."""
        if self.tabs is None:
            return
        target = self.tabs.widget(index)
        if not isinstance(target, QListWidget) or not isinstance(source, QListWidget):
            return
        if target is source or not items:
            return
        self.tabs.setCurrentIndex(index)
        self._move_entries(source, target, items)

    def _on_tab_changed(self, idx: int) -> None:
        if self.tabs is None:
            return
        if self.tabs.widget(idx) is self.add_page:
            lw = self._create_tab()
            self.tabs.setCurrentWidget(lw)
            self._save_config()
        QTimer.singleShot(0, lambda: update_list_columns(self.tabs.currentWidget()))
        self._sync_sidebar()
        self._apply_filter()

    def _rename_tab(self, idx: int) -> None:
        if self.tabs is None:
            return
        name, ok = QInputDialog.getText(
            self.tabs, lang.tr("rename.title"), lang.tr("rename.label"),
            text=self.tabs.tabText(idx),
        )
        name = name.strip()
        if ok and name:
            self.tabs.setTabText(idx, name)
            self.tabs.setTabToolTip(idx, name)
            # Nazwa nadana przez użytkownika przestaje być tłumaczona.
            w = self.tabs.widget(idx)
            if isinstance(w, QListWidget):
                w.setProperty("nameKey", "")
                w.setToolTip(name)
            self._save_config()

    def _close_tab(self, idx: int) -> None:
        if self.tabs is None:
            return
        w = self.tabs.widget(idx)
        if w is self.add_page:
            return
        if isinstance(w, QListWidget) and w.count() > 0:
            answer = QMessageBox.question(
                self.tabs, lang.tr("ask.close_tab.title"),
                lang.tr("ask.close_tab.text", name=self.tabs.tabText(idx), n=w.count()),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self.tabs.currentIndex() == idx and idx > 0:
            self.tabs.setCurrentIndex(idx - 1)
        self.tabs.removeTab(idx)
        w.deleteLater()
        self._save_config()

    def _show_tab_menu(self, pos: QPoint) -> None:
        if self.tabs is None:
            return
        tab_bar = self.tabs.tabBar()
        idx = tab_bar.tabAt(pos)
        if idx < 0 or self.tabs.widget(idx) is self.add_page:
            return
        menu = QMenu(self.tabs)
        menu.addAction(lang.tr("action.edit")).triggered.connect(
            lambda: self._rename_tab(idx)
        )
        menu.addAction(lang.tr("action.remove")).triggered.connect(
            lambda: self._close_tab(idx)
        )
        menu.exec(tab_bar.mapToGlobal(pos))

    def _on_tab_moved(self, from_idx: int, to_idx: int) -> None:
        if self.tabs is None:
            return
        add_idx = self.tabs.indexOf(self.add_page)
        if 0 <= add_idx < self.tabs.count() - 1:
            self.tabs.tabBar().moveTab(add_idx, self.tabs.count() - 1)
        self._save_config()

    def _sync_sidebar(self) -> None:
        if self.tabs is None or self.sidebar_grid_btn is None or self.sidebar_auto_btn is None:
            return
        lw = self.tabs.currentWidget()
        if not isinstance(lw, QListWidget):
            return
        for btn, prop in (
            (self.sidebar_grid_btn, "alignGrid"),
            (self.sidebar_auto_btn, "autoArrange"),
        ):
            btn.blockSignals(True)
            btn.setChecked(bool(lw.property(prop)))
            btn.blockSignals(False)

    def _toggle_sidebar(self, visible: bool) -> None:
        self._sidebar_visible = visible
        self.sidebar.setVisible(visible)
        self._save_config()

    def _show_tag(self, item: QListWidgetItem | None) -> None:
        tag = (item.data(TAG_ROLE) or "") if item is not None else ""
        if self.window is not None:
            self.window.statusBar().showMessage(tag if tag else lang.tr("status.ready"))

    # --- zwijanie do ikonki -----------------------------------------------

    def _collapse_to_icon(self) -> None:
        if self.window is None:
            return
        if self._float_icon is None:
            self._float_icon = FloatIcon(
                self._restore_window, self.app_icon,
                lambda menu: self._add_tabs_submenu(menu, self.tabs), self._quit_app,
            )
        geo = self.window.frameGeometry()
        # Ekran, na którym stoi okno (nie zawsze główny) — inaczej na multi-monitorze
        # ikonka wylądowałaby poza ekranem z aktywnym oknem.
        screen = self.window.screen() or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(geo.right() - self._float_icon.width() + 1,
                area.right() - self._float_icon.width() + 1)
        y = min(geo.top(), area.bottom() - self._float_icon.height() + 1)
        self._float_icon.move(max(x, area.left()), max(y, area.top()))
        self.window.hide()
        self._float_icon.show()
        self._float_icon.raise_()

    def _restore_window(self) -> None:
        if self._float_icon is not None:
            self._float_icon.hide()
        if self.window is None:
            return
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _toggle_window(self) -> None:
        if self.window is None:
            return
        if self.window.isVisible():
            self.window.hide()
        else:
            self._restore_window()

    def _on_window_closed(self) -> None:
        """Zamknięcie okna: zapis konfiguracji i schowanie do zasobnika."""
        self._save_config()
        if self.window is not None:
            self.window.hide()

    def _quit_app(self) -> None:
        """Kończy aplikację po potwierdzeniu użytkownika (wyjście z zasobnika/ikonki)."""
        if self.app is None:
            return
        dlg = QuitDialog(self.window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app.quit()

    # --- akcje bieżącego wpisu (skróty klawiszowe) ------------------------

    def _current_entry(self) -> tuple[QListWidget | None, QListWidgetItem | None]:
        if self.tabs is None:
            return None, None
        lw = self.tabs.currentWidget()
        if not isinstance(lw, QListWidget):
            return None, None
        return lw, lw.currentItem()

    def _open_entry(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        open_path(path)
        uses = (item.data(USES_ROLE) or 0) + 1
        item.setData(USES_ROLE, uses)
        self._save_config()

    def _export_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self.window, "Eksportuj konfigurację", "deskl_backup.json",
            "JSON (*.json)",
        )
        if not path:
            return
        data = config.read()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if self.window is not None:
                self.window.statusBar().showMessage("Wyeksportowano konfigurację", 5000)
        except (OSError, TypeError, ValueError):
            self._report_save_failure()

    def _import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window, "Importuj konfigurację", "", "JSON (*.json)",
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and config.write(data):
                self._load_config()
                if self.window is not None:
                    self.window.statusBar().showMessage("Zaimportowano konfigurację", 5000)
        except (OSError, json.JSONDecodeError):
            self._report_save_failure()

    def _open_current_entry(self) -> None:
        _lw, item = self._current_entry()
        if item is not None:
            self._open_entry(item)

    def _edit_current_entry(self) -> None:
        lw, item = self._current_entry()
        if lw is not None and item is not None:
            self._show_edit_dialog(self.window, lw, item)

    def _delete_current_entry(self) -> None:
        lw, item = self._current_entry()
        if lw is not None and item is not None:
            self._remove_entry(lw, item)

    def _setup_shortcuts(self, win: QMainWindow) -> None:
        def add(
            sequence: str, handler: Callable[[], None],
            context: Qt.ShortcutContext, parent: QWidget | None = None,
        ) -> QShortcut:
            shortcut = QShortcut(QKeySequence(sequence), parent or win)
            shortcut.setContext(context)
            shortcut.activated.connect(handler)
            return shortcut

        add("Ctrl+N", lambda: self._show_add_dialog(win, self.tabs.currentWidget() if self.tabs else None),
            Qt.ShortcutContext.WindowShortcut)
        add("Ctrl+T", self._new_tab, Qt.ShortcutContext.WindowShortcut)
        add("Ctrl+F", self._show_search, Qt.ShortcutContext.WindowShortcut)
        add("Escape", lambda: self._show_search(False),
            Qt.ShortcutContext.WindowShortcut)
        add("Return", self._open_current_entry,
            Qt.ShortcutContext.WidgetWithChildrenShortcut, self.tabs)
        add("Enter", self._open_current_entry,
            Qt.ShortcutContext.WidgetWithChildrenShortcut, self.tabs)
        add("F2", self._edit_current_entry,
            Qt.ShortcutContext.WidgetWithChildrenShortcut, self.tabs)
        add("Delete", self._delete_current_entry,
            Qt.ShortcutContext.WidgetWithChildrenShortcut, self.tabs)
        add("Ctrl+E", self._export_config, Qt.ShortcutContext.WindowShortcut)
        add("Ctrl+I", self._import_config, Qt.ShortcutContext.WindowShortcut)

    def _show_settings(self, anchor: QWidget) -> None:
        popup = SettingsPopup(
            self.window,
            dark=self._dark_mode,
            locked=self._window_locked,
            startup=is_startup_enabled(),
            language=lang.current(),
            on_dark=self._set_dark_mode,
            on_lock=self._set_window_lock,
            on_startup=set_startup,
            on_language=self._set_language,
        )
        self._settings_popup = popup
        popup.adjustSize()
        pos = anchor.mapToGlobal(QPoint(anchor.width() + 4, anchor.height()))
        popup.move(pos.x(), pos.y() - popup.height())
        popup.exec()
        self._settings_popup = None

    @staticmethod
    def _place_at_cursor(popup: QWidget) -> None:
        """Umieszcza popup nad kursorem, w granicach ekranu.

        Menu zasobnika otwiera się przy zegarze, więc popup musi trafić ponad
        kursor — inaczej wylądowałby pod paskiem zadań i byłby niewidoczny.
        """
        cursor = QCursor.pos()
        screen = QApplication.screenAt(cursor) or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            x = cursor.x() - popup.width()
            y = cursor.y() - popup.height()
            x = max(area.left(), min(x, area.right() - popup.width() + 1))
            y = max(area.top(), min(y, area.bottom() - popup.height() + 1))
            popup.move(x, y)
        else:
            popup.move(cursor)

    def _show_shortcuts(self, anchor: QWidget | None = None) -> None:
        popup = ShortcutsPopup(self.window)
        popup.adjustSize()
        if anchor is None:
            self._place_at_cursor(popup)
        else:
            pos = anchor.mapToGlobal(QPoint(anchor.width() + 4, anchor.height()))
            pos.setY(pos.y() - popup.height())
            popup.move(pos)
        popup.exec()

    def _show_about(self, anchor: QWidget | None = None) -> None:
        popup = AboutPopup(self.window, self.app_icon)
        popup.adjustSize()
        if anchor is None:
            self._place_at_cursor(popup)
        else:
            pos = anchor.mapToGlobal(QPoint(anchor.width() + 4, anchor.height()))
            pos.setY(pos.y() - popup.height())
            popup.move(pos)
        popup.exec()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_window()

    # --- start ------------------------------------------------------------

    def build(self) -> None:
        """Tworzy QApplication, okno i wszystkie widżety (bez uruchamiania pętli)."""
        self.app = QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)
        self._light_palette = self.app.palette()
        self._default_style = self.app.style().objectName()

        # Język musi być ustawiony przed budową UI, aby teksty były spójne.
        self._corners.clear()
        self._tray_items.clear()
        lang.set_language(self._stored_language())

        tabs = QTabWidget()
        tabs.setTabBar(EntryTabBar(tabs))
        apps_list = self._bind_list(self._name_tab(self._make_list(), "tab.apps"))
        www_list = self._bind_list(self._name_tab(self._make_list(web=True), "tab.www"))
        files_list = self._bind_list(self._name_tab(self._make_list(), "tab.files"))
        tabs.addTab(apps_list, lang.tr("tab.apps"))
        tabs.addTab(www_list, lang.tr("tab.www"))
        tabs.addTab(files_list, lang.tr("tab.files"))

        add_page = QWidget()
        tabs.addTab(add_page, "+")
        tabs.setTabToolTip(tabs.indexOf(add_page), lang.tr("tab.add"))

        tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tabs.setMovable(True)
        self.tabs = tabs
        self.add_page = add_page

        tabs.tabBar().customContextMenuRequested.connect(self._show_tab_menu)
        tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        tabs.tabBar().entryDropped.connect(self._on_tab_entry_dropped)
        tabs.currentChanged.connect(self._on_tab_changed)

        corner = QWidget()
        corner_layout = QHBoxLayout(corner)
        corner_layout.setContentsMargins(0, 0, 2, 0)
        corner_layout.setSpacing(1)

        mini_btn = self._corner("mini", "tip.mini")
        mini_btn.clicked.connect(self._collapse_to_icon)
        corner_layout.addWidget(mini_btn)

        self.top_btn = self._corner("pin", "tip.topmost")
        self.top_btn.setCheckable(True)
        self.top_btn.toggled.connect(self._set_topmost)
        corner_layout.addWidget(self.top_btn)

        corner.setLayout(corner_layout)
        tabs.setCornerWidget(corner)

        sidebar = QWidget()
        sidebar.setFixedWidth(28)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(2, 4, 2, 4)
        sidebar_layout.setSpacing(3)
        self.sidebar = sidebar

        sidebar_add_btn = self._corner("add", "tip.add")
        sidebar_add_btn.clicked.connect(
            lambda: self._show_add_dialog(self.window, self.tabs.currentWidget())
        )
        sidebar_layout.addWidget(sidebar_add_btn)

        sidebar_search_btn = self._corner("search", "tip.search")
        sidebar_search_btn.clicked.connect(lambda: self._show_search())
        sidebar_layout.addWidget(sidebar_search_btn)

        sidebar_broken_btn = self._corner("warn", "Broken Links")
        sidebar_broken_btn.clicked.connect(lambda: self._detect_broken_links())
        sidebar_layout.addWidget(sidebar_broken_btn)

        sidebar_stats_btn = self._corner("chart", "Usage Stats")
        sidebar_stats_btn.clicked.connect(lambda: self._show_usage_statistics())
        sidebar_layout.addWidget(sidebar_stats_btn)

        sidebar_layout.addStretch(1)

        self.sidebar_auto_btn = self._corner("auto", "tip.auto")
        self.sidebar_auto_btn.setCheckable(True)
        self.sidebar_auto_btn.toggled.connect(
            lambda checked: self._set_auto_arrange(self.tabs, checked)
        )
        sidebar_layout.addWidget(self.sidebar_auto_btn)

        self.sidebar_grid_btn = self._corner("grid", "tip.grid")
        self.sidebar_grid_btn.setCheckable(True)
        self.sidebar_grid_btn.toggled.connect(
            lambda checked: self._set_align_grid(self.tabs, checked)
        )
        sidebar_layout.addWidget(self.sidebar_grid_btn)

        sidebar_size_btn = self._corner("size", "tip.size")
        sidebar_size_btn.clicked.connect(lambda: self._toggle_size(self.tabs))
        sidebar_layout.addWidget(sidebar_size_btn)

        sidebar_view_btn = self._corner("view", "tip.view")
        sidebar_view_btn.clicked.connect(lambda: self._toggle_view(self.tabs))
        sidebar_layout.addWidget(sidebar_view_btn)

        sidebar_layout.addSpacing(10)

        sidebar_sep = QFrame()
        sidebar_sep.setFrameShape(QFrame.Shape.HLine)
        sidebar_sep.setFrameShadow(QFrame.Shadow.Sunken)
        sidebar_layout.addWidget(sidebar_sep)

        sidebar_layout.addSpacing(6)

        sidebar_settings_btn = self._corner("gear", "tip.settings")
        sidebar_settings_btn.clicked.connect(
            lambda: self._show_settings(sidebar_settings_btn)
        )
        sidebar_layout.addWidget(sidebar_settings_btn)

        sidebar_shortcuts_btn = self._corner("kbd", "tip.shortcuts")
        sidebar_shortcuts_btn.clicked.connect(
            lambda: self._show_shortcuts(sidebar_shortcuts_btn)
        )
        sidebar_layout.addWidget(sidebar_shortcuts_btn)

        sidebar_about_btn = self._corner("info", "tip.about")
        sidebar_about_btn.clicked.connect(lambda: self._show_about(sidebar_about_btn))
        sidebar_layout.addWidget(sidebar_about_btn)

        self.toggle_btn = self._corner("sidebar", "tip.sidebar")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(self._sidebar_visible)
        self.toggle_btn.toggled.connect(self._toggle_sidebar)

        left_corner = QWidget()
        left_corner_layout = QHBoxLayout(left_corner)
        left_corner_layout.setContentsMargins(8, 0, 2, 0)
        left_corner_layout.setSpacing(0)
        left_corner_layout.addWidget(self.toggle_btn)
        tabs.setCornerWidget(left_corner, Qt.Corner.TopLeftCorner)

        sidebar.setVisible(self._sidebar_visible)

        search_row = QWidget()
        search_layout = QHBoxLayout(search_row)
        search_layout.setContentsMargins(6, 3, 6, 3)
        search_layout.setSpacing(0)
        search_edit = QLineEdit()
        search_edit.setPlaceholderText(lang.tr("search.placeholder"))
        search_edit.setClearButtonEnabled(True)
        search_edit.setFixedHeight(26)
        search_edit.setStyleSheet("""
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
        search_edit.textChanged.connect(self._apply_filter)
        search_layout.addWidget(search_edit)
        search_row.setVisible(False)
        self.search_row = search_row
        self.search_edit = search_edit

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(search_row)
        right_layout.addWidget(tabs, 1)

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(sidebar)
        container_layout.addWidget(right, 1)

        window = MainWindow(self._on_window_closed)
        window.setCentralWidget(container)
        window.setWindowTitle("DeskL")
        window.resize(600, 400)
        window.statusBar().showMessage(lang.tr("status.ready"))
        self.window = window

        self._setup_shortcuts(window)

        self.app_icon = make_app_icon()
        self.app.setWindowIcon(self.app_icon)
        window.setWindowIcon(self.app_icon)

        self._load_config()
        self._apply_window_lock()
        window.show()

        tray = QSystemTrayIcon(self.app_icon, window)
        tray.setToolTip("DeskL")
        tray.activated.connect(self._on_tray_activated)
        tray_menu = QMenu()
        show_action = tray_menu.addAction(lang.tr("action.toggle_window"))
        show_action.triggered.connect(self._toggle_window)
        tray_menu.addSeparator()
        about_action = tray_menu.addAction(lang.tr("action.about"))
        about_action.triggered.connect(lambda: self._show_about())
        quit_action = tray_menu.addAction(lang.tr("action.quit"))
        quit_action.triggered.connect(self._quit_app)
        self._tray_items.extend((
            (show_action, "action.toggle_window"),
            (about_action, "action.about"),
            (quit_action, "action.quit"),
        ))
        tray.setContextMenu(tray_menu)
        tray.show()
        self.tray = tray

        self.app.aboutToQuit.connect(self._flush_config)

    def run(self) -> int:
        """Buduje interfejs i uruchamia pętlę zdarzeń."""
        self.build()
        if self.app is None:
            return 0
        return self.app.exec()


def main() -> int:
    """Punkt wejścia aplikacji."""
    # Sprawdź czy aplikacja jest już uruchomiona
    lock_file = QLockFile("DeskL.lock")
    if not lock_file.tryLock(100):
        # Aplikacja jest już uruchomiona
        print("DeskL is already running")
        return 1

    try:
        return DeskLApp().run()
    finally:
        lock_file.unlock()
