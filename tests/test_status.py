"""Tests the status file against a real (temporary) Anki collection.

Run with: python -m pytest tests   (needs `pip install anki pytest`)
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "minimalist_sync"))

from anki.collection import Collection  # noqa: E402

import folders  # noqa: E402
from status import build_status, write_status  # noqa: E402


@pytest.fixture
def col():
    folder = tempfile.mkdtemp()
    collection = Collection(os.path.join(folder, "collection.anki2"))
    yield collection
    collection.close()


def add_cards(col, deck_name, count):
    did = col.decks.id(deck_name)
    model = col.models.by_name("Basic")
    for i in range(count):
        note = col.new_note(model)
        note["Front"] = f"{deck_name} {i}"
        note["Back"] = "back"
        col.add_note(note, did)
    return did


def answer(col, did, times):
    """Answers `times` cards in the deck with Good."""
    from anki.scheduler.v3 import CardAnswer

    col.decks.select(did)
    for _ in range(times):
        queued = col.sched.get_queued_cards(fetch_limit=1).cards[0]
        card = col.get_card(queued.card.id)
        card.start_timer()
        col.sched.answer_card(col.sched.build_answer(card=card, states=queued.states, rating=CardAnswer.GOOD))


def test_counts_reviews_and_due(col):
    spanish = add_cards(col, "Spanish", 30)
    add_cards(col, "Other", 5)

    before = build_status(col, [spanish], "test")
    deck = before["decks"][0]
    assert deck["name"] == "Spanish"
    assert deck["total_cards"] == 30
    assert deck["done_today"]["reviews"] == 0
    assert deck["due"]["new"] == 20  # Anki's default new-card limit

    answer(col, spanish, 4)
    after = build_status(col, [spanish], "test")["decks"][0]
    assert after["done_today"]["reviews"] == 4
    assert after["done_today"]["cards"] == 4
    assert after["done_today"]["new_cards"] == 4
    assert after["due"]["new"] == 16


def test_subdecks_count_once(col):
    parent = add_cards(col, "Lang", 3)
    child = add_cards(col, "Lang::Verbs", 4)
    status = build_status(col, [parent, child], "test")
    assert status["decks"][0]["total_cards"] == 7  # the parent includes its subdeck
    assert status["total"]["total_cards"] == 7  # not 11
    answer(col, child, 2)
    status = build_status(col, [parent, child], "test")
    assert status["total"]["done_today"]["reviews"] == 2


def test_day_and_file(col, tmp_path):
    did = add_cards(col, "D", 1)
    status = build_status(col, [did], "1.0.0", now=1_700_000_000)
    assert status["version"] == 1
    assert status["day"]["cutoff"] > 0
    assert status["generated_at"] == "2023-11-14T22:13:20Z"
    path = write_status(status, str(tmp_path / "AnkiSync"))
    with open(path, encoding="utf-8") as f:
        assert json.load(f)["decks"][0]["id"] == did
    # No temporary files left behind.
    assert os.listdir(tmp_path / "AnkiSync") == ["status.json"]


def test_unknown_decks_are_skipped(col):
    did = add_cards(col, "D", 1)
    assert [d["id"] for d in build_status(col, [did, 999999], "t")["decks"]] == [did]


def test_folder_detection(tmp_path):
    home = str(tmp_path)
    assert folders.sync_folder(None, home, "darwin") is None
    container = tmp_path / "Library" / "Mobile Documents" / folders.CONTAINER / "Documents"
    container.mkdir(parents=True)
    assert folders.sync_folder(None, home, "darwin") == str(container / "AnkiSync")
    assert folders.sync_folder("/picked", home, "darwin") == "/picked"
    assert folders.sync_folder(None, home, "linux") is None
