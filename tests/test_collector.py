import backend.agents.collector as collector
from backend.config import Source


def test_collect_parses_entries_from_configured_sources(monkeypatch):
    monkeypatch.setattr(
        collector, "SOURCES", [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR")]
    )

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
    monkeypatch.setattr(
        collector, "SOURCES", [Source("Test Source", "http://example.com/rss", "fr", "contrats", "FR")]
    )

    class _EmptyFeed:
        entries = []

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: _EmptyFeed())

    result = collector.collect({"raw_items": [], "analyzed_items": []})

    assert result["raw_items"] == []
