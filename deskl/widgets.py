from __future__ import annotations

# Thin re-exports dla wstecznej kompatybilności
from .ui.widgets import *  # noqa: F401,F403
from .ui.widgets import (
    DRAG_MIME,
    TAG_ROLE,
    CornerButton,
    EntryList,
    EntryTabBar,
    FloatIcon,
    TagBar,
    TagChip,
    ToggleSwitch,
    _drag_items,
    _drag_source,
    install_delegate,
    tag_color,
    update_list_columns,
)

__all__ = [
    "DRAG_MIME",
    "TAG_ROLE",
    "CornerButton",
    "EntryList",
    "EntryTabBar",
    "FloatIcon",
    "TagBar",
    "TagChip",
    "ToggleSwitch",
    "_drag_items",
    "_drag_source",
    "install_delegate",
    "tag_color",
    "update_list_columns",
]
