"""Operacje biznesowe dla DeskL (przenoszenie wpisów, wyszukiwanie)."""
from __future__ import annotations


def move_entries_items(
    source_items: list[tuple[str, str, str | None, str, int]],
) -> list[tuple[str, str, str | None, str, int]]:
    """Zwraca listę danych do dodania przy przenoszeniu."""
    result: list[tuple[str, str, str | None, str, int]] = []
    for path, display_name, icon_path, tag, uses in source_items:
        if not path:
            continue
        result.append((path, display_name or path, icon_path or "", tag or "", int(uses or 0)))
    return result


def filter_haystack(
    text: str,
    path: str = "",
    tag: str = "",
) -> str:
    """Zwraca połączony tekst do wyszukiwania."""
    return " ".join((text, str(path or ""), str(tag or ""))).lower()


def search_query(text: str | None = None) -> str:
    """Normalizuje zapytanie wyszukiwania."""
    if text is None:
        return ""
    return str(text).strip().lower()
