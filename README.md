# Minimalist Anki Sync

An Anki Desktop add-on for the **Minimalist** iPhone app. Study in Anki as usual, and once you've met the day's study goals, Minimalist unlocks the apps you've locked on your phone.

There's no account and no server. The add-on writes a small file of counts into the app's own iCloud Drive folder, and iCloud copies it to your iPhone.

## What it sends

Only counts and deck names, for the decks you choose:

- reviews done today, cards studied and new cards seen (from Anki's review log, since the day started);
- cards still due today (new, learning, review), after your deck limits, the same numbers Anki shows;
- the time Anki's next day starts ("Next day starts at" in Preferences).

No card content, notes, media or review history leaves Anki. The file is `status.json` in `iCloud Drive/Minimalist/AnkiSync/`, and you can open it to check.

## Setup

1. On your iPhone, pick **Anki** as the unlock method in Minimalist.
2. On your computer, turn on **iCloud Drive** with the same Apple ID as your iPhone.
3. In Anki, install the add-on (**Tools > Add-ons > Get Add-ons…** and enter the code shown in the app), then restart Anki.
4. Choose **Minimalist > Select Decks…** and tick the decks that count. Subdecks are included.

Progress is sent after each answer (at most every 20 seconds), after each AnkiWeb sync, when a profile opens or closes, and with **Minimalist > Sync Now**. Reviews done in AnkiMobile or AnkiDroid count once Anki Desktop has synced them from AnkiWeb.

### Where the file goes

- **macOS:** `~/Library/Mobile Documents/iCloud~com~zkashef~MinimalistChessPhone/Documents/AnkiSync/`, found automatically. The folder appears once the iPhone app has turned on Anki sync and iCloud Drive has caught up.
- **Windows (iCloud for Windows):** the add-on looks in `iCloudDrive`. If it can't find the folder, choose it with **Minimalist > Sync Folder…** (the `AnkiSync` folder inside `Minimalist`). Not yet tested.
- **Linux:** iCloud Drive isn't available, so this add-on can't reach the phone.

## Development

The status logic in `minimalist_sync/status.py` has no GUI code, and the tests run it against a real temporary collection:

```sh
python3 -m venv .venv && .venv/bin/pip install anki pytest
.venv/bin/python -m pytest tests
```

`./build.sh` packages `minimalist_sync.ankiaddon` for AnkiWeb or a double-click install. Supports Anki 23.10 and later.

## Licence

GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).
