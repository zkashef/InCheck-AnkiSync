# Minimalist Anki Sync
# Copyright (C) 2026 the Minimalist Anki Sync authors
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See LICENSE for the full text.

"""Builds the status file the iPhone app reads.

Only counts and deck names are written: never card content, notes or media.
This module needs a collection but no GUI, so it can be tested on its own.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Iterable

FORMAT_VERSION = 1
SECONDS_PER_DAY = 86_400

# revlog.type values that count as studying (learn, review, relearn, filtered).
# 4 (manual reschedule) and 5 (reset) are not reviews.
STUDY_TYPES = (0, 1, 2, 3)


def build_status(col: Any, deck_ids: Iterable[int], addon_version: str, now: float | None = None) -> dict:
    """The status for the selected decks, as a JSON-ready dict."""
    now = time.time() if now is None else now
    sched = col.sched
    cutoff = int(sched.day_cutoff)  # the next rollover, in epoch seconds
    day_start = cutoff - SECONDS_PER_DAY
    tree = sched.deck_due_tree()

    selected = [did for did in dict.fromkeys(int(d) for d in deck_ids) if col.decks.get(did, default=False)]
    decks = []
    for did in selected:
        dids = col.decks.deck_and_child_ids(did)
        decks.append({
            "id": did,
            "name": col.decks.name(did),
            "total_cards": _card_count(col, dids),
            "done_today": _done_today(col, dids, day_start),
            "due": _due(col, tree, did),
        })

    # Totals over the selection without counting a subdeck twice when its
    # parent is selected too.
    tops = [did for did in selected if not any(_is_ancestor(col, other, did) for other in selected if other != did)]
    all_ids = sorted({cid for did in tops for cid in col.decks.deck_and_child_ids(did)})
    total_due = {"new": 0, "learning": 0, "review": 0}
    for did in tops:
        for key, value in _due(col, tree, did).items():
            total_due[key] += value

    return {
        "version": FORMAT_VERSION,
        "addon_version": addon_version,
        "generated_at": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": {
            "today": int(sched.today),
            "cutoff": cutoff,
            "rollover_hour": int(col.get_config("rollover", 4) or 0),
        },
        "decks": decks,
        "total": {
            "total_cards": _card_count(col, all_ids),
            "done_today": _done_today(col, all_ids, day_start),
            "due": total_due,
        },
    }


def write_status(status: dict, folder: str) -> str:
    """Writes status.json into `folder` atomically and returns its path."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "status.json")
    fd, tmp = tempfile.mkstemp(prefix=".status-", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def _ids(ids: Iterable[int]) -> str:
    return "(" + ",".join(str(int(i)) for i in ids) + ")" if ids else "(0)"


def _card_count(col: Any, dids: list[int]) -> int:
    return col.db.scalar(f"select count() from cards where did in {_ids(dids)} or odid in {_ids(dids)}") or 0


def _done_today(col: Any, dids: list[int], day_start: int) -> dict:
    """Reviews since the day started, for cards in these decks.

    `reviews` counts answers (one card can be answered several times);
    `cards` counts distinct cards; `new_cards` are cards seen for the first
    time today. Reviews done in AnkiMobile or AnkiDroid appear here once
    Anki Desktop has synced them from AnkiWeb.
    """
    since = day_start * 1000
    card_filter = f"cid in (select id from cards where did in {_ids(dids)} or odid in {_ids(dids)})"
    types = _ids(STUDY_TYPES)
    rows = col.db.all(
        f"select type, count(), count(distinct cid) from revlog "
        f"where id >= ? and ease > 0 and type in {types} and {card_filter} group by type",
        since,
    )
    by_type = {t: (n, c) for t, n, c in rows}
    cards = col.db.scalar(
        f"select count(distinct cid) from revlog where id >= ? and ease > 0 and type in {types} and {card_filter}",
        since,
    ) or 0
    new_cards = col.db.scalar(
        f"select count() from (select cid, min(id) as first from revlog "
        f"where ease > 0 and type in {types} and {card_filter} group by cid) where first >= ?",
        since,
    ) or 0
    return {
        "reviews": sum(n for n, _ in by_type.values()),
        "cards": cards,
        "new_cards": new_cards,
        "learning": by_type.get(0, (0, 0))[0] + by_type.get(2, (0, 0))[0],
        "review": by_type.get(1, (0, 0))[0] + by_type.get(3, (0, 0))[0],
    }


def _due(col: Any, tree: Any, did: int) -> dict:
    """Cards still due today, after the deck's daily limits, as Anki shows them."""
    node = col.decks.find_deck_in_tree(tree, did)
    if node is None:
        return {"new": 0, "learning": 0, "review": 0}
    return {"new": int(node.new_count), "learning": int(node.learn_count), "review": int(node.review_count)}


def _is_ancestor(col: Any, ancestor: int, did: int) -> bool:
    return did != ancestor and did in col.decks.deck_and_child_ids(ancestor)
