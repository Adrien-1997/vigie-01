"""Nœud mémoire : dédoublonnage court terme (README architecture, docs/cadrage.md §10 V1) et
historique des items analysés pour le recoupement de l'agent vérificateur (§10 V2, première tranche
— cf. backend/agents/verifier.py).

Stockage local fichier pour V1 : c'est une mémoire "courte" (fenêtre glissante), pas l'historique
interrogeable prévu en V3. Placeholder documenté, comme backend/guardrails.py : à remplacer par
Firestore si plusieurs instances doivent un jour partager cet état (déploiement Cloud Run, cf.
NOTES.private.md sur le séquencement GCP).
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

from backend.state import AnalyzedItem, RawItem, VeilleState

_STORE_FILE = Path(__file__).parent / ".seen_items.json"
DEDUP_WINDOW_DAYS = 7

_ANALYZED_STORE_FILE = Path(__file__).parent / ".analyzed_history.json"
# Plus long que DEDUP_WINDOW_DAYS : le recoupement (a-t-on déjà vu ce dossier ?) bénéficie de plus
# d'historique que le simple dédoublonnage d'items identiques.
RELATED_ITEMS_WINDOW_DAYS = 30


def _load() -> dict[str, str]:
    if not _STORE_FILE.exists():
        return {}
    return json.loads(_STORE_FILE.read_text(encoding="utf-8"))


def _save(seen: dict[str, str]) -> None:
    _STORE_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune(seen: dict[str, str]) -> dict[str, str]:
    cutoff = date.today() - timedelta(days=DEDUP_WINDOW_DAYS)
    return {link: seen_date for link, seen_date in seen.items() if date.fromisoformat(seen_date) >= cutoff}


def deduplicate(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : retire les raw_items déjà vus (clé = link), avant l'appel LLM de l'analyste.

    Placé entre collect et analyze plutôt qu'après analyze : un item déjà vu ne doit pas seulement
    être exclu du digest, il ne doit même pas être ré-analysé — sinon le budget LLM (§8) est
    consommé chaque jour sur des items déjà traités la veille.
    """
    seen = _prune(_load())
    today = date.today().isoformat()

    new_items: list[RawItem] = []
    for item in state["raw_items"]:
        if item["link"] in seen:
            continue
        new_items.append(item)
        seen[item["link"]] = today

    _save(seen)
    return {"raw_items": new_items}


def _load_analyzed() -> list[dict]:
    if not _ANALYZED_STORE_FILE.exists():
        return []
    return json.loads(_ANALYZED_STORE_FILE.read_text(encoding="utf-8"))


def _save_analyzed(records: list[dict]) -> None:
    _ANALYZED_STORE_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _prune_analyzed(records: list[dict]) -> list[dict]:
    cutoff = date.today() - timedelta(days=RELATED_ITEMS_WINDOW_DAYS)
    return [r for r in records if date.fromisoformat(r["date"]) >= cutoff]


def record_analyzed(items: list[AnalyzedItem]) -> None:
    """Ajoute les items analysés du run courant à l'historique de recoupement (§10 V2).

    Appelé après analyze() mais avant verify(), pour que search_related() ne voie jamais les items
    du run en cours — seulement l'historique des runs précédents (pas de faux-recoupement intra-run).
    """
    today = date.today().isoformat()
    records = _prune_analyzed(_load_analyzed())
    records.extend(
        {
            "date": today,
            "link": item["link"],
            "source": item["source"],
            "country": item["country"],
            "category": item["category"],
            "title_fr": item["title_fr"],
            "summary": item["summary"],
        }
        for item in items
    )
    _save_analyzed(records)


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.findall(r"\w+", text.lower()) if len(tok) > 2}


def search_related(query: str, exclude_link: str, limit: int = 5) -> list[dict]:
    """Recherche naïve par chevauchement de mots-clés dans l'historique (§10 V2, backend/agents/verifier.py).

    Pas d'embeddings/vector store : cohérent avec la convention "stockage fichier local comme
    placeholder documenté avant Firestore" déjà en place pour ce module.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[tuple[int, dict]] = []
    for record in _prune_analyzed(_load_analyzed()):
        if record["link"] == exclude_link:
            continue
        record_tokens = _tokenize(record["title_fr"]) | _tokenize(record["summary"])
        score = len(query_tokens & record_tokens)
        if score > 0:
            scored.append((score, record))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "date": record["date"],
            "source": record["source"],
            "country": record["country"],
            "category": record["category"],
            "title_fr": record["title_fr"],
        }
        for _, record in scored[:limit]
    ]
