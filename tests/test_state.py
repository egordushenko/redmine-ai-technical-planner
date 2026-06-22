from pathlib import Path

from app.storage.state import StateStore


def test_mark_processed(tmp_path: Path):
    store = StateStore(tmp_path / "state.sqlite3")

    store.mark_processed(1, "2026-06-22T10:00:00Z", "demo", "hash")

    assert store.is_already_processed(1, "2026-06-22T10:00:00Z")


def test_skip_already_processed_issue(tmp_path: Path):
    store = StateStore(tmp_path / "state.sqlite3")
    store.mark_processed(1, "2026-06-22T10:00:00Z", "demo", "hash")

    assert store.is_already_processed(1, "2026-06-22T10:00:00Z")
    assert not store.is_already_processed(1, "2026-06-22T11:00:00Z")
