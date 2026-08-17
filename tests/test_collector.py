from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import backend.agents.collector as collector
from backend.config import Source


def _published(hours_ago: float) -> str:
    return format_datetime(datetime.now(UTC) - timedelta(hours=hours_ago))


def test_collect_caps_items_per_source_keeping_the_most_recent(monkeypatch):
    monkeypatch.setattr(collector, "SOURCES", [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR")])
    monkeypatch.setattr(collector, "MAX_ITEMS_PER_SOURCE_PER_RUN", 2)

    class _FakeFeed:
        entries = [
            {"title": "Ancien", "link": "http://example.com/1", "published": _published(3)},
            {"title": "Récent", "link": "http://example.com/2", "published": _published(1)},
            {"title": "Milieu", "link": "http://example.com/3", "published": _published(2)},
        ]

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: _FakeFeed())

    result = collector.collect({"raw_items": [], "analyzed_items": []})

    assert [item["title"] for item in result["raw_items"]] == ["Récent", "Milieu"]


def test_collect_respects_a_source_specific_cap_override(monkeypatch):
    monkeypatch.setattr(
        collector,
        "SOURCES",
        [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR", max_per_run=1)],
    )
    monkeypatch.setattr(collector, "MAX_ITEMS_PER_SOURCE_PER_RUN", 12)

    class _FakeFeed:
        entries = [
            {"title": "Un", "link": "http://example.com/1", "published": _published(2)},
            {"title": "Deux", "link": "http://example.com/2", "published": _published(1)},
        ]

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: _FakeFeed())

    result = collector.collect({"raw_items": [], "analyzed_items": []})

    assert len(result["raw_items"]) == 1
    assert result["raw_items"][0]["title"] == "Deux"


def test_collect_parses_entries_from_configured_sources(monkeypatch):
    monkeypatch.setattr(collector, "SOURCES", [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR")])

    class _FakeFeed:
        entries = [
            {
                "title": "Titre 1",
                "link": "http://example.com/1",
                "published": "2026-01-01",
                "summary": "<p>Résumé 1</p>",
            }
        ]

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: _FakeFeed())

    result = collector.collect({"raw_items": [], "analyzed_items": []})

    assert len(result["raw_items"]) == 1
    item = result["raw_items"][0]
    assert item["source"] == "Test Source"
    assert item["theme"] == "contrats"
    assert item["country"] == "FR"
    assert item["state_affiliated"] is False
    assert item["link"] == "http://example.com/1"
    assert item["raw_text"] == "<p>Résumé 1</p>"


def test_collect_returns_no_items_when_feed_is_empty(monkeypatch):
    monkeypatch.setattr(collector, "SOURCES", [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR")])

    class _EmptyFeed:
        entries = []

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: _EmptyFeed())

    result = collector.collect({"raw_items": [], "analyzed_items": []})

    assert result["raw_items"] == []


def test_source_freshness_flags_a_source_with_no_recent_item(monkeypatch):
    # Un flux qui se parse sans erreur mais ne publie plus rien de récent (cas réel : OFAC, mort
    # ~1 an) doit ressortir comme silencieux, pas comme actif — c'est tout l'intérêt de la mesure.
    monkeypatch.setattr(
        collector,
        "SOURCES",
        [
            Source("Vivante", "http://example.com/a", "fr", "contrats", "FR"),
            Source("Morte", "http://example.com/b", "fr", "contrats", "FR"),
        ],
    )

    def _fake_parse(url):
        class _Feed:
            entries = (
                [{"title": "T", "link": "l", "published": _published(1)}]
                if url == "http://example.com/a"
                else [{"title": "Vieux", "link": "l2", "published": _published(9999)}]
            )

        return _Feed()

    monkeypatch.setattr(collector.feedparser, "parse", _fake_parse)

    result = collector.source_freshness()

    assert result == {"Vivante": 1, "Morte": 0}
