# Minimalist Anki Sync
# Copyright (C) 2026 the Minimalist Anki Sync authors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See LICENSE for the full text.

"""Lets the Minimalist iPhone app see how much Anki you've studied today.

The add-on writes a small file of counts (reviews done today and cards
still due, per chosen deck) into the app's own iCloud Drive folder. iCloud
copies it to your iPhone. There's no account and no server, and no card
content ever leaves Anki.
"""

from __future__ import annotations

import time

from aqt import gui_hooks, mw
from aqt.qt import (
    QAction,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from aqt.utils import openLink, showInfo, showWarning, tooltip

from . import folders
from .status import build_status, write_status

ADDON_VERSION = "1.1.0"
DECKS_KEY = "minimalistSyncDecks"  # stored in the collection, so it follows AnkiWeb sync
REPO_URL = "https://github.com/zkashef/minimalist-anki-sync"
# At most one write this often while reviewing.
MIN_INTERVAL = 20.0

_last_write = 0.0
_timer: QTimer | None = None


def _config() -> dict:
    return mw.addonManager.getConfig(__name__) or {}


def _save_config(config: dict) -> None:
    mw.addonManager.writeConfig(__name__, config)


def _selected_decks() -> list[int]:
    return [int(d) for d in (mw.col.get_config(DECKS_KEY, []) or [])] if mw.col else []


def _folder() -> str | None:
    return folders.sync_folder(_config().get("folder") or None)


def sync_now(quiet: bool = True) -> bool:
    """Writes the status file. Returns whether it was written."""
    global _last_write
    if not mw.col:
        return False
    folder = _folder()
    if not folder:
        if not quiet:
            showWarning(
                "The Minimalist folder isn't in iCloud Drive on this computer yet.\n\n"
                "1. On your iPhone, choose Anki as the unlock method in Minimalist.\n"
                "2. On this computer, turn on iCloud Drive with the same Apple ID.\n"
                "3. Wait a minute, then try again.\n\n"
                "On Windows, or if it still isn't found, use Minimalist > Sync Folder… to pick the folder."
            )
        return False
    decks = _selected_decks()
    if not decks and not quiet:
        showInfo("Choose the decks that count first: Minimalist > Select Decks…")
        return False
    try:
        write_status(build_status(mw.col, decks, ADDON_VERSION), folder)
    except Exception as error:  # a full disk or a permissions problem shouldn't break reviewing
        if not quiet:
            showWarning(f"Couldn't write to {folder}:\n{error}")
        return False
    _last_write = time.time()
    if not quiet:
        tooltip("Sent to your iPhone through iCloud.")
    return True


def _sync_soon() -> None:
    """After answering a card: write now, or once the minimum interval has passed."""
    global _timer
    wait = MIN_INTERVAL - (time.time() - _last_write)
    if wait <= 0:
        sync_now()
        return
    if _timer is None:
        _timer = QTimer(mw)
        _timer.setSingleShot(True)
        _timer.timeout.connect(lambda: sync_now())
    if not _timer.isActive():
        _timer.start(int(wait * 1000))


class DeckDialog(QDialog):
    """A checkbox for every deck and subdeck. Ticking a deck counts its subdecks too."""

    def __init__(self) -> None:
        super().__init__(mw)
        self.setWindowTitle("Minimalist: decks that count")
        layout = QVBoxLayout(self)
        label = QLabel("Tick the decks whose reviews count toward your goals on your iPhone. "
                       "A ticked deck includes its subdecks.")
        label.setWordWrap(True)
        layout.addWidget(label)

        # Real checkboxes rather than checkable list rows, whose boxes some
        # Anki themes draw invisibly.
        self.boxes: list[tuple[int, QCheckBox]] = []
        chosen = set(_selected_decks())
        content = QWidget()
        rows = QVBoxLayout(content)
        rows.setSpacing(4)
        for deck in sorted(mw.col.decks.all_names_and_ids(), key=lambda d: d.name.lower()):
            box = QCheckBox(deck.name.split("::")[-1])
            box.setChecked(int(deck.id) in chosen)
            box.setToolTip(deck.name)
            row = QHBoxLayout()
            row.setContentsMargins(24 * deck.name.count("::"), 0, 0, 0)
            row.addWidget(box)
            row.addStretch()
            rows.addLayout(row)
            self.boxes.append((int(deck.id), box))
        rows.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear = buttons.addButton("Clear All", QDialogButtonBox.ButtonRole.ResetRole)
        clear.clicked.connect(lambda: [box.setChecked(False) for _, box in self.boxes])
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(460, 560)

    def chosen(self) -> list[int]:
        return [did for did, box in self.boxes if box.isChecked()]


def select_decks() -> None:
    if not mw.col:
        return
    dialog = DeckDialog()
    if dialog.exec():
        mw.col.set_config(DECKS_KEY, dialog.chosen())
        sync_now(quiet=False)


def choose_folder() -> None:
    detected = folders.sync_folder(None)
    current = _config().get("folder") or ""
    lines = [
        f"Detected iCloud folder:\n{detected or 'not found'}",
        f"Folder you picked:\n{current or 'none (using the detected folder)'}",
        "Pick a different folder only if the detected one is missing, for example with iCloud for Windows. "
        "Choose the AnkiSync folder inside the Minimalist folder in iCloud Drive.",
    ]
    showInfo("\n\n".join(lines), title="Minimalist sync folder")
    picked = QFileDialog.getExistingDirectory(mw, "Choose the Minimalist AnkiSync folder", current or detected or "")
    if picked:
        config = _config()
        config["folder"] = picked
        _save_config(config)
        sync_now(quiet=False)


def reset_folder() -> None:
    config = _config()
    config["folder"] = ""
    _save_config(config)
    tooltip("Using the detected iCloud folder.")


def how_to_use() -> None:
    showInfo(
        "Minimalist unlocks the apps you've locked on your iPhone once you've done your Anki studying for the day.\n\n"
        "1. On your iPhone, choose Anki as the unlock method in Minimalist and set your study goals.\n"
        "2. On this computer, turn on iCloud Drive with the same Apple ID as your iPhone.\n"
        "3. Here, choose Minimalist > Select Decks… and tick the decks that count.\n"
        "4. Study as usual. Your progress is sent after each card (at most every 20 seconds), "
        "after each AnkiWeb sync, and when you close Anki.\n\n"
        "Reviews from AnkiMobile or AnkiDroid count once this computer has synced with AnkiWeb.\n\n"
        "Only counts and deck names are sent, through your own iCloud. No card content leaves Anki, "
        "and there's no account.",
        title="Minimalist",
    )


def check_for_updates() -> None:
    from aqt.addons import check_and_prompt_for_updates

    check_and_prompt_for_updates(mw, mw.addonManager, lambda _log: None)


def _add_menu() -> None:
    menu = QMenu("Minimalist", mw)
    for title, handler in [
        ("Select Decks…", select_decks),
        ("Sync Now", lambda: sync_now(quiet=False)),
        ("Sync Folder…", choose_folder),
        ("Use Detected Folder", reset_folder),
        (None, None),
        ("How to Use", how_to_use),
        ("Check for Updates", check_for_updates),
        ("Source Code", lambda: openLink(REPO_URL)),
    ]:
        if title is None:
            menu.addSeparator()
            continue
        action = QAction(title, mw)
        action.triggered.connect(handler)
        menu.addAction(action)
    # Next to Help, where there is one.
    bar = mw.form.menubar
    help_menu = getattr(mw.form, "menuHelp", None)
    if help_menu is not None:
        bar.insertMenu(help_menu.menuAction(), menu)
    else:
        bar.addMenu(menu)


gui_hooks.main_window_did_init.append(_add_menu)
gui_hooks.profile_did_open.append(lambda: sync_now())
gui_hooks.reviewer_did_answer_card.append(lambda *_: _sync_soon())
gui_hooks.sync_did_finish.append(lambda: sync_now())
gui_hooks.profile_will_close.append(lambda: sync_now())
