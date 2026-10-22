"""Test wyszukiwania globalnego (filtrowanie wszystkich zakładek) w DeskL.

Uruchamianie:  python "deskl\\tests\\test_search.py"
Działa w trybie offscreen na wydzielonym sandboxie (APPDATA w katalogu tymczasowym).
"""

import os
import shutil
import sys
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SANDBOX = os.path.join(tempfile.gettempdir(), "deskl_search_test")

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

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QListWidget, QListWidgetItem  # noqa: E402

QApplication.exec = lambda self, *a, **k: 0

from deskl import app as A  # noqa: E402

desk = A.DeskLApp()
desk.build()

TAG = A.TAG_ROLE

def add(lw, name, tag=""):
    item = QListWidgetItem(name)
    item.setData(Qt.ItemDataRole.UserRole, "C:/" + name)
    item.setData(TAG, tag)
    lw.addItem(item)

def hidden(lw):
    return [lw.item(i).isHidden() for i in range(lw.count())]

apps, www, files = desk.tabs.widget(0), desk.tabs.widget(1), desk.tabs.widget(2)
check("trzy zakładki to QListWidget",
      all(isinstance(w, QListWidget) for w in (apps, www, files)))

add(apps, "Alpha")
add(apps, "Beta", tag="work")
add(www, "Gamma")
add(files, "Delta")
add(files, "Browser")
check("zapełniono 3 zakładki (5 wpisów)",
      (apps.count(), www.count(), files.count()) == (2, 1, 2))

# --- trafienie tylko w zakładce 0 -------------------------------------------
desk.tabs.setCurrentIndex(0)
desk.search_edit.setText("alpha")
check("filtr: trafienie w zakładce 0", hidden(apps) == [False, True], hidden(apps))
check("filtr: ukryte w zakładce 1", hidden(www) == [True], hidden(www))
check("filtr: ukryte w zakładce 2", hidden(files) == [True, True], hidden(files))
check("status liczy wszystkie wpisy", desk.window.statusBar().currentMessage() == "Found 1 / 5",
      desk.window.statusBar().currentMessage())

# --- trafienie w innej zakładce -> automatyczne przejście --------------------
desk.tabs.setCurrentIndex(0)
desk.search_edit.setText("gamma")
check("globalne: przechodzi do zakładki z trafieniem", desk.tabs.currentIndex() == 1,
      desk.tabs.currentIndex())
check("globalne: wpis widoczny", hidden(www) == [False], hidden(www))
check("globalne: pozostałe zakładki ukryte",
      hidden(apps) == [True, True] and hidden(files) == [True, True])

# --- trafienia rozproszone po zakładkach ------------------------------------
desk.search_edit.setText("a")   # Alpha, Beta, Gamma, Delta
check("globalne: suma trafień z wielu zakładek",
      desk.window.statusBar().currentMessage() == "Found 4 / 5",
      desk.window.statusBar().currentMessage())

# --- szukanie po tagu -------------------------------------------------------
desk.tabs.setCurrentIndex(1)
desk.search_edit.setText("work")
check("filtr po tagu", hidden(apps) == [True, False], hidden(apps))
check("trafienie po tagu przełącza zakładkę", desk.tabs.currentIndex() == 0, desk.tabs.currentIndex())

# --- szukanie po ścieżce + wielkość liter ------------------------------------
desk.search_edit.setText("/DELTA")
check("filtr po ścieżce, bez rozróżniania wielkości liter",
      hidden(files) == [False, True], hidden(files))

# --- wyczyszczenie filtra ---------------------------------------------------
desk._show_search(False)
check("czyszczenie pokazuje wszystkie wpisy",
      hidden(apps) == [False, False] and hidden(www) == [False] and hidden(files) == [False, False])
check("po wyczyszczeniu wraca status gotowości",
      desk.window.statusBar().currentMessage() == "Ready",
      desk.window.statusBar().currentMessage())

shutil.rmtree(SANDBOX, ignore_errors=True)

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print("  - " + name)
    sys.exit(1)
print("ALL SEARCH TESTS PASSED")
