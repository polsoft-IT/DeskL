"""Funkcje pomocnicze DeskL: adresy, ikony, powłoka Windows i autostart."""

import ctypes
import os
import sys
import webbrowser
import winreg
from ctypes import wintypes
from urllib.parse import urlparse

from PyQt6.QtCore import QFileInfo, QPointF, QRectF, Qt, QUrl
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt6.QtWidgets import QApplication, QFileIconProvider

from .config import data_dir

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY_SCRIPT = os.path.join(PROJECT_ROOT, "DeskL.pyw")

_STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_NAME = "DeskL"

_link_icon_cache = None
_app_icon_cache = None
_icon_provider = None

def is_url(value):
    v = (value or "").strip().lower()
    return v.startswith(("http://", "https://", "ftp://", "www."))

def normalize_url(value):
    v = (value or "").strip()
    if v.lower().startswith("www."):
        v = "https://" + v
    return v

def url_title(value):
    url = normalize_url(value)
    host = urlparse(url).netloc or url
    if host.lower().startswith("www."):
        host = host[4:]
    return host or url

def open_path(path):
    if not path:
        return
    if is_url(path):
        webbrowser.open(normalize_url(path))
    elif sys.platform == "win32":
        os.startfile(path)

def show_properties(path):
    SEE_MASK_INVOKEIDLIST = 0x0000000C

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_INVOKEIDLIST
    info.lpVerb = "properties"
    info.lpFile = path
    info.nShow = 1
    ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info))

def link_icon():
    """Wektorowa ikona globusa dla skrótów internetowych."""
    global _link_icon_cache
    if _link_icon_cache is not None:
        return _link_icon_cache
    col = QColor(0, 120, 215)
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(col)
        pen.setWidthF(max(1.0, size * 0.055))
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = size / 2.0
        r = c - pen.widthF()
        p.drawEllipse(QPointF(c, c), r, r)
        p.drawEllipse(QRectF(c - r * 0.45, c - r, r * 0.9, r * 2.0))
        p.drawLine(QPointF(c - r, c), QPointF(c + r, c))
        for k in (-0.55, 0.55):
            y = c + k * r
            x = r * (1.0 - k * k) ** 0.5
            p.drawLine(QPointF(c - x, y), QPointF(c + x, y))
        p.end()
        icon.addPixmap(pm)
    _link_icon_cache = icon
    return icon

_native_icon_cache: dict[str, QIcon] = {}
_favicon_cache: dict[str, str] = {}  # Cache ścieżek do pobranych favicon


def get_cached_favicon(url):
    """Zwraca ścieżkę do zbuforowanego favicon dla URL."""
    domain = urlparse(normalize_url(url)).netloc.replace("www.", "")
    cached_path = _favicon_cache.get(domain)
    if cached_path and os.path.exists(cached_path):
        return cached_path
    return None


def cache_favicon(url, icon_path):
    """Buforuje ścieżkę do favicon dla URL."""
    domain = urlparse(normalize_url(url)).netloc.replace("www.", "")
    _favicon_cache[domain] = icon_path


def native_icon(path):
    """Ikona pliku/folderu z powłoki Windows z buforowaniem w pamięci."""
    if not path:
        return QIcon()
    if is_url(path):
        # Sprawdź cache dla favicon
        cached = get_cached_favicon(path)
        if cached and os.path.exists(cached):
            icon = QIcon(cached)
            if not icon.isNull():
                return icon
        return link_icon()

    cached = _native_icon_cache.get(path)
    if cached is not None:
        return cached

    # Dla standardowych typów plików (nie exe/ico/lnk i nie katalogów) ikona jest wspólna
    ext = os.path.splitext(path)[1].lower() if "." in path else ""
    if ext and ext not in (".exe", ".ico", ".lnk") and not os.path.isdir(path):
        ext_key = f"__ext_{ext}__"
        cached_ext = _native_icon_cache.get(ext_key)
        if cached_ext is not None:
            return cached_ext
    else:
        ext_key = None

    icon = None
    try:
        global _icon_provider
        if _icon_provider is None:
            _icon_provider = QFileIconProvider()
        icon = _icon_provider.icon(QFileInfo(path))
    except (OSError, RuntimeError):
        pass

    if icon is None or icon.isNull():
        icon = QIcon(path)
    if icon.isNull():
        icon = QIcon()

    _native_icon_cache[path] = icon
    if ext_key is not None:
        _native_icon_cache[ext_key] = icon
    return icon

def app_icon():
    """Ikona aplikacji ładowana z pliku ico.ico."""
    global _app_icon_cache
    if _app_icon_cache is not None:
        return _app_icon_cache

    # Ścieżka do pliku ikony
    icon_path = os.path.join(os.path.dirname(__file__), "ico.ico")

    # Spróbuj załadować ikonę z pliku
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            _app_icon_cache = icon
            return icon

    # Fallback - rysuj wektorową ikonę jeśli plik nie istnieje
    accent = QColor(0, 120, 215)
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        r = s * 0.22
        p.drawRoundedRect(QRectF(0.5, 0.5, s - 1.0, s - 1.0), r, r)
        f = p.font()
        f.setBold(True)
        f.setPixelSize(max(8, int(s * 0.62)))
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(0.0, 0.0, s, s), Qt.AlignmentFlag.AlignCenter, "D")
        p.end()
        icon.addPixmap(pm)
    _app_icon_cache = icon
    return icon

def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable or "pythonw.exe"
    if exe.lower().endswith("python.exe"):
        candidate = exe[: -len("python.exe")] + "pythonw.exe"
        if os.path.exists(candidate):
            exe = candidate
    return f'"{exe}" "{ENTRY_SCRIPT}"'

def is_startup_enabled():
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY) as key:
            winreg.QueryValueEx(key, _STARTUP_NAME)
        return True
    except OSError:
        return False

def set_startup(enabled):
    if sys.platform != "win32":
        return False
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _STARTUP_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, _STARTUP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, _STARTUP_NAME)
                except OSError:
                    pass
        return True
    except OSError:
        return False


def copy_path_to_clipboard(path):
    """Kopiuje ścieżkę do schowka systemowego."""
    if not path:
        return False
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(path)
        return True
    return False


def open_parent_folder(path):
    """Otwiera folder nadrzędny dla danej ścieżki."""
    if not path or is_url(path):
        return False
    if os.path.isfile(path):
        parent = os.path.dirname(path)
    elif os.path.isdir(path):
        parent = path
    else:
        return False
    if os.path.exists(parent):
        open_path(parent)
        return True
    return False


def run_as_admin(path):
    """Uruchamia plik jako administrator (tylko Windows)."""
    if not path or is_url(path) or sys.platform != "win32":
        return False
    try:
        import subprocess
        subprocess.run(["runas", "/user:Administrator", path], shell=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def is_broken_link(path):
    """Sprawdza czy ścieżka prowadzi do nieistniejącego zasobu."""
    if not path:
        return True
    if is_url(path):
        return False
    return not os.path.exists(path)


def fetch_favicon(url, callback, parent=None):
    """Pobiera favicon dla strony www i zwraca ścieżkę do zapisanego pliku przez callback.

    Args:
        url: Adres strony (https://example.com)
        callback: Funkcja przyjmująca (icon_path: str | None)
        parent: Rodzic QObject (opcjonalnie, pomaga w zarządzaniu pamięcią)

    Returns:
        Obiekt FaviconFetcher (należy go przechowywać, aby nie został usunięty przed zakończeniem)
    """
    # Sprawdź cache najpierw
    try:
        cached = get_cached_favicon(url)
        if cached:
            callback(cached)
            return None
    except Exception:
        pass  # Błąd cache - kontynuuj z pobieraniem

    from PyQt6.QtCore import QObject, QTimer, pyqtSignal

    class FaviconFetcher(QObject):
        finished = pyqtSignal(str)

        def __init__(self, url, parent=None):
            super().__init__(parent)
            self.url = url
            self.manager = QNetworkAccessManager(self)
            self.manager.finished.connect(self._on_reply)
            self._reply = None
            self._timeout_timer = QTimer(self)
            self._timeout_timer.setSingleShot(True)
            self._timeout_timer.timeout.connect(self._on_timeout)

        def start(self):
            try:
                parsed = urlparse(normalize_url(self.url))
                domain = parsed.netloc
                favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
                request = QNetworkRequest(QUrl(favicon_url))
                self._reply = self.manager.get(request)
                self._timeout_timer.start(10000)  # 10 sekund timeout
            except Exception:
                self.finished.emit("")

        def _on_timeout(self):
            """Timeout - przerwij pobieranie."""
            if self._reply is not None:
                self._reply.abort()
                self._reply.deleteLater()
                self._reply = None
            self.finished.emit("")

        def _on_reply(self, reply):
            self._timeout_timer.stop()
            try:
                if reply.error() == reply.NetworkError.NoError:
                    data = reply.readAll()
                    if not data.isEmpty():
                        try:
                            icon_dir = os.path.join(data_dir(), "icons")
                            os.makedirs(icon_dir, exist_ok=True)
                            domain = urlparse(normalize_url(self.url)).netloc.replace("www.", "")
                            icon_path = os.path.join(icon_dir, f"{domain}.png")
                            with open(icon_path, "wb") as f:
                                f.write(data.data())
                            cache_favicon(self.url, icon_path)
                            self.finished.emit(icon_path)
                            reply.deleteLater()
                            return
                        except OSError:
                            pass
            except Exception:
                pass
            self.finished.emit("")
            reply.deleteLater()

    fetcher = FaviconFetcher(url, parent)
    fetcher.finished.connect(callback)
    fetcher.start()
    return fetcher
