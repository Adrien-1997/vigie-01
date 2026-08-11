from datetime import date, timedelta

import backend.memory.store as store


def _item(link: str) -> dict:
    return {
        "source": "s",
        "theme": "t",
        "lang": "fr",
        "title": "titre",
        "link": link,
        "published": "",
        "raw_text": "",
    }


def test_deduplicate_filters_items_already_seen(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_STORE_FILE", tmp_path / "seen.json")

    first = store.deduplicate({"raw_items": [_item("a"), _item("b")], "analyzed_items": []})
    assert [i["link"] for i in first["raw_items"]] == ["a", "b"]

    second = store.deduplicate({"raw_items": [_item("a"), _item("c")], "analyzed_items": []})
    assert [i["link"] for i in second["raw_items"]] == ["c"]


def test_prune_drops_entries_older_than_dedup_window():
    old_date = (date.today() - timedelta(days=store.DEDUP_WINDOW_DAYS + 1)).isoformat()
    recent_date = date.today().isoformat()

    pruned = store._prune({"stale-link": old_date, "fresh-link": recent_date})

    assert pruned == {"fresh-link": recent_date}
