"""Wtyczka językowa: angielski (English) — język domyślny DeskL."""

CODE = "en"
NAME = "English"

STRINGS = {
    # status bar
    "status.ready": "Ready",
    "status.found": "Found {done} / {total}",
    "status.save_failed": "Could not save the configuration",

    # actions
    "action.add": "Add",
    "action.open": "Open",
    "action.edit": "Edit",
    "action.remove": "Delete",
    "action.rename": "Rename",
    "action.copy_link": "Copy link",
    "action.properties": "Properties",
    "action.paste": "Paste",
    "action.change": "Change...",
    "action.cancel": "Cancel",
    "action.save": "Save",
    "action.restore": "Restore window",
    "action.quit": "Quit",
    "action.about": "About",
    "action.toggle_window": "Show/hide",

    # menus
    "menu.tabs": "Tabs",
    "menu.view": "View",

    # view
    "view.icons": "Icons",
    "view.list": "List",
    "view.small": "Small",
    "view.large": "Large",
    "view.grid": "Grid",
    "view.auto": "Auto",

    # questions
    "ask.remove.title": "Remove item",
    "ask.remove.text": "Remove \u201c{name}\u201d?",
    "ask.close_tab.title": "Remove tab",
    "ask.close_tab.text": "Tab \u201c{name}\u201d contains {n} item(s). Remove it?",
    "ask.quit.title": "Quit DeskL",
    "ask.quit.text": "Quit DeskL?",
    "ask.broken.delete": "Delete all broken links?",

    # tabs and search
    "rename.title": "Rename",
    "rename.label": "Tab name:",
    "search.placeholder": "Search: name, path or tag (Esc closes)",
    "tab.add": "Add tab (Ctrl+T)",
    "tab.new": "Tab",
    "tab.empty": "Drag files here or click \u201cAdd\u201d (Ctrl+N)",
    "tab.apps": "Apps",
    "tab.www": "WWW",
    "tab.files": "Files",
    "tag.all": "All",

    # button tooltips
    "tip.mini": "Collapse to icon",
    "tip.topmost": "Always on top",
    "tip.add": "Add item",
    "tip.search": "Search (Ctrl+F)",
    "tip.auto": "Auto arrange",
    "tip.grid": "Align to grid",
    "tip.size": "Change icon size",
    "tip.view": "Change view",
    "tip.settings": "Settings",
    "tip.shortcuts": "Keyboard shortcuts",
    "tip.sidebar": "Show/hide side panel",

    # desktop icon
    "float.tooltip": "Drag to move \u2022 double-click restores the window",

    # settings
    "settings.title": "Settings",
    "settings.dark": "Dark mode",
    "settings.startup": "Run at system startup",
    "settings.lock": "Lock window size",
    "settings.language": "Language",
    "settings.startup_failed": "Could not save the autostart setting",

    # add/edit dialog
    "add.title": "Add",
    "add.link": "Link:",
    "add.link.placeholder": "https://example.com",
    "add.file": "File",
    "add.folder": "Folder",
    "add.type": "Type:",
    "add.name": "Name:",
    "add.name.web": "Name (URL by default)",
    "add.name.file": "Name (file name by default)",
    "add.tag": "Tag:",
    "add.tag.placeholder": "Tag (optional)",
    "add.icon": "Icon:",
    "add.icon.web": "Default globe icon",
    "add.icon.file": "Default file icon",
    "add.icon.default": "Default",
    "add.icon.fetch": "Fetch",
    "add.icon.fetching": "Fetching...",

    # pickers
    "dialog.pick_file": "Choose a file",
    "dialog.pick_folder": "Choose a folder",
    "dialog.pick_icon": "Choose an icon",
    "dialog.image_filter": "Images (*.png *.ico *.jpg *.jpeg *.bmp *.svg);;All files (*)",

    # about
    "about.subtitle": "Desktop Launcher",
    "about.description": "Shortcuts to files and folders in tabs, with tags and drag & drop.",

    # keyboard shortcuts window
    "shortcuts.title": "Keyboard Shortcuts",
    "shortcuts.subtitle": "Quick navigation and actions",
    "shortcuts.group.entries": "Items & Tabs",
    "shortcuts.group.search": "Search",
    "shortcuts.group.config": "Backup",
    "shortcuts.add": "Add new item",
    "shortcuts.tab": "New tab",
    "shortcuts.open": "Open selected item",
    "shortcuts.edit": "Edit selected item",
    "shortcuts.delete": "Delete selected item",
    "shortcuts.search": "Activate search",
    "shortcuts.escape": "Close search",
    "shortcuts.export": "Export configuration (JSON)",
    "shortcuts.import": "Import configuration (JSON)",
    "shortcuts.close_hint": "Press Esc or click outside to close",

    # usage statistics
    "stats.title": "Usage Statistics",
    "stats.subtitle": "Activity overview in the application",
    "stats.entries": "Entries",
    "stats.launches": "Launches",
    "stats.entries_short": "entries",
    "stats.launches_short": "launches",
    "stats.by_tab": "By Tab",
    "stats.top_10": "Top 10 Most Used",
    "stats.close_hint": "Press Esc or click outside to close",
}
