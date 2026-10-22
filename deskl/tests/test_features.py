"""Test dodatkowych funkcji DeskL: _show_about, skróty, tłumaczenia."""

import os
import shutil
import sys
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SANDBOX = os.path.join(tempfile.gettempdir(), "deskl_features_test")

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

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

QApplication.exec = lambda self, *a, **k: 0
QDialog.exec = lambda self, *a, **k: 0
QMessageBox.information = lambda *a, **k: 0

from deskl import app as A  # noqa: E402
from deskl import lang, widgets  # noqa: E402


def test_features():
    desk = A.DeskLApp()
    desk.build()

    # 1. Test czy _show_about istnieje i nie rzuca wyjątku
    try:
        desk._show_about()
        check("_show_about wykonuje się bez błędu", True)
    except (AttributeError, RuntimeError, TypeError) as exc:
        check("_show_about wykonuje się bez błędu", False, exc)

    # 2. Test czy _show_shortcuts wykonuje się bez błędu
    try:
        desk._show_shortcuts()
        check("_show_shortcuts wykonuje się bez błędu", True)
    except (AttributeError, RuntimeError, TypeError) as exc:
        check("_show_shortcuts wykonuje się bez błędu", False, exc)

    # 3. Test klucza tag.all w pakietach językowych
    for code in ("pl", "en"):
        lang.set_language(code)
        tr = lang.tr("tag.all")
        check(f"tłumaczenie tag.all w {code}", bool(tr) and tr != "[tag.all]", tr)

    # 4. Test paska TagBar z tag.all
    tag_bar = widgets.TagBar()
    tag_bar.set_tags(["test_tag"])
    check("TagBar ma chip tag.all", tag_bar._all_chip is not None and tag_bar._all_chip.text() != "[tag.all]")

    # 5. Test _open_current_entry
    try:
        desk._open_current_entry()
        check("_open_current_entry działa przy braku zaznaczenia", True)
    except (AttributeError, RuntimeError, TypeError) as exc:
        check("_open_current_entry działa przy braku zaznaczenia", False, exc)

    # 6. Test renderowania ikony przycisku about (info) i skrótów (kbd)
    from PyQt6.QtGui import QPixmap
    for glyph in ("info", "kbd", "pin", "view", "size", "add", "search", "grid", "auto", "mini", "gear", "sidebar"):
        btn = widgets.CornerButton(glyph, glyph)
        pm = QPixmap(btn.size())
        pm.fill()
        btn.render(pm)
        check(f"render CornerButton '{glyph}'", not pm.isNull())

    # 7. Test nowego eleganckiego okna ShortcutsPopup
    from deskl import dialogs
    popup = dialogs.ShortcutsPopup(desk.window)
    popup.adjustSize()
    pm_popup = QPixmap(popup.size())
    pm_popup.fill()
    popup.render(pm_popup)
    check("render ShortcutsPopup", not pm_popup.isNull() and popup.width() >= 300)

    print()
    if failures:
        print(f"FAILED: {len(failures)}")
        for name in failures:
            print("  - " + name)
        sys.exit(1)
    else:
        print("ALL FEATURES TESTS PASSED")

if __name__ == "__main__":
    test_features()
