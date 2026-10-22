"""Odczyt i zapis konfiguracji JSON aplikacji DeskL."""

import json
import logging
import os
import shutil

logger = logging.getLogger(__name__)

VERSION = 1

# Katalog danych aplikacji w profilu użytkownika: %APPDATA%\.polsoft\DeskL
APP_DIR = (".polsoft", "DeskL")
CONFIG_NAME = "deskl_config.json"

# Dawna lokalizacja konfiguracji (katalog projektu) — migrowana jednorazowo.
_LEGACY_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), CONFIG_NAME
)

def data_dir():
    """Katalog ustawień i plików aplikacji; tworzony, jeśli nie istnieje."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, *APP_DIR)
    os.makedirs(path, exist_ok=True)
    return path

def config_path():
    return os.path.join(data_dir(), CONFIG_NAME)

def _migrate_legacy():
    """Przenosi config z katalogu projektu do katalogu danych (jednorazowo)."""
    path = config_path()
    if os.path.exists(path) or not os.path.exists(_LEGACY_CONFIG):
        return
    try:
        shutil.move(_LEGACY_CONFIG, path)
    except OSError:
        try:
            shutil.copy2(_LEGACY_CONFIG, path)
        except OSError:
            pass

def ensure():
    """Tworzy katalog danych i wymagany plik konfiguracji, jeśli ich brakuje."""
    _migrate_legacy()
    path = config_path()
    if not os.path.exists(path):
        write({})
    return path

def read():
    ensure()
    try:
        with open(config_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

def write(data):
    """Zapisuje konfigurację. Zwraca False, gdy zapis się nie powiódł."""
    data["_version"] = VERSION
    path = config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Nie udało się zapisać konfiguracji %s: %s", path, exc)
        return False
    return True
