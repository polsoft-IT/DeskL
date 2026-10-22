"""Wtyczka językowa: polski (Polish)."""

CODE = "pl"
NAME = "Polski"

STRINGS = {
    # pasek stanu
    "status.ready": "Gotowy",
    "status.found": "Znaleziono {done} / {total}",
    "status.save_failed": "Nie udało się zapisać konfiguracji",

    # akcje
    "action.add": "Dodaj",
    "action.open": "Otwórz",
    "action.edit": "Edytuj",
    "action.remove": "Usuń",
    "action.rename": "Zmień nazwę",
    "action.copy_link": "Kopiuj link",
    "action.properties": "Właściwości",
    "action.paste": "Wklej",
    "action.change": "Zmień...",
    "action.cancel": "Anuluj",
    "action.save": "Zapisz",
    "action.restore": "Przywróć okno",
    "action.quit": "Zamknij",
    "action.about": "About",
    "action.toggle_window": "Pokaż/ukryj",

    # menu
    "menu.tabs": "Zakładki",
    "menu.view": "Widok",

    # widok
    "view.icons": "Ikony",
    "view.list": "Lista",
    "view.small": "Małe",
    "view.large": "Duże",
    "view.grid": "Siatka",
    "view.auto": "Auto",

    # pytania
    "ask.remove.title": "Usuń element",
    "ask.remove.text": "Usunąć „{name}”?",
    "ask.close_tab.title": "Usuń zakładkę",
    "ask.close_tab.text": "Zakładka „{name}” zawiera {n} element(ów). Usunąć?",
    "ask.quit.title": "Zamknij DeskL",
    "ask.quit.text": "Zamknąć DeskL?",
    "ask.broken.delete": "Usunąć wszystkie uszkodzone linki?",

    # zakładki i szukanie
    "rename.title": "Zmień nazwę",
    "rename.label": "Nazwa zakładki:",
    "search.placeholder": "Szukaj: nazwa, ścieżka lub tag (Esc zamyka)",
    "tab.add": "Dodaj zakładkę (Ctrl+T)",
    "tab.new": "Zakładka",
    "tab.empty": "Przeciągnij tu pliki lub kliknij „Dodaj” (Ctrl+N)",
    "tab.apps": "Apps",
    "tab.www": "WWW",
    "tab.files": "Pliki",
    "tag.all": "Wszystkie",

    # podpowiedzi przycisków
    "tip.mini": "Zwiń do ikonki",
    "tip.topmost": "Zawsze na wierzchu",
    "tip.add": "Dodaj element",
    "tip.search": "Szukaj (Ctrl+F)",
    "tip.auto": "Auto rozmieszczenie",
    "tip.grid": "Wyrównaj do siatki",
    "tip.size": "Zmień rozmiar ikon",
    "tip.view": "Zmień widok",
    "tip.settings": "Ustawienia",
    "tip.shortcuts": "Skróty klawiszowe",
    "tip.sidebar": "Pokaż/ukryj panel boczny",

    # ikonka na pulpicie
    "float.tooltip": "Przeciągnij, aby przenieść • podwójne kliknięcie przywraca okno",

    # ustawienia
    "settings.title": "Ustawienia",
    "settings.dark": "Tryb ciemny",
    "settings.startup": "Uruchamiaj przy starcie systemu",
    "settings.lock": "Zablokuj rozmiar okna",
    "settings.language": "Język",
    "settings.startup_failed": "Nie udało się zapisać ustawienia autostartu",

    # okno dodawania/edycji
    "add.title": "Dodaj",
    "add.link": "Link:",
    "add.link.placeholder": "https://adres-strony",
    "add.file": "Plik",
    "add.folder": "Folder",
    "add.type": "Typ:",
    "add.name": "Nazwa:",
    "add.name.web": "Nazwa (domyślnie adres)",
    "add.name.file": "Nazwa (domyślnie nazwa pliku)",
    "add.tag": "Tag:",
    "add.tag.placeholder": "Tag (opcjonalnie)",
    "add.icon": "Ikona:",
    "add.icon.web": "Domyślna ikona globusa",
    "add.icon.file": "Domyślna ikona pliku",
    "add.icon.default": "Domyślna",
    "add.icon.fetch": "Pobierz",
    "add.icon.fetching": "Pobieranie...",

    # okna wyboru
    "dialog.pick_file": "Wybierz plik",
    "dialog.pick_folder": "Wybierz folder",
    "dialog.pick_icon": "Wybierz ikonę",
    "dialog.image_filter": "Obrazy (*.png *.ico *.jpg *.jpeg *.bmp *.svg);;Wszystkie pliki (*)",

    # o programie
    "about.subtitle": "Desktop Launcher",
    "about.description": "Skróty do plików i folderów w zakładkach, z tagami i przeciąganiem.",

    # okno skrótów klawiszowych
    "shortcuts.title": "Skróty klawiszowe",
    "shortcuts.subtitle": "Szybkie sterowanie aplikacją",
    "shortcuts.group.entries": "Wpisy i zakładki",
    "shortcuts.group.search": "Wyszukiwanie",
    "shortcuts.group.config": "Kopia zapasowa",
    "shortcuts.add": "Dodaj nowy element",
    "shortcuts.tab": "Nowa zakładka",
    "shortcuts.open": "Otwórz zaznaczony element",
    "shortcuts.edit": "Edytuj zaznaczony element",
    "shortcuts.delete": "Usuń zaznaczony element",
    "shortcuts.search": "Aktywuj wyszukiwanie",
    "shortcuts.escape": "Zamknij wyszukiwanie",
    "shortcuts.export": "Eksportuj konfigurację (JSON)",
    "shortcuts.import": "Importuj konfigurację (JSON)",
    "shortcuts.close_hint": "Wciśnij Esc lub kliknij poza oknem, aby zamknąć",

    # statystyki użycia
    "stats.title": "Statystyki użycia",
    "stats.subtitle": "Przegląd aktywności w aplikacji",
    "stats.entries": "Wpisy",
    "stats.launches": "Uruchomienia",
    "stats.entries_short": "wpisów",
    "stats.launches_short": "uruchom.",
    "stats.by_tab": "Według zakładek",
    "stats.top_10": "Top 10 najczęściej używanych",
    "stats.close_hint": "Wciśnij Esc lub kliknij poza oknem, aby zamknąć",
}
