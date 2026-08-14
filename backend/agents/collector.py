"""Nœud collecteur : récupère et normalise les entrées des sources RSS configurées."""

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser

from backend.config import COLLECTION_LOOKBACK_HOURS, SOURCES, Source
from backend.state import RawItem, VeilleState


def _parse_entry(entry, source: Source) -> RawItem:
    return RawItem(
        source=source.name,
        theme=source.theme,
        lang=source.lang,
        country=source.country,
        state_affiliated=source.state_affiliated,
        title=entry.get("title", ""),
        link=entry.get("link", ""),
        published=entry.get("published", ""),
        raw_text=entry.get("summary", ""),
    )


def _is_recent(item: RawItem, cutoff: datetime) -> bool:
    """Écarte les items trop anciens (cf. COLLECTION_LOOKBACK_HOURS). Conserve les items sans
    date parsable — le garde-fou MAX_LLM_CALLS_PER_DAY reste le filet de sécurité final."""
    if not item["published"]:
        return True
    try:
        published = parsedate_to_datetime(item["published"])
    except (TypeError, ValueError):
        return True
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    return published >= cutoff


def collect(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : peuple raw_items à partir de toutes les sources configurées,
    en écartant les items plus anciens que COLLECTION_LOOKBACK_HOURS."""
    cutoff = datetime.now(UTC) - timedelta(hours=COLLECTION_LOOKBACK_HOURS)
    raw_items: list[RawItem] = []
    for source in SOURCES:
        feed = feedparser.parse(source.url)
        raw_items.extend(_parse_entry(entry, source) for entry in feed.entries)
    return {"raw_items": [item for item in raw_items if _is_recent(item, cutoff)]}
