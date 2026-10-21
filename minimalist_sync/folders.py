# Minimalist Anki Sync
# Copyright (C) 2026 the Minimalist Anki Sync authors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See LICENSE for the full text.

"""Finds the iPhone app's iCloud Drive folder on this computer."""

from __future__ import annotations

import os
import sys

# The app's iCloud container, as it appears on disk.
CONTAINER = "iCloud~com~zkashef~MinimalistChessPhone"
# The name iCloud Drive shows for the container (NSUbiquitousContainerName).
DISPLAY_NAME = "Minimalist"
SUBFOLDER = "AnkiSync"


def candidates(home: str | None = None, platform: str | None = None) -> list[str]:
    """Places the container's Documents folder can be, most likely first."""
    home = home or os.path.expanduser("~")
    platform = platform or sys.platform
    if platform == "darwin":
        return [os.path.join(home, "Library", "Mobile Documents", CONTAINER, "Documents")]
    if platform.startswith("win"):
        drive = os.path.join(home, "iCloudDrive")
        return [
            os.path.join(drive, CONTAINER),
            os.path.join(drive, CONTAINER, "Documents"),
            os.path.join(drive, DISPLAY_NAME),
        ]
    return []


def find_container(home: str | None = None, platform: str | None = None) -> str | None:
    """The container folder, if iCloud Drive has created it on this computer.

    It appears once the iPhone app has turned on Anki sync and iCloud Drive
    has caught up, which can take a minute.
    """
    for path in candidates(home, platform):
        if os.path.isdir(path):
            return path
    return None


def sync_folder(override: str | None, home: str | None = None, platform: str | None = None) -> str | None:
    """Where status.json goes: the folder the user picked, or the detected one."""
    if override:
        return override
    container = find_container(home, platform)
    return os.path.join(container, SUBFOLDER) if container else None
