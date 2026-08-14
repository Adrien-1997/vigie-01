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


def _analyzed_item(link: str, title_fr: str, summary: str, category: str = "contrat_armement") -> dict:
    return {
        "source": "s",
        "lang": "fr",
        "country": "FR",
        "state_affiliated": False,
        "title": "t",
        "title_fr": title_fr,
        "link": link,
        "published": "",
        "category": category,
        "summary": summary,
        "citation": "c",
        "location": "",
        "confidence_score": None,
        "corroborated": None,
    }


def test_search_related_finds_items_sharing_keywords(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")

    store.record_analyzed(
        [
            _analyzed_item("a", "Rafale vendu à la Grèce", "Contrat Dassault confirmé"),
            _analyzed_item("b", "Sous-marins nucléaires australiens", "Accord AUKUS"),
        ]
    )

    results = store.search_related("Rafale Grèce Dassault", exclude_link="c")

    assert [r["title_fr"] for r in results] == ["Rafale vendu à la Grèce"]


def test_search_related_excludes_the_item_itself(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")

    store.record_analyzed([_analyzed_item("a", "Rafale vendu à la Grèce", "Contrat Dassault confirmé")])

    results = store.search_related("Rafale Grèce Dassault", exclude_link="a")

    assert results == []


def test_search_related_prunes_entries_older_than_window(tmp_path, monkeypatch):
    history_file = tmp_path / "history.json"
    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", history_file)

    old_date = (date.today() - timedelta(days=store.RELATED_ITEMS_WINDOW_DAYS + 1)).isoformat()
    store._save_analyzed(
        [
            {
                "date": old_date,
                "link": "a",
                "source": "s",
                "country": "FR",
                "category": "contrat_armement",
                "title_fr": "Rafale vendu à la Grèce",
                "summary": "Contrat Dassault confirmé",
            }
        ]
    )

    results = store.search_related("Rafale Grèce Dassault", exclude_link="z")

    assert results == []


def test_record_analyzed_is_not_visible_to_search_before_it_is_called(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")

    # Rien enregistré encore : search_related sur un historique vide ne doit rien renvoyer.
    assert store.search_related("Rafale Grèce Dassault", exclude_link="z") == []
