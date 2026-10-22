from __future__ import annotations

import zlib
from functools import lru_cache

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QListWidget


@lru_cache(maxsize=256)
def tag_color(tag: str) -> QColor:
    if not tag:
        return QColor(140, 140, 140)
    hue = zlib.crc32(tag.lower().encode("utf-8")) % 360
    # Ulepszona paleta: wyższe nasycenie i jasność dla lepszej czytelności
    return QColor.fromHsv(hue, 180, 220)


@lru_cache(maxsize=128)
def _readable_text_rgb(r: int, g: int, b: int) -> QColor:
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return QColor(24, 24, 24) if lum > 150 else QColor(255, 255, 255)


def _readable_text(color: QColor) -> QColor:
    return _readable_text_rgb(color.red(), color.green(), color.blue())


def update_list_columns(lw: QListWidget) -> None:
    if lw.property("listMode") and lw.property("listMode") != "false":
        vp = lw.viewport()
        if vp is None:
            return
        w = (vp.width() - 16) // 3
        if w > 0:
            lw.setGridSize(QSize(w, lw.iconSize().height() + lw.fontMetrics().height() + 8))
