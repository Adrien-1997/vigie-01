"""Nœud collecteur : récupère et normalise les entrées des sources RSS configurées."""

import feedparser

from backend.config import Source, SOURCES
from backend.state import RawItem, VeilleState


def _parse_entry(entry, source: Source) -> RawItem:
    return RawItem(
        source=source.name,
        theme=source.theme,
        lang=source.lang,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        published=entry.get("published", ""),
        raw_text=entry.get("summary", ""),
    )


def collect(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : peuple raw_items à partir de toutes les sources configurées."""
    raw_items: list[RawItem] = []
    for source in SOURCES:
        feed = feedparser.parse(source.url)
        raw_items.extend(_parse_entry(entry, source) for entry in feed.entries)
    return {"raw_items": raw_items}
