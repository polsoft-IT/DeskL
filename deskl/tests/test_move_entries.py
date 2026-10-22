"""Test przenoszenia wpisów między zakładkami (D&D) w DeskL.

Uruchamianie:  python "deskl\\tests\\test_move_entries.py"
Działa w trybie offscreen na wydzielonym sandboxie (APPDATA w katalogu tymczasowym).
"""

import os
import shutil
import sys
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SANDBOX = os.path.join(tempfile.gettempdir(), "deskl_move_test")

shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
os.environ["APPDATA"] = SANDBOX
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, PROJECT)

failures = []

def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + str(extra)))
    if not cond:
        failures.append(name)

from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt  # noqa: E402
from PyQt6.QtGui import QDropEvent, QMouseEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

QApplication.exec = lambda self, *a, **k: 0

from deskl import app as A  # noqa: E402
from deskl import config, widgets  # noqa: E402

desk = A.DeskLApp()
desk.build()
QApplication.processEvents()

apps, www, files = desk.tabs.widget(0), desk.tabs.widget(1), desk.tabs.widget(2)

def paths(lw):
    return [lw.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lw.count())]

desk._add_entry("C:/Alpha", "Alpha", "", apps)
desk._add_entry("C:/Gamma", "Gamma", "", www)
check("stan początkowy", paths(apps) == ["C:/Alpha"] and paths(www) == ["C:/Gamma"],
      (paths(apps), paths(www)))

# --- 1. przenoszenie przez sygnał paska zakładek -----------------------------
item = apps.item(0)
desk._on_tab_entry_dropped(1, apps, [item])
check("wpis zniknął ze źródła", paths(apps) == [], paths(apps))
check("wpis pojawił się w zakładce docelowej", paths(www) == ["C:/Gamma", "C:/Alpha"], paths(www))
check("przełączono na zakładkę docelową", desk.tabs.currentIndex() == 1, desk.tabs.currentIndex())

# --- 2. upuszczenie na tę samą zakładkę = brak zmian -------------------------
item = www.item(0)
desk._on_tab_entry_dropped(1, www, [item])
check("upuszczenie na tę samą zakładkę nic nie zmienia",
      paths(www) == ["C:/Gamma", "C:/Alpha"], paths(www))

# --- 3. EntryTabBar.dropEvent rozpoznaje wpis i emituje indeks ---------------
bar = desk.tabs.tabBar()
received = []
bar.entryDropped.connect(lambda i, s, it: received.append((i, s, list(it))))

mime = QMimeData()
mime.setData(widgets.DRAG_MIME, b"1")
widgets._drag_source = www
widgets._drag_items = [www.item(0)]
rect = bar.tabRect(2)
point = QPointF(rect.center()) if not rect.isEmpty() else QPointF(10, 10)
event = QDropEvent(point, Qt.DropAction.MoveAction, mime,
                   Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
bar.dropEvent(event)
widgets._drag_source = None
widgets._drag_items = []
check("dropEvent emituje entryDropped z indeksem zakładki",
      len(received) == 1 and received[0][0] == 2 and received[0][1] is www,
      (received, rect))
check("dropEvent przyjmuje akcję Move",
      event.dropAction() == Qt.DropAction.MoveAction, event.dropAction())

# --- 4. obcy MIME nie jest przechwytywany ------------------------------------
foreign = QMimeData()
foreign.setText("zwykly tekst")
widgets._drag_source = None
foreign_event = QDropEvent(point, Qt.DropAction.CopyAction, foreign,
                           Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
foreign_event.accept()
bar.dropEvent(foreign_event)
check("obcy MIME nie emituje przenoszenia", len(received) == 1, len(received))

# --- 5. samodzielny start przeciągania po opuszczeniu listy ------------------
started = []
original_start = widgets.EntryList.startDrag
widgets.EntryList.startDrag = lambda self, actions: started.append(actions)

target = files
desk._add_entry("C:/Delta", "Delta", "", target)
QApplication.processEvents()
center = target.visualItemRect(target.item(0)).center()

def send(kind, pos, buttons):
    QApplication.sendEvent(target.viewport(), QMouseEvent(
        kind, QPointF(pos), QPointF(target.viewport().mapToGlobal(pos)),
        Qt.MouseButton.LeftButton if kind == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
        buttons, Qt.KeyboardModifier.NoModifier))

send(QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
send(QEvent.Type.MouseMove, QPoint(center.x(), -4), Qt.MouseButton.LeftButton)
check("przeciąganie startuje po opuszczeniu listy", len(started) == 1, started)

started.clear()
send(QEvent.Type.MouseButtonPress, center, Qt.MouseButton.LeftButton)
send(QEvent.Type.MouseMove, QPoint(center.x() + 6, center.y() + 6), Qt.MouseButton.LeftButton)
check("ruch wewnątrz listy nie startuje przenoszenia", started == [], started)

widgets.EntryList.startDrag = original_start

# --- 6. trwałość zmian w konfiguracji ---------------------------------------
desk._flush_config()
data = config.read()

def items_of(lw):
    sec = data.get(lw.property("tabId"), {})
    return [it.get("path") for it in sec.get("items", [])] if isinstance(sec, dict) else []

check("wpis zapisany w zakładce docelowej", "C:/Alpha" in items_of(www), items_of(www))
check("wpis usunięty z zakładki źródłowej", "C:/Alpha" not in items_of(apps), items_of(apps))

shutil.rmtree(SANDBOX, ignore_errors=True)

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print("  - " + name)
    sys.exit(1)
print("ALL MOVE-ENTRY TESTS PASSED")
