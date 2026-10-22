"""Wtyczki językowe DeskL.

Każdy moduł w tym katalogu jest osobną wtyczką językową i udostępnia:

    CODE     — kod języka (np. "pl"),
    NAME     — nazwa wyświetlana (np. "Polski"),
    STRINGS  — słownik klucz -> tekst, z polami {nazwa} do formatowania.

Nową wtyczkę wystarczy wrzucić do tego katalogu — zostanie wykryta
automatycznie przy starcie aplikacji.
"""

import importlib
import pkgutil

# Język domyślny (standardowy) aplikacji.
DEFAULT = "en"

_plugins: dict[str, object] = {}
_current = DEFAULT
_loaded = False
_active_strings: dict[str, str] = {}


def _refresh_active_strings():
    default_module = _plugins.get(DEFAULT)
    current_module = _plugins.get(_current)
    default_dict = getattr(default_module, "STRINGS", {}) if default_module else {}
    current_dict = getattr(current_module, "STRINGS", {}) if current_module else {}
    global _active_strings
    _active_strings = {**default_dict, **current_dict}


def load():
    """Wczytuje (raz) wszystkie wtyczki językowe z tego katalogu."""
    global _loaded
    if _loaded:
        return _plugins
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        _plugins[getattr(module, "CODE", info.name)] = module
    _loaded = True
    _refresh_active_strings()
    return _plugins


def available():
    """Kody dostępnych języków, w kolejności alfabetycznej nazw."""
    return sorted(load(), key=lambda code: _plugins[code].NAME)


def language_name(code):
    module = load().get(code)
    return module.NAME if module is not None else code


def set_language(code):
    """Ustawia aktywny język; zwraca faktycznie ustawiony kod."""
    global _current
    if code in load():
        _current = code
        _refresh_active_strings()
    return _current


def current():
    return _current


def tr(key, **kwargs):
    """Tekst dla klucza w aktywnym języku (awaryjnie język domyślny)."""
    if not _loaded:
        load()
    text = _active_strings.get(key, key)
    return text.format(**kwargs) if kwargs else text
